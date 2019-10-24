================================================
PlexTVDB API
================================================

This document describes the lower level Plexstuff TVDB API, upon which the :ref:`command line tools <TVDB Command Line Utilities>` and  the :ref:`GUI tool <plex_tvdb_totgui.py>` are built. It lives in ``plexstuff.plextvdb``.

plextvdb module
------------------------

This module implements the lower-level functionalty that does the following:

     * Provides the SQLAlchemy_ ORM class on TV shows to exclude from analysis or update on the Plex_ server. This is the ``showstoexclude`` table and is in the :py:class:`ShowsToExclude <plextvdb.ShowsToExclude>` class.

     * Save and retrieve the TVDB_ API configuration data from the ``plexconfig`` table.

     * Retrieve and refresh the TVDB_ API access token.

.. automodule:: plextvdb
   :members:

plextvdb.plextvdb module
-----------------------------

This module contains the main back-end functionality used by the Plex TVDB GUIs and CLIs. Here are the main features of this module.

     * Create calendar eye charts of episodes aired by calendar year.

     * Search TVDB_ for all episodes aired for a TV show, and determine those episodes that are missing from one's Plex_ TV library.

     * Extracts useful information on episodes and TV shows that are used by Plex TVDB GUIs and CLIs.

     * Robust functionality that, with the :ref:`plextvdb.plextvdb_torrents module`, allows for the automatic download of episodes missing from the Plex_ TV library.

.. automodule:: plextvdb.plextvdb
   :members:

plextvdb.plextvdb_torrents module
-----------------------------------

This module implements higher level interfaces to the Jackett_ torrent searching server, and functionality that allows for the automatic download of episodes missing from the Plex_ TV library.

The seven methods that return the episode magnet links found by different torrent services -- :py:meth:`get_tv_torrent_eztv_io <plextvdb.plextvdb_torrents.get_tv_torrent_eztv_io>` (`EZTV.IO`_), :py:meth:`get_tv_torrent_zooqle <plextvdb.plextvdb_torrents.get_tv_torrent_zooqle>` (Zooqle_), :py:meth:`get_tv_torrent_rarbg <plextvdb.plextvdb_torrents.get_tv_torrent_rarbg>` (RARBG_), :py:meth:`get_tv_torrent_torrentz <plextvdb.plextvdb_torrents.get_tv_torrent_torrentz>` (Torrentz_), :py:meth:`get_tv_torrent_kickass <plextvdb.plextvdb_torrents.get_tv_torrent_kickass>` (KickassTorrents_), :py:meth:`get_tv_torrent_tpb <plextvdb.plextvdb_torrents.get_tv_torrent_tpb>` (`The Pirate Bay`_), and the unified torrent searcher :py:meth:`get_tv_torrent_jackett <plextvdb.plextvdb_torrents.get_tv_torrent_jackett>` (Jackett_ torrent search) -- produce a common two element :py:class:`tuple` output format.

* If successful, then the first element is a :py:class:`list` of elements that match the searched episode. Each element is a :py:class:`dict`, ordered by the total number of seeds and leechs. The second element is the string ``"SUCCESS"``. The **common** keys in each element are,
  
  * ``title`` is the name of the candidate episode to download.
  * ``seeders`` is the number of seeds for this Magnet link.
  * ``leechers`` is the number of leeches for this Magnet link.
  * ``link`` is the Magnet URI link.

  Some methods may have more keys. For example, the top candidate when running ``data, status = get_tv_torrent_zooqle( 'The Simpsons S31E01' )`` is,

  .. code-block:: python

     {'title': 'The Simpsons S31E01 WEB x264-TBS[ettv]',
      'seeders': 182,
      'leechers': 68,
      'link': 'magnet:?xt=urn:btih:9dd4eac1873901420451fb569feb33ac0da649b5&dn=The+Simpsons+S31E01+WEB+x264-TBS[ettv]&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.pomf.se%3A80%2Fannounce&tr=udp%3A%2F%2Ftorrent.gresille.org%3A80%2Fannounce&tr=udp%3A%2F%2F11.rarbg.com%2Fannounce&tr=udp%3A%2F%2F11.rarbg.com%3A80%2Fannounce&tr=udp%3A%2F%2Fopen.demonii.com%3A1337%2Fannounce&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=http%3A%2F%2Ftracker.ex.ua%3A80%2Fannounce&tr=http%3A%2F%2Ftracker.ex.ua%2Fannounce&tr=http%3A%2F%2Fbt.careland.com.cn%3A6969%2Fannounce&tr=udp%3A%2F%2Fglotorrents.pw%3A6969%2Fannounce',
      'torrent_size': 170515743}

  The extra key is ``torrent_size``, the size of the candidate in bytes.

* If unsuccesful, then returns an error :py:class:`tuple` of the form returned by :py:meth:`return_error_raw <plexcore.return_error_raw>`.

As of |date|, here are the magnet link methods that work and don't work when searching for ``"The Simpsons S31E01"``.

.. _table_working_tvtorrents:

=======================  =======================================================================================  ===============
Torrent Service          Search Method                                                                            Does It Work?
=======================  =======================================================================================  ===============
`EZTV.IO`_               :py:meth:`get_tv_torrent_eztv_io <plextvdb.plextvdb_torrents.get_tv_torrent_eztv_io>`    False
Zooqle_                  :py:meth:`get_tv_torrent_zooqle <plextvdb.plextvdb_torrents.get_tv_torrent_zooqle>`      True
RARBG_                   :py:meth:`get_tv_torrent_rarbg <plextvdb.plextvdb_torrents.get_tv_torrent_rarbg>`        False
Torrentz_                :py:meth:`get_tv_torrent_torrentz <plextvdb.plextvdb_torrents.get_tv_torrent_torrentz>`  False
KickAssTorrents_         :py:meth:`get_tv_torrent_kickass <plextvdb.plextvdb_torrents.get_tv_torrent_kickass>`    False
`The Pirate Bay`_        :py:meth:`get_tv_torrent_tpb <plextvdb.plextvdb_torrents.get_tv_torrent_tpb>`            False
Jackett_ torrent search  :py:meth:`get_tv_torrent_jackett <plextvdb.plextvdb_torrents.get_tv_torrent_jackett>`    True
=======================  =======================================================================================  ===============

.. automodule:: plextvdb.plextvdb_torrents
   :members:

plextvdb.plextvdb_attic module
-------------------------------

This contains broken, stale, and long-untested and unused Plex TVDB functionality. Some methods may live here until they are actively used in Plex TVDB GUIs and CLIs.

.. automodule:: plextvdb.plextvdb_attic
   :members:

.. _SQLAlchemy: https://www.sqlalchemy.org
.. _TVDB: https://api.thetvdb.com/swagger
.. _plex: https://plex.tv
.. _Jackett: https://github.com/Jackett/Jackett
.. _`EZTV.IO`: https://eztv.io
.. _Zooqle: https://zooqle.com
.. _RARBG: https://en.wikipedia.org/wiki/RARBG
.. _Torrentz: https://en.wikipedia.org/wiki/Torrentz
.. _KickassTorrents: https://en.wikipedia.org/wiki/KickassTorrents
.. _`The Pirate Bay`: https://en.wikipedia.org/wiki/The_Pirate_Bay
.. |date| date:: %B %d, %Y
