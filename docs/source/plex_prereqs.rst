================================================
Prerequisites and Overall Design Philosophy
================================================

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

The CLIs are programmed with :py:class:`optparse's OptionParser( ) <optparse.OptionParser>` and have a comprehensive help that can be accessed via ``<cli_tool> -h``, where ``<cli_tool>`` refers to the the specific Python CLI.

The GUI tools all share common features. One can take a PNG screenshot of each widget and sub-widget with the ``Shift+Ctrl+P`` (or ``Shift+Command+P`` on Mac OS X computers) key combination. This helps to debug issues that may appear in the GUI, and helps to create useful documentation. I always try to put help screens into my GUIs, although not all the GUIs have working help dialogs.

Many of the GUIs and CLIs can be run with  a ``--noverify`` option to access SSL protected URLs and services without verification, which is needed when running in more restricted environments.

In fact, here is a summary of the 23 CLI's and GUI's currently in Plexstuff_.

.. |cbox| unicode:: U+2611 .. BALLOT BOX WITH CHECK

===============  ===========================================================================  =============================================================
Functionality    CLI                                                                          GUI
===============  ===========================================================================  =============================================================
``plexcore``     - :ref:`plex_core_cli.py <plex_core_cli.py_label>` |cbox|                    - :ref:`plex_config_gui.py <plex_config_gui.py_label>` |cbox|
                 - :ref:`plex_deluge_console.py <plex_deluge_console.py_label>` |cbox|        - :ref:`plex_core_gui.py <plex_core_gui.py_label>`
                 - :ref:`plex_resynclibs.py <plex_resynclibs.py_label>` |cbox|                - :ref:`plex_create_texts.py <plex_create_texts.py_label>`
                 - :ref:`plex_store_credentials.py <plex_store_credentials.py_label>` |cbox|
                 - :ref:`rsync_subproc.py <rsync_subproc.py_label>` |cbox|
``plextvdb``     - :ref:`get_plextvdb_batch.py <get_plextvdb_batch.py_label>` |cbox|          - :ref:`plex_tvdb_totgui.py <plex_tvdb_totgui.py_label>`
                 - :ref:`get_tv_tor.py <get_tv_tor.py_label>` |cbox|
                 - :ref:`plex_tvdb_epinfo.py <plex_tvdb_epinfo.py_label>` |cbox|
                 - :ref:`plex_tvdb_epname.py <plex_tvdb_epname.py_label>` |cbox|
                 - :ref:`plex_tvdb_futureshows.py <plex_tvdb_futureshows.py_label>` |cbox|
                 - :ref:`plex_tvdb_plots.py <plex_tvdb_plots.py_label>` |cbox|
``plextmdb``     - :ref:`get_mov_tor.py <get_mov_tor.py_label>` |cbox|                        - :ref:`plex_tmdb_totgui.py <plex_tmdb_totgui.py_label>`
``plexmusic``    - :ref:`plex_music_album.py <plex_music_album.py_label>`
                 - :ref:`plex_music_metafill.py <plex_music_metafill.py_label>`
                 - :ref:`plex_music_songs.py <plex_music_songs.py_label>`
                 - :ref:`upload_to_gmusic.py <upload_to_gmusic.py_label>`
``plexemail``    - :ref:`plex_email_notif.py <plex_email_notif.py_label>`                     - :ref:`plex_email_gui.py <plex_email_gui.py_label>`
===============  ===========================================================================  =============================================================

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
