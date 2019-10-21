================================================
TVDB Command Line Utilities
================================================

This section describes the six Plexstuff TVDB command line utilities.

* :ref:`get_plextvdb_batch.py` does...

* :ref:`get_tv_tor.py` finds `Magnet links <Magnet URI_>`_ of television shows, and by default prints out the chosen magnet link. This executable uses the Jackett_ server to search for TV shows, and can optionally upload these links to the specified Deluge_ server (see :numref:`Plexstuff Settings Configuration`).

* :ref:`plex_tvdb_epinfo.py` creates a JSON file of the :py:class:`dict` of episodes associated with a TV show, and uploads this JSON episodes file to the SSH server, and remote subdirectory (see :numref:`Plexstuff Settings Configuration`). This JSON file can be used to rename episodes in a season or TV show that has been downloaded by the Deluge_ server.

* :ref:`plex_tvdb_epname.py` prints out information by season or by episode for a TV show.

* :ref:`plex_tvdb_futureshows.py` summarizes information on those TV shows, that exist in the Plex_ server, that will air new seasons.

* :ref:`plex_tvdb_plots.py` creates eye chart summary plots, by calendar year, of TV shows that have aired in a given year. These plots are in `SVGZ <https://en.wikipedia.org/wiki/Scalable_Vector_Graphics#Compression>`_ format.

.. _get_plextvdb_batch.py_label:

get_plextvdb_batch.py
^^^^^^^^^^^^^^^^^^^^^^^
The help output, when running ``get_plextvdb_batch.py -h``, produces the following. Here, ``$(num_cores)`` is *TWICE* the number of CPUs on the Plex_ server. This code is currently designed to be run *ONLY* on the Plex_ server.

.. code-block:: bash

   Usage: get_plextvdb_batch.py [options]

   Options:
     -h, --help            show this help message and exit
     --maxtime=MAXTIME_IN_SECS
                           The maximum amount of time to spend (in seconds), per
                           candidate magnet link, trying to download a TV show.
                           Default is 1000 seconds.
     --num=NUM_ITERS       The maximum number of different magnet links to try
                           before giving up. Default is 2.
     --token=TOKEN         Optional argument. If chosen, user provided Plex
                           access token.
     --info                If chosen, then run in info mode.
     --debug               If chosen, then run in debug mode.
     --numthreads=NUMTHREADS
                           Number of threads over which to search for TV shows in
                           my library. Default is $(num_cores).
     --nomax               If chosen, do not restrict maximum size of downloaded
                           file.
     --nomin               If chosen, do not restrict minimum size of downloaded
                           file.
     --raw                 If chosen, then use the raw string to download the
                           torrent.

To better understand the command line switches (flags and inputs), we describe how the this executable, which searches for new episodes of TV shows on the Plex_ server on a given day, works.

.. _get_plextvdb_batch.py_point1label:

1. by default, this does a Magnet link search for an episode using its IMDb_ info, and looks for those episodes whose download sizes are 80% to 120% of the average size of episodes that already exist for that TV show on the Plex_ server.

.. _get_plextvdb_batch.py_point2label:

2. by default, the number of threads this executable uses for its work is *TWICE* the number of CPUs on the Plex_ server.

.. _get_plextvdb_batch.py_point3label:

3. in order to quit a search for episode, for a given episode that has been aired but is missing from the Plex_ server, this will wait for ``MAXTIME_IN_SECS`` seconds to fully download an episode from its Magnet link, and will only search through the ``NUM_ITERS`` top choices of Magnet links found for each episode. The choices for Magnet links for an episode are ordered by the sum of its number of seeders and leechers (see :ref:`get_tv_tor.py`).

Here are the common flags and command line inputs.

* ``--token`` allows you to explicitly set the Plex_ access token for the server.

* ``--info`` prints out ``INFO`` level logging output.

* ``--debug`` prints out ``DEBUG`` level logging output.

Here are the command line inputs that change the operation of this execution.

* ``--maxtime_in_secs`` sets the maximum number of seconds that a given thread will wait for an episode Magnet link to download (see :ref:`point #3 <get_plextvdb_batch.py_point3label>`). This must be positive.

* ``--nums`` sets the number of top choices of Magnet links through which to search (see :ref:`point #3 <get_plextvdb_batch.py_point3label>`). This must be positive.

* ``--numthreads`` sets the number of threads used for downloading new episodes onto the Plex_ server (see :ref:`point #2 <_get_plextvdb_batch.py_point2label>`).

* The ``--nomin`` flag means that there is no *lower* limit to the size of episode files to be downloaded onto the Plex_ server (see :ref:`point #1 <get_plextvdb_batch.py_point1label>`).

* The ``--nomax`` flag means that there is no *upper* limit to the size of episode files to be downloaded onto the Plex_ server (see :ref:`point #1 <get_plextvdb_batch.py_point1label>`).

* The ``--raw`` flag does not use the default IMDB_ information to search for the torrent. Instead it uses the full string to search for the episode (see :ref:`point #1 <get_plextvdb_batch.py_point1label>`).

Here is a demonstration of its operation, searching for new episodes to download on the Plex_ server on ``Sunday, 20 October 2019``. `The Great British Bake-Off <https://en.wikipedia.org/wiki/The_Great_British_Bake_Off>`_ is going to be ignored because this show has been excluded for identification and searches. The output format during evaluation is descriptive because the process can take more than a few seconds.

.. code-block:: bash

   tanim-desktop $ get_plextvdb_batch.py

   0, started on October 20, 2019 @ 05:34:46 PM
   1, found TV library: TV Shows.
   2, excluding these TV shows: The Great British Bake Off.
   3, took 22.912 seconds to get list of 4 episodes to download.
   4, here are the 4 episodes to get: Bob's Burgers S10E04, Family Guy S18E04, Mr. Robot S04E03, The Simpsons S31E04.
   started downloading 4 episodes on October 20, 2019 @ 05:35:09 PM
   successfully processed 0 / 4 episodes in 69.244 seconds.
   could not download Bob's Burgers S10E04, Family Guy S18E04, Mr. Robot S04E03, The Simpsons S31E04.
   processed from start to finish in 69.244 seconds.
   5, everything done in 92.156 seconds.
   6, finished on October 20, 2019 @ 05:36:19 PM.

Here, there were four new episodes to download: `Bob's Burgers S10E04 <https://www.imdb.com/title/tt10750120>`_, `Family Guy S18E04 <https://www.imdb.com/title/tt10680780>`_, `Mr. Robot S04E03 <https://www.imdb.com/title/tt8084160>`_, and `The Simpsons S31E04 <https://www.imdb.com/title/tt10750104>`_. One can find it very useful to run this executable through an automated process. Here is an example systemd user unit file (:download:`get_plextvdb_batch.service </_static/get_plextvdb_batch.service>`) and timer file (:download:`get_plextvdb_batch.timer </_static/get_plextvdb_batch.timer>`) to run ``get_plextvdb_batch.py`` every day at 130 AM, 630 PM, and 930 PM. One can follow `instructions on how to set up and run systemd user units <https://wiki.archlinux.org/index.php/systemd/User>`_.

* copy :download:`get_plextvdb_batch.service </_static/get_plextvdb_batch.service>` and :download:`get_plextvdb_batch.timer </_static/get_plextvdb_batch.timer>` to the ``~/.config/systemd/user`` directory.

* replace ``$PLEXSTUFF_DIR`` with the path to ``get_plextvdb_batch.py``.

* register the unit and timer with systemd by running ``systemctl --user enable get_plextvdb_batch.service`` and ``systemctl --user enable get_plextvdb_batch.timer``.

* start the unit with timer by running ``systemctl --user start get_plextvdb_batch.service``.

.. _get_tv_tor.py_label:

get_tv_tor.py
^^^^^^^^^^^^^^^
The help output, when running ``get_tv_tor.py -h``, produces the following.

.. code-block:: bash

   Usage: get_tv_tor.py [options]

   Options:
     -h, --help            show this help message and exit
     -n NAME, --name=NAME  Name of the TV show to get.
     --maxnum=MAXNUM       Maximum number of torrents to look through. Default is
                           10.
     --raw                 If chosen, then use the raw string (for jackett) to
                           download the torrent.
     -f FILENAME, --filename=FILENAME
                           If defined, put torrent or magnet link into filename.
     --add                 If chosen, push the magnet link into the deluge
                           server.
     --info                If chosen, run in info mode.
     --noverify            If chosen, do not verify SSL connections.
     --timing              If chosen, show timing information (how long to get TV
                           torrents).

These are common flags used by all standard operations of this CLI.

* ``--info`` prints out ``INFO`` level logging output.

* ``--noverify`` does not verify SSL connections.

* ``--timing`` prints out how long, in seconds, any given operation (for instance, getting and choosing TV show `Magnet links`_) takes.

The ``-n`` or ``--name`` flag is used to specify the TV show and episode, for example `The Simpsons S30E10 <simpsons_s30e10_>`_ (`The Simpsons <the_simpsons_>`_, season 30 and episode 10)

Here is how to get an episode, `The Simpsons S30E10 <simpsons_s30e10_>`_. We then choose a given Magnet link by number, and the Magnet URI is printed out. The choices are sorted by the total number of seeds (SE) and leechers (LE) found for that link. By default, the IMDb_ information for this episode (TV show and season) is used to look for Magnet links.

.. code-block:: bash

   tanim-desktop $ get_tv_tor.py -n "The Simpsons S30E10"
   Choose TV episode or series:
   1: The Simpsons s30e10 720p WEB x264-300M (1 SE, 17 LE)
   2: The Simpsons S30E10 720p WEB x264-TBS[TGx] (5 SE, 12 LE)
   3: The Simpsons S30E10 XviD-AFG[TGx] (0 SE, 14 LE)
   4: The Simpsons S30E10 Tis the 30th Season 1080p AMZN WEB-DL DD+5 1 H 264-QOQ[TGx] (5 SE, 5 LE)
   5: The Simpsons S30E10 WEB x264-TBS[ettv] (8 SE, 1 LE)
   6: The Simpsons S30E10 1080P WEB-DL DD5 1 H 264 (3 SE, 5 LE)
   7: The Simpsons S30E10 1080p WEB x264-TBS[TGx] (2 SE, 6 LE)
   8: The Simpsons S30E10 720p WEB x265-MiNX[TGx] (0 SE, 8 LE)
   9: The Simpsons S30E10 720p WEB x264-TBS[ettv] (1 SE, 6 LE)
   10: The Simpsons S30E10 720p WEB x264-TBS [eztv] (5 SE, 1 LE)
   1
   Chosen TV show: The Simpsons s30e10 720p WEB x264-300M
   magnet:?xt=urn:btih:17f7373e9e7e0343370191a3173e0f69ce02dbc1&dn=The+Simpsons+s30e10+720p+WEB+x264-300M&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.pomf.se%3A80%2Fannounce&tr=udp%3A%2F%2Ftorrent.gresille.org%3A80%2Fannounce&tr=udp%3A%2F%2F11.rarbg.com%2Fannounce&tr=udp%3A%2F%2F11.rarbg.com%3A80%2Fannounce&tr=udp%3A%2F%2Fopen.demonii.com%3A1337%2Fannounce&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=http%3A%2F%2Ftracker.ex.ua%3A80%2Fannounce&tr=http%3A%2F%2Ftracker.ex.ua%2Fannounce&tr=http%3A%2F%2Fbt.careland.com.cn%3A6969%2Fannounce&tr=udp%3A%2F%2Fglotorrents.pw%3A6969%2Fannounce

We can modify this command with the following.

* ``-f`` or ``--filename`` is used to output the Magnet URI into a file,

  .. code-block:: bash

     tanim-desktop $ get_tv_tor.py -n "The Simpsons S30E10" -f simpsons_s30e10.magnet
     
     Choose TV episode or series:
     1: The Simpsons s30e10 720p WEB x264-300M (1 SE, 17 LE)
     2: The Simpsons S30E10 720p WEB x264-TBS[TGx] (5 SE, 12 LE)
     3: The Simpsons S30E10 XviD-AFG[TGx] (0 SE, 14 LE)
     4: The Simpsons S30E10 Tis the 30th Season 1080p AMZN WEB-DL DD+5 1 H 264-QOQ[TGx] (5 SE, 5 LE)
     5: The Simpsons S30E10 WEB x264-TBS[ettv] (8 SE, 1 LE)
     6: The Simpsons S30E10 1080P WEB-DL DD5 1 H 264 (3 SE, 5 LE)
     7: The Simpsons S30E10 1080p WEB x264-TBS[TGx] (2 SE, 6 LE)
     8: The Simpsons S30E10 720p WEB x265-MiNX[TGx] (0 SE, 8 LE)
     9: The Simpsons S30E10 720p WEB x264-TBS[ettv] (1 SE, 6 LE)
     10: The Simpsons S30E10 720p WEB x264-TBS [eztv] (5 SE, 1 LE)
     1
     Chosen TV show: The Simpsons s30e10 720p WEB x264-300M

* ``--add`` adds the Magnet URI to the Deluge_ server. The operation of ``plex_deluge_console.py`` is described in :numref:`plex_deluge_console.py`.

  .. code-block:: bash

     tanim-desktop $ get_tv_tor.py -n "The Simpsons S30E10" --add
     ...
     tanim-desktop $ plex_deluge_console.py info
     Name: The Simpsons s30e10 720p WEB x264-300M
     ID: 17f7373e9e7e0343370191a3173e0f69ce02dbc1
     State: Downloading
     Down Speed: 0.0 KiB/s Up Speed: 0.0 KiB/s
     Seeds: 0 (0) Peers: 0 (1) Availability: 0.00
     Size: 0.0 KiB/0.0 KiB Ratio: -1.000
     Seed time: 0 days 00:00:00 Active: 0 days 00:00:03
     Tracker status: opentrackr.org: Announce OK
     Progress: 0.00% [~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~]

* The ``--raw`` flag does not use the default IMDB_ information to search for the torrent. Instead it uses the full string (here ``"The Simpsons S30E10"``) to search for the episode. Here is an example,

  .. code-block:: bash

     tanim-desktop $ get_tv_tor.py -n "The Simpsons S30E10" --raw
     
     Choose TV episode or series:
     1: The.Simpsons.S30E10.WEB.x264-TBS[ettv] (159.1 MiB) (1130 SE, 1336 LE)
     2: The.Simpsons.S30E10.720p.WEB.x264-TBS[ettv] (444.1 MiB) (488 SE, 596 LE)
     3: The Simpsons S30E10 720p WEB x265-MiNX (186.4 MiB) (401 SE, 441 LE)
     4: The Simpsons S30E10 WEB x264-TBS (159.1 MiB) (298 SE, 327 LE)
     5: The Simpsons S30E10 720p WEB x264-TBS (444.1 MiB) (207 SE, 230 LE)
     6: The Simpsons S30E10 WEBRip x264-ION10 (199.2 MiB) (109 SE, 123 LE)
     7: [ACESSE COMANDOTORRENTS.COM] The Simpsons S30E10 [720p] [WEB-DL] [DUAL] (373.0 MiB) (45 SE, 51 LE)
     8: The.Simpsons.S30E10.720p.WEB.x265-MiNX[eztv].mkv (186.4 MiB) (15 SE, 32 LE)
     9: The.Simpsons.S30E10.WEBRip.x264-ION10 (199.2 MiB) (15 SE, 23 LE)
     10: The.Simpsons.S30E10.WEB.x264-TBS[ettv] (159.0 MiB) (13 SE, 15 LE)
     ...

  Notice the differences in these links from the ones before (using the IMDb_ information).

.. _plex_tvdb_epinfo.py_label:

plex_tvdb_epinfo.py
^^^^^^^^^^^^^^^^^^^^^^
The help output, when running ``plex_tvdb_epinfo.py -h``, produces the following.

.. code-block:: bash

   Usage: plex_tvdb_epinfo.py [options]
   
   Options:
     -h, --help            show this help message and exit
     -s SHOW, --show=SHOW  Names of the TV Show to push into remote server.
     -j JSONFILE, --jsonfile=JSONFILE
			   Name of the JSON file into which to store the episode
                           information. Default is eps.json.
     --debug               If chosen, then run DEBUG logging.

* ``-s`` or ``--show`` specifies the show whose information, as a JSON file, is uploaded to the remote SSH server.

* ``-j`` or ``--jsonfile`` specifies the name of the JSON file. The file's name must end in ``.json``.

* ``--debug`` prints out ``DEBUG`` level logging output.

For example, to upload information about `The Simpsons <the_simpsons_>`_ into a file, ``the_simpsons.json``, in the remote SSH server and the remote home directory (``REMOTE_HOME_DIR``).

.. code-block:: bash

   tanim-desktop $ plex_tvdb_epinfo.py -s "The Simpsons" -j the_simpsons.json
   put episode info for "The Simpsons" into REMOTE_HOME_DIR/the_simpsons.json in 7.341 seconds.

This JSON file contains dictionary data. Each key is the season number. Each value is another dictionary -- keys are the episode number, and values are the episode names.

.. code-block:: python

   {
     "1": {
      "1": "Simpsons Roasting on an Open Fire",
      "2": "Bart the Genius",
      "3": "Homer's Odyssey",
      "4": "There's No Disgrace Like Home",
      "5": "Bart the General",
      "6": "Moaning Lisa",
      "7": "The Call of the Simpsons",
      "8": "The Telltale Head",
      "9": "Life on the Fast Lane",
      "10": "Homer's Night Out",
      "11": "The Crepes of Wrath",
      "12": "Krusty Gets Busted",
      "13": "Some Enchanted Evening"
     },
   ...
   }

.. _plex_tvdb_epname.py_label:

plex_tvdb_epname.py
^^^^^^^^^^^^^^^^^^^^^^^^^^
The help output, when running ``plex_tvdb_epname.py -h``, produces the following.

.. code-block:: bash

   Usage: plex_tvdb_epname.py [options]

   Options:
     -h, --help            show this help message and exit
     -s SERIES, --series=SERIES
                           The name of the series
     -e EPSTRING, --epstring=EPSTRING
     	                   The episode string, in the form S%02dE%02d.
     --summary             If chosen, get a summary of all the seasons and
                           episodes for the SERIES.
     -S SEASON, --season=SEASON
      	                  If chosen, get a list of all episode titles for this
                          season of the SERIES.
     --noverify            If chosen, do not verify the SSL connection.

The ``--noverify`` flag says to not verify SSL connections.

Here are the three ways to get information on episodes for a specified TV show. For the purposes of this demonstration, we will use `The Simpsons <the_simpsons_>`_.

* To get a summary of all episodes of a TV show (`The Simpsons <the_simpsons_>`_), run ``plex_tvdb_epname.py -s "The Simpsons" --summary``,

  .. code-block:: bash

     668 episodes for The Simpsons
     SEASON 01: 13 episodes
     SEASON 02: 22 episodes
     SEASON 03: 24 episodes
     SEASON 04: 22 episodes
     SEASON 05: 22 episodes
     SEASON 06: 25 episodes
     SEASON 07: 25 episodes
     SEASON 08: 25 episodes
     SEASON 09: 25 episodes
     SEASON 10: 23 episodes
     SEASON 11: 22 episodes
     SEASON 12: 21 episodes
     SEASON 13: 22 episodes
     SEASON 14: 22 episodes
     SEASON 15: 22 episodes
     SEASON 16: 21 episodes
     SEASON 17: 22 episodes
     SEASON 18: 22 episodes
     SEASON 19: 20 episodes
     SEASON 20: 21 episodes
     SEASON 21: 23 episodes
     SEASON 22: 22 episodes
     SEASON 23: 22 episodes
     SEASON 24: 22 episodes
     SEASON 25: 22 episodes
     SEASON 26: 22 episodes
     SEASON 27: 22 episodes
     SEASON 28: 22 episodes
     SEASON 29: 21 episodes
     SEASON 30: 23 episodes
     SEASON 31: 6 episodes

* To get a summary of episodes aired (so far) for a given season and a TV show, for example run ``plex_tvdb_epname.py -s "The Simpsons" -S 10``.
  
  .. code-block:: bash

     23 episodes in SEASON 10 of The Simpsons.
     Episode 01/23: Lard of the Dance (Sunday, 23 August 1998)
     Episode 02/23: The Wizard of Evergreen Terrace (Sunday, 20 September 1998)
     Episode 03/23: Bart the Mother (Sunday, 27 September 1998)
     Episode 04/23: Treehouse of Horror IX (Sunday, 25 October 1998)
     Episode 05/23: When You Dish Upon a Star (Sunday, 08 November 1998)
     Episode 06/23: D'oh-in in the Wind (Sunday, 15 November 1998)
     Episode 07/23: Lisa Gets an A (Sunday, 22 November 1998)
     Episode 08/23: Homer Simpson in: 'Kidney Trouble' (Sunday, 06 December 1998)
     Episode 09/23: Mayored to the Mob (Sunday, 20 December 1998)
     Episode 10/23: Viva Ned Flanders (Sunday, 10 January 1999)
     Episode 11/23: Wild Barts Can't Be Broken (Sunday, 17 January 1999)
     Episode 12/23: Sunday, Cruddy Sunday (Sunday, 31 January 1999)
     Episode 13/23: Homer to the Max (Sunday, 07 February 1999)
     Episode 14/23: I'm with Cupid (Sunday, 14 February 1999)
     Episode 15/23: Marge Simpson in: 'Screaming Yellow Honkers' (Sunday, 21 February 1999)
     Episode 16/23: Make Room for Lisa (Sunday, 28 February 1999)
     Episode 17/23: Maximum Homerdrive (Sunday, 28 March 1999)
     Episode 18/23: Simpsons Bible Stories (Sunday, 04 April 1999)
     Episode 19/23: Mom and Pop Art (Sunday, 11 April 1999)
     Episode 20/23: The Old Man and the C Student (Sunday, 25 April 1999)
     Episode 21/23: Monty Can't Buy Me Love (Sunday, 02 May 1999)
     Episode 22/23: They Saved Lisa's Brain (Sunday, 09 May 1999)
     Episode 23/23: Thirty Minutes Over Tokyo (Sunday, 16 May 1999)

* To get summary information on a specific episode, for example run ``plex_tvdb_epname.py -s "The Simpsons" -e s30e10`` (season 30, episode 10).

  .. code-block:: bash

     tanim-desktop $ plex_tvdb_epname.py -s "The Simpsons" -e s30e10
     'Tis the 30th Season (Sunday, 09 December 2018)     

.. _plex_tvdb_futureshows.py_label:

plex_tvdb_futureshows.py
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The help output, when running ``plex_tvdb_futureshows.py -h``, produces the following.

.. code-block:: bash

   Usage: plex_tvdb_futureshows.py [options]

   Options:
     -h, --help  show this help message and exit
     --noverify  If chosen, do not verify the SSL connection.
     --local     Check for locally running plex server.
     --info      If chosen, run with INFO logging mode.

* ``--noverify`` does not verify SSL connections.

* ``--local`` specifies that we look for a local (``https://localhost:3400``) running Plex_ server.

* ``--info`` prints out ``INFO`` level logging output.

This executable prints out summary information on TV shows, that exist on the Plex_ server, excluding those shows that will not be searched. In this example, `The Great British Bake-Off <https://en.wikipedia.org/wiki/The_Great_British_Bake_Off>`_ is going to be ignored. The output format during evaluation is descriptive because the process can take more than a few seconds.

.. code-block:: bash

   tanim-desktop $ plex_tvdb_futureshows.py
   0, started on October 20, 2019 @ 04:30:33 PM
   1, found TV library: TV Shows.
   2, excluding these TV shows: The Great British Bake Off.
   3, Found 11 TV shows with new seasons after October 20, 2019, in 23.104 seconds.

   SHOW                          LAST SEASON    NEXT SEASON  AIR DATE              DAYS TO NEW SEASON
   --------------------------  -------------  -------------  ------------------  --------------------
   Travel Man: 48 Hours in...              9             10  October 21, 2019                       1
   BoJack Horseman                         5              6  October 25, 2019                       5
   Silicon Valley                          5              6  October 27, 2019                       7
   Rick and Morty                          3              4  November 10, 2019                     21
   The Man in the High Castle              3              4  November 15, 2019                     26
   The Expanse                             3              4  December 13, 2019                     54
   Lost in Space (2018)                    1              2  December 24, 2019                     65
   Schitt's Creek                          5              6  January 07, 2020                      79
   Homeland                                7              8  February 09, 2020                    112
   Outlander                               4              5  February 16, 2020                    119
   American Crime Story                    2              3  September 27, 2020                   343
   
   4, processed everything in 23.106 seconds.
   5, finished everything on October 20, 2019 @ 04:30:56 PM.

.. _plex_tvdb_plots.py_label:

plex_tvdb_plots.py
^^^^^^^^^^^^^^^^^^^^
The help output, when running ``plex_tvdb_plots.py -h``, produces the following. ``$(cwd)`` refers to the current working directory in which this CLI is run.

.. code-block:: bash

   Usage: plex_tvdb_plots.py [options]

   Options:
     -h, --help         show this help message and exit
     --years=S_YEARS    Give a list of years as a string, such as "1980,1981".
                     	Optional.
     --noverify         If chosen, do not verify the SSL connection.
     --local            Check for locally running plex server.
     --dirname=DIRNAME  Directory into which to store those plots. Default is
                     	$(cwd).

You can choose the calendar year or years for which you want to return eye chart plots of episodes that exist on the Plex_ server, excluding those shows that will not be searched. In this example, `The Great British Bake-Off <https://en.wikipedia.org/wiki/The_Great_British_Bake_Off>`_ is going to be ignored. In this example, we look for all episodes in the Plex_ server that have aired in 2000, 2005, 2010, and 2015. The output format during evaluation is descriptive because the process can take more than a few seconds.

.. code-block:: bash

   tanim-desktop $ plex_tvdb_plots.py --years 2000,2005,2010,2015
   0, started on October 20, 2019 @ 04:38:19 PM
   1, found TV library: TV Shows.
   2, excluding these TV shows: The Great British Bake Off.
   3, we found 4 years to use: 2000, 2005, 2010, 2015.
   4, started processing 4 years of TV shows after 6.055 seconds.
   5, finished processing year = 2000 (01 / 04) in 9.295 seconds.
   6, finished processing year = 2005 (02 / 04) in 9.714 seconds.
   7, finished processing year = 2010 (03 / 04) in 10.167 seconds.
   8, finished processing year = 2015 (04 / 04) in 10.569 seconds.
   9, processed all 4 years in 10.570 seconds.
   10, finished everything on October 20, 2019 @ 04:38:30 PM.

This produces the episode eye charts for 2000, 2005, 2010, and 2015.

.. |tvdata_2000| image:: plex-tvdb-cli-figures/tvdata.2000.svg
   :width: 100%

.. |tvdata_2005| image:: plex-tvdb-cli-figures/tvdata.2005.svg
   :width: 100%

.. |tvdata_2010| image:: plex-tvdb-cli-figures/tvdata.2010.svg
   :width: 100%

.. |tvdata_2015| image:: plex-tvdb-cli-figures/tvdata.2015.svg
   :width: 100%

+---------------+-----------------+
| |tvdata_2000| |  |tvdata_2005|  +
+---------------+-----------------+
| |tvdata_2010| |  |tvdata_2015|  +
+---------------+-----------------+

Here is an example eye chart, for episodes aired in 2000. Each day is colored and annotated by the number of new episodes aired that day, using a legend on the upper left named ``number of new episodes on a day``. Each month also shows the number of new episodes, in the number of TV shows, aired that month. On the upper right summarizes the new episodes aired that year: the number of days on which new episodes aired, the number of new episodes, and the number of shows.

.. _plex_tvdb_cli_figures_plots_tvdata_2000:

.. figure:: plex-tvdb-cli-figures/tvdata.2000.svg
   :width: 100%
   :align: center	

.. _Jackett: https://github.com/Jackett/Jackett
.. _Deluge: https://en.wikipedia.org/wiki/Deluge_(software)
.. _deluge_console: https://whatbox.ca/wiki/Deluge_Console_Documentation
.. _rsync: https://en.wikipedia.org/wiki/Rsync
.. _Plex: https://plex.tv
.. _`Magnet URI`: https://en.wikipedia.org/wiki/Magnet_URI_scheme
.. _SQLite3: https://www.sqlite.org/index.html
.. _simpsons_s30e10: https://en.wikipedia.org/wiki/'Tis_the_30th_Season
.. _the_simpsons: https://en.wikipedia.org/wiki/The_Simpsons
.. _IMDb: https://en.wikipedia.org/wiki/IMDb 
