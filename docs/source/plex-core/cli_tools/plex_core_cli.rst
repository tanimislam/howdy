================================================
Core Command Line Utilities
================================================

This section describes the two Plexstuff core command line utilities.

* ``plex_core_cli.py`` shows the list of email addresses, and names, of Plex account holders who have access to your Plex server. It can also show emails and names of all people who can receive email notifications about your Plex server. One can also change the list of email addresses that are notified by email of the Plex server.

* ``plex_deluge_console.py`` is a mocked up Deluge_ client, whose operation is very similar to the `deluge-console <deluge_console_>`_ command line interface. It is designed for the most common operations of `deluge-console <deluge_console_>`_, using Deluge_ server settings that are described in :numref:`Plexstuff Settings Configuration` and :numref:`Login Services`.

* ``plex_resynclibs.py`` summarizes information about the Plex servers to which you have access.

* ``plex_store_credentials.py`` sets up the Google OAuth2 services authentication from the command line, similarly to what ``plex_config_gui.py`` does as described in :numref:`Summary of Setting Up Google Credentials` and in :numref:`Music Services` when setting up the `unofficial Google Music API <https://unofficial-google-music-api.readthedocs.io/en/latest>`_.

* ``rsync_subproc.py`` rsync_ copies (and removes) files from the remote server and optional remote subdirectory, to the local server and local directory, or vice-versa. This tool also allows one to update the location of the remote server, the remote subdirectory, and the local subdirectory. The update of the remote path, and local and remote subdirectories, can also be changed through the ``plex_config_gui.py`` GUI, as described in :numref:`Local and Remote (Seedhost) SSH Setup` and :numref:`Login Services` (see the screen shot in :numref:`login_step02_settings`).

``plex_core_cli.py``
^^^^^^^^^^^^^^^^^^^^
The help output, when running ``plex_core_cli.py -h``, produces the following.

.. code:: bash

   Usage: plex_core_cli.py [options]

   Options:
	-h, --help            show this help message and exit
  	--username=USERNAME   Your plex username.
  	--password=PASSWORD   Your plex password.
  	--friends             Get list of guests of your Plex server.
  	--mappedfriends       Get list of guests with mapping, of your Plex server.
  	--addmapping          If chosen, then add extra friends from Plex friends.
  	--guestemail=GUEST_EMAIL
		              Name of the Plex guest email.
        --newemails=NEW_EMAILS
			      Name of the new emails associated with the Plex guest
                              email.
        --replace_existing    If chosen, replace existing email to send newsletter
                              to.


As described in the above section, this CLI can do the following *operations*.

* list the email addresses, with names (if found), of friends of your Plex_ server.

* list the email addresses, with names (if found), of *all* people who have access to your Plex_ server.

* change those people who can have access to your Plex_ server.

There are two parts to this tool: *authentication* and *operation*. Each *operation* with ``plex_core_cli.py`` must be run with a given *authorization*. For example, to get a list of friends of the Plex_ server by giving the Plex_ username and password for your Plex_ server, you would run.

.. code:: bash

   plex_core_cli.py --username=XXXX --password=YYYY --friends

Authentication happens in two ways.

* by providing the *username* and *password* for the Plex_ account that runs your Plex_ server. Here, provide it with,

  .. code:: bash

     plex_core_cli.py --username=XXXX --password=YYYY ...

  here, ``...`` refers to subsequent commands. One must give a valid *username* and *password*, otherwise the program exits.

* by implicitly using the Plex_ authorizations stored in ``~/.config/plexstuff/app.db``. Here, no extra authorization needs to be provided.

Here is how to do each of the three *operations*.

* to list the email addresses and names of the Plex_ friends, run this way using implicit authorization, for example.

  .. code:: bash

     plex_core_cli.py --friends

  this will produce this type of output.

  .. code:: bash

     XX HAVE FOUND NAMES, 0 DO NOT HAVE FOUND NAMES

     XX PLEX FRIENDS WITH NAMES

     NAME                       |  EMAIL
     ---------------------------|--------------------------------
     AAAAA                      |  A@AA.com
     BBBBB                      |  B@BB.com
     CCCCC                      |  C@CC.com
     DDDDD                      |  D@DD.com
     EEEEE                      |  E@EE.com
     ...


  this tool gets the names for each email address from the Google contacts on your authenticated Google account.

* to list the email addresses and names of the people who can receive Plex_ newsletter and notification emails, run this way using implicit authorization, for example.

  .. code:: bash

     plex_core_cli.py --mappedfriends

  this will produce this type of output.

  .. code:: bash

     XX HAVE FOUND NAMES, 0 DO NOT HAVE FOUND NAMES

     XX MAPPED PLEX FRIENDS WITH NAMES

     NAME                       |  EMAIL
     ---------------------------|--------------------------------
     AAAAA                      |  A@AA.com
     BBBBB                      |  B@BB.com
     CCCCC                      |  C@CC.com
     DDDDD                      |  D@DD.com
     EEEEE                      |  E@EE.com
     ...


  this tool gets the names for each email address from the Google contacts on your authenticated Google account.

* to add new emails that will reveice Plex_ newsletter or notification emails, here we run with implicit authorization and add two new emails (``A@XXX.com`` and ``A@YYY.com``) associated with a Plex_ friend with email account ``A@AA.com``. There can be two ways email addresses are added.

  1. to add these new emails while also getting emails at ``A@AA.com``, run the following command,

     .. code:: bash

     	plex_core_cli.py --addmapping --guestemail=A@AA.com --newemails=A@XXX.com,A@YYY.com

  2. to add these new emails while no longer getting emails at ``A@AA.com``, run the following command but with ``--replace_existing``,

     .. code:: bash

     	plex_core_cli.py --addmapping --guestemail=A@AA.com --newemails=A@XXX.com,A@YYY.com --replace_existing
  

  Note that ``A@AA.com`` must be a friend email of the Plex_ server, otherwise this operation will not work.

``plex_deluge_console.py``
^^^^^^^^^^^^^^^^^^^^^^^^^^

``plex_resynclibs.py``
^^^^^^^^^^^^^^^^^^^^^^^^^^

``plex_store_credentials.py``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ 

``rsync_subproc.py``
^^^^^^^^^^^^^^^^^^^^


.. _Deluge: https://en.wikipedia.org/wiki/Deluge_(software)
.. _deluge_console: https://whatbox.ca/wiki/Deluge_Console_Documentation
.. _rsync: https://en.wikipedia.org/wiki/Rsync
.. _Plex: https://plex.tv
