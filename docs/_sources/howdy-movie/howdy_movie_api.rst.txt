================================================
Howdy Movie API
================================================
This document describes the lower level Howdy TMDB API, upon which :ref:`get_mov_tor` and :ref:`howdy_movie_totgui_label` are built. It lives in ``howdy.movie``.

howdy.movie module
--------------------------

This module implements the lower-level functionality that does the following:

   * Stores and retrieves the TMDB_ API key.
   
   * Creates two configuration singletons, :py:class:`TMDBEngine <howdy.movie.TMDBEngine>` and :py:class:`TMDBEngineSimple <howdy.movie.TMDBEngineSimple>`, that contain movie genre information from the TMDB_ database.

.. automodule:: howdy.movie
   :members:
   :private-members:
   :inherited-members:

howdy.movie.movie module
-------------------------------------
This module contains the main back-end functionality used by the :ref:`get_mov_tor` and :ref:`howdy_movie_totgui_label`, and other functionalities that are used by methods in the :ref:`Howdy TV API`. Here are the main features of this module.

   * Retrieving TV show information using the TMDB_ database.

   * Getting comprehensive movie information.

.. automodule:: howdy.movie.movie
   :members:

howdy.movie.movie_torrents module
------------------------------------------------
This module implements higher level interfaces to the Jackett_ torrent searching server, and functionality that allows for the automatic download of episodes missing from the Plex_ Movie library. It is very similar to the :ref:`tv.tv_torrents module <howdy.tv.tv_torrents module>`, except for the following differences.

* methods here are called with ``movie_torrent_`` instead of ``tv_torrent_``.

* no method that searches on the Torrentz_ torrent tracker.
  
* an extra method, :py:meth:`get_movie_torrent <howdy.movie.movie_torrents.get_movie_torrent>` uses the `YTS API`_ to retrieve movie `torrent files <torrent file_>`_ instead of Magnet links.

Here are the six methods that return the movie magnet links found by different torrent services -- :py:meth:`get_movie_torrent_eztv_io <howdy.movie.movie_torrents.get_movie_torrent_eztv_io>` (`EZTV.IO`_), :py:meth:`get_movie_torrent_zooqle <howdy.movie.movie_torrents.get_movie_torrent_zooqle>` (Zooqle_), :py:meth:`get_movie_torrent_rarbg <howdy.movie.movie_torrents.get_movie_torrent_rarbg>` (RARBG_), :py:meth:`get_movie_torrent_kickass <howdy.movie.movie_torrents.get_movie_torrent_kickass>` (KickassTorrents_), :py:meth:`get_movie_torrent_tpb <howdy.movie.movie_torrents.get_movie_torrent_tpb>` (`The Pirate Bay`_), and the unified torrent searcher :py:meth:`get_movie_torrent_jackett <howdy.movie.movie_torrents.get_movie_torrent_jackett>` (Jackett_ torrent search) -- produce a common two element :py:class:`tuple` output format.

* If successful, then the first element is a :py:class:`list` of elements that match the searched episode. Each element is a :py:class:`dict`, ordered by the total number of seeds and leechs. The second element is the string ``"SUCCESS"``. The **common** keys in each element are,
  
  * ``title`` is usually the name of the candidate movie to download.
  * ``seeders`` is the number of seeds for this Magnet link.
  * ``leechers`` is the number of leeches for this Magnet link.
  * ``link`` is the Magnet URI link.

  Some methods may have more keys. For example, the top candidate when running ``data, status = get_movie_torrent_zooqle( 'Star Trek Beyond' )`` (a search on Zooqle_ for `Star Trek Beyond`_) is,

  .. code-block:: python

     {'title': 'Star Trek Beyond (2016) [720p] (897.141 MB)',
      'raw_title': 'Star Trek Beyond (2016) [720p]',
       'seeders': 219,
       'leechers': 17,
       'link': 'magnet:?xt=urn:btih:87e08ea9ed87fd2b54ba66c755cf054889680f17&dn=Star+Trek+Beyond+(2016)+[720p]&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.pomf.se%3A80%2Fannounce&tr=udp%3A%2F%2Ftorrent.gresille.org%3A80%2Fannounce&tr=udp%3A%2F%2F11.rarbg.com%2Fannounce&tr=udp%3A%2F%2F11.rarbg.com%3A80%2Fannounce&tr=udp%3A%2F%2Fopen.demonii.com%3A1337%2Fannounce&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=http%3A%2F%2Ftracker.ex.ua%3A80%2Fannounce&tr=http%3A%2F%2Ftracker.ex.ua%2Fannounce&tr=http%3A%2F%2Fbt.careland.com.cn%3A6969%2Fannounce&tr=udp%3A%2F%2Fglotorrents.pw%3A6969%2Fannounce',
       'torrent_size' : 940720557}

  The extra keys here are ``torrent_size`` (the size of the candidate in bytes), and ``raw_title`` (the name of the candidate to download). Here ``title`` is the name of the candidate, and in parentheses is the size of the download in MB or GB.

An extra method, :py:meth:`get_movie_torrent <howdy.movie.movie_torrents.get_movie_torrent>` uses the `YTS API`_ to retrieve movie `torrent files <torrent file_>`_.

As of |date|, here are three movie torrent finding methods that work and don't work when searching for `Star Trek Beyond`_. See :numref:`table_working_tvtorrents` for a description of what services or trackers work for downloading TV torrents.

.. _table_working_movietorrents:

.. list-table:: Which Movie Torrent Trackers or Services Work?
   :widths: auto

   * - Torrent Service
     - Logo
     - Search Method
     - Does It Work?
   * - `EZTV.IO`_
     - |eztv_logo_image|
     - :py:meth:`get_movie_torrent_eztv_io <howdy.movie.movie_torrents.get_movie_torrent_eztv_io>`
     - ``False``
   * - Zooqle_
     - |zooqle_logo_image|
     - :py:meth:`get_movie_torrent_zooqle <howdy.movie.movie_torrents.get_movie_torrent_zooqle>`
     - ``True``
   * - RARBG_
     - |rarbg_logo_image|
     - :py:meth:`get_movie_torrent_rarbg <howdy.movie.movie_torrents.get_movie_torrent_rarbg>`
     - ``False``
   * - KickAssTorrents_
     - |kickass_torrents_logo_image|
     - :py:meth:`get_movie_torrent_kickass <howdy.movie.movie_torrents.get_movie_torrent_kickass>`
     - ``False``
   * - `The Pirate Bay`_
     - |pirate_bay_logo_image|
     - :py:meth:`get_movie_torrent_tpb <howdy.movie.movie_torrents.get_movie_torrent_tpb>`
     - ``False``
   * - Jackett_ torrent search
     - |jackett_logo_image|
     - :py:meth:`get_movie_torrent_jackett <howdy.movie.movie_torrents.get_movie_torrent_jackett>`
     - ``True``
   * - `YTS API`_
     - |yts_logo_image|
     - :py:meth:`get_movie_torrent <howdy.movie.movie_torrents.get_movie_torrent>`
     - ``True``

.. |eztv_logo_image| image:: howdy-movie-figs/eztv_logo.png
   :width: 100%
   :align: middle
   :target: `EZTV.IO`_

.. |zooqle_logo_image| image:: howdy-movie-figs/zooqle_logo.png
   :width: 100%
   :align: middle
   :target: Zooqle_

.. |rarbg_logo_image| image:: howdy-movie-figs/rarbg_logo.png
   :width: 100%
   :align: middle
   :target: RARBG_

.. |kickass_torrents_logo_image| image:: howdy-movie-figs/kickass_torrents_logo.png
   :width: 100%
   :align: middle
   :target: KickAssTorrents_

.. |pirate_bay_logo_image| image:: howdy-movie-figs/pirate_bay_logo.svg
   :width: 100%
   :align: middle
   :target: `The Pirate Bay`_

.. |jackett_logo_image| image:: howdy-movie-figs/jackett_logo.png
   :width: 100%
   :align: middle
   :target: Jackett_

.. |yts_logo_image| image:: howdy-movie-figs/yts_logo.svg
   :width: 100%
   :align: middle
   :target: `YTS API`_

.. automodule:: howdy.movie.movie_torrents
   :members:

.. _TMDB: https://www.themoviedb.org/documentation/api?language=en-US
.. _`YTS API`: https://yts.ag/api
.. _Jackett: https://github.com/Jackett/Jackett
.. _`EZTV.IO`: https://eztv.io
.. _plex: https://plex.tv
.. _Zooqle: https://zooqle.com
.. _RARBG: https://en.wikipedia.org/wiki/RARBG
.. _Torrentz: https://en.wikipedia.org/wiki/Torrentz
.. _KickassTorrents: https://en.wikipedia.org/wiki/KickassTorrents
.. _`The Pirate Bay`: https://en.wikipedia.org/wiki/The_Pirate_Bay
.. _`torrent file`: https://en.wikipedia.org/wiki/Torrent_file
.. _`Star Trek Beyond`: https://en.wikipedia.org/wiki/Star_Trek_Beyond
.. |date| date:: %B %d, %Y
