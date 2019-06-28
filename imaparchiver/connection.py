# ------------------------------------------------------------
# connection.py
#
# IMAP4 server connection object
#
# This file is part of imap-archiver.
# See the LICENSE file for the software license.
# (C) Copyright 2015-2019, Oliver Maurhart, dyle71@gmail.com
# ------------------------------------------------------------

# thanks to a lot of inspiration from
# http://pymotw.com/2/imaplib/

import getpass
import imaplib
import re
import sys
from typing import List

from .config import Config
from . import color
from .mailbox import Mailbox


class Connection(object):

    """This represents a IMAP4 connection."""

    def __init__(self, host: str, port: str, username: str, password: str):
        """Constructor.

        :param host:        the host to connect
        :param port:        the host's port number (if 0 then the default will be used)
        :param username:    user account for login
        :param password:    user password for login
        """
        self._connection = None
        self._capabilities = []
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

    @property
    def capabilities(self) -> List:
        """Returns the capabilities of this connection to the remote host."""
        return self._capabilities

    def create_mailbox(self, path: str, delimiter: str) -> None:
        """Create a mailbox folder (recursively)  on the server.

        The folder path given is created recursively. So if path = 'a.b.c.' then
        the folder 'a' is created, then 'b' and finally 'c'.

        :param str path:        the mailbox folder name as understood by the IMAP4 server.
        :param str delimiter:   path delimier used
        """
        if not self._connection:
            raise RuntimeError('No connection to IMAP4 server.')

        if len(path) == 0:
            return

        path_stripped = Mailbox.strip_path(path)
        mb = ''
        for path_particle in path_stripped.split(delimiter):

            if len(mb) > 0:
                mb = mb + delimiter
            mb = mb + path_particle

            mb_quoted = mb
            if ' ' in mb:
                mb_quoted = '"' + mb + '"'

            r, d = self._connection.select(mb_quoted)
            if r == 'NO':
                self._connection.create(mb_quoted)
            self._connection.subscribe(mb_quoted)

    def _dump_capabilities(self) -> None:
        """Show the capabilities of the connection to the user."""
        if Config().verbose is False:
            return
        sys.stderr.write(color.connection_detail('Capabilities of the remote host connected:\n'))
        if len(self.capabilities) == 0:
            sys.stderr.write(color.connection_detail('<NONE>\n'))
        else:
            for cap in self.capabilities:
                sys.stderr.write(color.connection_detail(f'    {cap}\n'))

    @staticmethod
    def _fix_port(port: int) -> int:
        """Returns the default port for the connection if not has been set.

        :param port:        the port as set by the user
        :return:            the port to use for the connection
        """
        if port is not None and port != 0:
            return port
        if Config().ssl:
            return imaplib.IMAP4_SSL_PORT
        else:
            return imaplib.IMAP4_PORT

    def establish(self, host, port):
        """
            Establishes a connection to the IMAP4 server.

            :param str host:    the IMAP4 server host
            :param int port:    the port to connect to
        """
        if Config().verbose is True:
            sys.stderr.write('Connecting... ')

        port = self._fix_port(port)

        try:
            if Config().ssl is True:
                self._connection = imaplib.IMAP4_SSL(host, port)
            else:
                self._connection = imaplib.IMAP4(host, port)

        except Exception as e:
            sys.stderr.write(color.error(f'failed to connect {host}:{port}\n' + str(e)) + '\n')
            self._connection = None
            sys.exit(1)

        if Config().verbose is True:
            sys.stdout.write(color.success('connected.\n') + 'Checking capabilities...')

        res, caps = self._connection.capability()
        if res != 'OK' or len(caps) == 0:
            sys.stderr.write(color.error(f'failed to check capabilities of remote host.\n'))
            sys.exit(1)
        if Config().verbose is True:
            sys.stderr.write(color.success('done.\n'))
        self._capabilities = caps[0].decode().split()
        self._dump_capabilities()

        if 'STARTTLS' in self.capabilities:
            self._connection.starttls()
            if Config().verbose is True:
                sys.stderr.write(color.success('Switched to STARTTLS.\n'))

    @property
    def imap4(self) -> object:
        """Get the imaplib.IMAP4 (or imaplib.IMAP4_SSL) object instance"""
        return self._connection

    def login(self, username, password):
        """
            Run user authentication against a mail server.

            :param str username:    the user account used to log in
            :param int password:    the user's password for log in
        """
        if not self._connection:
            raise RuntimeError('No connection to IMAP4 server.')

        if Config().verbose is True:
            sys.stderr.write('Logging in... ')

        auth_methods = self._pick_auth_methods()
        try:

            if 'CRAM-MD5' in auth_methods:
                res, data = self._connection.login_cram_md5(username, password)
            elif 'PLAIN' in auth_methods:
                res, data = self._connection.login(username, password)
            else:
                sys.stderr.write(color.error('sorry: no AUTH method available I can deal with. =(\n'))
                sys.exit(1)

        except Exception as e:
            sys.stderr.write(color.error('failed to login.\n' + str(e)) + '\n')
            sys.exit(1)

        if Config().verbose is True:
            sys.stderr.write(color.success('done.\n'))
            sys.stderr.write(color.success(f'User {username} logged in.\n'))

    def mailboxes(self, root: str = 'INBOX'):
        """Load all mailboxes from the server.

        :param root:    top root mailbox
        """

        if self._connection is None:
            raise RuntimeError('No connection to IMAP4 server.')

        if root:
            res, mailbox_list = self._connection.list(root)
        else:
            res, mailbox_list = self._connection.list()
        if res != 'OK':
            raise RuntimeError('Server error on listing mailboxes. Returned: ' + str(res))

        mbs = {}
        for m in mailbox_list:
            if m is not None:
                mb = Mailbox(self, m.decode())
                mbs[mb.name] = mb

        return mbs

    @staticmethod
    def parse(connect: str) -> (str, str, int, str):
        """Parse and get connection params.

        :param connect:     some string in the form "USER[:PASSWORD]@HOST[:PORT]"
        :return:            host, port, username, password
        """
        # worst case scenario: "alice@somehost.domain:password@someotherhost.otherdomain:7892"
        port = 0
        password = None

        parts_at = connect.split('@')
        if len(parts_at) == 1:
            sys.stderr.write(color.error('Malformed connection string - type --help for help\n'))
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
            sys.stderr.write(color.error('Failed to parse mailserver part.\n' + str(e)) + '\n')
            sys.exit(1)

        if not host:
            sys.stderr.write(color.error('Cannot deduce host.\n'))
            sys.exit(1)

        try:
            if user_and_password.find(':') == -1:
                username = user_and_password
            else:
                username = user_and_password.split(':')[:-1][0]
                password = user_and_password.split(':')[-1:][0]
        except Exception as e:
            sys.stderr.write(color.error('Failed to parse credential part.\n' + str(e)) + '\n')
            sys.exit(1)

        if username is None:
            sys.stderr.write(color.error('Cannot deduce user.'))
            sys.exit(1)

        if password is None:
            password = getpass.getpass(f'No user password given. Please enter password for user {username}: ')

        if Config().verbose is True:
            sys.stderr.write(color.connection_detail(f'User: {username}\n'))
            sys.stderr.write(color.connection_detail('Pass: ********************\n'))
            sys.stderr.write(color.connection_detail(f'Host: {host}\n'))
            if port != 0:
                sys.stderr.write(color.connection_detail(f'Port: {port}\n'))
            else:
                sys.stderr.write(color.connection_detail('Port: <default>\n'))

        return host, port, username, password

    def _pick_auth_methods(self) -> List:
        """Picks the set of available AUTH methods of the server.

        :return:    the list of available AITH methods.
        """
        auth = []
        for cap in self.capabilities:
            m = re.match('AUTH=(.*)', cap)
            if m is not None and len(m.groups()) == 1:
                auth.append(m.groups()[0])

        return auth