================================================
Core Command Line Utilities
================================================

This section describes the two Plexstuff core command line utilities.

* :ref:`plex_core_cli.py` shows the list of email addresses, and names, of Plex account holders who have access to your Plex server. It can also show emails and names of all people who can receive email notifications about your Plex server. One can also change the list of email addresses that are notified by email of the Plex server.

* :ref:`plex_deluge_console.py` is a mocked up Deluge_ client, whose operation is very similar to the `deluge-console <deluge_console_>`_ command line interface. It is designed for the most common operations of `deluge-console <deluge_console_>`_, using Deluge_ server settings that are described in :numref:`Plexstuff Settings Configuration` and :numref:`Login Services`.

* :ref:`plex_resynclibs.py` summarizes information about the Plex servers to which you have access.

* :ref:`plex_store_credentials.py` sets up the Google OAuth2 services authentication from the command line, similarly to what ``plex_config_gui.py`` does as described in :numref:`Summary of Setting Up Google Credentials` and in :numref:`Music Services` when setting up the `unofficial Google Music API <https://unofficial-google-music-api.readthedocs.io/en/latest>`_.

* :ref:`rsync_subproc.py` rsync_ copies (and removes) files from the remote server and optional remote subdirectory, to the local server and local directory, or vice-versa. This tool also allows one to update the location of the remote server, the remote subdirectory, and the local subdirectory. The update of the remote path, and local and remote subdirectories, can also be changed through the ``plex_config_gui.py`` GUI, as described in :numref:`Local and Remote (Seedhost) SSH Setup` and :numref:`Login Services` (see the screen shot in :numref:`login_step02_settings`).

.. _plex_core_cli.py_label:

plex_core_cli.py
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

.. _plex_deluge_console.py_label:

plex_deluge_console.py
^^^^^^^^^^^^^^^^^^^^^^^^^^
This is a much reduced Deluge command line console client. It does the following operations: :ref:`torrent info (info)`, :ref:`removing torrents (rm or del)`, :ref:`adding torrents (add)`, :ref:`pausing and resuming torrents (pause or resume)`, and :ref:`pushing credentials (push)`. Running ``plex_deluge_console.py -h`` gives the following output.

.. code-block:: bash

   Possible commands: info, rm (del), add, pause, resume, push

By convention, the variable ``md5_trunc`` refers to a truncated initial substring of the full torrent's MD5 hash. For example, given an MD5 hash of a torrent, such as ``ed53ba61555cab24946ebf2f346752805601a7fb``, a possible ``md5_trunc`` is ``ed5``. One can specify a collection of multiple ``md5_trunc`` as long as they are valid and unique (such as ``md5_trunc_1, md5_trunc_2, ...``).

It may be convenient to have some useful BASH shortcuts for ``plex_deluge_console.py``, which you can store in ``~/.bashrc``. Here is a snippet of self-explanatory aliases I find useful.

.. code-block:: bash

   alias pdci='plex_deluge_console.py info'
   alias pdcr='plex_deluge_console.py rm'
   alias pdca='plex_deluge_console.py add'
   alias pdcp='plex_deluge_console.py pause'
   alias pdcres='plex_deluge_console.py resume'



torrent info (info)
--------------------
You can get nicely formatted information on a collection of torrents, or all torrents, through running ``plex_deluge_console.py info ...``. ``plex_deluge_console.py info`` will show nicely formatted information on ALL torrents.

.. code-block:: bash
   
   plex_deluge_console.py info
   Name: ubuntu-19.10-beta-desktop-amd64.iso	
   ID: ed53ba61555cab24946ebf2f346752805601a7fb
   State: Seeding
   Up Speed: 0.0 KiB/s
   Seeds: 0 (72) Peers: 0 (3) Availability: 0.00
   Size: 2.1 GiB/2.1 GiB Ratio: 0.000
   Seed time: 0 days 00:01:40 Active: 0 days 00:01:53
   Tracker status: ubuntu.com: Announce OK
   
   Name: ubuntu-19.10-beta-live-server-amd64.iso
   ID: ed4bd9a0aed4c5e5dd7911aa785a3d180e267e4d
   State: Downloading
   Down Speed: 901.9 KiB/s Up Speed: 0.0 KiB/s ETA: 0 days 00:12:58
   Seeds: 8 (21) Peers: 1 (1) Availability: 8.01
   Size: 5.0 MiB/691.0 MiB Ratio: 0.000
   Seed time: 0 days 00:00:00 Active: 0 days 00:00:05
   Tracker status: ubuntu.com: Announce OK
   Progress: 0.72% 	       [#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~]

You can give it a list of truncated MD5 hashes to get status information on selected torrents,

.. code-block:: bash

   plex_deluge_console.py info ed5
   Name: ubuntu-19.10-beta-desktop-amd64.iso
   ID: ed53ba61555cab24946ebf2f346752805601a7fb
   State: Seeding
   Up Speed: 112.2 KiB/s ETA: 0 days 02:47:24
   Seeds: 0 (72) Peers: 1 (3) Availability: 0.00
   Size: 2.1 GiB/2.1 GiB Ratio: 0.000
   Seed time: 0 days 00:03:44 Active: 0 days 00:03:57
   Tracker status: ubuntu.com: Announce OK
   

removing torrents (rm or del)
-------------------------------
You can remove some or all torrents by running ``plex_deluge_console.py rm`` or ``plex_deluge_console.py del``. You can access the help for this operation by running ``plex_deluge_console.py rm -h``.

.. code-block:: bash
   
   Usage: plex_deluge_console.py [options]
   
   Options:
     -h, --help         show this help message and exit
     -R, --remove_data  remove the torrent's data

* ``plex_deluge_console.py rm md5trunc_1 md5_trunc_2 ...`` removes specified torrents but keeps whatever data has been downloaded on the Deluge server. You would run this once the torrent's state was ``Seeding`` or ``Paused`` (see :ref:`torrent info (info)`).

* ``plex_deluge_console.py rm -R ...`` does the same, but also removes whatever data has been downloaded from the Deluge server.

* ``plex_deluge_console.py rm`` without specific torrents removes (or removes with deletion) ALL torrents from the Deluge server.

adding torrents (add)
-----------------------
You can add torrents to the Deluge server by running ``plex_deluge_console.py add``. You can add a torrent file as URL, a torrent file on disk, and a `Magnet URI`_.

* torrent file as remote URL:

.. code-block:: bash

   plex_deluge_console.py add http://releases.ubuntu.com/19.10/ubuntu-19.10-beta-live-server-amd64.iso.torrent

* torrent file on disk:

.. code-block:: bash

   plex_deluge_console.py add ubuntu-19.10-beta-desktop-amd64.iso.torrent

* `Magnet URI`_:

.. code-block:: bash

   plex_deluge_console.py add "magnet:?xt=urn:btih:49efb5fdd274abb26c5ea6361d1d9be28e4db2d3&dn=archlinux-2019.09.01-x86_64.iso&tr=udp://tracker.archlinux.org:6969&tr=http://tracker.archlinux.org:6969/announce"


pausing and resuming torrents (pause or resume)
-------------------------------------------------
You can pause torrents on the Deluge server by running ``plex_deluge_console.py pause``, and you can resume them by running ``plex_deluge_console.py resume``.


* You can pause/resume specific torrents by running ``plex_deluge_console.py pause md5trunc_1 md5_trunc_2 ...`` or ``plex_deluge_console.py resume md5trunc_1 md5_trunc_2 ...``.

* You can pause/resume ALL torrents on the Deluge server by not specifying any truncated MD5 hashes, ``plex_deluge_console.py pause`` or ``plex_deluge_console.py resume``.  

.. 28-09-2019: Pause and resume don't seem to be working right now when connecting to the Seedhost seedbox Deluge server.

pushing credentials (push)
----------------------------------
You can push new Deluge server credentials (URL, port, username, and password) to the SQLite3_ configuration database. Running ``plex_deluge_console.py push -h`` gives its help syntax,

.. code-block:: bash

   Usage: plex_deluge_console.py [options]

   Options:
     -h, --help           show this help message and exit
     --host=URL           URL of the deluge server. Default is localhost.
     --port=PORT          Port for the deluge server. Default is 12345.
     --username=USERNAME  Username to login to the deluge server. Default is
                       	  admin.
     --password=PASSWORD  Password to login to the deluge server. Default is
                       	  admin.

Push new Deluge server settings into the configuration database by running,

.. code-block:: bash

   plex_deluge_console.py push --host=HOST --port=PORT --username=USERNAME --password=PASSWORD

If those are valid settings, nothing more happens. If these are invalid settings, then specific error messages will print to the screen.

.. _plex_resynclibs.py_label:

plex_resynclibs.py
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. _plex_store_credentials.py_label:

plex_store_credentials.py
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ 

.. _rsync_subproc.py_label:

rsync_subproc.py
^^^^^^^^^^^^^^^^^^^^


.. _Deluge: https://en.wikipedia.org/wiki/Deluge_(software)
.. _deluge_console: https://whatbox.ca/wiki/Deluge_Console_Documentation
.. _rsync: https://en.wikipedia.org/wiki/Rsync
.. _Plex: https://plex.tv
.. _`Magnet URI`: https://en.wikipedia.org/wiki/Magnet_URI_scheme
.. _SQLite3: https://www.sqlite.org/index.html
