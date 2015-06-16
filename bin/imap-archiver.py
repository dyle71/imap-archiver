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


def imap_create_mailbox(connection, delimiter, mailbox):

    """Create a mailbox name recurisvely"""
    m = ''
    for mailbox_part in mailbox.split(delimiter):
        connection.create('"' + m + mailbox_part + '"')
        connection.subscribe('"' + m + mailbox_part + '"')
        m = m + mailbox_part + delimiter


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


def connect(connection_params):

    """Connect to the IMAP server
    
    @param  connection_params   a dict holding connection details
    @return connection object (imaplib.IMAP_SSL)
    """

    try:
        if 'port' in connection_params:
            con = imaplib.IMAP4_SSL(connection_params['host'], connection_params['port'])
        else:
            con = imaplib.IMAP4_SSL(connection_params['host'])

    except Exception as e:
        if 'port' in connection_params:
            print('failed to connect %s:%d' % (connection_params['host'], connection_params['port']))
        else:
            print('failed to connect %s' % connection_params['host'])
        print(e)
        sys.exit(1)

    auth_method = []
    try:

        # collect authentication methods and login
        res, capabilities = con.capability()
        for cap in capabilities[0].split():
            c = cap.decode('UTF-8')
            m = re.match('AUTH=(.*)', c)
            if m is not None and len(m.groups()) == 1:
                auth_method.append(m.groups()[0])
        
        if 'CRAM-MD5' in auth_method:
            res, data = con.login_cram_md5(connection_params['user'], connection_params['password'])
        else:
            res, data = con.login(connection_params['user'], connection_params['password'])

    except Exception as e:
        print('failed to login')
        print(e)
        sys.exit(1)

    print('%s logged in' % connection_params['user'])

    return con


def inspect_mailbox(connection, mailbox):

    """Inspect a mailbox folder and return mail-lists

    @param  connection      IMAP connection
    @param  mailbox         mailbox name
    @return mails_all       all mails
    @return mails_seen      seen mails
    @return mails_per_year  seen mails per year
    """

    connection.select(mailbox)
    res, [mails_all] = connection.search(None, 'ALL')
    res, [mails_seen] = connection.search(None, 'SEEN')
    mails_all = mails_all.decode('UTF-8').split(' ')
    if len(mails_all) > 0 and mails_all[0] == '': mails_all.pop()
    mails_seen = mails_seen.decode('UTF-8').split(' ')
    if len(mails_seen) > 0 and mails_seen[0] == '': mails_seen.pop()
    mails_per_year = {}

    if len(mails_seen) > 0:

        res, header_data = connection.fetch(','.join(mails_seen), '(BODY.PEEK[HEADER])')
       
        pattern_mailid = re.compile('(?P<msgid>.*?) .*')
        for h in header_data:
            if isinstance(h, tuple):

                mail_id = pattern_mailid.match(h[0].decode('UTF-8')).groups()[0]
                mail_header = h[1].split(b'\r\n')
                for mh in mail_header:
                    if mh.startswith(b'Date:'):

                        mail_year = email.utils.parsedate(str(mh)[8:])[0]
                        if mail_year not in mails_per_year:
                            mails_per_year[mail_year] = []
                        mails_per_year[mail_year].append(mail_id)

    return mails_all, mails_seen, mails_per_year


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
    parser_scan.add_argument('-l', '--list-boxes-only', dest='list_boxes_only', action='store_const', 
            const=True, default=False, help='Only list mailbox, do not examine each mail therein.')
    parser_scan.set_defaults(func = scan)

    parser_move = subparser.add_parser('move', help='move old emails to target mailbox')
    parser_move.add_argument('connect_url', metavar='CONNECT-URL', 
            help='Connection details. Syntax is USER[:PASS]@HOST[:PORT] like \'john@example.com\' or \
                \'bob:mysecret@mail-server.com:143\'. If password PASS is omitted you are asked for it.')
    parser_move.add_argument('mailbox_from', metavar='MAILBOX_FROM', 
            help='mailbox to start moving from.')
    parser_move.add_argument('mailbox_to', metavar='MAILBOX_TO', 
            help='mailbox to move to.')
    parser_move.set_defaults(func = move)

    parser_clean = subparser.add_parser('clean', help='delete empty mailboxes with no mail or child mailbox.')
    parser_clean.add_argument('connect_url', metavar='CONNECT-URL', 
            help='Connection details. Syntax is USER[:PASS]@HOST[:PORT] like \'john@example.com\' or \
                \'bob:mysecret@mail-server.com:143\'. If password PASS is omitted you are asked for it.')
    parser_clean.add_argument('mailbox', metavar='MAILBOX',
            help='Top mailbox to start cleaning.')
    parser_clean.set_defaults(func = clean)

    args = parser.parse_args()

    if 'func' not in dir(args):
        parser.print_help()
        sys.exit(1)
        
    if args.version:
        show_version()
        sys.exit(0)

    args.func(args)


def move(args):

    """Move old mails from one mailsbox to another, keeping the folder structure"""
    con = connect(parse_connection(args.connect_url))
    res, mailbox_list = con.list(args.mailbox_from)

    pattern = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')
    for mailbox_list_item in mailbox_list:
        if mailbox_list_item is None:
            continue

        flags, delimiter, mailbox = pattern.match(mailbox_list_item.decode('UTF-8')).groups()
        mails_all, mails_seen, mails_old = inspect_mailbox(con, mailbox)
        
    try: 
        con.close()
        con.logout()
    except:
        pass
    pass


def parse_connection(connection_string):

    """Parse and get connection params 
    
    @param  connection_string   string of USER[:PASSWORD]@HOST[:PORT]
    @return connection detail dict
    """

    # worst case scenario: "alice@somehost.domain:password@someotherhost.otherdomain:7892"
    con = {}
    parts_at = connection_string.split('@')
    if len(parts_at) == 1:
        print('malformed connection string - type --help for help')
        sys.exit(1)

    host_and_port = parts_at[-1:][0]
    if len(parts_at) > 2:
        user_and_password = '@'.join(parts_at[:-1])
    else:
        user_and_password = parts_at[0] 

    try:
        if host_and_port.find(':') == -1:
            con['host'] = host_and_port
        else:
            con['host'] = host_and_port.split(':')[:-1][0]
            con['port'] = int(host_and_port.split(':')[-1:][0])

    except Exception as e:
        print('failed to parse mailserver part')
        print(e)
        sys.exit(1)

    if len(con['host']) == 0:
        print('cannot deduce host')
        sys.exit(1)

    try:
        if user_and_password.find(':') == -1:
            con['user'] = user_and_password
        else:
            con['user'] = user_and_password.split(':')[:-1][0]
            con['password'] = user_and_password.split(':')[-1:][0]
    except Exception as e:
        print('failed to parse credential part')
        print(e)
        sys.exit(1)

    if len(con['user']) == 0:
        print('cannot deduce user')
        sys.exit(1)

    if 'password' not in con:
        con['password'] = getpass.getpass(
                'no user password given. plase enter password for user \'%s\': ' % con['user'])

    return con


def scan(args):

    """Scan IMAP folders"""
    con = connect(parse_connection(args.connect_url))
    if args.mailbox is None:
        res, mailbox_list = con.list()
    else:
        res, mailbox_list = con.list(args.mailbox)

    mail_date_max = datetime.date(datetime.date.today().year - 1, 1, 1).year

    pattern = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')
    for mailbox_list_item in mailbox_list:
        if mailbox_list_item is None:
            continue

        flags, delimiter, mailbox = pattern.match(mailbox_list_item.decode('UTF-8')).groups()

        if not args.list_boxes_only:
            mails_all, mails_seen, mails_old = inspect_mailbox(con, mailbox)
            old_mails = 0
            for y in mails_old:
                if y < mail_date_max:
                    old_mails = old_mails + len(mails_old[y])

            print("mailbox: %s - ALL: %d, SEEN: %d, OLD: %d" % (mailbox, len(mails_all), len(mails_seen), old_mails))

        else:
            print("mailbox: %s" % mailbox)
        
    try: 
        con.close()
        con.logout()
    except:
        pass


def show_version():

    """Show the version"""

    print('IMAP-Archiver V{0}'.format(__version__))
    print(__author__)
    print(__copyright__)
    print('Licensed under the terms of {0} - please read "{1}"'.format(__license__, __licenseurl__))


if __name__ == "__main__":
    main()

