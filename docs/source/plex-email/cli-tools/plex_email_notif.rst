.. _plex_email_notif.py_label:

================================================
plex_email_notif.py
================================================

This is documentation for the Plexstuff one-off email announcement commnand line interface, ``plex_email_notif.py``. You specify a simple email, with a simple text subject line a simple plaintext body, to email either to yourself at your Plex_ account or also to friends of your Plex_ server. The list of your Plex_ server friends can be accessed using :ref:`plex_core_cli.py`, and specifically this command,

.. code-block:: bash

   plex_core_cli.py --friends

that produces a list of friends with and without associated names in your Google Contacts.

.. _plex_core_cli_example:

.. figure:: plex-email-cli-figures/plex_core_cli_example.png
   :width: 100%
   :align: center

The help output, when running ``plex_email_notif.py -h``, produces the following.

.. code-block:: bash

   Usage: plex_email_notif.py [options]

   Options:
     -h, --help         show this help message and exit
     --debug            Run debug mode if chosen.
     --test             Send a test notification email if chosen.
     --subject=SUBJECT  Subject of notification email. Default is "Plex
                        notification for November 03, 2019.".
     --body=BODY        Body of the email to be sent. Default is "This is a test."

* The ``--debug`` flag prints out :py:const:`DEBUG <logging.DEBUG>` level :py:mod:`logging <logging>` output.

* ``--subject`` specifies the subject line. If it is not specified, then the subject is ``"Plex notification for <DATE>"``, where ``<DATE>`` is the current date in ``MONTH DAY, YEAR`` format (such as January 01, 2019).

* ``--body`` specifies the text body of the email. if it is not specified, then the default body is ``"This is a test."``.

* ``--test`` just sends the email to your Plex_ email account. I find it useful to run with ``--test`` first, until the subject and the body of the email is correct. Without the ``--test`` flag, this email is sent to all the friends of youe Plex_ server (see :numref:`plex_core_cli_example`).

.. _Plex: https://plex.tv
