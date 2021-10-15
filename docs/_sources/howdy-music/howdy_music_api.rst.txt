================================================
Howdy Music API
================================================
This document describes the lower level Howdy Music API, upon which the :ref:`command line tools <Howdy Music Command Line Utilities>`  are built. It lives in ``howdy.music``.

howdy.music module
----------------------------
This contains only three methods: two format durations strings for YouTube_ clips, and a third is used to search for M4A_ music files that are missing artist or album information.

.. automodule:: howdy.music
   :members:

howdy.music.music module
---------------------------------------

This contains the low-level functionality that does three things.

* Gets music metadata using either the Gracenote_, LastFM_, or MusicBrainz_ APIs.

* Retrieves YouTube_ clips using the `YouTube Google API`_ and yt-dlp_.

  .. note::

     I checked on 15 OCTOBER 2021, and I see some disturbing things. The latest version of youtube-dl_ is 6 JUNE 2021. This `discussion on YCombinator <https://news.ycombinator.com/item?id=28289981>`_ says that ``YouTube is dead``. Also, when I used the youtube-dl_ command line or the YoutubeDL API, my download speeds are no faster than 80 kbp/s. This means using yt-dlp_.

     From my cursory work, doing ``howdy_music_songs -M -a Air -s "All I Need"``, the old youtube-dl_ speeds that I loved and got used to seems to work again!

* Uploads music to one's own `Google Play Music`_ account using GMusicAPI_, and sets its credentials.

.. automodule:: howdy.music.music
   :members:

howdy.music.pygn module
----------------------------------

This contains functionality used by the :py:class:`HowdyMusic <howdy.music.music.HowdyMusic>` higher level object interface to the Gracenote_ API.

.. automodule:: howdy.music.pygn
   :members:

.. URLs here
.. _YouTube: https://www.youtube.com
.. _M4A: https://en.wikipedia.org/wiki/MPEG-4_Part_14
.. _Gracenote: https://developer.gracenote.com/web-api
.. _LastFM: https://www.last.fm/api
.. _MusicBrainz: https://musicbrainz.org/doc/Development/XML_Web_Service/Version_2
.. _`YouTube Google API`: https://developers.google.com/youtube/v3
.. _yt-dlp: https://github.com/yt-dlp/yt-dlp
.. _youtube-dl: https://ytdl-org.github.io/youtube-dl/index.html
.. _GMusicAPI: https://unofficial-google-music-api.readthedocs.io
.. _`Google Play Music`: https://play.google.com/music/listen
