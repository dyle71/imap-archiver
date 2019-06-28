#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ------------------------------------------------------------
# setup.py
#
# imap-archiver setuptools main file
#
# This file is part of imap-archiver.
# See the LICENSE file for the software license.
# (C) Copyright 2015-2019, Oliver Maurhart, dyle71@gmail.com
# ------------------------------------------------------------

from setuptools import setup

import imaparchiver

setup(
    name='imap-archiver',
    version=imaparchiver.__version__,
    description='Archive IMAP mails locally and remove empty folder.',
    long_description='This tool logs into an IMAP server, scans the mails, dumps and remove all  '
                     'mails before a specify date and cleanses empty mail folders.',
    author='Oliver Maurhart',
    author_email='dyle71@gmail.com',
    maintainer='Oliver Maurhart',
    maintainer_email='dyle71@gmail.com',
    url='https://github.com/dyle71/imap-archiver',
    license='MIT',

    # sources
    packages=['imaparchiver'],
    py_modules=[],
    scripts=['bin/imap-archiver'],

    # data
    include_package_data=False,
    data_files=[
        ('share/imap-archiver', ['requirements.txt'])
    ]
)
