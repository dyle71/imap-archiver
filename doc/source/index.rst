.. imap-archiver documentation master file, created by
   sphinx-quickstart on Wed Mar  1 11:09:16 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to imap-archiver's documentation!
=========================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   code

Indices and tables
==================

* :ref:`genindex`

.. * :ref:`modindex`
.. * :ref:`search`

Sample:
$ bin/imaparchiver.py -V move --omit-mailbox INBOX dyle@dyle.org@dyle.org INBOX Archives
$ bin/imaparchiver.py -V move dyle@dyle.org@dyle.org '"INBOX.Persons.Wohlfahrt Stephanie"' Archives
