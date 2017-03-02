#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ------------------------------------------------------------
# connection.py
#
# IMAP4 server connection object
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

import imaplib
import re
import sys

from imaparchiver.mailbox import Mailbox


# ------------------------------------------------------------
# code

class Connection(object):

    """This represents a IMAP4 connection."""

    verbose = False
    """Verbose on connection methods."""

    def __init__(self, host, port, username, password):
        """Constructor.

        :param str host:        the host to connect
        :param int port:        the host's port number (if 0 then the default will be used)
        :param str username:    user account for login
        :param str password:    user password for login
        """

        self._connection = None

        self.establish(host, port)
        self.login(username, password)


    def __del__(self):
        """Destructor."""
        try:
            if not self._connection is None:
                self._connection.close()
                self._connection.logout()
        except:
            pass


    def establish(self, host, port):

        """Establishes a connection to the IMAP4 server.

        :param str host:    the IMAP4 server host
        :param int port:    the port to connect to
        """

        if Connection.verbose is True:
            print('Connecting... ', end='')

        try:
            if port != 0:
                self._connection = imaplib.IMAP4(host, port)
            else:
                self._connection = imaplib.IMAP4(host)

        except Exception as e:
            if port != 0:
                print('failed to connect %s:%d' % (host, port))
            else:
                print('failed to connect %s' % host)
            print(e)
            self._connection = None
            sys.exit(1)

        if Connection.verbose is True:
            print('connected.')
            print('Checking capabilities...', end='')

        res, caps = self._connection.capability()
        if b'STARTTLS' in caps[0].split():
            self._connection.starttls()
            if Connection.verbose is True:
                print('done')
                print('Switched to STARTTLS.')
        else:
            if Connection.verbose is True:
                print('done')


    @property
    def imap4(self):
        """Get the imaplib.IMAP4 object instance"""
        return self._connection


    def login(self, username, password):

        """Run user authentication against a mail server.

        :param str username:    the user account used to log in
        :param int password:    the user's password for log in
        """

        if not self._connection:
            raise RuntimeError('No connection to IMAP4 server.')

        if Connection.verbose is True:
            print('Logging in... ', end='')

        auth_method = []
        try:

            # collect authentication methods and login
            res, capabilities = self._connection.capability()

            for cap in capabilities[0].split():
                c = cap.decode('utf-8')
                m = re.match('AUTH=(.*)', c)
                if m is not None and len(m.groups()) == 1:
                    auth_method.append(m.groups()[0])

            if 'CRAM-MD5' in auth_method:
                res, data = self._connection.login_cram_md5(username, password)
            else:
                res, data = self._connection.login(username, password)

        except Exception as e:
            print('Failed to login')
            print(e)
            sys.exit(1)

        if Connection.verbose is True:
            print('done.')
            print('User %s logged in.' % username)


    def mailboxes(self, root='INBOX'):

        """Load all mailboxes from the server.

        :param str root:    top root mailbox
        """

        if not self._connection:
            raise RuntimeError('No connection to IMAP4 server.')

        res, mailbox_list = self._connection.list(root)
        if res != 'OK':
            raise RuntimeError('Server error on listing mailboxes. Returned: ' + str(res))

        mbs = {}
        for m in mailbox_list:
            mb = Mailbox(self, m)
            mbs[mb.name] = mb

        return mbs


if __name__ == "__main__":
    import sys
    print('This file is not meant to be run directly.')
    sys.exit(1)
