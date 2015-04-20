#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ------------------------------------------------------------
# main.py
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


# ------------------------------------------------------------
# imports

import argparse
import logging
import sys

import __init__ as imap_archiver


# ------------------------------------------------------------
# code


def main():
    
    """IMAP-Archiver start"""

    # parse arguments
    parser = argparse.ArgumentParser(description = 'IMAP-Archiver')
    parser.add_argument('-l', '--logging', dest='loglevel', type=int, default=30, help='set logging level (see python logging module) - default is WARNING: 30')
    parser.add_argument('-v', '--version', dest='version', action='store_const', const=True, default=False, help='version information')
    args = parser.parse_args()

    # do not proceed if only version is asked
    if args.version:
        show_version()
        sys.exit(0)

    # fix logging
    logging.getLogger(None).setLevel(args.loglevel)



def show_version():

    """Show the version"""

    print('IMAP-Archiver V{0}'.format(imap_archiver.__version__))
    print(imap_archiver.__author__)
    print(imap_archiver.__copyright__)
    print('Licensed under the terms of {0} - please read "{1}"'.format(imap_archiver.__license__, imap_archiver.__licenseurl__))


if __name__ == "__main__":
    main()


