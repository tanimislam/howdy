================================================
Music Command Line Utilities
================================================

This section describes the four Plexstuff music command line utilities.

* :ref:`plex_music_album.py` can do three possible things: download an album image given an artist name and album name; pretty-print out all the studio albums released by an artist; and print out all the songs released on an album by an artist. It uses either the LastFM_ or MusicBrainz_ APIs.

* :ref:`plex_music_metafill.py` is an older Plex_ Music executable. It gets choices and song clips from YouTube_ and music metadata using the Gracenote_ API. This was an earlier trial to improve the functionality of :ref:`plex_music_songs.py`.

* :ref:`plex_music_songs.py` does...

* :ref:`upload_to_gmusic.py` does...

.. _plex_music_album.py_label:

plex_music_album.py
^^^^^^^^^^^^^^^^^^^^^^^
The help output, when running ``plex_music_album.py -h``, produces the following.

.. code-block:: bash

     Usage: plex_music_album.py [options]

     Options:
       -h, --help            show this help message and exit
       -a ARTIST_NAME, --artist=ARTIST_NAME
			     Name of the artist to get album image for.
       -A ALBUM_NAME, --album=ALBUM_NAME
			     Name of the album to get album image for.
       --songs               If chosen, get the song listing instead of downloading
			     the album image.
       --formatted           If chosen, print the song listing in a format
			     recognized by plex_music_metafill.py for downloading a
			     collection of songs.
       --albums              If chosen, then get a list of all the songs in all
			     studio albums for the artist.
       --debug               Run with debug mode turned on.
       --noverify            If chosen, do not verify SSL connections.
       --musicbrainz         If chosen, use Musicbrainz to get the artist metadata.
			     Note that this is expensive, and is always applied
			     when the --albums flag is set.

These are the common operational flags,

* ``--debug`` prints out :py:const:`DEBUG <logging.DEBUG>` level :py:mod:`logging` output.

* ``--noverify`` does not verify SSL connections.

* By default, this executable uses the LastFM_ API to get music metadata. The ``--musicbrainz`` flag then means the MusicBrainz_ API is used.
			     
Here are the three operations,

* Download an album's image to a PNG_ file in the current working directory. Here, the ``-a`` or ``--artist`` (artist) and ``-A`` or ``--album`` (album) need to be specified. To download the album image for the `Moon Safari`_ album released by Air_,

  .. code-block:: bash

     tanim-desktop $ plex_music_album.py -a Air -A "Moon Safari"
     tanim-desktop $ Air.Moon Safari.png

  Here is the image,

  .. _plex_music_album_image:
  
  .. figure:: plex-music-cli-figures/Air.Moon_Safari.png
     :width: 100%
     :align: center

* The ``--albums`` flag gets a formatted, pretty-printed list of albums released by an artist.  Here, the ``-a`` or ``--artist`` (artist) need to be specified. For example, for Air_,

  .. code-block:: bash

     tanim-desktop $ plex_music_albums.py -a Air --albums
     
     Air has 7 studio albums.

     Studio Album                         Year    # Tracks
     ---------------------------------  ------  ----------
     Moon Safari                          1998          10
     10 000 Hz Legend                     2001          12
     City Reading (Tre Storie Western)    2003          19
     Talkie Walkie                        2004          11
     Pocket Symphony                      2006          12
     Love 2                               2009          12
     Music for Museum                     2014           9

* The ``--song`` flag returns a list of songs released on a specific album by the artist. Here, the ``-a`` or ``--artist`` (artist) and ``-A`` or ``--album`` (album) need to be specified.

  * By default, the standard pretty-printed formatting if we do not use the ``--formatted`` flag. To get all the songs in track order for `Moon Safari`_ album released by Air_,

    .. code-block:: bash

       tanim-desktop $ plex_music_album.py -a Air -A "Moon Safari" --songs		  

       Song                                        Track #
       ----------------------------------------  ---------
       La Femme d'Argent                                 1
       Sexy Boy                                          2
       All I Need                                        3
       Kelly Watch the Stars                             4
       Talisman                                          5
       Remember                                          6
       You Make It Easy                                  7
       Ce Matin-Là                                       8
       New Star in the Sky (Chanson Pour Solal)          9
       Le Voyage De Pénélope                            10

.. _plex_music_abum_songs_formatted:

  * If we run with the ``--formatted`` flag, then the output is a semi-colon-delimited collection of songs in this album. This is an input format that can then be processed by :ref:`plex_music_metafill.py`. For songs in the `Moon Safari`_ album released by Air_,

    .. code-block:: bash

       tanim-desktop $ plex_music_album.py -a Air -A "Moon Safari" --songs --formatted	    

       La Femme d'Argent;Sexy Boy;All I Need;Kelly Watch the Stars;Talisman;Remember;You Make It Easy;Ce Matin-Là;New Star in the Sky (Chanson Pour Solal);Le Voyage De Pénélope

.. _plex_music_metafill.py_label:

plex_music_metafill.py
^^^^^^^^^^^^^^^^^^^^^^^^
The help output, when running ``plex_music_metafill.py -h``, produces the following.

.. code-block:: bash

     Usage: plex_music_metafill.py [options]

     Options:
       -h, --help            show this help message and exit
       -s SONG_NAMES, --songs=SONG_NAMES
			     Names of the song to put into M4A files. Separated by
			     ;
       -a ARTIST_NAME, --artist=ARTIST_NAME
			     Name of the artist to put into the M4A file.
       --maxnum=MAXNUM       Number of YouTube video choices to choose for your
			     song. Default is 10.
       -A ALBUM_NAME, --album=ALBUM_NAME
			     If defined, then use ALBUM information to get all the
			     songs in order from the album.
       --noverify            If chosen, do not verify SSL connections.	

Here are the common elements of its operation,
       
* the ``--noverify`` flag means to not verify SSL connections.

* the ``--maxnum`` setting is the maximum numbr of YouTube_ clips from which to choose. This must be :math:`\ge 1`, and its default is ``10``.

* the artist must always be specified with the ``-a`` or ``--artist`` setting.

This executable has two modes of operation. In each mode, for each song in the collection, this tool finds that song, finds that clip, and asks the user to choose a selection with a number from ``1`` to at most ``maxnum``. For example, here I choose YouTube_ clip #1 for the first track in the `Moon Safari`_ album released by Air_,

.. code-block:: bash

     ACTUAL ARTIST: Air
     ACTUAL ALBUM: Moon Safari
     ACTUAL YEAR: 1998
     ACTUAL NUM TRACKS: 10
     ACTUAL SONG: La Femme d'Argent
     Choose YouTube video:
     1: Air - La Femme d'Argent (07:12)
     2: Air - La Femme D'Argent (07:11)
     3: Air - La Femme D'Argent (05:55)
     4: La Femme D'Argent Extended - 26 Seamless Minutes (26:37)
     5: La femme d'argent (07:07)
     6: Air - La Femme d'Argent (Live at Canal+ 17.06.2016) HD (08:39)
     7: AIR - La Femme D'Argent (Live in France, 2007) (10:13)
     8: Air - La Femme D'Argent (EXTENDED 1H47) (01:47:42)
     9: Air - La femme d'argent 432hz (07:11)
     10: San Francisco 1906 with music by Air - La Femme D'Argent (07:06)
     1 
     [youtube] U4U19zwFENs: Downloading webpage
     [youtube] U4U19zwFENs: Downloading video info webpage
     WARNING: Unable to extract video title
     [download] Air.La Femme d'Argent.m4a has already been downloaded
     [download] 100% of 6.90MiB
     [ffmpeg] Correcting container in "Air.La Femme d'Argent.m4a"

* In the first mode of operation, give it a list of songs separated by semicolons. The format of songs is described in :ref:`this bullet point <plex_music_abum_songs_formatted>`, e.g.,

  .. code-block:: bash

     La Femme d'Argent;Sexy Boy;All I Need;Kelly Watch the Stars;Talisman;Remember;You Make It Easy;Ce Matin-Là;New Star in the Sky (Chanson Pour Solal);Le Voyage De Pénélope

  For songs in order in tha album `Moon Safari`_ by Air_. Below is an animation showing how this works in practice when downloading these songs. Here we always choose YouTube_ clip #1.

     
.. _plex_music_songs.py_label:

plex_music_songs.py
^^^^^^^^^^^^^^^^^^^^^^

.. _upload_to_gmusic.py_label:

upload_to_gmusic.py
^^^^^^^^^^^^^^^^^^^^^^^^^^


.. _YouTube: https://www.youtube.com
.. _Deluge: https://en.wikipedia.org/wiki/Deluge_(software)
.. _deluge_console: https://whatbox.ca/wiki/Deluge_Console_Documentation
.. _rsync: https://en.wikipedia.org/wiki/Rsync
.. _Plex: https://plex.tv
.. _`Magnet URI`: https://en.wikipedia.org/wiki/Magnet_URI_scheme
.. _SQLite3: https://www.sqlite.org/index.html
.. _Gracenote: https://developer.gracenote.com/web-api
.. _LastFM: https://www.last.fm/api
.. _MusicBrainz: https://musicbrainz.org/doc/Development/XML_Web_Service/Version_2
.. _PNG: https://en.wikipedia.org/wiki/Portable_Network_Graphics
.. _Air: https://en.wikipedia.org/wiki/Air_(band)
.. _`Moon Safari`: https://en.wikipedia.org/wiki/Moon_Safari
