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


# ------------------------------------------------------------
# imports

import argparse
import getpass
import imaplib
import logging
import re
import sys

import __init__ as imap_archiver


# ------------------------------------------------------------
# code

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


def imap_disconnect(connection):

    """Disconnect from the IMAP server"""
    logging.info('disconnecting from server')
    try:
        connection.logout()
    except:
        pass


def imap_work(connection):

    """Do the actual work on the IMAP server"""
    try:

        pattern = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')

        # get all inbox subs
        res, inbox_list = connection.list('inbox')
        for i in inbox_list:
            flags, delimiter, mailbox_name = pattern.match(i.decode('UTF-8')).groups()
            logging.debug('found mailbox: %s' % mailbox_name)

    except Exception as err:
        logging.error('working on mail failed: %s' % str(err))
        

def main():
    
    """IMAP-Archiver start"""

    # parse arguments
    parser = argparse.ArgumentParser(description = 'IMAP-Archiver')
    parser.add_argument('-t', '--host', dest='host', type=str, help='IMAP host name to connect')
    parser.add_argument('-p', '--port', dest='port', type=int, default=993, help='IMAP host port to connect')
    parser.add_argument('-u', '--user', dest='user', type=str, help='user account to log in')
    parser.add_argument('-k', '--password', dest='password', type=str, help='user password to log in')
    parser.add_argument('-l', '--logging', dest='loglevel', type=int, default=30, help='set logging level (see python logging module) - default is WARNING: 30 - the lower the more output')
    parser.add_argument('-v', '--version', dest='version', action='store_const', const=True, default=False, help='version information')
    args = parser.parse_args()

    # do not proceed if only version is asked
    if args.version:
        show_version()
        sys.exit(0)

    # fix logging
    logging.getLogger(None).setLevel(args.loglevel)

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

    # work
    con = imap_connect(args.host, args.port, args.user, args.password)
    imap_work(con)
    imap_disconnect(con)


def show_version():

    """Show the version"""

    print('IMAP-Archiver V{0}'.format(imap_archiver.__version__))
    print(imap_archiver.__author__)
    print(imap_archiver.__copyright__)
    print('Licensed under the terms of {0} - please read "{1}"'.format(imap_archiver.__license__, imap_archiver.__licenseurl__))


if __name__ == "__main__":
    main()

