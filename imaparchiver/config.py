# ------------------------------------------------------------
# imaparchiver/config.py
#
# imap-archiver config object
#
# This file is part of imaparchiver.
# See the LICENSE file for the software license.
# (C) Copyright 2015-2019, Oliver Maurhart, dyle71@gmail.com
# ------------------------------------------------------------

"""This module contains the app wide configuration object."""


class _Singleton(type):

    """Singleton class instance."""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Config(metaclass=_Singleton):

    """This object holds the app wide configurations like command line options, etc."""

    def __init__(self):
        self.dry_run = False
        self.no_color = False
        self.ssl = False
        self.verbose = False
