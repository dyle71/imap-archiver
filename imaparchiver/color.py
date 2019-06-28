# ------------------------------------------------------------
# imaparchiver/color.py
#
# provides colorful output
#
# This file is part of imaparchiver.
# See the LICENSE file for the software license.
# (C) Copyright 2015-2019, Oliver Maurhart, dyle71@gmail.com
# ------------------------------------------------------------

"""This module generated colorized text outputs for the terminal."""

import colors

from .config import Config


def connection_detail(t: str) -> str:
    """Color for connection details.

    :param t:   the text
    :return:    a colorized version of the text
    """
    if not Config().no_color:
        return colors.color(t, fg='green')
    return t


def error(t: str) -> str:
    """Color for error messages.

    :param t:   the text
    :return:    a colorized version of the text
    """
    if not Config().no_color:
        return colors.color(t, fg='red')
    return t


def mailbox(t: str) -> str:
    """Color for mailbox names.

    :param t:   the text
    :return:    a colorized version of the text
    """
    if not Config().no_color:
        return colors.color(t, fg='blue')
    return t


def success(t: str) -> str:
    """Color for success messages.

    :param t:   the text
    :return:    a colorized version of the text
    """
    if not Config().no_color:
        return colors.color(t, fg='yellow')
    return t
