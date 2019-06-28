#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ------------------------------------------------------------
# imaparchiver/__main__.py
#
# imaparchiver package start
#
# This file is part of imaparchiver.
# See the LICENSE file for the software license.
# (C) Copyright 2015-2019, Oliver Maurhart, dyle71@gmail.com
# ------------------------------------------------------------

"""This is the imaparchiver package start script."""

import sys

from . import command_line


def main() -> None:
    """imaparchiver main startup."""
    try:
        command_line.cli(prog_name='imap-archiver')
    except Exception as e:
        sys.stderr.write(str(e) + '\n')
        sys.exit(1)


if __name__ == '__main__':
    main()

