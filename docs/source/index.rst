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
* `Subliminal <https://subliminal.readthedocs.io/en/latest/>`_ to download movie and TV show subtitles.

Here are some of the best known lower APIs used to help one manage your Plex_ server.

* `Tautulli <https://tautulli.com>`_ to monitor your Plex_ server.
* `Jackett <https://github.com/Jackett/Jackett>`_ is a relatively successful proxy server that consolidates the torrent search from a´ large number of public, private, and semi-private torrent trackers and services into a single search user interface and API. I discuss this in more detail in :numref:`The Jackett Server`.
* `PlexAPI <PlexAPI_>`_ are the unofficial bindings to the Plex API. They are based off the older `unofficial Plex API <unofficial_plex_api_>`_. I still use `the older lower-level REST API <unofficial_plex_api_>`_ because it seems to offer more freedom (such as finer grained multithreaded HTTP requests, and access to remote servers) than PlexAPI_.

To get started, I assume you have your own Plex server. In order to get started with Plex, start at the `Plex website <Plex_>`_ and put your media into it. Next, follow the :ref:`Installation` instructions. Join or identify the music, television, and movie based services described in :numref:`Plexstuff Services Configuration`, and server settings described in :numref:`Plexstuff Settings Configuration`. Use ``plex_config_gui.py`` to save your services and settings information, and then you will be good to go in using the ~25 or so command line and GUI tools to manage your Plex server.

Prerequisites
-------------
You will need to have PyQt4_, sshpass_, and pandoc_ on your machine. `Pandoc <pandoc_>`_ is needed by Plexstuff tools that convert emails written in LaTeX_ into HTML. On Debian based systems (such as Ubuntu_. Mint_, or Debian_), you can install PyQt4_, sshpass_, and pandoc_ with the following command (as sudo_ or root).

.. code:: bash

  sudo apt install python3-pyqt4 sshpass pandoc

Equivalent commands to install PyQt4_ and sshpass_ exist on `Red Hat`_ based systems, such as Fedora_ or CentOS_.

In a common scenario, you may need to use Plexstuff on a Linux machine you do not administer or own. Typically PyQt4_ and sshpass_ are installed, but pandoc_ is a more niche tool that must be installed by hand into your home directory if it has not been installed by default. By my convention the executables and other resources (such as includes and libraries) will be installed under ``~/.local``. Sources of necessary tools will be decompressed and live in ``~/.local/src``. Here are the eight steps I used in order to get pandoc_ installed.

1. Ensure that ``~/.local/bin`` and ``~/.cabal/bin`` are in your PATH.

2. Download the ``Linux x86-64`` pre-built version of the `Haskell Stack build tool <stack_>`_ and decompress into ``~/.local/src``. Here is a link, `https://get.haskellstack.org/stable/linux-x86_64-static.tar.gz <https://get.haskellstack.org/stable/linux-x86_64-static.tar.gz>`_. Decompress with the following command,

  .. code:: bash

    tar stack-2.1.1-linux-x86_64-static.tar.gz && rm stack-2.1.1-linux-x86_64-static.tar.gz

  This will create a directory, ``~/.local/src/stack-2.1.1-linux-x86_64-static``.

3. cd into ``~/.local/src/stack-2.1.1-linux-x86_64-static`` and install a *bootstrapped* Glasgow Haskell Compiler (ghc_) for Linux with the following command,

  .. code:: bash

    ./stack ghc

  This will install ghc_ into ``~/.stack/programs/x86_64-linux/ghc-8.6.5/bin/ghc``. We need to install a bootstrapped Haskell compiler, because one needs (a version of) ghc_ in order to build ghc_ from source!

4. Download the latest version of the Glasgow Haskell Compiler, as of 8 July 2019, it is `ghc-8.6.5-src.tar.xz <https://downloads.haskell.org/~ghc/8.6.5/ghc-8.6.5-src.tar.xz>`_. Once it has downloaded into ``~/.local/src``, decompress and untar this way. Note that you need `xz <https://en.wikipedia.org/wiki/Xz>`_ to be installed on your machine.

  .. code:: bash

    xz -cd ghc-8.6.5-src.tar.xz | tar xvf -
    rm ghc-8.6.5-src.tar

  This will create the source directory, ``~/.local/src/ghc-8.6.5``.

5. cd into ``~/.local/src/ghc-8.6.5``. Configure, ``make``, and ``make install`` ghc_ with the following three commands in order.

  .. code:: bash

    ./configure --prefix=$HOME/.local --with-ghc=$HOME/.stack/programs/x86_64-linux/ghc-8.6.5/bin/ghc_
    make && make install

6. At this point, remove the stack_ source and distribution directories,

  .. code:: bash

    rm -rf ~/.local/src/stack-2.1.1-linux-x86_64-static
    rm -rf ~/.stack

7. Download and install cabal_, a command line tool to manage Haskell packages. First, download the cabal_ x86-64 binary, `cabal-install-2.4.1.0-x86_64-unknown-linux.tar.xz <https://downloads.haskell.org/~cabal/cabal-install-latest/cabal-install-2.4.1.0-x86_64-unknown-linux.tar.xz>`_, into ``~/.local/src``.

  .. code:: bash

    xz -cd cabal-install-2.4.1.0-x86_64-unknown-linux.tar.xz | tar xvf -
    rm cabal-install-2.4.1.0-x86_64-unknown-linux.tar.xz

  Second, move ``cabal`` into ``~/.local/bin``,

  .. code:: bash

    mv ~/.local/src/cabal ~/.local/bin
    rm -f ~/.local/src/cabal.sig

  Third, run ``cabal update`` to make cabal_ operational.

8. FINALLY,  install ``pandoc`` into ``~/.local/bin`` in these steps. First run,

  .. code:: bash

    cabal install pandoc

  This will install ``pandoc`` into ``~/.cabal/bin/pandoc``. Move ``pandoc`` from ``~/.cabal/bin/pandoc`` into ``~/.local/bin``.

  .. code:: bash

    mv ~/.cabal/bin/pandoc ~/.local/bin


Installation
------------

Currently, parts of the installation are straightforward. Just copy out ``plexstuff`` into a directory you own on a Linux machine. To automatically get all the Python dependencies (and there are a lot of them!) installed onto your machine (specifically, your user account), just run a single CLI executable from the top level directory, such as ``get_tv_tor.py``, the following way.

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

Common Design Philosophies and Features for Command Line and GUIs
----------------------------------------------------------------------------------------------------------

Since I am forced to use the tools I developed to manage my Plex server, my command line interfaces (CLIs) and GUIs share common features that I hope make these tools *discoverable* and more easily *debuggable*.

The CLIs are programmed with :py:class:`optparse's OptionParser( ) <optparse.OptionParser>` and have a comprehensive help that can accessed via ``<cli_tool> -h``, where ``<cli_tool>`` refers to the the specific Python CLI.

The GUI tools all share common features. One can take a PNG screenshot of each widget and sub-widget with the ``Shift+Ctrl+P`` (or ``Shift+Command+P`` on Mac OS X computers) key combination. This helps to debug issues that may appear in the GUI, and helps to create useful documentation. I always try to put help screens into my GUIs, although not all the GUIs have working help dialogs.

Many of the GUIs and CLIs can be run with  a ``--noverify`` option to access SSL protected URLs and services without verification, which is needed when running in more restricted environments.

Table of Contents
-----------------

.. toctree::
  :maxdepth: 2
  :numbered:

  plex-config/plex_config
  plex-core/plex_core
  plex-tvdb/plex_tvdb
  plex-tmdb/plex_tmdb
  plex-music/plex_music
  plex-email/plex_email

TODO
----

Here are some things I would like to finish.

* Fill out documentation for all the CLIs and GUIs.
* Fill out documentation for the lower level APIs.
* Fill out help dialogs for the CLIs and GUIs.
* Complete the testing suite.
* Streamline the OAuth2 authentication process, and provide more logical authorization and verification work flows.
* Transition GUIs to use PyQt5_, with the eventual use of fbs_.

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
