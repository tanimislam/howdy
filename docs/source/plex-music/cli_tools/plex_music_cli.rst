================================================
Music Command Line Utilities
================================================

This section describes the four Plexstuff music command line utilities.

* :ref:`plex_music_album.py` can do three possible things: download an album image given an artist name and album name; pretty-print out all the studio albums released by an artist; and print out all the songs released on an album by an artist. It uses either the LastFM_ or MusicBrainz_ APIs.

* :ref:`plex_music_metafill.py` is an older Plex_ Music executable. It gets choices and song clips from YouTube_ and music metadata using the Gracenote_ API. This was an earlier trial to improve the functionality of :ref:`plex_music_songs.py`.

* :ref:`plex_music_songs.py` is a work-horse CLI that can do three things (:ref:`download songs with artist and song list <download_by_artist_songs>`, :ref:`download songs with artist and album <download_by_artist_album>`, or :ref:`download a list of songs with a list of corresponding artists <download_by_artists_songs_list>`) using the three music metadata services (Gracenote_, LastFM_, or MusicBrainz_).

* :ref:`upload_to_gmusic.py` uploads MP3_ or M4A_ music files to one's `Google Play Music`_ account, or pushes the appropriate :py:mod:`gmusicapi` :py:class:`Mobileclient <gmusicapi.Mobileclient>` credentials into the SQLite3_ configuration database.

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

.. _plex_music_album_get_albums:
	
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

This executable has two modes of operation. In each mode, for each song in the collection, this tool finds that song, finds that clip, and asks the user to select a clip with a number from ``1`` to at most ``maxnum``. For convenience, each YouTube_ clip also shows its duration in MM:SS format. For example, here I choose YouTube_ clip #1 for the first track in the `Moon Safari`_ album released by Air_,

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

  For songs in order in the album `Moon Safari`_ by Air_. Below is an animation showing how this works in practice when downloading these songs. Here we always choose YouTube_ clip #1.

  .. _plex_music_metafill_songs:

  .. youtube:: PflzMfN4A9w
     :width: 100%

  The list of songs came from the LastFM_ service, and Gracenote_ cannot find Air_ songs in `Moon Safari`_ with the names ``Ce Matin-Là`` and ``Le Voyage De Pénélope`` due (probably) to diacritical accents.

* In the second mode of operation, give it the album name with ``-A`` or ``--album``. For example ``plex_music_metafill.py -a Air -A "Moon Safari"`` to get all ten songs in this album,

  .. _plex_music_metafill_album:
  
  .. youtube:: OMu5wpb49Sw
     :width: 100%

  Here Gracenote_ is able to find all songs, including ``Ce Matin La`` (instead of ``Ce Matin-Là``) and ``Le Voyage De Penelope`` (instead of ``Le Voyage De Pénélope``).
  
.. _plex_music_songs.py_label:

plex_music_songs.py
^^^^^^^^^^^^^^^^^^^^^^
The help output, when running ``plex_music_songs.py -h``, produces the following.

.. code-block:: bash

     Usage: plex_music_songs.py [options]

     Options:
       -h, --help            show this help message and exit
       -a ARTIST_NAME, --artist=ARTIST_NAME
			     Name of the artist to put into the M4A file.
       -s SONG_NAMES, --songs=SONG_NAMES
			     Names of the song to put into M4A files. Separated by
			     ;
       --maxnum=MAXNUM       Number of YouTube video choices to choose for each of
			     your songs.Default is 10.
       -A ALBUM_NAME, --album=ALBUM_NAME
			     If defined, then get all the songs in order from the
			     album.
       --new                 If chosen, use the new format for getting the song
			     list. Instead of -a or --artist, will look for
			     --artists. Each artist is separated by a ';'.
       --artists=ARTIST_NAMES
			     List of artists. Each artist is separated by a ';'.
       --lastfm              If chosen, then only use the LastFM API to get song
			     metadata.
       --musicbrainz         If chosen, use Musicbrainz to get the artist metadata.
			     Note that this is expensive.
       --noverify            Do not verify SSL transactions if chosen.
       --debug               Run with debug mode turned on.

In all three operations, here are required arguments or common flags,

* ``-a`` or ``--artist``: the artist must always be specified.

* ``--maxnum`` specifies the maximum number of YouTube_ video clips from which to choose. This number must be :math:`\ge 1`, and its default is ``10``.

* ``--noverify`` does not verify SSL connections.

* ``--debug`` prints out :py:const:`DEBUG <logging.DEBUG>` level :py:mod:`logging` output.
       
The complicated collection of flags and arguments allows ``plex_music_songs.py`` to download a collection of songs in three ways,

* in :numref:`download_by_artist_songs`, by specifying artist and list of songs.

* in :numref:`download_by_artist_album`, by specifying artist and album.

* in :numref:`download_by_artists_songs_list`, by specifying a corresponding list of songs with matching artists.

and using three music metadata services: Gracenote_, LastFM_, and MusicBrainz_. The Gracenote_ service is used or started with by default, but,

* ``--lastfm`` says to use or start with the LastFM_ API.

* ``--musicbrainz`` says to use or start with the MusicBrainz_ API.

* At most only one of ``--lastfm`` or ``--musicbrainz`` can be specified.

Each of the three operations can be either *progressive* or *exclusive*.

.. _progressive_selection:

* *progressive* means that the selection and downloading of songs starts with a given music service. If that service does not work, then it continues by order until successful. For example, if the Gracenote_ service does not work, then try LastFM_; if LastFM_ does not work, then try MusicBrainz_; if MusicBrainz_ does not work, then give up. :numref:`order_progress_music_service` summarizes how this process works, based on the metadata choice flag (``--lastfm``, ``--musicbrainz``, or none). The number in each cell determines the order in which to try until success -- 1 means 1st, 2 means 2nd, etc.

   .. _order_progress_music_service:

   =================  ============  =========  ==============
   metadata flag        Gracenote_  LastFM_    MusicBrainz_
   =================  ============  =========  ==============
   default (no flag)             1  2          3
   ``--lastfm``                  1  2
   ``--musicbrainz``             1
   =================  ============  =========  ==============

.. _exclusive_selection:
   
* *exclusive* means that the selection of downloading of songs *only uses* a single given music service; if the songs cannot be found using it, then it gives up. :numref:`order_exclusive_music_service` summarizes how this process works, matching metadata flag to music service.

  .. _order_exclusive_music_service:

  =================  ============  =========  ==============
  metadata flag      Gracenote_    LastFM_    MusicBrainz_
  =================  ============  =========  ==============
  default (no flag)  1
  ``--lastfm``                     1
  ``--musicbrainz``                           1
  =================  ============  =========  ==============

Once the metadata service finds the metadata for those songs, the CLI provides a selection of YouTube_ clips corresponding to a given song *AND* what the music metadata service thinks is the best match to the selected song. Each clip also shows the length (in MM:SS format) to let you choose one that is high ranking and whose length best matches the song's length.

.. _example_song_youtube_clip:

Here ``plex_music_songs.py`` looks for a song, Remember_ by Air_, using the music service MusicBrainz_,

1. The service finds the match and prints out the artist, album, and song.
       	       	     	 
   .. code-block:: bash
   
      ACTUAL ARTIST: Air
      ACTUAL ALBUM: Moon Safari
      ACTUAL SONG: Remember (02:34)

   MusicBrainz_ always gives the song length after the song name (ACTUAL SONG row). LastFM_ may do so if it can find the song's length (by internally using the MusicBrainz_ API). Gracenote_ does not have the song length information.
   
2. A selection of candidate YouTube_ clips are given, each with duration. I find it best to choose a clip that is as highly ranked as possible and whose duration matches the actual song's duration (if provided).

   .. code-block:: bash

      ACTUAL ARTIST: Air
      ACTUAL ALBUM: Moon Safari
      ACTUAL SONG: Remember (02:34)
      Choose YouTube video:
      1: Air - Remember (04:13)
      2: Remember (02:35)
      3: Air - Remember (02:49)
      4: Remember (David Whitaker Version) (02:22)
      5: Air - Remember – Live in San Francisco (03:04)
      6: Air - Remember (03:41)
      7: Air - Remember – Outside Lands 2016, Live in San Francisco (02:40)
      8: Air - Remember (Original Mix) (03:14)
      9: AIR - Remember live@ FOX Oakland (02:38)
      10: Air - Remember (02:24)

3. Make a selection from the command line, such as ``2`` (because the high ranking clip's duration matches the song's duration very closely). The song then downloads into the file, ``Air.Remember.m4a``, in the current working directory.

   .. code-block:: bash

      ACTUAL ARTIST: Air
      ACTUAL ALBUM: Moon Safari
      ACTUAL SONG: Remember (02:34)
      Choose YouTube video:
      1: Air - Remember (04:13)
      2: Remember (02:35)
      3: Air - Remember (02:49)
      4: Remember (David Whitaker Version) (02:22)
      5: Air - Remember – Live in San Francisco (03:04)
      6: Air - Remember (03:41)
      7: Air - Remember – Outside Lands 2016, Live in San Francisco (02:40)
      8: Air - Remember (Original Mix) (03:14)
      9: AIR - Remember live@ FOX Oakland (02:38)
      10: Air - Remember (02:24)
      2
      [youtube] JqMdhEy4hG8: Downloading webpage
      [youtube] JqMdhEy4hG8: Downloading video info webpage
      WARNING: Unable to extract video title
      [youtube] JqMdhEy4hG8: Downloading js player vflGnuoiU
      [youtube] JqMdhEy4hG8: Downloading js player vflGnuoiU
      [download] Destination: Air.Remember.m4a
      [download] 100% of 2.38MiB in 00:02
      [ffmpeg] Correcting container in "Air.Remember.m4a"

.. _download_by_artist_songs:

download songs using ``--songs`` and ``--artist`` flag
--------------------------------------------------------
Here, one specifies the collection of songs to download by giving the artist and list of songs through ``--songs``. Each song is separated by a ";". The metadata service to use here is :ref:`progressive <progressive_selection>`. For example, to get `Don't be Light`_ and `Mer du Japon`_ by Air_ using the MusicBrainz_ service,

.. _plex_music_songs_download_artist_songs:

.. youtube:: W8pmTqFJy68
   :width: 100%

.. _download_by_artist_album:

download songs using ``--artist`` and ``--album`` flag
-------------------------------------------------------
One specifies the collection of songs to download by giving the artist and album through ``--album``. The metadata service to use is :ref:`progressive <progressive_selection>`. You can get the list of albums produced by the artist by running :ref:`plex_music_albums.py --artist="artist" --albums <plex_music_album_get_albums>`. The clip below demonstrates how to get the album `Moon Safari`_ by Air_ using the MusicBrainz_ service,

.. _plex_music_songs_download_artist_album:

.. youtube:: njkhP5VE7Kc
   :width: 100%

.. _download_by_artists_songs_list:

download songs using ``--new``, ``--artists`` and ``--songs``
---------------------------------------------------------------------
Here, one uses the `--new`` flag and specifies, IN ORDER, the artists (using the ``--artists`` argument) and respective songs (using the ``--songs`` argument)  to download the collection of songs. Artists are separated by ";" and songs are separated by ";". The metadata service to use here is :ref:`exclusive <exclusive_selection>`. For example, to get these two songs by two different artists using the MusicBrainz_ service,

* `Different <https://youtu.be/YNB2Cw5y66o>`_ by `Ximena Sariñana <https://en.wikipedia.org/wiki/Ximena_Sari%C3%B1ana>`_.

* `Piensa en Mí <https://youtu.be/LkPn2ny5V4E>`_ by `Natalia Lafourcade <https://en.wikipedia.org/wiki/Natalia_Lafourcade>`_.

We run this command,

.. code-block:: bash

   plex_music_service.py --new --artists="Ximena Sariñana;Natalia Lafourcade" -s "Different;Piensa en Mí" --musicbrainz

whose video is shown below,

.. _plex_music_songs_download_artists_songs_list:

.. youtube:: cRvxkGb2q3Y
   :width: 100%

.. _upload_to_gmusic.py_label:

upload_to_gmusic.py
^^^^^^^^^^^^^^^^^^^^^^^^^^
The help output, when running ``upload_to_gmusic.py -h``, produces the following.

.. code-block:: bash

   Usage: upload_to_gmusic.py [options]

   Options:
     -h, --help            show this help message and exit
     -f FILENAMES, --filenames=FILENAMES
			   Give the list of filenames to put into the Google
			   Music Player.
     -P                    If chosen, then push Google Music API Mobileclient
			   credentials into the configuration database.
     --noverify            If chosen, do not verify SSL connections.

The ``--noverify`` flag disables verification of SSL HTTP connections. The standard operation of this tool is to *upload* songs to your `Google Play Music`_ account. The ``-f`` or ``--filenames`` argument can take semicolon-delimited filenames, or standard POSIX globs, for example,

.. code-block:: bash

   upload_to_gmusic.py -f "Air.*m4a"

attempts to upload all filenames that match ``Air.*m4a``.

The other mode of operation, running with the ``-P`` flag without specifying files to upload, attempts to refresh the :py:mod:`gmusicapi` :py:class:`Mobileclient <gmusicapi.Mobileclient>` OAuth2 credentials. Its operation is similar to that of :ref:`plex_store_credentials.py`. These dialogs in the shell appear,

.. code-block:: bash

   tanim-desktop $ upload_to_gmusic.py -P
   Please go to this URL in a browser window:https://accounts.google.com/o/oauth2/auth...
   After giving permission for Google services on your behalf,
   type in the access code:

Second, go to the URL to which you are instructed. Once you copy that URL into your browser, you will follow a set of prompts asking you to choose which Google account to allow access, and to allow permissions for this app to access your `Google Play Music`_ account.

Third, paste the code similar to as described in :ref:`Step #7 <google_step07_oauthtokencopy>` into the interactive text dialog, ``...type in the access code:``. Once successful, you will receive this message in the shell,

.. code-block:: bash

   Success. Stored GMusicAPI Mobileclient credentials.


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
.. _M4A: https://en.wikipedia.org/wiki/MPEG-4_Part_14
.. _MP3: https://en.wikipedia.org/wiki/MP3
.. _`Google Play Music`: https://play.google.com/music/listen
.. _Remember: https://youtu.be/D7umgkNX8NM
.. _`Don't be Light`: https://youtu.be/ysk_dQ39ctE
.. _`Mer du Japon`: https://youtu.be/Sjq4_sHy06U
