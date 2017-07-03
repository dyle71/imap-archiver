#!/bin/env python
# -*- coding: utf-8 -*-

# ------------------------------------------------------------
# imaparchiver package file
#
# Autor: Oliver Maurhart, <dyle@dyle.org>
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


from imaparchiver.connection import Connection
from imaparchiver.mailbox import Mailbox


# public modules
__all__ = ['connection', 'mailbox']

# package metadata
__author__      = 'Oliver Maurhart <dyle@dyle.org>'
__copyright__   = 'Copyright 2015-2017 Oliver Maurhart'
__license__     = 'GPL v3'
__licenseurl__  = 'http://www.gnu.org/licenses/gpl.html'
__title__       = 'imaparchiver'
__version__     = '0.5.1'


verbose = False
"""Global verbose flag."""


def quote_path(path):
    """
        Add quotes to mailbox path if necessary.

        :param str path:    a mailbox path
        :return:            an quoted mailbox path (if necessary)
        :rtype:             str
    """
    path_quoted = path
    if not ' ' in path_quoted:
        return path_quoted

    if path_quoted[0] != '"':
        path_quoted = '"' + path_quoted
    if path_quoted[-1] != '"':
        path_quoted = path_quoted + '"'

    return path_quoted


def strip_path(path):
    """
        Remove quotes from a mailbox path.

        :param str path:    a mailbox path
        :return:            an unquoted mailbox path
        :rtype:             str
    """
    path_stripped = path
    while len(path_stripped) > 0 and path_stripped[0] == '"':
        path_stripped = path_stripped[1:]
    while len(path_stripped) > 0 and path_stripped[-1] == '"':
        path_stripped = path_stripped[:-1]

    return path_stripped
