=================================================================
Consolidating Plexstuff Configuration With ``plex_config_gui.py``
=================================================================

Although ``plex_config_gui.py`` is part of ``plexcore``, and naturally lives in :numref:`Plexstuff Core Functionality`, I suggest you use this configuration tool to naturally consolidate the Plexstuff services and settings. The final configuration data will live in an `sqlite version 3 <https://en.wikipedia.org/wiki/SQLite>`_ database that is located in ``~/.local/plexstuff/app.db`` and is readable only by the user (and root).

Some of the ``plex_config_gui.py`` screenshots are found in :numref:`Summary of Setting Up Google Credentials` (specifically :numref:`google_step01_credentials`, :numref:`google_step02_refreshcredentials`, and :numref:`google_step04_oauthtokenstring`) and in :numref:`Plexstuff Settings Configuration` (specifically :numref:`login_step01_login` and :numref:`login_step02_settings`).
