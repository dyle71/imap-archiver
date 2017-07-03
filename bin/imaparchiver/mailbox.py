#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ------------------------------------------------------------
# mailbox.py
#
# A single mailbox
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

# ------------------------------------------------------------
# imports

import email.utils
import re

import imaparchiver


# ------------------------------------------------------------
# code

class Mailbox(object):

    """This is a single mailbox found on the IMAP4 server."""

    def __init__(self, connection, mailbox_entry):

        """
            Constructor.

            Deconstruct a IMAP4 server mailbox response. This response may look like:

                b'(\\HasNoChildren) "." "INBOX.Subfolder.Folder with Spaces"'
            or
                b'(\\HasChildren) "." INBOX.Subfolder.Folder_with_no_spaces'

            :param imaparchiver.Connection connection:  parent IMAP4 server connection instance
            :param str mailbox_entry:                   the mailbox entry as passed by the server
        """
        pattern = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')
        flags, delimiter, mailbox = pattern.match(mailbox_entry.decode('utf-8')).groups()
        self._children = not re.match('.*HasChildren.*', flags) is None
        self._delimiter = delimiter
        self._path = mailbox
        self._name = mailbox
        if self._name.endswith('"'):
            self._name = self._name[:-1]
        if self._name.startswith('"'):
            self._name = self._name[1:]
        self._connection = connection


    @property
    def children(self):
        """Does this mailbox do have children?"""
        return self._children


    def copy(self, mail_ids, destination):
        """
            Copy mails from the current mailbox to a destination mailbox.

            :param list[str] mail_ids:  list of mail ids to copy
            :param str destination:     name of destination mailbox
        """
        self.select()
        m = ','.join(mail_ids)
        d = imaparchiver.quote_path(destination)
        self._connection.imap4.copy(m, d)


    def delete(self):
        """Delete this mailbox on the IMAP4 server."""
        self._connection.imap4.select()
        self._connection.imap4.delete(self.path)


    @property
    def delimiter(self):
        """Mailbox name delimiter used to build mailbox hirarchy."""
        return self._delimiter


    def expunge(self):
        """Permanently delete marked mails in current mailbox."""
        self.select()
        self._connection.imap4.expunge()


    def fetch(self, ids, message_parts):
        """
            Get some content from the IMAP4 server within this mailbox.

            Example:

            >>> con.fetch('1,2', '(BODY)')
            ('OK', [b'1 (BODY ("text" "plain" ("charset" "UTF-8") NIL NIL "8bit" 909 38))',
                    b'2 (BODY ("text" "plain" ("charset" "ISO-8859-1" "format" "flowed") NIL NIL "7bit" 696 32))'])

            :param list[int] ids:       the mail ids requested
            :param str message_parts:   content requested
            :return:                    return code, list[content]
            :rtype:                     str, list[bytes]
        """
        self.select()
        return self._connection.imap4.fetch(ids, message_parts)


    def inspect(self):

        """
            Inspect the current mailbox.

            :return:    all mail ids, seen mail ids, deleted mail ids, seen mails per year
            :rtype:     tuple(list[int], list[int], list[int], dict{int->[int]})
        """
        res, [mails_all] = self.search('ALL')
        res, [mails_seen] = self.search('SEEN')
        res, [mails_deleted] = self.search('DELETED')

        mails_all = mails_all.decode('utf-8').split(' ')
        if len(mails_all) > 0 and mails_all[0] == '':
            mails_all.pop()

        mails_seen = mails_seen.decode('utf-8').split(' ')
        if len(mails_seen) > 0 and mails_seen[0] == '':
            mails_seen.pop()

        mails_deleted = mails_deleted.decode('utf-8').split(' ')
        if len(mails_deleted) > 0 and mails_deleted[0] == '':
            mails_deleted.pop()

        mails_per_year = {}

        if len(mails_seen) > 0:

            # run in chunks of 1000 mails... reason: overload of library otherwise
            i = 0
            m = mails_seen[i:i + 1000]

            while len(m) > 0:

                res, header_data = self.fetch(','.join(m), '(BODY.PEEK[HEADER])')
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

        return mails_all, mails_seen, mails_deleted, mails_per_year


    @property
    def name(self):
        """The name of the mailbox stripped from leading and trialing quotes to be better human readable."""
        return self._name


    @property
    def path(self):
        """The mailbox id used by the IMAP4 server."""
        return self._path


    def search(self, *criteria):
        """
            Search inside the selected mailbox.

            :param str* criteria:   IMAP4 search criterias
            :return:                result string, mail ids matching the criteris
            :rtype:                 str, list[bytes]
        """
        self.select()
        return self._connection.imap4.search(None, *criteria)


    def select(self):
        """
            Select a mailbox for the next IMAP operation.

            :param str mailbox: the mailbox
            :return:            number of mails in the mailbox
        """
        if not self._connection:
            raise RuntimeError('No connection.')
        return int(self._connection.imap4.select(self.path)[1][0])


    def store(self, mail_ids, operation, flags):
        """
            Modify mail flags inside this mailbox.

            This will delete the mails 1, 2 and 5 in the current mailbox:
            >>> mb = Mailbox(...)
            >>> mb.store([b'1', b'2', b'5'], '+FLAGS', r'(\Deleted)')

            :param list[str] mail_ids:  list of mail ids to modify
            :param str operation:       flag operation
            :param str flags:           IMAP4 flags to apply
        """
        self.select()
        m = ','.join(mail_ids)
        self._connection.imap4.store(m, operation, flags)


if __name__ == "__main__":
    import sys
    print('This file is not meant to be run directly.')
    sys.exit(1)
