#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ------------------------------------------------------------
# mail.py
#
# A single mail
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



# ------------------------------------------------------------
# code

class Mail(object):

    """This is a single mail found on the IMAP4 server."""

    verbose = False
    """Verbose on mail methods."""

    def __init__(self, mailbox, id):

        """Constructor.

        :param imaparchiver.Mailbox mailbox:    parent Mailbox instance
        :param int id:                          mail id inside the mailbox
        """

        self._mailbox = mailbox
        self._id = id


if __name__ == "__main__":
    import sys
    print('This file is not meant to be run directly.')
    sys.exit(1)
