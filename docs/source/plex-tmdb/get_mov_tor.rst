.. _get_mov_tor.py_label:

================================================
get_mov_tor.py
================================================

This executable finds either Magnet links or `torrent files <torrent file_>`_ of movies. By default it either prints out the chosen magnet link, or downloads the `torrent file <torrent file_>`_ into the directory to which this tool has executed. This executable uses, among other torrent searches, the Jackett_ server to search for movies, and may optionally upload the Magnet links or `torrent files <torrent file_>`_ to the specified Deluge_ server (see :numref:`Plexstuff Settings Configuration`).

The help output, when running ``get_mov_tor.py -h``, produces the following.

.. code-block:: bash

   Usage: get_mov_tor.py [options]

   Options:
     -h, --help            show this help message and exit
     -n NAME, --name=NAME  Name of the movie file to get.
     -y YEAR, --year=YEAR  Year to look for the movie file to get.
     --maxnum=MAXNUM       Maximum number of torrents to look through. Default is
                           10.
     --timeout=TIMEOUT     Timeout on when to quit getting torrents (in seconds).
                           Default is 60 seconds..
     -f FILENAME, --filename=FILENAME
                           If defined, put option into filename.
     --bypass              If chosen, bypass YTS.AG.
     --nozooq              If chosen, bypass ZOOQLE.
     --info                If chosen, run in info mode.
     --add                 If chosen, push the magnet link into the deluge
                           server.
     --noverify            If chosen, do not verify SSL connections.
     --timing              If chosen, show timing information (how long to get movie
                           torrents).
     --doRaw               If chosen, do not use IMDB matching for Jackett
                           torrents.

There are 13 flags or command line settings, so it is useful to split the different possible functionalities into separate sections. This tool can operate in three ways: choose a `torrent file`_; choose a Magnet link (similar to what is done in :ref:`get_tv_tor.py`); and bypass the Jackett_ server to use a cocktail of torrent trackers for which I have developed some functionality (see :numref:`plextmdb.plextmdb_torrents module`). :numref:`Demonstration of Default Operation` demonstrates the default mode of operation for this tool. :numref:`Common Flags and Settings` describe those settings to ``get_mov_tor.py`` that are shared by all operations. Finally, :numref:`Choice of Torrent Search` describes how to change the search for `torrent files <torrent file_>`_.

Demonstration of Default Operation
-----------------------------------

The only required argument is ``-n`` or ``--name``, which specifies which movie to search. It is the only argument that is required.By default, this tool uses the IMDb_ information on a movie to search for the movie torrent. It also first searches for `torrent files <torrent file_>`_ using the `YTS API`_: if it finds a selection of `torrent files <torrent file_>`_, then it stops there, asks for user input, and creates a `torrent file`_ in the current working directory; if the `torrent file` search does not work, then it searches for Magnet links using Jackett_ and Zooqle_, asks for user input, and prints out the full Magnet link in the user shell. Here are two examples of default operation,

* When ``get_mov_tor.py`` is able to find `torrent files <torrent file_>`_, here looking for `Star Trek Beyond`_. Here, there is only a single choice, and a single `torrent file`_, ``Star_Trek_Beyond.torrent``, is created in the current working directory

  .. code-block:: bash

     tanim-desktop $ get_mov_tor.py -n "Star Trek Beyond"
     Chosen movie Star Trek Beyond

  If there were several choices, such as searching for ``"Star Trek"``, then we would choose the number of the `torrent file`_ corresponding to `Star Trek IV`_ (choice ``6``), and its `torrent file`_, ``Star_Trek_IV:_The_Voyage_Home.torrent``, is created in the current working directory.

  .. code-block:: bash

     tanim-desktop $ get_mov_tor.py -n "Star Trek"
     choose movie: 1: Star Trek
     2: Star Trek Beyond
     3: Star Trek Generations
     4: Star Trek II: The Wrath of Khan
     5: Star Trek III: The Search for Spock
     6: Star Trek IV: The Voyage Home
     7: Star Trek Into Darkness
     8: Star Trek V: The Final Frontier
     9: Star Trek VI: The Undiscovered Country
     10: Star Trek: First Contact
     11: Star Trek: Insurrection
     12: Star Trek: Nemesis
     13: Star Trek: The Motion Picture
     6
     Chosen movie Star Trek IV: The Voyage Home

* In default operation, if we choose a more obscure movie for which a `torrent file`_ cannot be found, we get a selection of Magnet links. For example, here we search for the more obscure Michael Moore documentary, _`Slacker Uprising`.

  .. code-block:: bash

     tanim-desktop $ get_mov_tor.py -n "Slacker Uprising"
     Choose movie:
     1: Восстание бездельников / Slacker Uprising (Майкл Мур / Michael Moore) [2008, США, Документальный, WEB-DL 1080p] VO + Sub Rus + Original Eng () (1 SE, 2 LE)
     2: Slacker Uprising 2007.1080p WEB-DL AAC2.0 H264-TrollHD [PublicHD] (3.666 GB) (1 SE, 0 LE)
     2
     magnet link: magnet:?xt=urn:btih:08dcd040e04ae3a0aebf7da22f03e9050ec52edc&dn=Slacker+Uprising+2007.1080p+WEB-DL+AAC2.0+H264-TrollHD+[PublicHD]&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.pomf.se%3A80%2Fannounce&tr=udp%3A%2F%2Ftorrent.gresille.org%3A80%2Fannounce&tr=udp%3A%2F%2F11.rarbg.com%2Fannounce&tr=udp%3A%2F%2F11.rarbg.com%3A80%2Fannounce&tr=udp%3A%2F%2Fopen.demonii.com%3A1337%2Fannounce&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=http%3A%2F%2Ftracker.ex.ua%3A80%2Fannounce&tr=http%3A%2F%2Ftracker.ex.ua%2Fannounce&tr=http%3A%2F%2Fbt.careland.com.cn%3A6969%2Fannounce&tr=udp%3A%2F%2Fglotorrents.pw%3A6969%2Fannounce

* Finally, if you do not like any of the choices, *and if there is more than one choice*, you can type in ``q`` or other non-numeric character to exit.

  .. code-block:: bash

     tanim-desktop $ get_mov_tor.py -n "Slacker Uprising"
     Choose movie:
     1: Восстание бездельников / Slacker Uprising (Майкл Мур / Michael Moore) [2008, США, Документальный, WEB-DL 1080p] VO + Sub Rus + Original Eng () (1 SE, 2 LE)
     2: Slacker Uprising 2007.1080p WEB-DL AAC2.0 H264-TrollHD [PublicHD] (3.666 GB) (1 SE, 0 LE)
     q
     Error, did not give a valid integer value. Exiting...

  .. note:: this is a bug, I should try to allow the user to stop their choice even if only one Magnet link or `torrent file`_ is found.

Common Flags and Settings
---------------------------------------
Separate from whether or not a `torrent file`_ or Magnet link is downloaded, or on which torrent trackers will be searched, are the choices and modifications of the movie on which to search.

* ``-y`` or ``--year`` is optionally the YEAR on which to search for the torrent. Setting this can better specify the movie, and may be useful when searching for more obscure movies.

* ``--maxnum`` is the maximum number of magnet links or torrent files to return. The default is 10, but it must be :math:`\ge 5`.

* ``--timeout`` tells ``get_mov_tor.py`` to exit after this many seconds if no selection has been found. The default is 60 seconds, but it must be :math:`\ge 10` seconds.

* ``--info`` prints out ``INFO`` level logging output.

* ``--noverify`` says to not verify SSL connections.

* ``--timing`` can be an useful flag, to tell us how many seconds it took from starting a torrent search, to making a choice of which `torrent file`_ or Magnet link to use.

* ``--doRaw`` says to only use the search string in ``-n`` or ``--name`` to search for Magnet links. If a collection of `torrent files <torrent file_>`_ are found, then this flag is ignored.

These two flags change what happens to the magnet link or `torrent file`_.

* ``-f`` or ``--filename`` means to put the Magnet link into a file specified by ``--filename``. *However*, this argument is ignored if the tool finds a collection of `torrent files <torrent file_>`_; the name is fixed by the `torrent file`_ choice name (see :numref:`Demonstration of Default Operation` for examples).

* ``--add`` adds the Magnet URI to the Deluge_ server. The operation of ``plex_deluge_console.py`` is described in :numref:`plex_deluge_console.py`.

If ``--f`` is used, then the ``--add`` flag cannot be set. Consequently, if the ``--add`` flag is set, then ``--f`` cannot be used.

Choice of Torrent Search
------------------------------

The default operation is `torrent file`_ search first, then Magnet link. Setting the ``--bypass`` flag stops the `torrent file`_ search to go directly to Magnet link; this can be useful if the file search does not work, or if the `torrent file`_ we choose never gets started (this often occurs with older and more stale torrents).

By default one parallel process searches for Magnet links using Jackett_, and the other parallel process uses Zooqle_. The ``--nozooq`` flag turns off the Zooqle_ Magnet link search.

.. _`torrent file`: https://en.wikipedia.org/wiki/Torrent_file
.. _Jackett: https://github.com/Jackett/Jackett
.. _Zooqle: https://zooqle.com
.. _Deluge: https://en.wikipedia.org/wiki/Deluge_(software)
.. _IMDb: https://en.wikipedia.org/wiki/IMDb
.. _`YTS API`: https://yts.ag/api
.. _Jackett: https://github.com/Jackett/Jackett
.. _`Star Trek Beyond`: https://en.wikipedia.org/wiki/Star_Trek_Beyond
.. _`Star Trek IV`: https://en.wikipedia.org/wiki/Star_Trek_IV:_The_Voyage_Home
