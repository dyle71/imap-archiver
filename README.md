imaparchiver
============

This tool moves email messages and structures from imap accounts to dedicated archive folders.

Example:

    Inbox /
        - No, really            01.03.2015
        - Hello my friend       04.10.2014
        - A Message             14.04.2013
        Friends /
            Joe /
                - Nice Concert          12.04.2014
                - Let us have a beer    01.11.2013
            Bill /
                - Where is my shirt?    23.06.2013

to

    Inbox /
        - No, really            01.03.2015
        - Hello my friend       04.10.2014
        Friends /
            Joe /
                - Nice Concert          12.04.2014
    Archive /
        2013 /
            Inbox /
                - A Message             14.04.2013
            Friends /
                Joe /
                    - Let us have a beer    01.11.2013
                Bill /
                    - Where is my shirt?    23.06.2013

So your IMAP folders wont be bloated with old messages but are cleaned continually. Ideally
you may download all the mails from last year but one and clean you IMAP Account.

```
usage: imaparchiver.py [-h] [-d] [-v] {scan,move,clean} ...

IMAP-Archiver

positional arguments:
  {scan,move,clean}  sub-commands
    scan             scan IMAP folders
    move             move old emails to target mailbox
    clean            delete empty mailboxes with no mail or child mailbox.

optional arguments:
  -h, --help         show this help message and exit
  -d, --dry-run      Dry run: do not actually make any steps but act as if.
  -v, --version      Show version information and exit.
```

Detailed command options:

Scan: scans the IMAP account for old mails.

```
imaparchiver.py scan [-h] [-m MAILBOX] [-l] CONNECT-URL

positional arguments:
  CONNECT-URL           Connection details. Syntax is USER[:PASS]@HOST[:PORT]
                        like 'john@example.com' or 'bob:mysecret@mail-
                        server.com:143'. If password PASS is omitted you are
                        asked for it.

optional arguments:
  -h, --help            show this help message and exit
  -m MAILBOX, --mailbox MAILBOX
                        Top mailbox to start scanning.
  -l, --list-boxes-only
                            Only list mailbox, do not examine each mail therein.
```

Move: move old mails to dediacted sub folder

```
imaparchiver.py move [-h] CONNECT-URL MAILBOX-FROM MAILBOX-TO

positional arguments:
  CONNECT-URL   Connection details. Syntax is USER[:PASS]@HOST[:PORT] like
                'john@example.com' or 'bob:mysecret@mail-server.com:143'. If
                password PASS is omitted you are asked for it.
  MAILBOX_FROM  mailbox to start moving from.
  MAILBOX_TO    mailbox to move to.

optional arguments:
  -h, --help    show this help message and exit
```

Clean/Purge: remove empty (no mails, no child) mailboxes at the bottom of the mailbox tree

```
imaparchiver.py clean [-h] CONNECT-URL MAILBOX

positional arguments:
  CONNECT-URL  Connection details. Syntax is USER[:PASS]@HOST[:PORT] like
               'john@example.com' or 'bob:mysecret@mail-server.com:143'. If
               password PASS is omitted you are asked for it.
  MAILBOX      Top mailbox to start cleaning.

optional arguments:
  -h, --help   show this help message and exit
```

Examples:

Scan all folders:

```
$ imap-archiver.py scan --mailbox INBOX john@example.com
no user password given. plase enter password for user 'john':
john logged in
mailbox: "INBOX" - ALL: 111, SEEN: 111, OLD: 24
mailbox: "INBOX.Persons" - ALL: 0, SEEN: 0, OLD: 0
mailbox: "INBOX.Persons.My Friend" - ALL: 4, SEEN: 4, OLD: 2
...
```

Move old emails:

```
$ imap-archiver.py move john@example.com INBOX Archives
```

Clean or prune empty subfolders:

```
$ imap-archiver.py clean john@example.com INBOX
```


Notes
-----

* This tool uses Python3. Therefore the Sphinx installment for documentation purpose should also be running in Python 3.

  You can achieve this by
  ```
  $ pip3 install Sphinx
  ```

* When your username contains the '@' (like my.name@mailprovider.com) and you log into a server called "mail.com" then the CONNECT-URL is ```my.name@mailprovider.com@mail.com```.


(C)opyright 2015-2017, Oliver Maurhart
dyle@dyle.org
