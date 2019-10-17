================================================
Core Command Line Utilities
================================================

This section describes the two Plexstuff core command line utilities.

* :ref:`plex_core_cli.py` shows the list of email addresses, and names, of Plex account holders who have access to your Plex server. It can also show emails and names of all people who can receive email notifications about your Plex server. One can also change the list of email addresses that are notified by email of the Plex server.

* :ref:`plex_deluge_console.py` is a mocked up Deluge_ client, whose operation is very similar to the `deluge-console <deluge_console_>`_ command line interface. It is designed for the most common operations of `deluge-console <deluge_console_>`_, using Deluge_ server settings that are described in :numref:`Plexstuff Settings Configuration` and :numref:`Login Services`.

* :ref:`plex_resynclibs.py` summarizes information about the Plex_ servers to which you have access, summarizes the Plex_ library information for those Plex_ servers which you own, and can also refresh those libraries in your owned servers.

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
The help output, when running ``plex_resynclibs.py -h``, produces the following.

.. code-block:: bash

   Usage: plex_resynclibs.py [options]

   Options:
      -h, --help            show this help message and exit
      --libraries           If chosen, just give the sorted names of all libraries
                            in the Plex server.
      --refresh             If chosen, refresh a chosen library in the Plex
                            server. Must give a valid name for the library.
      --summary             If chosen, perform a summary of the chosen library in
                            the Plex server. Must give a valid name for the
                            library.
      --library=LIBRARY     Name of a (valid) library in the Plex server.
      --servername=SERVERNAME
                            Optional name of the server to check for.
      --servernames         If chosen, print out all the servers owned by the
                            user.
      --noverify            Do not verify SSL transactions if chosen.

``--noverify`` is a standard option in many of the Plexstuff CLI and GUIs to ignore verification of SSL transactions. It is optional and will default to ``False``.

When running this CLI, you must choose *one and only one* of these options.

* ``--servernames`` gives you the list of the Plex_ servers to which you have access, and which you own.

* ``--libraries``  prints out a list of the libraries on the Plex_ server you chose and which you own. Here you can explicitly choose a Plex_ server by name with ``--servername=SERVERNAME`` or have a default one you own chosen for you.

* ``--summary`` prints out a summary of the Plex_ library you have chosen with ``--library=LIBRARY``.

* ``--refresh`` refreshes the Plex_ library you have chosen withh ``--library=LIBRARY``.

Here I find it useful to show how this tool works by example.

1. First, we can determine those Plex_ servers to which we have access

   .. code-block:: bash
   
      plex_resynclibs.py --servernames

   This will print out a nicely formatted table. Each row is a Plex_ server. The columns are the server's name, whether we own it, and its remote URL with port (which is of the form ``https://IP-ADDRESS:PORT``).

   .. code-block:: bash

      Name           Is Owned    URL
      -------------  ----------  ---------------------------
      tanim-desktop  True        https://IP-ADDR1:PORT1
      XXXX    	     False       https://IP-ADDR2:PORT2
      YYYY	     False       https://IP-ADDR3:PORT3

2. Now we can look for the Plex_ libraries in the Plex_ server *which we own*. If we don't choose a Plex_ server with ``--servername=SERVERNAME``, then the first one in the row which we own will be chosen by default. The syntax is,

   .. code-block:: bash

      plex_resynclibs.py --servername=tanim-desktop --libraries

   This will print out a nicely formatted table. Each row is a library. There is a column of the library's name and its type. I have only shown three of the six Plex_ libraries on my server.

   .. code-block:: bash

      Here are the 6 libraries in this Plex server: tanim-desktop.

      Name                Library Type
      ------------------  --------------
      Movies              movie
      Music               artist
      XXXX		  AAAA
      YYYY       	  BBBB
      TV Shows            show
      ZZZZ		  CCCC

   ``movie`` means Movies, ``show`` means TV shows, and ``artist`` means music.

3. We can get summary information about each Plex_ library with the ``--summary`` flag and ``--library=LIBRARY``. Here are the three examples on getting summary information on a movie, TV show, and music library. This summary information may take a while.

   * On a movie library.

     .. code-block:: bash

        tanim-desktop $ plex_resynclibs.py --servername=tanim-desktop --library=Movies --summary
	
	"Movies" is a movie library. There are 1886 movies here. The total size of movie media is 1.632 TB.
	The total duration of movie media is 4 months, 20 days, 19 hours, 50 minutes, and 22.054 seconds.

   * On a TV show library.

     .. code-block:: bash

        tanim-desktop $ plex_resynclibs.py --servername=tanim-desktop --library="TV Shows" --summary

	"TV Shows" is a TV library. There are 21167 TV files in 236 TV shows. The total size of TV media is
	5.301 TB. The total duration of TV shows is 1 year, 2 months, 15 days, 11 hours, 42 minutes, and
	6.409 seconds.

   * On a music library.

     .. code-block:: bash

        tanim-desktop $ plex_resynclibs.py --servername=tanim-desktop --library=Music --summary

	"Music" is a music library. There are 9911 songs made by 814 artists in 1549 albums. The total size
	of music media is 54.785 GB. The total duration of music media is 26 days, 18 hours, 59 minutes, and
	55.185 seconds.

4. Finally, we can refresh a library that we specify with the ``--refresh`` flag and ``--library=LIBRARY``. Here are three examples on how to refresh the movie, TV show, and music library.

   .. code-block:: bash

      plex_resynclibs.py --servername=tanim-desktop --library=Movies --refresh
      plex_resynclibs.py --servername=tanim-desktop --library="TV Shows" --refresh
      plex_resynclibs.py --servername=tanim-desktop --library=Music --refresh


.. _plex_store_credentials.py_label:

plex_store_credentials.py
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ 
:numref:`Core Command Line Utilities` describes this executable's functionality very well. First, run this executable, ``plex_store_credentials.py``, which will return this interactive text dialog in the shell.

.. code-block:: bash

   tanim-desktop $ plex_store_credentials.py
   Please go to this URL in a browser window:https://accounts.google.com/o/oauth2/auth...
   After giving permission for Google services on your behalf,
   type in the access code:

Second, go to the URL to which you are instructed. Once you copy that URL into your browser, you will see a browser window as shown in :ref:`Step #3 <google_step03_authorizeaccount>`, :ref:`Step #5 <google_step05_scaryscreen>`, :ref:`Step #6 <google_step06_allowbutton>`, and :ref:`Step #7 <google_step07_oauthtokencopy>` in :numref:`Summary of Setting Up Google Credentials`.

Third, paste the code as described in :ref:`Step #7 <google_step07_oauthtokencopy>` into the interactive text dialog, ``...type in the access code:``. Once successful, you will receive this message in the shell,

.. code-block:: bash

   Success. Stored GOOGLE credentials.

.. _rsync_subproc.py_label:

rsync_subproc.py
^^^^^^^^^^^^^^^^^^^^
The help output, when running ``rsync_subproc.py -h``, produces the following.

.. code-block:: bash

   Usage: rsync_subproc.py [options]

   Options:
     -h, --help            show this help message and exit
     -S STRING, --string=STRING
                           the globbed string to rsync from on the remote
                           account. Default is "*.mkv".
     -N NUMTRIES, --numtries=NUMTRIES
                           number of attempts to go through an rsync process.
                           Default is 10.
     -D, --debug           if chosen, then write debug output.
     -R, --reverse         If chosen, push files from local server to remote.
                           Since files are deleted from source once done, you
                           should probably make a copy of the source files if you
                           want to still keep them afterwards.
     -P, --push            push RSYNC credentials into configuration file.
     -L LOCAL_DIR          Name of the local directory into which we download
                           files and directory. Default is XXXX.
     --ssh=SSHPATH         SSH path from which to get files.
     --subdir=SUBDIR       name of the remote sub directory from which to get
                           files. Optional.

This executable provides a convenient higher-level command-line interface to rsync_ uploading and downloading that resumes on transfer failure, and deletes the origin files once the transfer is complete. One also does not need to execute this command in ``LOCAL_DIR``.

The main rsync_ based uploading and downloading is described in :ref:`rsync_ based functionality`, and setting the SSH credentials, and local and remote locations, is described in :ref:`rsync_subproc settings with --push`.

rsync_ based functionality
---------------------------
One can either upload files and directories to, or download files and directories from, the remote location and the remote subdirectory (which we call ``SUBDIR``). The local directory is called ``LOCAL_DIR``. If the remote directory is not defined, it is *by default* the home directory of that account.

The debug flag, ``-D`` or ``--debug``, is extremely useful, as it displays the lower level shell command that is executed to get the rsync_ transfer going.

The files or directories are selected with ``-S STRING`` or ``--string=STRING`` and follows the standard `POSIX globbing <https://en.wikipedia.org/wiki/Glob_(programming)>`_ convention. For instance, you can specify ``-S "The*"`` (``STRING`` in quotations) to select the remote directory ``The Simpsons`` to download. In order to simplify this CLI's behavior,

* There can be no spaces in the ``STRING`` selection.

* The ``STRING`` selection does not behave as a `Regular expression <https://en.wikipedia.org/wiki/Regular_expression>`_.

The ``-N`` or ``--numtries`` flag sets the number of tries that the rsync_ process will attempt before giving up or finishing the transfer. The default is 10, but this number must be :math:`\ge 1`.

To download a remote directory (``SUBDIR/Ubuntu_18.04``) until success into ``LOCAL_DIR``, and delete all files inside the remote directory, you can run this command with debug.

.. code-block:: bash

   tanim-desktop $ rsync_subproc.py -D -S "Ubuntu_*"
   STARTING THIS RSYNC CMD: rsync --remove-source-files -P -avz --rsh="/usr/bin/sshpass XXXX ssh" -e ssh YYYY@ZZZZ:SUBDIR/Ubuntu_* LOCAL_DIR
   TRYING UP TO 10 TIMES.
   
   SUCCESSFUL ATTEMPT 1 / 10 IN 25.875 SECONDS.

Note that after a period of time (here, 25.875 seconds), the process will terminate with either a descriptive success or descriptive failure message. Note that in the debug output, the SSH password is not printed out (except for an ``XXXX``).

To upload the local directory (``LOCAL_DIR/Ubuntu_18.04``) until success into ``SUBDIR``, and delete all files inside the local directory, you can run this command with debug and the ``-R`` or ``--reverse`` flag.

.. code-block:: bash

   tanim-desktop $ rsync_subproc.py -D -R -S Ubuntu*
   STARTING THIS RSYNC CMD: rsync --remove-source-files -P -avz --rsh="/usr/bin/sshpass XXXX ssh" -e ssh LOCAL_DIR/Ubuntu_18.04 YYYY@ZZZZ:SUBDIR/
   TRYING UP TO 10 TIMES.
   
   SUCCESSFUL ATTEMPT 1 / 10 IN 264.802 SECONDS.


rsync_subproc settings with --push
------------------------------------
Running ``rsync_subproc.py -P`` or ``rsync_subproc.py --push`` will update or set the SSH settings for the remote server, and the local and remote subdirectories. :numref:`Local and Remote (Seedhost) SSH Setup` and :numref:`Login Services` (see the screen shot in :numref:`login_step02_settings`) describe the form that these settings take.

* the format of the SSH setting is ``username@ssh_server``.

* the ``SUBDIR`` is located relative to the ``usename`` home directory on ``ssh_server``, ``$HOME/SUBDIR``.

* the ``LOCAL_DIR`` local directory is described with an absolute path.

Thus, to set settings for ``rsync_subproc.py``, one would run,

.. code-block:: bash

   rsync_subproc.py -P -L LOCAL_DIR --ssh=username@ssh_server --subdir=SUBDIR

Note that here, the SSH password is the same as the remote Deluge_ server's password. See, e.g., :numref:`plex_deluge_console.py` or :numref:`Local and Remote (Seedhost) SSH Setup` and figures therein.

.. _Deluge: https://en.wikipedia.org/wiki/Deluge_(software)
.. _deluge_console: https://whatbox.ca/wiki/Deluge_Console_Documentation
.. _rsync: https://en.wikipedia.org/wiki/Rsync
.. _Plex: https://plex.tv
.. _`Magnet URI`: https://en.wikipedia.org/wiki/Magnet_URI_scheme
.. _SQLite3: https://www.sqlite.org/index.html
