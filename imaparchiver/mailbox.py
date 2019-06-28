# ------------------------------------------------------------
# imaparchiver/mailbox.py
#
# A single mailbox
#
# This file is part of imap-archiver.
# See the LICENSE file for the software license.
# (C) Copyright 2015-2019, Oliver Maurhart, dyle71@gmail.com
# ------------------------------------------------------------

import email.utils
import re
import sys
from typing import Dict, List, Optional

from . import color


class Mailbox(object):

    """This is a single mailbox found on the IMAP4 server."""

    def __init__(self, connection: object, mailbox_entry: str):

        """Constructor.

        Deconstruct a IMAP4 server mailbox response. This response may look like:
            b'(\\HasNoChildren) "." "INBOX.Subfolder.Folder with Spaces"'
        or
            b'(\\HasChildren) "." INBOX.Subfolder.Folder_with_no_spaces'

        :param connection:      parent IMAP4 server connection instance
        :param mailbox_entry:   the mailbox entry as passed by the server
        """
        pattern = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')
        flags, delimiter, mailbox = pattern.match(mailbox_entry).groups()
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
    def children(self) -> bool:
        """Does this mailbox do have children?"""
        return self._children

    def copy(self, mail_ids: List[str], destination: str = None) -> None:
        """Copy mails from the current mailbox to a destination mailbox.

        :param list[str] mail_ids:  list of mail ids to copy
        :param str destination:     name of destination mailbox
        """
        if len(mail_ids) == 0 or len(destination) == 0:
            return
        self.select()
        m = ','.join(mail_ids)
        d = self.quote_path(destination)
        self._connection.imap4.copy(m, d)

    def delete(self) -> None:
        """Delete this mailbox on the IMAP4 server."""
        self._connection.imap4.select()
        self._connection.imap4.delete(self.path)

    @property
    def delimiter(self) -> str:
        """Mailbox name delimiter used to build mailbox hierarchy."""
        return self._delimiter

    def expunge(self) -> None:
        """Permanently delete marked mails in current mailbox."""
        self.select()
        self._connection.imap4.expunge()

    def fetch(self, ids, message_parts) -> (str, List[str]):
        """Get some content from the IMAP4 server within this mailbox.

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

    def inspect(self) -> (List[int], List[int], List[int], Dict[int, List[int]]):

        """Inspect the current mailbox.

        :return:    all mail ids, seen mail ids, deleted mail ids, seen mails per year
        """
        res, [mails_all] = self.search('ALL')
        res, [mails_seen] = self.search('SEEN')
        res, [mails_deleted] = self.search('DELETED')

        mails_all = mails_all.decode().split(' ')
        if len(mails_all) > 0 and mails_all[0] == '':
            mails_all.pop()

        mails_seen = mails_seen.decode().split(' ')
        if len(mails_seen) > 0 and mails_seen[0] == '':
            mails_seen.pop()

        mails_deleted = mails_deleted.decode().split(' ')
        if len(mails_deleted) > 0 and mails_deleted[0] == '':
            mails_deleted.pop()

        mails_per_year = {}
        if len(mails_seen) > 0:

            # run in chunks of 1000 mails... reason: overload of library otherwise
            i = 0
            m = mails_seen[i:i + 1000]
            while len(m) > 0:

                res, header_data = self.fetch(','.join(m), '(BODY.PEEK[HEADER])')
                pattern_mail_id = re.compile('(?P<msgid>.*?) .*')
                for h in header_data:
                    if isinstance(h, tuple):

                        mail_id = pattern_mail_id.match(h[0].decode()).groups()[0]
                        mail_header = h[1].split(b'\r\n')
                        mail_year = self._year_from_mail_header(mail_header)
                        if mail_year is not None:
                            if mail_year not in mails_per_year:
                                mails_per_year[mail_year] = []
                            mails_per_year[mail_year].append(mail_id)

                i = i + 1000
                m = mails_seen[i:i + 1000]

        return mails_all, mails_seen, mails_deleted, mails_per_year

    @property
    def name(self) -> str:
        """The name of the mailbox stripped from leading and trialing quotes to be better human readable."""
        return self._name

    @property
    def path(self) -> str:
        """The mailbox id used by the IMAP4 server."""
        return self._path

    @staticmethod
    def quote_path(path: str) -> str:
        """Add quotes to mailbox path if necessary.

        :param path:    a mailbox path
        :return:        a quoted mailbox path (if necessary)
        """
        path_quoted = path
        if ' ' not in path_quoted:
            return path_quoted

        if path_quoted[0] != '"':
            path_quoted = '"' + path_quoted
        if path_quoted[-1] != '"':
            path_quoted = path_quoted + '"'
        return path_quoted

    def search(self, *criteria) -> (str, List[bytes]):
        """Search inside the selected mailbox.

        :param criteria:    IMAP4 search criteria
        :return:            result string, mail ids matching the criteria
        """
        self.select()
        return self._connection.imap4.search(None, *criteria)

    def select(self) -> int:
        """Selects this mailbox for the next IMAP operation.

        :return:     the number of mails in this mailbox
        """
        if not self._connection:
            raise RuntimeError('No connection.')
        return int(self._connection.imap4.select(self.path)[1][0])

    @staticmethod
    def strip_path(path: str = None) -> str:
        """Remove quotes from a mailbox path.

        :param path:        a mailbox path
        :return:            an unquoted mailbox path
        """
        path_stripped = path
        while len(path_stripped) > 0 and path_stripped[0] == '"':
            path_stripped = path_stripped[1:]
        while len(path_stripped) > 0 and path_stripped[-1] == '"':
            path_stripped = path_stripped[:-1]

        return path_stripped

    def store(self, mail_ids: List[int], operation: str, flags: str) -> None:
        """Modify mail flags inside this mailbox.

        This will delete the mails 1, 2 and 5 in the current mailbox:
        >>> mb = Mailbox(...)
        >>> mb.store([b'1', b'2', b'5'], '+FLAGS', r'(\Deleted)')

        :param mail_ids:    list of mail ids to modify
        :param operation:   IMAP4 operation
        :param flags:       IMAP4 flags to apply
        """
        self.select()
        m = ','.join(mail_ids)
        self._connection.imap4.store(m, operation, flags)

    @staticmethod
    def _year_from_mail_header(mail_header: List[bytes]) -> Optional[int]:
        """Pick the year of the email by examinig a mail header.

        :param mail_header:     all mail headers of a mail
        :return:                the year of the mail
        """
        for mh in mail_header:
            if mh.startswith(b'Date:'):
                try:
                    return email.utils.parsedate(str(mh)[8:])[0]
                except:
                    sys.stderr.write(color.error('Failed to deduce year of mail.\n'))
                    sys.stderr.write(color.error('Defective mail: \n' + str(mail_header) + '\n'))
                    return None

