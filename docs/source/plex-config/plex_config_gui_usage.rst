=================================================================
Consolidating Plexstuff Configuration With ``plex_config_gui.py``
=================================================================

Although ``plex_config_gui.py`` is part of ``plexcore``, and naturally lives in :numref:`Plexstuff Core Functionality`, I suggest you use this configuration tool to naturally consolidate the Plexstuff services and settings. The final configuration data will live in an `sqlite version 3 <https://en.wikipedia.org/wiki/SQLite>`_ database that is located in ``~/.local/plexstuff/app.db`` and is readable only by the user (and root).
