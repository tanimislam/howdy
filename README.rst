###################################################################
Plexstuff - Yet Another Way to Manage Your Plex_ Server's Content
###################################################################

Plexstuff is a (hopefully) useful SDK that I have developed to manage (and download) the movies, television shows, and music in which I am interested. I hope that it is, or becomes, a worthy member of the rich community of services used to manage one's media.

Here are a few of the best known high level media management services:

* `Radarr <https://radarr.video/>`_ or `Couchpotato <https://couchpota.to/>`_ to manage your movies (automatically download them, etc.).
* `Sonarr <https://sonarr.tv/>`_ or `Sickrage <https://www.sickrage.ca/>`_ to manage your television shows (automatically download them as they become available, for instance).
* `Lidarr <https://lidarr.audio/>`_ to manage your music.
* `Subliminal <https://subliminal.readthedocs.io/en/latest/>`_ to download movie and TV show subtitles.

Here are some of the best known lower APIs used to help one manage your Plex_ server.

* `Tautulli <https://tautulli.com>`_ to monitor your Plex_ server.
* `Jackett <https://github.com/Jackett/Jackett>`_ is a relatively successful proxy server that consolidates the torrent search from a´ large number of public, private, and semi-private torrent trackers and services into a single search user interface and API.

* `PlexAPI <PlexAPI_>`_ are the unofficial bindings to the Plex API. They are based off the older `unofficial Plex API <unofficial_plex_api_>`_. I still use it because it seems to offer more freedom (such as finer grained multithreaded HTTP requests, and access to remote servers) than PlexAPI_.

The comprehensive documentation lives in HTML created with `Sphinx <http://www.sphinx-doc.org/en/master/>`_, and now in the `Read the Docs <Plexstuff_>`_ page for this project. To generate the documentation, go to the ``docs`` subdirectory. In that directory, run ``make html``. Load ``docs/build/html/index.html`` into a browser to see the documentation.


.. these are the links
.. _unofficial_plex_api: https://github.com/Arcanemagus/plex-api/wiki
.. _Plex: https://plex.tv
.. _PlexAPI: https://python-plexapi.readthedocs.io/en/latest/introduction.html
.. _PyQt4: https://www.riverbankcomputing.com/static/Docs/PyQt4/index.html
.. _PyQt5: https://www.riverbankcomputing.com/static/Docs/PyQt5/index.html
.. _sshpass: https://linux.die.net/man/1/sshpass
.. _pandoc: https://pandoc.org
.. _sudo: https://en.wikipedia.org/wiki/Sudo
.. _LaTeX: https://en.wikipedia.org/wiki/LaTeX
.. _ghc: https://www.haskell.org/ghc
.. _stack: https://docs.haskellstack.org/en/stable/README
.. _cabal: http://hackage.haskell.org/package/cabal-install
.. _Ubuntu: https://www.ubuntu.com
.. _Mint: https://linuxmint.com
.. _Debian: https://www.debian.org
.. _Red Hat: https://www.redhat.com/en
.. _Fedora: https://getfedora.org
.. _CentOS: https://www.centos.org
.. _fbs: https://www.learnpyqt.com/courses/packaging-and-distribution/packaging-pyqt5-apps-fbs
.. _Plexstuff: https://plexstuff.readthedocs.io
.. _Plex: https://plex.tv
