#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ------------------------------------------------------------
# imaparchiver.py
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
__copyright__   = 'Copyright 2015-2017 Oliver Maurhart'
__license__     = 'GPL v3'
__licenseurl__  = 'http://www.gnu.org/licenses/gpl.html'
__title__       = 'imaparchiver'
__version__     = '0.5.0'


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


def clean(args):

    """Clean empty leaf nodes in the IMAP folder structure.

    :param dict args:   argparse.Namespace instance
    """

    con = connect(parse_connection(args.connect_url, args.verbose), args.verbose)

    pattern = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')

    res, mailbox_list = con.list(args.mailbox)
    for i in mailbox_list:

        if i is None:
            continue

        flags, delimiter, mailbox_name = pattern.match(i.decode('UTF-8')).groups()

        # do not work on top level mailbox itself
        if delimiter not in mailbox_name:
            continue

        if flags == '\\HasChildren':
            continue

        res, [mail_count] = con.select(mailbox_name)
        if int(mail_count) == 0:
            print("Mailbox: %s - removing (no mails, no childrem)" % mailbox_name)
            if not args.dry_run:
                con.delete(mailbox_name)

    try:
        con.close()
        con.logout()
    except:
        pass


def connect(connection_params, verbose):

    """Connect to the IMAP server.

    :param dict connection_params:  a dict holding connection details
    :param bool verbose:            be chatty when processing
    :return:                        a connection object
    :rtype:                         imaplib.IMAP4
    """

    con = establish_connection(connection_params, verbose)
    login(con, connection_params, verbose)

    return con


def create_mailbox(connection, delimiter, mailbox):

    """Create a mailbox name recurisvely.

    :param imaplib.IMAP4    connection:      the IMAP connection
    :param str              delimiter:       the current mailbox name delimiter
    :param list             mailbox:         the list of mailbox names to create
    """
    m = ''
    for mailbox_part in mailbox.split(delimiter):
        connection.create('"' + m + mailbox_part + '"')
        connection.subscribe('"' + m + mailbox_part + '"')
        m = m + mailbox_part + delimiter


def establish_connection(connection_params, verbose):

    """Establishes a connection to the IMAP4 server.

    :param dict connection_params:  a dict holding connection details
    :param bool verbose:            be chatty when processing
    :return:                        connection object
    :rtype:                         imaplib.IMAP4
    """

    if verbose is True:
        print('Connecting...', end='')

    try:
        if 'port' in connection_params:
            con = imaplib.IMAP4(connection_params['host'], connection_params['port'])
        else:
            con = imaplib.IMAP4(connection_params['host'])

    except Exception as e:
        if 'port' in connection_params:
            print('failed to connect %s:%d' % (connection_params['host'], connection_params['port']))
        else:
            print('failed to connect %s' % connection_params['host'])
        print(e)
        sys.exit(1)

    if verbose is True:
        print('connected.')
        print('Checking capabilities...', end='')

    res, caps = con.capability()
    if b'STARTTLS' in caps[0].split():
        con.starttls()
        if verbose is True:
            print('done')
            print('Switched to STARTTLS.')
    else:
        if verbose is True:
            print('done')

    return con


def inspect_mailbox(connection, mailbox):

    """Inspect a mailbox folder and return mail-lists.

    :param imaplib.IMAP4    connection:     the IMAP connection
    :param str              mailbox:        the mailbox name to inspect
    :return:                                (all mails, seen mails, seen mails per year)
    :rtype:                                 tuple(list, list, dict)
    """

    connection.select(mailbox)
    res, [mails_all] = connection.search(None, 'ALL')
    res, [mails_seen] = connection.search(None, 'SEEN')
    mails_all = mails_all.decode('UTF-8').split(' ')

    if len(mails_all) > 0 and mails_all[0] == '':
        mails_all.pop()

    mails_seen = mails_seen.decode('UTF-8').split(' ')
    if len(mails_seen) > 0 and mails_seen[0] == '':
        mails_seen.pop()

    mails_per_year = {}

    if len(mails_seen) > 0:

        # run in chunks of 1000 mails... reason: overload of library otherwise
        i = 0
        m = mails_seen[i:i + 1000]

        while len(m) > 0:

            res, header_data = connection.fetch(','.join(m), '(BODY.PEEK[HEADER])')

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
            i = i + 1000
            m = mails_seen[i:i + 1000]

    return mails_all, mails_seen, mails_per_year


def login(con, connection_params, verbose):

    """Run user authentication against a mail server.

    :param imaplib.IMAP4    con:                the IMAP connection
    :param dict             connection_params:  a dict holding connection details
    :param bool             verbose:            be chatty when processing
    :return:                                    the imap4 connection
    :rtype:                                     imaplib.IMAP4
    """

    if verbose is True:
        print('Logging in...', end='')

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
            print('NO cram-md5')
            res, data = con.login(connection_params['user'], connection_params['password'])

    except Exception as e:
        print('Failed to login')
        print(e)
        sys.exit(1)

    if verbose is True:
        print('done.')
        print('User %s logged in.' % connection_params['user'])

    return con


def main():

    """IMAPArchiver start."""

    # parse arguments
    parser = argparse.ArgumentParser(description = 'IMAP-Archiver')

    parser.add_argument('-d', '--dry-run', dest='dry_run', action='store_const', const=True, default=False,
            help='Dry run: do not actually make any steps but act as if.')
    parser.add_argument('-V', '--verbose', dest='verbose', action='store_const', const=True, default=False,
            help='Be verbose.')
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
    parser_move.add_argument('mailbox_from', metavar='MAILBOX-FROM',
            help='Mailbox to start moving from.')
    parser_move.add_argument('mailbox_to', metavar='MAILBOX-TO',
            help='Mailbox to move to.')
    parser_move.set_defaults(func = move)

    parser_clean = subparser.add_parser('clean', help='delete empty mailboxes with no mail or child mailbox.')
    parser_clean.add_argument('connect_url', metavar='CONNECT-URL',
            help='Connection details. Syntax is USER[:PASS]@HOST[:PORT] like \'john@example.com\' or \
                \'bob:mysecret@mail-server.com:143\'. If password PASS is omitted you are asked for it.')
    parser_clean.add_argument('mailbox', metavar='MAILBOX',
            help='Top mailbox to start cleaning.')
    parser_clean.set_defaults(func = clean)

    args = parser.parse_args()
    print(args)
    sys.exit(0)

    if 'func' not in dir(args):
        parser.print_help()
        sys.exit(1)

    if args.version:
        show_version()
        sys.exit(0)

    args.func(args)


def max_year():

    """Returns the maximum year for which mails < max_year() are considered old.

    :return:    most recent year for which mails are old
    :rtype:     int
    """
    return datetime.date(datetime.date.today().year - 1, 1, 1).year


def move(args):

    """Move old mails from one mailsbox to another, keeping the folder structure.

    :param dict args:   argparse.Namespace instance
    """

    con = connect(parse_connection(args.connect_url, args.verbose), args.verbose)
    res, mailbox_list = con.list(args.mailbox_from)

    mail_max_year = max_year()

    pattern = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')
    for mailbox_list_item in mailbox_list:
        if mailbox_list_item is None:
            continue

        flags, delimiter, mailbox = pattern.match(mailbox_list_item.decode('UTF-8')).groups()
        mails_all, mails_seen, mails_old = inspect_mailbox(con, mailbox)

        # move mails
        mb = strip_mailbox(mailbox)
        first_move = True
        for y in mails_old:
            if y < mail_max_year:
                archive_mailbox = '"' + args.mailbox_to + delimiter + str(y) + delimiter + mb + '"'
                print("Mailbox: %s - moving %d mails to %s" % (mailbox, len(mails_old[y]), archive_mailbox))
                if not args.dry_run:
                    create_mailbox(con, delimiter, archive_mailbox)
                    mail_ids = ','.join(mails_old[y])
                    con.copy(mail_ids, archive_mailbox)
                    con.store(mail_ids, '+FLAGS', r'(\Deleted)')

    try:
        con.close()
        con.logout()
    except:
        pass


def parse_connection(connection_string, verbose):

    """Parse and get connection params.

    :param str  connection_string:  some string in the form "USER[:PASSWORD]@HOST[:PORT]"
    :return:                        connection detail dict
    :rtype:                         dict
    """

    # worst case scenario: "alice@somehost.domain:password@someotherhost.otherdomain:7892"
    con = {}
    parts_at = connection_string.split('@')
    if len(parts_at) == 1:
        print('Malformed connection string - type --help for help')
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
        print('Ffailed to parse mailserver part')
        print(e)
        sys.exit(1)

    if len(con['host']) == 0:
        print('Cannot deduce host')
        sys.exit(1)

    try:
        if user_and_password.find(':') == -1:
            con['user'] = user_and_password
        else:
            con['user'] = user_and_password.split(':')[:-1][0]
            con['password'] = user_and_password.split(':')[-1:][0]
    except Exception as e:
        print('Failed to parse credential part')
        print(e)
        sys.exit(1)

    if len(con['user']) == 0:
        print('Cannot deduce user')
        sys.exit(1)

    if 'password' not in con:
        con['password'] = getpass.getpass(
                'No user password given. Please enter password for user \'%s\': ' % con['user'])

    if verbose is True:
        p = '<default>'
        if 'port' in con:
            p = str(con['port'])
        print('User: %s' % con['user'])
        print('Pass: %s' % ('*' * len(con['password'])))
        print('Host: %s' % con['host'])
        print('Port: %s' % p)

    return con


def scan(args):

    """Scan IMAP folders.

    :param dict args:   argparse.Namespace instance
    """

    con = connect(parse_connection(args.connect_url, args.verbose), args.verbose)
    if args.mailbox is None:
        res, mailbox_list = con.list()
    else:
        res, mailbox_list = con.list(args.mailbox)
    if (args.verbose):
        print('Mailboxes found: %d.' % len(mailbox_list))

    mail_max_year = max_year()
    if (args.verbose):
        print('"Old" mails: mails before year %d.' % mail_max_year)

    pattern = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')
    for mailbox_list_item in mailbox_list:

        if mailbox_list_item is None:
            continue

        flags, delimiter, mailbox = pattern.match(mailbox_list_item.decode('UTF-8')).groups()

        if not args.list_boxes_only:
            mails_all, mails_seen, mails_old = inspect_mailbox(con, mailbox)
            old_mails = 0
            for y in mails_old:
                if y < mail_max_year:
                    old_mails = old_mails + len(mails_old[y])

            print("Mailbox: %s - ALL: %d, SEEN: %d, OLD: %d" % (mailbox, len(mails_all), len(mails_seen), old_mails))

        else:
            print("Mailbox: %s" % mailbox)

    try:
        con.close()
        con.logout()
    except:
        pass


def show_version():

    """Show the version."""

    print('IMAP-Archiver V{0}'.format(__version__))
    print(__author__)
    print(__copyright__)
    print('Licensed under the terms of {0} - please read "{1}"'.format(__license__, __licenseurl__))


def strip_mailbox(mailbox):

    """Strip leading and trailing quotes from a mailbox name.

    :return:    the mailbox name without quotes
    :rtype:     str
    """
    if mailbox.endswith('"'): mailbox = mailbox[:-1]
    if mailbox.startswith('"'): mailbox = mailbox[1:]
    return mailbox


if __name__ == "__main__":
    main()
