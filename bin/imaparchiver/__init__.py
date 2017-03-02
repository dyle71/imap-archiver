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
from imaparchiver.mail import Mail


# public modules
__all__ = ['connection', 'mailbox']

# package metadata
__author__      = 'Oliver Maurhart <dyle@dyle.org>'
__copyright__   = 'Copyright 2015-2017 Oliver Maurhart'
__license__     = 'GPL v3'
__licenseurl__  = 'http://www.gnu.org/licenses/gpl.html'
__title__       = 'imaparchiver'
__version__     = '0.5.0'


def set_verbose(verbose):
    Connection.verbose = True
    Mailbox.verbose = True
    Mail.verbose = True
    
