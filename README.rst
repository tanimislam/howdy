.. image:: https://badges.gitter.im/plexstuff/community.svg
   :target: https://gitter.im/plexstuff/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=body_badge

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
* `Jackett <https://github.com/Jackett/Jackett>`_ is a relatively successful proxy server that consolidates the torrent search from a large number of public, private, and semi-private torrent trackers and services into a single search user interface and API.

* `PlexAPI <PlexAPI_>`_ are the unofficial bindings to the Plex API. They are based off the older `unofficial Plex API <unofficial_plex_api_>`_. I still use it because it seems to offer more freedom (such as finer grained multithreaded HTTP requests, and access to remote servers) than PlexAPI_.

The command line tools are built using Python's OptionParser_ module, and the GUIs are built with PyQt5_.

The comprehensive documentation lives in HTML created with `Sphinx <http://www.sphinx-doc.org/en/master/>`_, and now in the `Read the Docs <Plexstuff_>`_ page for this project. To generate the documentation, go to the ``docs`` subdirectory. In that directory, run ``make html``. Load ``docs/build/html/index.html`` into a browser to see the documentation.

Quick and Dirty -- How Do I Get It Working?
--------------------------------------------
Although discussed in the `Sphinx documentation <Plexstuff_>`_, to get everything working you need pandoc_, sshpass_, and PyQt5_. Getting all this on Linux machines is probably more straightforward than on Macs and Windows machines.

To be able to use all the CLIs, GUIs, and API functionality, there are ``12`` sets of configurations that need to work: four for login, four for credentials, and four for music.

.. |main_config_gui| image:: https://plexstuff.readthedocs.io/en/latest/_images/plex_config_gui_serviceswidget.png
   :width: 100%
   :align: middle

.. |login_config_gui| image:: https://plexstuff.readthedocs.io/en/latest/_images/plex_login_mainfigure.png
   :width: 100%
   :align: middle

.. |credentials_config_gui| image:: https://plexstuff.readthedocs.io/en/latest/_images/plex_credentials_mainfigure.png
   :width: 100%
   :align: middle

.. |music_config_gui| image:: https://plexstuff.readthedocs.io/en/latest/_images/plexmusic_mainfigure.png
   :width: 100%
   :align: middle

===========================================  ===========================================  ======================================================  ===========================================
|main_config_gui|                            |login_config_gui|                           |credentials_config_gui|                                |music_config_gui|
`12 total settings <sec_main_config_gui_>`_  `4 login settings <sec_login_config_gui_>`_  `4 credential settings <sec_credentials_config_gui_>`_  `4 music settings <sec_music_config_gui_>`_
===========================================  ===========================================  ======================================================  ===========================================

What Are Some Interesting Command Line Executables?
-----------------------------------------------------------------
You can try out `plex_music_songs.py`_ to get individual songs or all the songs in an artist's studio album, or `plex_music_album.py <https://plexstuff.readthedocs.io/en/latest/plex-music/cli_tools/plex_music_cli.html#plex-music-album-py>`_ to find all the studio albums an artist released. Here are three YouTube_ clips that show `plex_music_songs.py`_ in action, and were made with `Embed YouTube`_.

.. |plex_music_songs_clip1| image:: https://img.youtube.com/vi/W8pmTqFJy68/0.jpg
   :width: 100%
   :align: middle
   :target: https://www.youtube.com/watch?v=W8pmTqFJy68

.. |plex_music_songs_clip2| image:: https://img.youtube.com/vi/njkhP5VE7Kc/0.jpg
   :width: 100%
   :align: middle
   :target: https://www.youtube.com/watch?v=njkhP5VE7Kc

.. |plex_music_songs_clip3| image:: https://img.youtube.com/vi/W8pmTqFJy68/0.jpg
   :width: 100%
   :align: middle
   :target: https://www.youtube.com/watch?v=cRvxkGb2q3Y

===========================================  ===========================================  ===========================================
|plex_music_songs_clip1|                     |plex_music_songs_clip2|                     |plex_music_songs_clip3|                  
===========================================  ===========================================  ===========================================

.. links to plexstuff sections

.. _sec_main_config_gui: https://plexstuff.readthedocs.io/en/latest/plex-config/plex_config_gui_usage.html
.. _sec_login_config_gui: https://plexstuff.readthedocs.io/en/latest/plex-config/plex_config_gui_usage.html#login-services
.. _sec_credentials_config_gui: https://plexstuff.readthedocs.io/en/latest/plex-config/plex_config_gui_usage.html#credentials-services
.. _sec_music_config_gui: https://plexstuff.readthedocs.io/en/latest/plex-config/plex_config_gui_usage.html#music-services
	   

.. these are the links
.. _unofficial_plex_api: https://github.com/Arcanemagus/plex-api/wiki
.. _Plex: https://plex.tv
.. _PlexAPI: https://python-plexapi.readthedocs.io/en/latest/introduction.html
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
.. _OAuth2: https://en.wikipedia.org/wiki/OAuth#OAuth_2.0
.. _OptionParser: https://docs.python.org/3/library/optparse.html#optparse.OptionParser
.. _`Embed YouTube`: http://embedyoutube.org
.. _`plex_music_songs.py`: https://plexstuff.readthedocs.io/en/latest/plex-music/cli_tools/plex_music_cli.html#plex-music-songs-py
.. _Youtube: https://www.youtube.com
