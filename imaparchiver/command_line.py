# ------------------------------------------------------------
# imaparchiver/command_line.py
#
# handle command line stuff and arguments
#
# This file is part of imaparchiver.
# See the LICENSE file for the software license.
# (C) Copyright 2015-2019, Oliver Maurhart, dyle71@gmail.com
# ------------------------------------------------------------

"""This module provides all command line stuff and figures."""

import click
import datetime
import email.utils
import os
import sys
import time

from . import color
from .config import Config
from .connection import Connection
from .mailbox import Mailbox


@click.group(invoke_without_command=True)
@click.option('-d', '--dry-run', is_flag=True, default=False,
              help='Dry run: do not actually make any steps but act as if.')
@click.option('--no-color', is_flag=True, default=False, help='Turn off color output.')
@click.option('-V', '--verbose', is_flag=True, default=False, help='Be verbose.')
@click.option('-v', '--version', is_flag=True, default=False, help='Show version information and exit.')
@click.pass_context
def cli(ctx: click.Context,
        dry_run: bool = False,
        no_color: bool = False,
        verbose: bool = False,
        version: bool = False) -> None:
    Config().dry_run = dry_run
    Config().no_color = no_color
    Config().verbose = verbose
    if version:
        show_version()
        ctx.exit(0)
    if ctx.invoked_subcommand is None:
        ctx.fail('Missing command.')


@cli.command()
@click.option('--ssl', is_flag=True, default=False, help='Connect via SSL (e.g. for MS Exchange).')
@click.argument('CONNECT', required=True, nargs=1)
@click.argument('MAILBOX', required=True, nargs=1)
def clean(ssl: bool = False, connect: str = None, mailbox: str = None) -> None:
    """Delete empty mailboxes with no mail or child mailbox.

    \b
    CONNECT holds the connection details. Syntax is USER[:PASS]@HOST[:PORT]
    like 'john@example.com' or 'bob:mysecret@mail-server.com:143'.
    If password PASS is omitted you are asked for it.

    MAILBOX is the mailbox to start cleaning
    """
    Config().ssl = ssl
    host, port, username, password = Connection.parse(connect)
    con = Connection(host, port, username, password)

    mbs = con.mailboxes(mailbox)
    for mb in sorted(mbs):

        mbs[mb].expunge()
        mail_count = mbs[mb].select()
        if mail_count == 0 and not mbs[mb].children:
            if Config().verbose is True:
                mb_output = color.mailbox(mb)
                sys.stderr.write(f'Mailbox: {mb_output} - removing (no mails, no children)\n')
            if Config().dry_run is False:
                mbs[mb].delete()


@cli.command()
@click.option('--ssl', is_flag=True, default=False, help='Connect via SSL (e.g. for MS Exchange).')
@click.argument('CONNECT', required=True, nargs=1)
@click.argument('MAILBOX', required=True, nargs=1)
@click.argument('FOLDER', required=True, nargs=1)
def download(ssl: bool = False, connect: str = None, mailbox: str = None, folder: str = None) -> None:
    """Recursively download messages from an IMAP folder.

    \b
    CONNECT holds the connection details. Syntax is USER[:PASS]@HOST[:PORT]
    like 'john@example.com' or 'bob:mysecret@mail-server.com:143'.
    If password PASS is omitted you are asked for it.

    MAILBOX is the mailbox name to start downloading.

    FOLDER is the local target folder to download mails to.
    """
    if Config().verbose:
        sys.stderr.write("Recursively downloading messages from IMAP4 '" +
                         color.mailbox(mailbox) +
                         "' to folder '" +
                         folder + "'")
    try:
        os.makedirs(folder)
    except FileExistsError:
        pass
    except Exception as e:
        sys.stderr.write(color.error(f"Failed to create/access folder '{folder}':\n" + str(e)) + '\n')
        sys.exit(1)

    Config().ssl = ssl
    host, port, username, password = Connection.parse(connect)
    con = Connection(host, port, username, password)

    mbs = con.mailboxes(mailbox)
    for mb_name in sorted(mbs):

        m = mbs[mb_name]
        mb_name_output = color.mailbox(mb_name)
        mail_count = m.select()
        if mail_count > 0:

            mail_folder = os.path.join(folder, mb_name.replace(m.delimiter, os.sep))
            sys.stderr.write('Downloading ' + str(mail_count) +
                             f" mails from mailbox '{mb_name_output}' to '{mail_folder}'\n")

            r, d = m.search('ALL')
            if not r == 'OK':
                sys.stderr.write(color.error('Failed to list messages in mailbox.\n'))
                continue

            for m_id in d[0].decode().split(' '):

                sys.stdout.write(f'Fetching message {m_id}\n')
                r, mail_header = m.fetch(m_id, '(BODY.PEEK[HEADER])')
                try:
                    header_line = mail_header[0][1].split(b'\r\n')
                    for l in header_line:
                        if l.startswith(b'Date:'):
                            t = email.utils.parsedate(str(l)[8:])
                            if t:
                                filename = str(time.mktime(t)) + ".mail"
                                break
                            else:
                                sys.stderr.write(color.error('Failed to parse timestamp: ' + str(l) + '\n'))
                                sys.exit(1)

                except Exception as e:
                    sys.stderr.write(color.error('Failed to fetch message header:\n' + str(e) + '\n'))
                    sys.exit(1)

                if filename is None:
                    sys.stderr.write(color.error('Cannot deduce filename for mail.\n'))
                    sys.exit(1)

                sys.stderr.write(f'Writing mail as "{filename}"\n')
                r, mail_content = m.fetch(m_id, '(BODY[])')
                if not r == 'OK':
                    sys.stderr.write(color.error('Failed to fetch mail body.\n'))
                    sys.exit(1)

                try:
                    try:
                        os.makedirs(mail_folder)
                    except:
                        pass
                    f = open(os.path.join(mail_folder, filename), 'wb')
                    f.write(mail_content[0][1])
                    f.close()
                except Exception as e:
                    print("Failed to write to mail file: " + str(e))
                    sys.exit(1)


def max_year() -> int:
    """Returns the maximum year for which mails < max_year() are considered old.

    :return:    most recent year for which mails are old
    """
    return datetime.date(datetime.date.today().year - 1, 1, 1).year


@cli.command()
@click.option('--ssl', is_flag=True, default=False, help='Connect via SSL (e.g. for MS Exchange).')
@click.option('-o', '--omit-mailbox', type=str, default=None, help='List of mailboxes to ignore.')
@click.option('-y', '--year', type=int, default=None, help='Any mail before 1st January this year are considered old.')
@click.argument('CONNECT', required=True, nargs=1)
@click.argument('MAILBOX-FROM', required=True, nargs=1)
@click.argument('MAILBOX-TO', required=True, nargs=1)
def move(ssl: bool = False,
         omit_mailbox: str = None,
         year: int = None,
         connect: str = None,
         mailbox_from: str = None,
         mailbox_to: str = None) -> None:
    """Move old emails to target mailbox.

    \b
    CONNECT holds the connection details. Syntax is USER[:PASS]@HOST[:PORT]
    like 'john@example.com' or 'bob:mysecret@mail-server.com:143'.
    If password PASS is omitted you are asked for it.

    MAILBOX-FROM is the mailbox to start moving from. Use double quotes
    if name contains spaces.

    MAILBOX-TO is the to move to. Use double quotes if name contains spaces.
    """
    Config().ssl = ssl
    host, port, username, password = Connection.parse(connect)
    con = Connection(host, port, username, password)

    omit = []
    if omit_mailbox is not None:
        omit = omit_mailbox.split(',')
    if year is None:
       year = max_year()
    if Config().verbose:
        sys.stderr.write(f'Year sent of mails to be moved: < {year}\n')

    mbs = con.mailboxes(mailbox_from)
    for mb in sorted(mbs):

        mb_from_output = color.mailbox(mb)
        if mbs[mb] is None:
            continue
        if mb in omit:
            if Config().verbose:
                sys.stderr.write(f'Omitting mailbox {mb_from_output}\n')
            continue

        if Config().verbose:
            sys.stderr.write(f'Checking mailbox {mb_from_output}...\n')

        mails_all, mails_seen, mails_deleted, mails_per_year = mbs[mb].inspect()
        for y in mails_per_year:
            if y < year:
                archive_mailbox = mailbox_to + mbs[mb].delimiter + str(y) + mbs[mb].delimiter + mb
                if ' ' in archive_mailbox:
                    archive_mailbox = '"' + archive_mailbox + '"'
                mb_to_output = color.mailbox(archive_mailbox)

                mails_to_move = len(mails_per_year[y])
                sys.stdout.write(f'Mailbox: {mb_from_output} - moving {mails_to_move} mails to {mb_to_output}\n')
                if Config().dry_run is False:
                    con.create_mailbox(archive_mailbox, mbs[mb].delimiter)
                    mbs[mb].copy(mails_per_year[y], archive_mailbox)
                    mbs[mb].store(mails_per_year[y], '+FLAGS', r'(\Deleted)')
                    mbs[mb].expunge()


@cli.command()
@click.option('--ssl', is_flag=True, default=False, help='Connect via SSL (e.g. for MS Exchange).')
@click.option('-m', '--mailbox', help='Top mailbox to start scanning. Use quotes if name contains spaces.')
@click.option('-l', '--list-boxes-only', is_flag=True, default=False,
              help='Only list mailbox, do not examine each mail therein.')
@click.argument('CONNECT', required=True, nargs=1)
def scan(ssl: bool = False, mailbox: str = None, list_boxes_only: bool = False, connect: str = None) -> None:
    """Scan IMAP folders.

    \b
    CONNECT holds the connection details. Syntax is USER[:PASS]@HOST[:PORT]
    like 'john@example.com' or 'bob:mysecret@mail-server.com:143'.
    If password PASS is omitted you are asked for it.
    """
    Config().ssl = ssl
    host, port, username, password = Connection.parse(connect)
    con = Connection(host, port, username, password)
    mbs = con.mailboxes(Mailbox.strip_path(mailbox))
    header_shown = False
    for mb in sorted(mbs):

        if list_boxes_only is False:

            if not header_shown:
                print('%-70s   all mails   seen mails   deleted mails' % 'Mailbox name')
                print('%s-----------------------------------------' % ('-' * 70))
                header_shown = True

            mails_all, mails_seen, mails_deleted, mails_per_year = mbs[mb].inspect()
            if Config().no_color:
                print('%-70s       %5d        %5d           %5d' %
                      (color.mailbox(mb), len(mails_all), len(mails_seen), len(mails_deleted)))
            else:
                print('%-79s       %5d        %5d           %5d' %
                      (color.mailbox(mb), len(mails_all), len(mails_seen), len(mails_deleted)))

        else:
            if not header_shown:
                print('Mailboxes')
                print('%s-----------------------------------------' % ('-' * 70))
                header_shown = True
            print(color.mailbox(mb))


def show_version() -> None:
    """Shows the program version."""
    from . import __version__
    print('imap-archiver V' + __version__)
