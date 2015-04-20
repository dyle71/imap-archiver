imap-archiver
=============

This tool moves email messages and structures from imap accounts to dedicated archive folders.

Example:

<<<

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
>>>

This should not touch the Inbox folder but all folders underneath and move the messages older
than a year to corresponding archive subfolders.

Like:

<<<

    Inbox /
        - No, really            01.03.2015
        - Hello my friend       04.10.2014
        - A Message             14.04.2013
        Friends /
            Joe /
                - Nice Concert          12.04.2014 
    Archive /
        2013 /
            Friends /
                Joe /
                    - Let us have a beer    01.11.2013
                Bill /
                    - Where is my shirt?    23.06.2013
>>>

So your IMAP folders wont be bloated with old messages but are cleaned continually. Ideally 
you may download all the mails from last year but one and clean you IMAP Account.

