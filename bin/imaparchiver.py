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


# ------------------------------------------------------------
# imports

import argparse
import datetime
# import email
# import email.utils
import getpass
# import imaplib
# import inspect
# import re
import sys

from imaparchiver import Connection
import imaparchiver


# ------------------------------------------------------------
# code


# def clean(args):
#
#     """Clean empty leaf nodes in the IMAP folder structure.
#
#     :param argparse.Namespace args: parsed command line arguments
#     """
#
#     con = connect(parse_connection(args.connect_url, args.verbose), args.verbose)
#
#     pattern = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')
#
#     res, mailbox_list = con.list(args.mailbox)
#     for i in mailbox_list:
#
#         if i is None:
#             continue
#
#         flags, delimiter, mailbox_name = pattern.match(i.decode('UTF-8')).groups()
#
#         # do not work on top level mailbox itself
#         if delimiter not in mailbox_name:
#             continue
#
#         if flags == '\\HasChildren':
#             continue
#
#         res, [mail_count] = con.select(mailbox_name)
#         if int(mail_count) == 0:
#             print("Mailbox: %s - removing (no mails, no children)" % mailbox_name)
#             if not args.dry_run:
#                 con.select()
#                 con.delete(mailbox_name)
#
#     try:
#         con.close()
#         con.logout()
#     except:
#         pass
#
#
# def connect(connection_params, verbose):
#
#     """Connect to the IMAP server.
#
#     :param dict connection_params:  a dict holding connection details
#     :param bool verbose:            be chatty when processing
#     :return:                        a connection object
#     :rtype:                         imaplib.IMAP4
#     """
#
#     con = establish_connection(connection_params, verbose)
#     login(con, connection_params, verbose)
#
#     return con
#
#
# def create_mailbox(connection, delimiter, mailbox):
#
#     """Create a mailbox name recurisvely.
#
#     :param imaplib.IMAP4    connection:      the IMAP connection
#     :param str              delimiter:       the current mailbox name delimiter
#     :param list             mailbox:         the list of mailbox names to create
#     """
#     m = ''
#     for mailbox_part in mailbox.split(delimiter):
#         mb = '"' + m + mailbox_part + '"'
#         connection.create(mb)
#         connection.subscribe(mb)
#         m = m + mailbox_part + delimiter
#
#
# def debug_line(frame, str=''):
#
#     """Dump current debug line info.
#
#     :param frame frame: the current python interpreter frame object
#     """
#     if not frame is None:
#         tb = inspect.getframeinfo(frame)
#         print("==dgb== %s:%d" % (tb.filename, tb.lineno), end='')
#         if not str:
#             print(str)
#         else:
#             print('')
#
#
# def decode_mailbox_list_entry(mailbox_list_item):
#
#     """Decode the mailbox list entry returned by an IMAP4 server.
#
#     :param bytes mailbox_list_item: the mailbox list entry returned by the server.
#     :return:                        flags, delimiter, mailbox
#     :rtype:                         str, str, str
#     """
#
#     pattern = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')
#     flags, delimiter, mailbox = pattern.match(mailbox_list_item.decode('UTF-8')).groups()
#     return flags, delimiter, mailbox
#
#
# def inspect_mailbox(connection, mailbox):
#
#     """Inspect a mailbox folder and return mail-lists.
#
#     :param imaplib.IMAP4    connection:     the IMAP connection
#     :param str              mailbox:        the mailbox name to inspect
#     :return:                                (all mail ids, seen mail ids, seen mails per year)
#     :rtype:                                 tuple(list[int], list[int], dict{int->[int]})
#     """
#
#     connection.select(mailbox)
#     res, [mails_all] = connection.search(None, 'ALL')
#     res, [mails_seen] = connection.search(None, 'SEEN')
#     mails_all = mails_all.decode('UTF-8').split(' ')
#
#     if len(mails_all) > 0 and mails_all[0] == '':
#         mails_all.pop()
#
#     mails_seen = mails_seen.decode('UTF-8').split(' ')
#     if len(mails_seen) > 0 and mails_seen[0] == '':
#         mails_seen.pop()
#
#     mails_per_year = {}
#
#     if len(mails_seen) > 0:
#
#         # run in chunks of 1000 mails... reason: overload of library otherwise
#         i = 0
#         m = mails_seen[i:i + 1000]
#
#         while len(m) > 0:
#
#             res, header_data = connection.fetch(','.join(m), '(BODY.PEEK[HEADER])')
#
#             pattern_mailid = re.compile('(?P<msgid>.*?) .*')
#             for h in header_data:
#                 if isinstance(h, tuple):
#
#                     mail_id = pattern_mailid.match(h[0].decode('UTF-8')).groups()[0]
#                     mail_header = h[1].split(b'\r\n')
#                     for mh in mail_header:
#                         if mh.startswith(b'Date:'):
#
#                             mail_year = email.utils.parsedate(str(mh)[8:])[0]
#                             if mail_year not in mails_per_year:
#                                 mails_per_year[mail_year] = []
#                             mails_per_year[mail_year].append(mail_id)
#             i = i + 1000
#             m = mails_seen[i:i + 1000]
#
#     return mails_all, mails_seen, mails_per_year


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
    parser_move.add_argument('-o', '--omit-mailbox',
            help='List of mailboxes to ignore.')
    parser_move.add_argument('connect_url', metavar='CONNECT-URL',
            help='Connection details. Syntax is USER[:PASS]@HOST[:PORT] like \'john@example.com\' or \
                \'bob:mysecret@mail-server.com:143\'. If password PASS is omitted you are asked for it.')
    parser_move.add_argument('mailbox_from', metavar='MAILBOX-FROM',
            help='Mailbox to start moving from.')
    parser_move.add_argument('mailbox_to', metavar='MAILBOX-TO',
            help='Mailbox to move to.')
    parser_move.set_defaults(func = move)

    # parser_clean = subparser.add_parser('clean', help='delete empty mailboxes with no mail or child mailbox.')
    # parser_clean.add_argument('connect_url', metavar='CONNECT-URL',
    #         help='Connection details. Syntax is USER[:PASS]@HOST[:PORT] like \'john@example.com\' or \
    #             \'bob:mysecret@mail-server.com:143\'. If password PASS is omitted you are asked for it.')
    # parser_clean.add_argument('mailbox', metavar='MAILBOX',
    #         help='Top mailbox to start cleaning.')
    # parser_clean.set_defaults(func = clean)

    args = parser.parse_args()
    if args.version:
        show_version()
        sys.exit(0)

    if 'func' not in dir(args):
        parser.print_help()
        sys.exit(1)

    imaparchiver.verbose = args.verbose
    args.func(args)


def max_year():

    """Returns the maximum year for which mails < max_year() are considered old.

    :return:    most recent year for which mails are old
    :rtype:     int
    """
    return datetime.date(datetime.date.today().year - 1, 1, 1).year


def move(args):

    """Move old mails from one mailbox to another, keeping the folder structure.

    :param argparse.Namespace args: parsed command line arguments
    """

    host, port, username, password = parse_connection(args.connect_url, args.verbose)
    con = Connection(host, port, username, password)

    omit = []
    if args.omit_mailbox:
        omit = args.omit_mailbox.split(',')
    mail_max_year = max_year()
    if args.verbose:
        print('Year sent of mails to be moved: <' + str(mail_max_year))

    mbs = con.mailboxes(args.mailbox_from)
    for mb in sorted(mbs):

        if mbs[mb] is None:
            continue
        if mb in omit:
            print('Omitting mailbox ' + mb)
            continue

        if args.verbose:
            print('Checking mailbox ' + mb + '... ')

        mails_all, mails_seen, mails_deleted, mails_per_year = mbs[mb].inspect()

        # move mails
        first_move = True
        for year in mails_per_year:
            if year < mail_max_year:
                archive_mailbox = args.mailbox_to + mbs[mb].delimiter + str(year) + mbs[mb].delimiter + mb
                if ' ' in archive_mailbox:
                    archive_mailbox = '"' + archive_mailbox + '"'

                print("Mailbox: %s - moving %d mails to %s" % (mb, len(mails_per_year[year]), archive_mailbox))
                if not args.dry_run:
                    con.create_mailbox(archive_mailbox, mbs[mb].delimiter)
                    mbs[mb].copy(mails_per_year[year], archive_mailbox)
                    mbs[mb].store(mails_per_year[year], '+FLAGS', r'(\Deleted)')


def parse_connection(connection_string, verbose):

    """Parse and get connection params.

    :param str  connection_string:  some string in the form "USER[:PASSWORD]@HOST[:PORT]"
    :return:                        host, port, username, password
    :rtype:                         str, int, str, password
    """

    # worst case scenario: "alice@somehost.domain:password@someotherhost.otherdomain:7892"
    host = ''
    port = 0
    username = ''
    password = ''

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
            host = host_and_port
        else:
            host = host_and_port.split(':')[:-1][0]
            port = int(host_and_port.split(':')[-1:][0])

    except Exception as e:
        print('Failed to parse mailserver part.')
        print(e)
        sys.exit(1)

    if not host:
        print('Cannot deduce host.')
        sys.exit(1)

    try:
        if user_and_password.find(':') == -1:
            username = user_and_password
        else:
            username = user_and_password.split(':')[:-1][0]
            password = user_and_password.split(':')[-1:][0]
    except Exception as e:
        print('Failed to parse credential part.')
        print(e)
        sys.exit(1)

    if not username:
        print('Cannot deduce user')
        sys.exit(1)

    if not password:
        password = getpass.getpass('No user password given. Please enter password for user \'%s\': ' % username)

    if verbose is True:
        print('User: %s' % username)
        print('Pass: %s' % ('*' * len(password)))
        print('Host: %s' % host)
        if port != 0:
            print('Port: %d' % port)
        else:
            print('Port: <default>')

    return host, port, username, password


def scan(args):

    """Scan IMAP folders.

    :param argparse.Namespace args: parsed command line arguments
    """

    host, port, username, password = parse_connection(args.connect_url, args.verbose)
    con = Connection(host, port, username, password)

    header_shown = False
    mbs = con.mailboxes(args.mailbox)
    for mb in sorted(mbs):

        if not header_shown:
            print('%-70s   all mails   seen mails   deleted mails' % 'name')
            print('%s-----------------------------------------' % ('-' * 70))
            header_shown = True


        if not args.list_boxes_only:
            mails_all, mails_seen, mails_deleted, mails_per_year = mbs[mb].inspect()
            print('%-70s       %5d        %5d           %5d' % (mb, len(mails_all), len(mails_seen), len(mails_deleted)))
        else:
            print('%-70s                                   ' % (mb))


def show_version():

    """Show the version."""

    import imaparchiver

    print('IMAP-Archiver V{0}'.format(imaparchiver.__version__))
    print(imaparchiver.__author__)
    print(imaparchiver.__copyright__)
    print('Licensed under the terms of %s' % imaparchiver.__license__)
    print('Please read %s' % imaparchiver.__licenseurl__)


if __name__ == "__main__":
    main()
