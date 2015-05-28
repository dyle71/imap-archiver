#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ------------------------------------------------------------
# imap-archiver.py
# 
# startup for IMAP Archiver
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# ------------------------------------------------------------

# thanks to a lot of inspiration from
# http://pymotw.com/2/imaplib/

# metadata
__author__      = 'Oliver Maurhart <dyle@dyle.org>'
__copyright__   = 'Copyright 2015 Oliver Maurhart'
__license__     = 'GPL v3'
__licenseurl__  = 'http://www.gnu.org/licenses/gpl.html'
__title__       = 'imap-archiver'
__version__     = '0.3'


# ------------------------------------------------------------
# imports

import argparse
import datetime
import email
import email.utils
import getpass
import imaplib
import re
import sys


# ------------------------------------------------------------
# code


def imap_clean(connection, top_mailbox, dry_run):

    """Delete all empty mailboxes with no childs under the given mailbox"""

    pattern = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')
    mailbox_deleted = True
    while mailbox_deleted:

        mailbox_deleted = False

        # get all mailboxes and subs 
        for top_mb in top_mailbox:
            res, mailbox_list = connection.list(top_mb)
            for i in mailbox_list:

                if i is None:
                    continue

                flags, delimiter, mailbox_name = pattern.match(i.decode('UTF-8')).groups()

                # do not work on top level mailbox itself
                if delimiter not in mailbox_name:
                    continue

                # do not delete intermediate nodes
                if flags == '\\HasChildren':
                    continue

                # select mailbox and see how many mails are in there
                res, [mail_count] = connection.select(mailbox_name)
                if int(mail_count) == 0:
                    if not dry_run:
                        connection.delete(mailbox_name)
                    mailbox_deleted = True


def imap_connect(host, port, user, password):

    """Connect to the IMAP server"""

    try:
        con = imaplib.IMAP4_SSL(host, port)
    except Exception as err:
        sys.exit(1)

    auth_method = []
    try:
        
        # check for authentication methods
        res, capabilities = con.capability()
        for cap in capabilities[0].split():
            c = cap.decode('UTF-8')
            m = re.match('AUTH=(.*)', c)
            if m is not None and len(m.groups()) == 1:
                auth_method.append(m.groups()[0])
        
        # go for suitable authentication
        if 'CRAM-MD5' in auth_method:
            res, data = con.login_cram_md5(user, password)
        else:
            res, data = con.login(user, password)

    except Exception as err:
        sys.exit(1)


    return con


def imap_create_mailbox(connection, delimiter, mailbox):

    """Create a mailbox name recurisvely"""
    m = ''
    for mailbox_part in mailbox.split(delimiter):
        connection.create('"' + m + mailbox_part + '"')
        connection.subscribe('"' + m + mailbox_part + '"')
        m = m + mailbox_part + delimiter


def imap_disconnect(connection):

    """Disconnect from the IMAP server"""
    try:
        connection.close()
        connection.logout()
    except:
        pass


def imap_move(connection, mailbox, delimiter, dry_run):

    """Fetch emails from the mailbox and move them"""

    # clean up mailbox name
    mb = mailbox
    if mb.endswith('"'): mb = mb[:-1]
    if mb.startswith('"'): mb = mb[1:]
    if mb.lower() == 'inbox':
        # ignore all mails in inbox
        return

    connection.select(mailbox)

    # pick all read emails
    res, [mail_ids] = connection.search(None, 'SEEN')
    if mail_ids is None or len(mail_ids) == 0:
        # no emails
        return

    mail_ids = mail_ids.decode('UTF-8')
    mail_ids = ','.join(mail_ids.split(' '))
    mail_ids_to_move = {}
    mail_date_max = datetime.date(datetime.date.today().year - 1, 1, 1)

    # get all header data and check date
    res, header_data = connection.fetch(mail_ids, '(BODY.PEEK[HEADER])')
    pattern_mailid = re.compile('(?P<msgid>.*?) .*')
    for h in header_data:
        if isinstance(h, tuple):

            mail_id = pattern_mailid.match(h[0].decode('UTF-8')).groups()[0]
            try:
                mail = email.message_from_string(h[1].decode('UTF-8'))
            except Exception as e:
                continue
            
            mail_year = email.utils.parsedate(mail['Date'])[0]
            move_mail = mail_year < mail_date_max.year
            debug_string = 'MailID: %s - Date: %s - From: %s - To: %s - Subject: %s' \
                    % (mail_id, mail['Date'], mail['From'], mail['To'], mail['Subject'])
            if move_mail:
                debug_string = '---- MOVE TO ARCHIVE ---- ' + debug_string
                if mail_year not in mail_ids_to_move: 
                    mail_ids_to_move[mail_year] = []
                mail_ids_to_move[mail_year].append(mail_id)
            else:
                debug_string = '                          ' + debug_string

    # move mails
    for y in mail_ids_to_move:
        archive_mailbox = 'Archives' + delimiter + y + delimiter + mb
        if not dry_run:
            imap_create_mailbox(connection, delimiter, archive_mailbox)
            mail_ids = ','.join(mail_ids_to_move[y])
            connection.copy(mail_ids, '"' + archive_mailbox + '"')
            connection.store(mail_ids, '+FLAGS', r'(\Deleted)')

    if not dry_run:
        connection.expunge()

    connection.close()


def imap_scan(connection, top_mailbox ):

    """Scan all mailboxes"""

    try:

        pattern = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')

        # get all mailboxes and subs 
        for top_mb in top_mailbox:
            res, mailbox_list = connection.list(top_mb)
            for i in mailbox_list:
                if i is None:
                    continue

                flags, delimiter, mailbox = pattern.match(i.decode('UTF-8')).groups()
                connection.select(mailbox)

                # pick all read emails
                res, [mail_ids] = connection.search(None, 'SEEN')
                if mail_ids is None or len(mail_ids) == 0:
                    # no emails
                    return

                mail_ids = mail_ids.decode('UTF-8')
                mail_ids = ','.join(mail_ids.split(' '))
                mail_date_max = datetime.date(datetime.date.today().year - 1, 1, 1)

                # get all header data and check date
                res, header_data = connection.fetch(mail_ids, '(BODY.PEEK[HEADER])')
                pattern_mailid = re.compile('(?P<msgid>.*?) .*')
                for h in header_data:
                    if isinstance(h, tuple):

                        mail_id = pattern_mailid.match(h[0].decode('UTF-8')).groups()[0]
                        try:
                            mail = email.message_from_string(h[1].decode('UTF-8'))
                        except Exception as e:
                            continue
                        
                        mail_year = email.utils.parsedate(mail['Date'])[0]
                        move_mail = mail_year < mail_date_max.year
                        info_string = 'MailID: %s - Date: %s - From: %s - To: %s - Subject: %s' \
                                % (mail_id, mail['Date'], mail['From'], mail['To'], mail['Subject'])
                        if move_mail:
                            info_string = '---- MOVE TO ARCHIVE ---- ' + info_string
                        else:
                            info_string = '                          ' + info_string

    except Exception as err:
        pass
 

def imap_work(connection, top_mailbox, dry_run):

    """Do the actual work on the IMAP server"""
    try:

        pattern = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')

        # get all mailboxes and subs 
        for top_mb in top_mailbox:
            res, mailbox_list = connection.list(top_mb)
            for i in mailbox_list:
                if i is None:
                    continue
                flags, delimiter, mailbox_name = pattern.match(i.decode('UTF-8')).groups()
                imap_move(connection, mailbox_name, delimiter, dry_run)

    except Exception as err:
        pass       














def clean(args):

    """Clean empty leaf nodes in the IMAP folder structure"""
    print('---> in clean <---')
    pass


def main():
    
    """IMAP-Archiver start"""

    # parse arguments
    parser = argparse.ArgumentParser(description = 'IMAP-Archiver')

    parser.add_argument('-d', '--dry-run', dest='dry_run', action='store_const', const=True, default=False, 
            help='Dry run: do not actually make any steps but act as if.')
    parser.add_argument('-v', '--version', dest='version', action='store_const', const=True, default=False, 
            help='Show version information and exit.')

    subparser = parser.add_subparsers(help='sub-commands')

    parser_scan = subparser.add_parser('scan', help='scan IMAP folders')
    parser_scan.add_argument('connect_url', metavar='CONNECT-URL', 
            help='Connection details. Syntax is USER[:PASS]@HOST[:PORT] like \'john@example.com\' or \
                \'bob:mysecret@mail-server.com:143\'. If password PASS is omitted you are asked for it.')
    parser_scan.add_argument('-m', '--mailbox', 
            help='Top mailbox to start scanning.')
    parser_scan.set_defaults(func = scan)

    parser_move = subparser.add_parser('move', help='move old emails to target mailbox')
    parser_move.add_argument('connect_url', metavar='CONNECT-URL', 
            help='Connection details. Syntax is USER[:PASS]@HOST[:PORT] like \'john@example.com\' or \
                \'bob:mysecret@mail-server.com:143\'. If password PASS is omitted you are asked for it.')
    parser_move.set_defaults(func = move)

    parser_clean = subparser.add_parser('clean', help='delete empty mailboxes with no mail or child mailbox.')
    parser_clean.add_argument('connect_url', metavar='CONNECT-URL', 
            help='Connection details. Syntax is USER[:PASS]@HOST[:PORT] like \'john@example.com\' or \
                \'bob:mysecret@mail-server.com:143\'. If password PASS is omitted you are asked for it.')
    parser_clean.add_argument('mailbox', metavar='MAILBOX',
            help='Top mailbox to start cleaning.')
    parser_clean.set_defaults(func = clean)

    args = parser.parse_args()

    # do not proceed if only version is asked
    if args.version:
        show_version()
        sys.exit(0)

    # call subcommand
    args.func(args)

    sys.exit(1)






    do_move = True
    do_clean = True
    do_scan = False

    # check arguments
    if not args.host:
        sys.exit(1)

    if not (0 <= args.port <= 65535):
        sys.exit(1)

    if not args.user:
        sys.exit(1)

    if not args.password:
        args.password = getpass.getpass('no user password given. plase enter password: ')
        if not args.password:
            sys.exit(1)

    only_options = 0
    if args.only_move: only_options = only_options + 1
    if args.only_clean: only_options = only_options + 1
    if args.only_scan: only_options = only_options + 1
    if only_options > 1:
        sys.exit(1)

    if args.only_move:
        do_move = True
        do_clean = False
        do_scan = False

    if args.only_clean:
        do_move = False
        do_clean = True
        do_scan = False

    if args.only_scan:
        do_move = False
        do_clean = False
        do_scan = True

    # work
    top_mailbox = ['Inbox', 'Sent']
    con = imap_connect(args.host, args.port, args.user, args.password)
    if do_move:
        imap_work(con, top_mailbox, args.dry_run)
    if do_clean:
        imap_clean(con, top_mailbox, args.dry_run)
    if do_scan:
        imap_scan(con, top_mailbox)

    # ... and out
    imap_disconnect(con)


def move(args):

    """Move old mails from one mailsbox to another, keeping the folder structure"""
    print('---> in move <---')
    pass


def parse_connection(connection_string):

    """Parse and get connection params: USER[:PASSWORD]@HOST[:PORT]"""

    c = {}
    parts_at = connection_string.split('@')
    host_and_port = parts_at[-1:][0]
    if len(parts_at) > 2:
        user_and_password = '@'.join(parts_at[:-1])
    else:
        user_and_password = parts_at[0] 

    try:
        if host_and_port.find(':') == -1:
            c['host'] = host_and_port
        else:
            c['host'] = host_and_port.split(':')[:-1][0]
            c['port'] = int(host_and_port.split(':')[-1:][0])
    except Exception as e:
        print('failed to parse mailserver part')
        print(e)
        sys.exit(1)

    if 'host' not in c:
        print('cannot deduce mailserver')
        sys.exit(1)

    try:
        if user_and_password.find(':') == -1:
            c['user'] = user_and_password
        else:
            c['user'] = user_and_password.split(':')[:-1][0]
            c['password'] = user_and_password.split(':')[-1:][0]
    except Exception as e:
        print('failed to parse credential part')
        print(e)
        sys.exit(1)

    if 'user' not in c:
        print('cannot deduce user')
        sys.exit(1)

    if 'password' not in c:
        c['password'] = getpass.getpass('no user password given. plase enter password for user %s: ' % c['user'])

    return c


def scan(args):

    """Scan IMAP fodlers"""
    con_param = parse_connection(args.connect_url)
    print(con_param)


def show_version():

    """Show the version"""

    print('IMAP-Archiver V{0}'.format(__version__))
    print(__author__)
    print(__copyright__)
    print('Licensed under the terms of {0} - please read "{1}"'.format(__license__, __licenseurl__))


if __name__ == "__main__":
    main()

