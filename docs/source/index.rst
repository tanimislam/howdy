.. plexstuff documentation master file, created by
   sphinx-quickstart on Sun Jun 23 11:03:17 2019.
   You can adapt this file completely to your liking, but it should at least contain the root `toctree` directive.

###################################################################
Plexstuff - Yet Another Way to Manage Your Plex_ Server's Content
###################################################################

Introduction
------------

Plexstuff is a (hopefully) useful tool that I have developed to manage (and download) the movies, television shows, and music in which I am interested. I hope that it is, or becomes, a worthy member of the rich community of services used to manage one's media.

Here are a few of the best known high level media management services:

* `Radarr <https://radarr.video/>`_ or `Couchpotato <https://couchpota.to/>`_ to manage your movies (automatically download them, etc.).
* `Sonarr <https://sonarr.tv/>`_ or `Sickrage <https://www.sickrage.ca/>`_ to manage your television shows (automatically download them as they become available, for instance).
* `Lidarr <https://lidarr.audio/>`_ to manage your music.

Here are some of the best known lower APIs used to help one manage your Plex_ server.

* `Tautulli <https://tautulli.com/>`_ to monitor your Plex_ server.
* `Jackett <https://github.com/Jackett/Jackett>`_ is a relatively successful proxy server that consolidates the torrent search from a´ large number of public, private, and semi-private torrent trackers and services into a single search user interface and API. I discuss this in more detail in :numref:`The Jackett Server`.
* `PlexAPI <PlexAPI_>`_ are the unofficial bindings to the Plex API. They are based off the older `unofficial Plex API <unofficial_plex_api_>`_. I still use `the older lower-level REST API <unofficial_plex_api_>`_ because it seems to offer more freedom (such as finer grained multithreaded HTTP requests, and access to remote servers) than PlexAPI_.

To get started, I assume you have your own Plex server. In order to get started with Plex, start at the `Plex website <Plex_>`_ and put your media into it. Next, follow the :ref:`Installation` instructions. Join or identify the music, television, and movie based services described in :numref:`Plexstuff Services Configuration`, and server settings described in :numref:`Plexstuff Settings Configuration`. Use ``plex_config_gui.py`` to save your services and settings information, and then you will be good to go in using the ~25 or so command line and GUI tools to manage your Plex server.

Installation
------------

Currently, installation is straightforward. Just copy out ``plexstuff`` into a directory you own on a Linux machine. You will need to have `PyQt4 <https://www.riverbankcomputing.com/software/pyqt/download>`_ and `sshpass <https://linux.die.net/man/1/sshpass>`_ on your machine.

To automatically, get all the dependencies (and there are a lot of them!) installed onto your machine (specifically, your user account), just run a single CLI executable from the top level directory, such as ``get_tv_tor.py``, the following way.

.. code:: bash

  get_tv_tor.py -h

If you are missing any packages, and almost certainly you are if you are using this ``plexstuff`` in the beginning, you will get a command line warning dialog like this,

.. code:: bash

  YOU NEED TO INSTALL THESE PACKAGES: cfscrape.
  I WILL INSTALL THEM INTO YOUR USER DIRECTORY.
  DO YOU ACCEPT?
  MAKE OPTION:
  1: YES, INSTALL THESE PACKAGES.
  2: NO, DO NOT INSTALL THESE PACKAGES.

Choose ``1`` and the missing packages (in this case `cfscrape <https://github.com/Anorov/cloudflare-scrape>`_) will be installed.

Common Design Philosophies for Command Line and GUIs
-----------------------------------------------------

Since I am forced to use the tools I developed to manage my Plex server, my command line interfaces (CLIs) and GUIs share common features that I hope make these tools *discoverable* and more easily *debuggable*.

The CLIs are programmed with :py:class:`optparse's OptionParser( ) <optparse.OptionParser>` and have a comprehensive help that can accessed via ``<cli_tool> -h``.

The GUI tools all share common features. One can take a PNG screenshot of each widget and sub-widget with the ``Shift+Ctrl+P`` (or ``Shift+Command+P`` on Mac OS X computers) key combination. This helps to debug issues that may appear in the GUI, and helps to create useful documentation. I always try to put HELP screens into my GUIs, although this is still a very hard thing to do alone.

Table of Contents
-----------------

.. toctree::
  :maxdepth: 1
  :numbered:

  plex-config/plex_config
  plex-core/plex_core

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _unofficial_plex_api: https://github.com/Arcanemagus/plex-api/wiki
.. _Plex: https://plex.tv
.. _PlexAPI: https://python-plexapi.readthedocs.io/en/latest/introduction.html
