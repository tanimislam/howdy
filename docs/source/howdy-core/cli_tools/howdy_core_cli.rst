================================================
Howdy Core Command Line Utilities
================================================
This section describes the five Howdy core command line utilities.

* :ref:`howdy_core_cli` shows the list of email addresses, and names, of Plex account holders who have access to your Plex server. It can also show emails and names of all people who can receive email notifications about your Plex server. One can also change the list of email addresses that are notified by email of the Plex server.

* :ref:`howdy_deluge_console` is a mocked up Deluge_ client, whose operation is very similar to the `deluge-console <deluge_console_>`_ command line interface. It is designed for the most common operations of `deluge-console <deluge_console_>`_, using Deluge_ server settings that are described in :numref:`Howdy Settings Configuration` and :numref:`Login Services`.

* :ref:`howdy_resynclibs` summarizes information about the Plex_ servers to which you have access, summarizes the Plex_ library information for those Plex_ servers which you own, and can also refresh those libraries in your owned servers.

* :ref:`howdy_store_credentials` sets up the Google OAuth2 services authentication from the command line, similarly to what ``howdy_config_gui`` does as described in :numref:`Summary of Setting Up Google Credentials` and in :numref:`Music Services` when setting up the `unofficial Google Music API <https://unofficial-google-music-api.readthedocs.io/en/latest>`_.

* :ref:`rsync_subproc` rsync_ copies (and removes) files from the remote server and optional remote subdirectory, to the local server and local directory, or vice-versa. This tool also allows one to update the location of the remote server, the remote subdirectory, and the local subdirectory. The update of the remote path, and local and remote subdirectories, can also be changed through the ``howdy_config_gui`` GUI, as described in :numref:`Local and Remote (Seedhost) SSH Setup` and :numref:`Login Services` (see the screen shot in :numref:`login_step02_settings`).

* :ref:`get_book_tor` finds `Magnet links <Magnet URI_>`_ of ebooks, and by default prints out the chosen magnet link. This executable uses the Jackett_ server to search for ebooks, and can optionally upload these links to the specified Deluge_ server (see :numref:`Howdy Settings Configuration`). It borrows much of its workflow from :ref:`get_tv_tor` and :ref:`get_mov_tor`.

.. _howdy_core_cli_label:

howdy_core_cli
^^^^^^^^^^^^^^^^^^^^
The help output, when running ``howdy_core_cli -h``, produces the following.

.. code-block:: console

   usage: howdy_core_cli [-h] [--username USERNAME] [--password PASSWORD] [--friends] [--mappedfriends] [--addmapping] [--guestemail GUEST_EMAIL] [--newemails NEW_EMAILS] [--replace_existing]

   optional arguments:
     -h, --help            show this help message and exit
     --username USERNAME   Your plex username.
     --password PASSWORD   Your plex password.
     --friends             Get list of guests of your Plex server.
     --mappedfriends       Get list of guests with mapping, of your Plex server.
     --addmapping          If chosen, then add extra friends from Plex friends.
     --guestemail GUEST_EMAIL
			   Name of the Plex guest email.
     --newemails NEW_EMAILS
			   Name of the new emails associated with the Plex guest email.
     --replace_existing    If chosen, replace existing email to send newsletter to.

As described in the above section, this CLI can do the following *operations*.

* list the email addresses, with names (if found), of friends of your Plex_ server.

* list the email addresses, with names (if found), of *all* people who have access to your Plex_ server.

* change those people who can have access to your Plex_ server.

There are two parts to this tool: *authentication* and *operation*. Each *operation* with ``howdy_core_cli`` must be run with a given *authorization*. For example, to get a list of friends of the Plex_ server by giving the Plex_ username and password for your Plex_ server, you would run.

.. code-block:: console

   howdy_core_cli --username=XXXX --password=YYYY --friends

Authentication happens in two ways.

* by providing the *username* and *password* for the Plex_ account that runs your Plex_ server. Here, provide it with,

  .. code-block:: console

     howdy_core_cli --username=XXXX --password=YYYY ...

  here, ``...`` refers to subsequent commands. One must give a valid *username* and *password*, otherwise the program exits.

* by implicitly using the Plex_ authorizations stored in ``~/.config/plexstuff/app.db``. Here, no extra authorization needs to be provided.

Here is how to do each of the three *operations*.

* to list the email addresses and names of the Plex_ friends, run this way using implicit authorization, for example.

  .. code-block:: console

     howdy_core_cli --friends

  this will produce this type of output.

  .. code-block:: console

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

  .. code-block:: console

     howdy_core_cli --mappedfriends

  this will produce this type of output.

  .. code-block:: console

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

     .. code-block:: console

     	howdy_core_cli --addmapping --guestemail=A@AA.com --newemails=A@XXX.com,A@YYY.com

  2. to add these new emails while no longer getting emails at ``A@AA.com``, run the following command but with ``--replace_existing``,

     .. code-block:: console

     	howdy_core_cli --addmapping --guestemail=A@AA.com --newemails=A@XXX.com,A@YYY.com --replace_existing

  Note that ``A@AA.com`` must be a friend email of the Plex_ server, otherwise this operation will not work.

.. _howdy_deluge_console_label:

howdy_deluge_console
^^^^^^^^^^^^^^^^^^^^^^^^^^
This is a much reduced Deluge command line console client. It does the following operations: :ref:`torrent info (info)`, :ref:`removing torrents (rm or del)`, :ref:`adding torrents (add)`, :ref:`pausing and resuming torrents (pause or resume)`, and :ref:`pushing credentials (push)`. Running ``howdy_deluge_console -h`` gives the following output.

.. code-block:: console

   usage: howdy_deluge_console [-h] {info,resume,pause,rm,del,add,push} ...

   positional arguments:
     {info,resume,pause,rm,del,add,push}
			   Choose one of these three modes of operation: rm, add, pause, resume, or push.
       info                Print summary info on a specific torrent, or all torrents.
       resume              Resume selected torrents, or all torrents.
       pause               Pause selected torrents, or all torrents.
       rm (del)            Remove selected torrents, or all torrents.
       add                 Add a single torrent, as a magnet link or a file.
       push                Push settings for a new deluge server to configuration.

   optional arguments:
     -h, --help            show this help message and exit

By convention, the variable ``md5_trunc`` refers to a truncated initial substring of the full torrent's MD5 hash. For example, given an MD5 hash of a torrent, such as ``ed53ba61555cab24946ebf2f346752805601a7fb``, a possible ``md5_trunc`` is ``ed5``. One can specify a collection of multiple ``md5_trunc`` as long as they are valid and unique (such as ``md5_trunc_1, md5_trunc_2, ...``).

It may be convenient to have some useful BASH shortcuts for ``howdy_deluge_console``, which you can store in ``~/.bashrc``. Here is a snippet of self-explanatory aliases I find useful.

.. code-block:: console

   alias pdci='howdy_deluge_console info'
   alias pdcr='howdy_deluge_console rm'
   alias pdca='howdy_deluge_console add'
   alias pdcp='howdy_deluge_console pause'
   alias pdcres='howdy_deluge_console resume'

torrent info (info)
--------------------
You can get nicely formatted information on a collection of torrents, or all torrents, through running ``howdy_deluge_console info``. Running ``howdy_deluge_console info -h`` gives the following output.

.. code-block:: console

   usage: howdy_deluge_console info [-h] [-f] [torrent [torrent ...]]

   positional arguments:
     torrent     The hash ID, or identifying initial substring, of torrents for which to get information. Example usage is "howdy_deluge_console info ab1 bc2", where "ab1" and "bc2" are the first three digits of
		 the MD5 hashes of torrents to examine.

   optional arguments:
     -h, --help  show this help message and exit
     -f, --file  If chosen, then spit out the torrent selections into a debug output file. Name of the file is given by howdy_deluge_console.YYYYMMDD-HHMMSS.txt

``howdy_deluge_console info`` will show nicely formatted information on ALL torrents.

.. code-block:: console
   
   howdy_deluge_console info
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

.. code-block:: console

   howdy_deluge_console info ed5
   Name: ubuntu-19.10-beta-desktop-amd64.iso
   ID: ed53ba61555cab24946ebf2f346752805601a7fb
   State: Seeding
   Up Speed: 112.2 KiB/s ETA: 0 days 02:47:24
   Seeds: 0 (72) Peers: 1 (3) Availability: 0.00
   Size: 2.1 GiB/2.1 GiB Ratio: 0.000
   Seed time: 0 days 00:03:44 Active: 0 days 00:03:57
   Tracker status: ubuntu.com: Announce OK

Furthermore, since this CLI does not have UNIX piping and redirect functionalities, running with the ``-f`` or ``--file`` flag will spit out a debug text output of torrent statuses, the same as spit out into the command line. The name of the debug output file is ``howdy_deluge_console.YYYYMMDD-HHMMSS.txt``: the middle text is the 4-digit year, 2-digit month, 2-digit-day, followed by hour-min-second, at the time when the info command was requested.

removing torrents (rm or del)
-------------------------------
You can remove some or all torrents by running ``howdy_deluge_console rm`` or ``howdy_deluge_console del``. Running ``howdy_deluge_console rm -h`` gives the following output.

.. code-block:: console

   usage: howdy_deluge_console rm [-h] [-R] torrent [torrent ...]

   positional arguments:
     torrent            The hash ID, or identifying initial substring, of torrents to remove.

   optional arguments:
     -h, --help         show this help message and exit
     -R, --remove_data  Remove the torrent's data.

* ``howdy_deluge_console rm md5trunc_1 md5_trunc_2 ...`` removes specified torrents but keeps whatever data has been downloaded on the Deluge server. You would run this once the torrent's state was ``Seeding`` or ``Paused`` (see :ref:`torrent info (info)`).

* ``howdy_deluge_console rm -R ...`` does the same, but also removes whatever data has been downloaded from the Deluge server.

* ``howdy_deluge_console rm`` without specific torrents removes (or removes with deletion) ALL torrents from the Deluge server.

adding torrents (add)
-----------------------
You can add torrents to the Deluge server by running ``howdy_deluge_console add``. You can add a torrent file as URL, a torrent file on disk, and a `Magnet URI`_. Running ``howdy_deluge_console add -h`` gives the following output.

.. code-block:: console

   usage: howdy_deluge_console add [-h] torrent

   positional arguments:
     torrent     The fully realized magnet link, or file, to add to the torrent server.

   optional arguments:
     -h, --help  show this help message and exit

* torrent file as remote URL:

.. code-block:: console

   howdy_deluge_console add http://releases.ubuntu.com/19.10/ubuntu-19.10-beta-live-server-amd64.iso.torrent

* torrent file on disk:

.. code-block:: console

   howdy_deluge_console add ubuntu-19.10-beta-desktop-amd64.iso.torrent

* `Magnet URI`_:

.. code-block:: console

   howdy_deluge_console add "magnet:?xt=urn:btih:49efb5fdd274abb26c5ea6361d1d9be28e4db2d3&dn=archlinux-2019.09.01-x86_64.iso&tr=udp://tracker.archlinux.org:6969&tr=http://tracker.archlinux.org:6969/announce"

pausing and resuming torrents (pause or resume)
-------------------------------------------------
You can pause torrents on the Deluge server by running ``howdy_deluge_console pause``, and you can resume them by running ``howdy_deluge_console resume``.

* You can pause/resume specific torrents by running ``howdy_deluge_console pause md5trunc_1 md5_trunc_2 ...`` or ``howdy_deluge_console resume md5trunc_1 md5_trunc_2 ...``.

* You can pause/resume ALL torrents on the Deluge server by not specifying any truncated MD5 hashes, ``howdy_deluge_console pause`` or ``howdy_deluge_console resume``.  

.. 28-09-2019: Pause and resume don't seem to be working right now when connecting to the Seedhost seedbox Deluge server.

pushing credentials (push)
----------------------------------
You can push new Deluge server credentials (URL, port, username, and password) to the SQLite3_ configuration database. Running ``howdy_deluge_console push -h`` gives its help syntax,

.. code-block:: console

   usage: howdy_deluge_console push [-h] [--host url] [--port port] [--username username] [--password password]

   optional arguments:
     -h, --help           show this help message and exit
     --host url           URL of the deluge server. Default is localhost.
     --port port          Port for the deluge server. Default is 12345.
     --username username  Username to login to the deluge server. Default is admin.
     --password password  Password to login to the deluge server. Default is admin.

Push new Deluge server settings into the configuration database by running,

.. code-block:: console

   howdy_deluge_console push --host=HOST --port=PORT --username=USERNAME --password=PASSWORD

If those are valid settings, nothing more happens. If these are invalid settings, then specific error messages will print to the screen.

.. _howdy_resynclibs_label:

howdy_resynclibs
^^^^^^^^^^^^^^^^^^^^^^^^^^
The help output, when running ``howdy_resynclibs -h``, produces the following.

.. code-block:: console

   usage: howdy_resynclibs [-h] [--libraries] [--refresh] [--summary] [--library LIBRARY] [--servername SERVERNAME] [--servernames] [--noverify]

   optional arguments:
     -h, --help            show this help message and exit
     --libraries           If chosen, just give the sorted names of all libraries in the Plex server.
     --refresh             If chosen, refresh a chosen library in the Plex server. Must give a valid name for the library.
     --summary             If chosen, perform a summary of the chosen library in the Plex server. Must give a valid name for the library.
     --library LIBRARY     Name of a (valid) library in the Plex server.
     --servername SERVERNAME
			   Optional name of the server to check for.
     --servernames         If chosen, print out all the servers owned by the user.
     --noverify            Do not verify SSL transactions if chosen.

``--noverify`` is a standard option in many of the Howdy CLI and GUIs to ignore verification of SSL transactions. It is optional and will default to ``False``.

When running this CLI, you must choose *one and only one* of these options.

* ``--servernames`` gives you the list of the Plex_ servers to which you have access, and which you own.

* ``--libraries``  prints out a list of the libraries on the Plex_ server you chose and which you own. Here you can explicitly choose a Plex_ server by name with ``--servername=SERVERNAME`` or have a default one you own chosen for you.

* ``--summary`` prints out a summary of the Plex_ library you have chosen with ``--library=LIBRARY``.

* ``--refresh`` refreshes the Plex_ library you have chosen withh ``--library=LIBRARY``.

Here I find it useful to show how this tool works by example.

1. First, we can determine those Plex_ servers to which we have access

   .. code-block:: console
   
      howdy_resynclibs --servernames

   This will print out a nicely formatted table. Each row is a Plex_ server. The columns are the server's name, whether we own it, and its remote URL with port (which is of the form ``https://IP-ADDRESS:PORT``).

   .. code-block:: console

      Name           Is Owned    URL
      -------------  ----------  ---------------------------
      tanim-desktop  True        https://IP-ADDR1:PORT1
      XXXX    	     False       https://IP-ADDR2:PORT2
      YYYY	     False       https://IP-ADDR3:PORT3

2. Now we can look for the Plex_ libraries in the Plex_ server *which we own*. If we don't choose a Plex_ server with ``--servername=SERVERNAME``, then the first one in the row which we own will be chosen by default. The syntax is,

   .. code-block:: console

      howdy_resynclibs --servername=tanim-desktop --libraries

   This will print out a nicely formatted table. Each row is a library. There is a column of the library's name and its type. I have only shown three of the six Plex_ libraries on my server.

   .. code-block:: console

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

     .. code-block:: console

        tanim-desktop $ howdy_resynclibs --servername=tanim-desktop --library=Movies --summary
	
	"Movies" is a movie library. There are 1886 movies here. The total size of movie media is 1.632 TB.
	The total duration of movie media is 4 months, 20 days, 19 hours, 50 minutes, and 22.054 seconds.

   * On a TV show library.

     .. code-block:: console

        tanim-desktop $ howdy_resynclibs --servername=tanim-desktop --library="TV Shows" --summary

	"TV Shows" is a TV library. There are 21167 TV files in 236 TV shows. The total size of TV media is
	5.301 TB. The total duration of TV shows is 1 year, 2 months, 15 days, 11 hours, 42 minutes, and
	6.409 seconds.

   * On a music library.

     .. code-block:: console

        tanim-desktop $ howdy_resynclibs --servername=tanim-desktop --library=Music --summary

	"Music" is a music library. There are 9911 songs made by 814 artists in 1549 albums. The total size
	of music media is 54.785 GB. The total duration of music media is 26 days, 18 hours, 59 minutes, and
	55.185 seconds.

4. Finally, we can refresh a library that we specify with the ``--refresh`` flag and ``--library=LIBRARY``. Here are three examples on how to refresh the movie, TV show, and music library.

   .. code-block:: console

      howdy_resynclibs --servername=tanim-desktop --library=Movies --refresh
      howdy_resynclibs --servername=tanim-desktop --library="TV Shows" --refresh
      howdy_resynclibs --servername=tanim-desktop --library=Music --refresh


.. _howdy_store_credentials_label:

howdy_store_credentials
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ 
:numref:`Howdy Core Command Line Utilities` describes this executable's functionality very well. Its help screen can be displayed by running ``howdy_store_credentials -h``,

.. code-block:: console

   usage: howdy_store_credentials [-h] [--noverify]

   optional arguments:
     -h, --help  show this help message and exit
     --noverify  If chosen, do not verify SSL connections.

The ``--noverify`` flag disables the verification of SSL connections. First, run this executable, ``howdy_store_credentials``, which will return this interactive text dialog in the shell.

.. code-block:: console

   tanim-desktop $ howdy_store_credentials
   Please go to this URL in a browser window:https://accounts.google.com/o/oauth2/auth...
   After giving permission for Google services on your behalf,
   type in the access code:

Second, go to the URL to which you are instructed. Once you copy that URL into your browser, you will see a browser window as shown in :ref:`Step #3 <google_step03_authorizeaccount>`, :ref:`Step #5 <google_step05_scaryscreen>`, :ref:`Step #6 <google_step06_allowbutton>`, and :ref:`Step #7 <google_step07_oauthtokencopy>` in :numref:`Summary of Setting Up Google Credentials`.

Third, paste the code as described in :ref:`Step #7 <google_step07_oauthtokencopy>` into the interactive text dialog, ``...type in the access code:``. Once successful, you will receive this message in the shell,

.. code-block:: console

   Success. Stored GOOGLE credentials.

.. _rsync_subproc_label:

rsync_subproc
^^^^^^^^^^^^^^^^^^^^
The help output, when running ``rsync_subproc -h``, produces the following.

.. code-block:: console

   usage: rsync_subproc [-h] [-S STRING] [-N NUMTRIES] [-D] [-R] {-P} ...

   positional arguments:
     {push}
       push                push RSYNC credentials into configuration file.

   optional arguments:
     -h, --help            show this help message and exit
     -S STRING, --string STRING
			   the globbed string to rsync from on the remote account. Default is "*.mkv".
     -N NUMTRIES, --numtries NUMTRIES
			   number of attempts to go through an rsync process. Default is 10.
     -D, --debug           if chosen, then write debug output.
     -R, --reverse         If chosen, push files from local server to remote. Since files are deleted from source once done, you should probably make a copy of the source files if you want to still keep them afterwards.

This executable provides a convenient higher-level command-line interface to rsync_ uploading and downloading that resumes on transfer failure, and deletes the origin files once the transfer is complete. One also does not need to execute this command in ``LOCAL_DIR``.

The main rsync_ based uploading and downloading is described in :ref:`rsync_ based functionality`. Setting the SSH credentials, and local and remote locations, is described in :ref:`rsync_subproc settings with push`.

rsync_ based functionality
---------------------------
One can either upload files and directories to, or download files and directories from, the remote location and the remote subdirectory (which we call ``SUBDIR``). The local directory is called ``LOCAL_DIR``. If the remote directory is not defined, it is *by default* the home directory of that account.

The debug flag, ``-D`` or ``--debug``, is extremely useful, as it displays the lower level shell command that is executed to get the rsync_ transfer going.

The files or directories are selected with ``-S STRING`` or ``--string=STRING`` and follows the standard `POSIX globbing <https://en.wikipedia.org/wiki/Glob_(programming)>`_ convention. For instance, you can specify ``-S "The*"`` (``STRING`` in quotations) to select the remote directory ``The Simpsons`` to download. In order to simplify this CLI's behavior,

* There can be no spaces in the ``STRING`` selection.

* The ``STRING`` selection does not behave as a `Regular expression <https://en.wikipedia.org/wiki/Regular_expression>`_.

The ``-N`` or ``--numtries`` flag sets the number of tries that the rsync_ process will attempt before giving up or finishing the transfer. The default is 10, but this number must be :math:`\ge 1`.

To download a remote directory (``SUBDIR/Ubuntu_18.04``) until success into ``LOCAL_DIR``, and delete all files inside the remote directory, you can run this command with debug.

.. code-block:: console

   tanim-desktop $ rsync_subproc -D -S "Ubuntu_*"
   STARTING THIS RSYNC CMD: rsync --remove-source-files -P -avz --rsh="/usr/bin/sshpass XXXX ssh" -e ssh YYYY@ZZZZ:SUBDIR/Ubuntu_* LOCAL_DIR
   TRYING UP TO 10 TIMES.
   
   SUCCESSFUL ATTEMPT 1 / 10 IN 25.875 SECONDS.

Note that after a period of time (here, 25.875 seconds), the process will terminate with either a descriptive success or descriptive failure message. Note that in the debug output, the SSH password is not printed out (except for an ``XXXX``).

To upload the local directory (``LOCAL_DIR/Ubuntu_18.04``) until success into ``SUBDIR``, and delete all files inside the local directory, you can run this command with debug and the ``-R`` or ``--reverse`` flag.

.. code-block:: console

   tanim-desktop $ rsync_subproc -D -R -S Ubuntu*
   STARTING THIS RSYNC CMD: rsync --remove-source-files -P -avz --rsh="/usr/bin/sshpass XXXX ssh" -e ssh LOCAL_DIR/Ubuntu_18.04 YYYY@ZZZZ:SUBDIR/
   TRYING UP TO 10 TIMES.
   
   SUCCESSFUL ATTEMPT 1 / 10 IN 264.802 SECONDS.

rsync_subproc settings with push
------------------------------------
Running ``rsync_subproc push`` will update or set the SSH settings for the remote server, and the local and remote subdirectories. :numref:`Local and Remote (Seedhost) SSH Setup` and :numref:`Login Services` (see the screen shot in :numref:`login_step02_settings`) describe the form that these settings take. The help output, when running ``rsync_subproc push -h``, produces the following.

.. code-block:: console

   usage: rsync_subproc push [-h] [-L LOCAL_DIR] [--ssh SSHPATH] [--subdir SUBDIR]

   optional arguments:
     -h, --help       show this help message and exit
     -L LOCAL_DIR     Name of the local directory into which we download files and directory. Default is XXXX.
     --ssh SSHPATH    SSH path from which to get files.
     --subdir SUBDIR  name of the remote sub directory from which to get files. Optional.


* the format of the SSH setting is ``username@ssh_server``.

* the ``SUBDIR`` is located relative to the ``usename`` home directory on ``ssh_server``, ``$HOME/SUBDIR``.

* the ``LOCAL_DIR`` local directory is described with an absolute path.

Thus, to set settings for ``rsync_subproc``, one would run,

.. code-block:: console

   rsync_subproc push -L LOCAL_DIR --ssh=username@ssh_server --subdir=SUBDIR

Note that here, the SSH password is the same as the remote Deluge_ server's password. See, e.g., :numref:`howdy_deluge_console` or :numref:`Local and Remote (Seedhost) SSH Setup` and figures therein.

.. _get_book_tor_label:

get_book_tor
^^^^^^^^^^^^^
The help output, when running ``get_book_tor -h``, produces the following.

.. code-block:: console

   usage: get_book_tor [-h] -n NAME [--maxnum MAXNUM] [-f FILENAME] [--add] [--info] [--noverify]

   optional arguments:
     -h, --help            show this help message and exit
     -n NAME, --name NAME  Name of the book to get.
     --maxnum MAXNUM       Maximum number of torrents to look through. Default is 10.
     -f FILENAME, --filename FILENAME
			   If defined, put magnet link into filename.
     --add                 If chosen, push the magnet link into the deluge server.
     --info                If chosen, run in info mode.
     --noverify            If chosen, do not verify SSL connections.

These are common flags used by all standard operations of this CLI.

* ``--info`` prints out :py:const:`INFO <logging.INFO>` level :py:mod:`logging` output.

* ``--noverify`` does not verify SSL connections.

The ``-n`` or ``--name`` flag is used to specify the ebook, for example `Plagues and Peoples <plagues_and_peoples_>`_ by `William McNeill`_.

Here is how to get this ebook,  `Plagues and Peoples <plagues_and_peoples_>`_. The selection of ebook torrents are much smaller than TV shows and movies, so we often get *one* choice rather than multiple choices. If we had multiple choices, we could choose a given Magnet link by number, and the choices are sorted by the total number of seeds (SE) and leechers (LE) found for that link. The Magnet link is printed out here.

.. code-block:: console

   tanim-desktop $ get_book_tor -n "Plagues and Peoples"
   Chosen book: Plagues and Peoples (2.1 MiB)
   magnet link: magnet:?xt=urn:btih:85C37477333AD716864B3D25F5DFF1B9AFF1ADE6&dn=Plagues+and+Peoples&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969%2Fannounce&tr=udp%3A%2F%2F9.rarbg.to%3A2920%2Fannounce&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337&tr=udp%3A%2F%2Ftracker.internetwarriors.net%3A1337%2Fannounce&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.pirateparty.gr%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.cyberia.is%3A6969%2Fannounce

We can modify this command with the following.

* ``-f`` or ``--filename`` is used to output the Magnet URI into a file,

  .. code-block:: console

     tanim-desktop $ get_book_tor -n "Plagues and Peoples" -f plagues_and_peoples.txt
     Chosen book: Plagues and Peoples (2.1 MiB)

* ``--add`` adds the Magnet URI to the Deluge_ server. The operation of ``howdy_deluge_console`` is described in :numref:`howdy_deluge_console`.

  .. code-block:: console

     tanim-desktop: torrents $ get_book_tor -n "Plagues and Peoples" --add
     Chosen book: Plagues and Peoples (2.1 MiB)
     ...
     tanim-desktop: torrents $ howdy_deluge_console info
     Name: Plagues and Peoples
     ID: 85c37477333ad716864b3d25f5dff1b9aff1ade6
     State: Downloading
     Down Speed: 0.0 KiB/s Up Speed: 0.0 KiB/s
     Seeds: 0 (1) Peers: 0 (1) Availability: 0.00
     Size: 0.0 KiB/0.0 KiB Ratio: -1.000
     Seed time: 0 days 00:00:00 Active: 0 days 00:00:35
     Tracker status: coppersurfer.tk: Announce OK
     Progress: 0.00% [~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~]

  
.. _Deluge: https://en.wikipedia.org/wiki/Deluge_(software)
.. _deluge_console: https://whatbox.ca/wiki/Deluge_Console_Documentation
.. _rsync: https://en.wikipedia.org/wiki/Rsync
.. _Plex: https://plex.tv
.. _`Magnet URI`: https://en.wikipedia.org/wiki/Magnet_URI_scheme
.. _SQLite3: https://www.sqlite.org/index.html
.. _Jackett: https://github.com/Jackett/Jackett
.. _plagues_and_peoples: https://en.wikipedia.org/wiki/Plagues_and_Peoples
.. _`William McNeill`: https://en.wikipedia.org/wiki/William_H._McNeill_(historian)
