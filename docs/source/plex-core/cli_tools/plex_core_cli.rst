================================================
Core Command Line Utilities
================================================

This section describes the two Plexstuff core command line utilities.

* ``plex_core_cli.py`` shows the list of email addresses, and names, of Plex account holders who have access to your Plex server. It can also show emails and names of all people who can receive email notifications about your Plex server. One can also change the list of email addresses that are notified by email of the Plex server.

* ``plex_deluge_console.py`` is a mocked up Deluge_ client, whose operation is very similar to the `deluge-console <deluge_console_>`_ command line interface. It is designed for the most common operations of the Deluge_ command line tool, using Deluge_ server settings that are described in :numref:`Plexstuff Settings Configuration` and :numref:`Login Services`.

* ``plex_resynclibs.py`` summarizes information about the Plex servers to which you have access.

* ``plex_store_credentials.py`` sets up the Google OAuth2 services authentication from the command line, similarly to what ``plex_config_gui.py`` does as described in :numref:`Summary of Setting Up Google Credentials` and in :numref:`Music Services` when setting up the `unofficial Google Music API <https://unofficial-google-music-api.readthedocs.io/en/latest>`_.

* ``rsync_subproc.py`` rsync_ copies (and removes) files from the remote server and optional remote subdirectory, to the local server and local directory, or vice-versa. This tool also allows one to update the location of the remote server, the remote subdirectory, and the local subdirectory. The update of the remote path, and local and remote subdirectories, can also be changed through the ``plex_config_gui.py`` GUI, as described in :numref:`Local and Remote (Seedhost) SSH Setup` and :numref:`Login Services` (see the screen shot in :numref:`login_step02_settings`).

``plex_core_cli.py``
^^^^^^^^^^^^^^^^^^^^

``plex_deluge_console.py``
^^^^^^^^^^^^^^^^^^^^^^^^^^

``plex_resynclibs.py``
^^^^^^^^^^^^^^^^^^^^^^^^^^

``plex_store_credentials.py``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ 

``rsync_subproc.py``
^^^^^^^^^^^^^^^^^^^^


.. _Deluge: https://en.wikipedia.org/wiki/Deluge_(software)
.. _deluge_console: https://whatbox.ca/wiki/Deluge_Console_Documentation
.. _rsync: https://en.wikipedia.org/wiki/Rsync
