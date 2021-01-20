.. image:: https://badges.gitter.im/howdy/community.svg
   :target: https://gitter.im/tanimislam/howdy?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge

.. image:: https://readthedocs.org/projects/howdy/badge/?version=latest
   :target: https://tanimislam.ddns.net/howdy

#############################################################################
|howdy_icon| Howdy! - Yet Another Way to Manage Your Plex_ Server's Content
#############################################################################
Howdy! (previously Plexstuff) is a (hopefully) useful SDK_ that I have developed to manage the movies, television shows, and music in which I am interested. I hope that it is, or becomes, a worthy member of the rich community of services used to manage one's media.

Here are a few of the best known high level media management services:

* Radarr_ or Couchpotato_ to manage your movies.
* Sonarr_ or Sickrage_ to manage your television shows.
* Lidarr_ to manage your music.
* Subliminal_ to download subtitles of movies and TV shows.

Here are some of the best known lower APIs used to help one manage your Plex_ server.

* Tautulli_ to monitor your Plex_ server.
* Jackett_ is a relatively successful proxy server that consolidates the torrent search from a large number of public, private, and semi-private torrent trackers and services into a single search user interface and API.

* `PlexAPI <PlexAPI_>`_ is the unofficial bindings to the Plex API. They are based off the older `unofficial Plex API <unofficial_plex_api_>`_. I still use the `unofficial Plex API <unofficial_plex_api_>`_ because it seems to offer more freedom (such as finer grained multithreaded HTTP requests, and access to remote servers) than PlexAPI_.

The command line tools are built using Python's ArgumentParser_ object, and the GUIs are built with PyQt5_.

The comprehensive documentation lives in HTML created with Sphinx_, and now in the `Read the Docs <Howdy_>`_ page for this project. To generate the documentation,

1. go to the ``docs`` subdirectory.
2. In that directory, run ``make html``.
3. Load ``docs/build/html/index.html`` into a browser to see the documentation.

Quick and Dirty -- How Do I Get It Working?
--------------------------------------------
Although discussed in the `Sphinx documentation <Howdy_>`_, to get everything working you need sshpass_ and PyQt5_. Getting all this on Linux machines is probably more straightforward than on Macs and Windows machines.

To be able to use all the CLIs, GUIs, and API functionality, there are ``12`` sets of configurations that need to work: four for login, four for credentials, and four for music.

.. |main_config_gui| image:: https://tanimislam.github.io/howdy/_images/howdy_config_gui_serviceswidget.png 
   :width: 100%
   :align: middle

.. |login_config_gui| image:: https://tanimislam.github.io/howdy/_images/howdy_login_mainfigure.png
   :width: 100%
   :align: middle

.. |credentials_config_gui| image:: https://tanimislam.github.io/howdy/_images/howdy_credentials_mainfigure.png
   :width: 100%
   :align: middle

.. |music_config_gui| image:: https://tanimislam.github.io/howdy/_images/howdymusic_mainfigure.png
   :width: 100%
   :align: middle

.. list-table::
   :widths: auto

   * - |main_config_gui|
     - |login_config_gui|
     - |credentials_config_gui|
     - |music_config_gui|
   * - `12 total settings <sec_main_config_gui_>`_
     - `4 login settings <sec_login_config_gui_>`_
     - `4 credential settings <sec_credentials_config_gui_>`_
     - `4 music settings <sec_music_config_gui_>`_

What Are Some Interesting Command Line Executables?
-----------------------------------------------------------------
You can try out `howdy_music_songs`_ to get individual songs or all the songs in an artist's studio album, or `howdy_music_album`_ to find all the studio albums an artist released. Here are three YouTube_ clips that show `howdy_music_songs`_ in action.

.. |howdy_music_songs_clip1| image:: https://tanimislam.github.io/howdy/_images/howdy_music_songs_download_by_song_and_artist.gif
   :width: 100%
   :align: middle

.. |howdy_music_songs_clip2| image:: https://tanimislam.github.io/howdy/_images/howdy_music_songs_download_by_artist_and_album_SHRINK.gif
   :width: 100%
   :align: middle

.. |howdy_music_songs_clip3| image:: https://tanimislam.github.io/howdy/_images/howdy_music_songs_download_by_sep_list_artist_songs.gif
   :width: 100%
   :align: middle

.. list-table::
   :widths: auto
   
   * - |howdy_music_songs_clip1|
     - |howdy_music_songs_clip2|
     - |howdy_music_songs_clip3|
   * - `Download artists & songs <yt_clip1_>`_
     - `Download artist & album <yt_clip2_>`_
     - `Download sep artists & songs <yt_clip3_>`_

.. top level links
.. _SDK: https://en.wikipedia.org/wiki/Software_development_kit
.. _Radarr: https://radarr.video
.. _Couchpotato: https://couchpota.to
.. _Sonarr: https://sonarr.tv
.. _Sickrage: https://www.sickrage.ca
.. _Lidarr: https://lidarr.audio
.. _Subliminal: https://subliminal.readthedocs.io/en/latest
.. _Tautulli: https://tautulli.com
.. _Jackett: https://github.com/Jackett/Jackett
.. _Sphinx: https://www.sphinx-doc.org/en/master

.. howdy icon
.. |howdy_icon| image:: https://tanimislam.github.io/howdy/_static/howdy_icon_VECTA.svg
   :width: 100
   :align: middle
       
.. links to YouTube clips
.. _yt_clip1: https://youtu.be/W5AYAFYI9QA
.. _yt_clip2: https://youtu.be/2IxzTvWN0K8
.. _yt_clip3: https://youtu.be/11rOnEDfMos

.. links to howdy sections
.. _sec_main_config_gui: https://tanimislam.github.io/howdy/howdy-config/howdy_config_gui_usage.html
.. _sec_login_config_gui: https://tanimislam.github.io/en/latest/howdy-config/howdy_config_gui_usage.html#login-services
.. _sec_credentials_config_gui: https://tanimislam.github.io/howdy/howdy-config/howdy_config_gui_usage.html#credentials-services
.. _sec_music_config_gui: https://tanimislam.github.io/howdy/howdy-config/howdy_config_gui_usage.html#music-services

.. these are other links
.. _unofficial_plex_api: https://github.com/Arcanemagus/plex-api/wiki
.. _Plex: https://plex.tv
.. _PlexAPI: https://python-plexapi.readthedocs.io/en/latest/introduction.html
.. _PyQt5: https://www.riverbankcomputing.com/static/Docs/PyQt5/index.html
.. _sshpass: https://linux.die.net/man/1/sshpass
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
.. _OAuth2: https://en.wikipedia.org/wiki/OAuth#OAuth_2.0
.. _ArgumentParser: https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser
.. _`Embed YouTube`: http://embedyoutube.org
.. _`howdy_music_songs`: https://tanimislam.github.io/howdy/howdy-music/cli_tools/howdy_music_cli.html#howdy-music-songs
.. _`howdy_music_album`: https://tanimislam.github.io/howdy/howdy-music/cli_tools/howdy_music_cli.html#howdy-music-album
.. _Youtube: https://www.youtube.com
.. _Howdy: https://howdy.readthedocs.io
