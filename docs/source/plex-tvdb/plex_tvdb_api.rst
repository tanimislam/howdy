================================================
TVDB API
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

