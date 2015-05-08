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
__version__     = '0.2'


# ------------------------------------------------------------
# imports

import argparse
import datetime
import email
import email.utils
import getpass
import imaplib
import logging
import re
import sys


# ------------------------------------------------------------
# code


def imap_clean(connection, top_mailbox, dry_run):

    """Delete all empty mailboxes with no childs under the given mailbox"""

    logging.info('cleaning mailbox: %s' % top_mailbox)

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
                    logging.info('---- DELETE ---- mailbox %s has %s mails' % (mailbox_name, mail_count))
                    if not dry_run:
                        connection.delete(mailbox_name)
                    mailbox_deleted = True


def imap_connect(host, port, user, password):

    """Connect to the IMAP server"""

    logging.info('connecting server %s:%d' % (host, port))
    try:
        con = imaplib.IMAP4_SSL(host, port)
    except Exception as err:
        logging.error('connecting server %s:%d failed: %s' % (host, port, str(err)))
        sys.exit(1)

    logging.info('server %s:%d connected' % (host, port))
    auth_method = []
    try:
        
        # check for authentication methods
        res, capabilities = con.capability()
        logging.debug('server capabilities:')
        for cap in capabilities[0].split():
            c = cap.decode('UTF-8')
            logging.debug('\t%s' % c)
            m = re.match('AUTH=(.*)', c)
            if m is not None and len(m.groups()) == 1:
                auth_method.append(m.groups()[0])
        
        # go for suitable authentication
        for a in auth_method:
            logging.debug('found authentication: %s' % a)
        if 'CRAM-MD5' in auth_method:
            res, data = con.login_cram_md5(user, password)
        else:
            res, data = con.login(user, password)

    except Exception as err:
        logging.error('logging into server %s:%d failed: %s' % (host, port, str(err)))
        sys.exit(1)

    logging.info('user %s logged in' % user)

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
    logging.info('disconnecting from server')
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

    logging.info('searching for old mails in mailbox: %s' % mailbox)
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
                logging.warn('failed to decode mailid %s in mailbox %s - dropping' % (mail_id, mb))
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
            logging.debug(debug_string)

    # move mails
    for y in mail_ids_to_move:
        archive_mailbox = 'Archives' + delimiter + y + delimiter + mb
        logging.info('moving %d mails to %s' % (len(mail_ids_to_move[y]), archive_mailbox))
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
                logging.info('scanning for old mails in mailbox: %s' % mailbox)
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
                            logging.warn('failed to decode mailid %s in mailbox %s - dropping' % (mail_id, mailbox))
                            continue
                        
                        mail_year = email.utils.parsedate(mail['Date'])[0]
                        move_mail = mail_year < mail_date_max.year
                        info_string = 'MailID: %s - Date: %s - From: %s - To: %s - Subject: %s' \
                                % (mail_id, mail['Date'], mail['From'], mail['To'], mail['Subject'])
                        if move_mail:
                            info_string = '---- MOVE TO ARCHIVE ---- ' + info_string
                        else:
                            info_string = '                          ' + info_string
                        logging.info(info_string)

    except Exception as err:
        logging.error('scanning on failed: %s' % str(err))
 

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
        logging.error('working on mail failed: %s' % str(err))
       

def main():
    
    """IMAP-Archiver start"""

    # parse arguments
    parser = argparse.ArgumentParser(description = 'IMAP-Archiver')
    parser.add_argument('-t', '--host', dest='host', type=str, 
            help='IMAP host name to connect.')
    parser.add_argument('-p', '--port', dest='port', type=int, default=993, 
            help='IMAP host port to connect.')
    parser.add_argument('-u', '--user', dest='user', type=str, 
            help='User account to log in.')
    parser.add_argument('-k', '--password', dest='password', type=str, 
            help='User password to log in. If not specified a prompt will show up.')
    parser.add_argument('-d', '--dry-run', dest='dry_run', action='store_const', const=True, default=False, 
            help='Dry run: do not actually make any steps but act as if; decrease loglevel for verbosity.')
    parser.add_argument('-l', '--logging', dest='loglevel', type=int, default=30, 
            help='Set logging level (see python logging module). Default is WARNING: 30 - the lower the more output.')
    parser.add_argument('-v', '--version', dest='version', action='store_const', const=True, default=False, 
            help='Show version information and exit.')
    parser.add_argument('--only-move', dest='only_move', action='store_const', const=True, default=False, 
            help='Only move mails to the archive. Do not clean empty mail directories.')
    parser.add_argument('--only-clean', dest='only_clean', action='store_const', const=True, default=False, 
            help='Only clean empty mail directores. Do not move old mails to the archives.')
    parser.add_argument('--only-scan', dest='only_scan', action='store_const', const=True, default=False, 
            help='Only scan all mailboxes.')
    args = parser.parse_args()

    # do not proceed if only version is asked
    if args.version:
        show_version()
        sys.exit(0)

    # fix logging
    logging.getLogger(None).setLevel(args.loglevel)

    do_move = True
    do_clean = True
    do_scan = False

    # check arguments
    if not args.host:
        logging.error('no host given. type \'-h\' for help.')
        sys.exit(1)

    if not (0 <= args.port <= 65535):
        logging.error('port number invalid. type \'-h\' for help.')
        sys.exit(1)

    if not args.user:
        logging.error('no user given. type \'-h\' for help.')
        sys.exit(1)

    if not args.password:
        args.password = getpass.getpass('no user password given. plase enter password: ')
        if not args.password:
            logging.error('no user password given. type \'-h\' for help.')
            sys.exit(1)

    only_options = 0
    if args.only_move: only_options = only_options + 1
    if args.only_clean: only_options = only_options + 1
    if args.only_scan: only_options = only_options + 1
    if only_options > 1:
        logging.error('several --only-* options specified, please chose exactly one.')
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


def show_version():

    """Show the version"""

    print('IMAP-Archiver V{0}'.format(__version__))
    print(__author__)
    print(__copyright__)
    print('Licensed under the terms of {0} - please read "{1}"'.format(__license__, __licenseurl__))


if __name__ == "__main__":
    main()

