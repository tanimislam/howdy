================================================
Prerequisites and Overall Design Philosophy
================================================

To get started, I assume you have your own Plex server. In order to get started with Plex, start at the `Plex website <Plex_>`_ and put your media into it. Next, follow the :ref:`Installation` instructions. Join or identify the music, television, and movie based services described in :numref:`Plexstuff Services Configuration`, and server settings described in :numref:`Plexstuff Settings Configuration`. Use ``plex_config_gui`` to save your services and settings information, and then you will be good to go in using the ~25 or so command line and GUI tools to manage your Plex server.

Prerequisites
-------------
You will need to have PyQt5_, PyQtWebEngine_, sshpass_, and pandoc_ on your machine. `Pandoc <pandoc_>`_ is needed by Plexstuff tools that convert emails written in LaTeX_ into HTML. On Debian based systems (such as Ubuntu_. Mint_, or Debian_), you can install PyQt5_, sshpass_, and pandoc_ with the following command (as sudo_ or root).

.. code-block:: console

   sudo apt install python3-pyqt5 python3-pyqt5.qtwebengine sshpass pandoc

Equivalent commands to install PyQt5_ and sshpass_ exist on `Red Hat`_ based systems, such as Fedora_ or CentOS_. *An even easier way to install the latest version of PyQt5 on your user account is with this command*,

.. code-block:: console

   pip3 install --user pyqt5

.. note::

   The installation of PyQtWebEngine_ is relatively difficult. On my Ubuntu 20.04 machine, I had to run ``sudo apt install python3-pyqt5.qtwebengine`` to get this to work. More portable and universal commands, such as ``pip3 install --user pyqtwebengine``, will *install* PyQtWebEngine_, but imports *may not work*.
   
In a common scenario, you may need to use Plexstuff on a Linux machine you do not administer or own. Typically PyQt5_ and sshpass_ are installed, but pandoc_ is a more niche tool that must be installed by hand into your home directory if it has not been installed by default. By my convention the executables and other resources (such as includes and libraries) will be installed under ``~/.local``. Sources of necessary tools will be decompressed and live in ``~/.local/src``. Here are the eight steps I used in order to get pandoc_ installed.

1. Ensure that ``~/.local/bin`` and ``~/.cabal/bin`` are in your PATH.

2. Download the ``Linux x86-64`` pre-built version of the `Haskell Stack build tool <stack_>`_ and decompress into ``~/.local/src``. Here is a link, `https://get.haskellstack.org/stable/linux-x86_64-static.tar.gz <https://get.haskellstack.org/stable/linux-x86_64-static.tar.gz>`_. Decompress with the following command,

  .. code-block:: console

    tar stack-2.1.1-linux-x86_64-static.tar.gz && rm stack-2.1.1-linux-x86_64-static.tar.gz

  This will create a directory, ``~/.local/src/stack-2.1.1-linux-x86_64-static``.

3. cd into ``~/.local/src/stack-2.1.1-linux-x86_64-static`` and install a *bootstrapped* Glasgow Haskell Compiler (ghc_) for Linux with the following command,

  .. code-block:: console

    ./stack ghc

  This will install ghc_ into ``~/.stack/programs/x86_64-linux/ghc-8.6.5/bin/ghc``. We need to install a bootstrapped Haskell compiler, because one needs (a version of) ghc_ in order to build ghc_ from source!

4. Download the latest version of the Glasgow Haskell Compiler, as of 8 July 2019, it is `ghc-8.6.5-src.tar.xz <https://downloads.haskell.org/~ghc/8.6.5/ghc-8.6.5-src.tar.xz>`_. Once it has downloaded into ``~/.local/src``, decompress and untar this way. Note that you need `xz <https://en.wikipedia.org/wiki/Xz>`_ to be installed on your machine.

  .. code-block:: console

    xz -cd ghc-8.6.5-src.tar.xz | tar xvf -
    rm ghc-8.6.5-src.tar

  This will create the source directory, ``~/.local/src/ghc-8.6.5``.

5. cd into ``~/.local/src/ghc-8.6.5``. Configure, ``make``, and ``make install`` ghc_ with the following three commands in order.

  .. code-block:: console

    ./configure --prefix=$HOME/.local --with-ghc=$HOME/.stack/programs/x86_64-linux/ghc-8.6.5/bin/ghc_
    make && make install

6. At this point, remove the stack_ source and distribution directories,

  .. code-block:: console

    rm -rf ~/.local/src/stack-2.1.1-linux-x86_64-static
    rm -rf ~/.stack

7. Download and install cabal_, a command line tool to manage Haskell packages. First, download the cabal_ x86-64 binary, `cabal-install-2.4.1.0-x86_64-unknown-linux.tar.xz <https://downloads.haskell.org/~cabal/cabal-install-latest/cabal-install-2.4.1.0-x86_64-unknown-linux.tar.xz>`_, into ``~/.local/src``.

  .. code-block:: console

    xz -cd cabal-install-2.4.1.0-x86_64-unknown-linux.tar.xz | tar xvf -
    rm cabal-install-2.4.1.0-x86_64-unknown-linux.tar.xz

  Second, move ``cabal`` into ``~/.local/bin``,

  .. code-block:: console

    mv ~/.local/src/cabal ~/.local/bin
    rm -f ~/.local/src/cabal.sig

  Third, run ``cabal update`` to make cabal_ operational.

8. FINALLY,  install ``pandoc`` into ``~/.local/bin`` in these steps. First run,

  .. code-block:: console

    cabal install pandoc

  This will install ``pandoc`` into ``~/.cabal/bin/pandoc``. Move ``pandoc`` from ``~/.cabal/bin/pandoc`` into ``~/.local/bin``.

  .. code-block:: console

    mv ~/.cabal/bin/pandoc ~/.local/bin


Installation
------------

Since this package has been setup-ified, installation is very easy. Just ``cd`` into the ``plexstuff`` directory, and run,

.. code-block:: console

   python3 setup.py install --user

Or you can run pip from that directory. This installation process is especially suited for active development; you make changes to your code, and interactive tests of the API or of the executables are *immediately* reflected.

.. code-block:: console

   pip3 install --user -e .

Or, if you feel ridiculously brave, you can install from the GitHub_ URL.

.. code-block:: console

   pip3 install --user git+https://github.com/tanimislam/plexstuff.git#egg=plexstuff


Common Design Philosophies and Features for Command Line and GUIs
----------------------------------------------------------------------------------------------------------

Since I am forced to use the tools I developed to manage my Plex server, my command line interfaces (CLIs) and GUIs share common features that I hope make these tools *discoverable* and more easily *debuggable*.

The CLIs are programmed with :py:class:`argparse's ArgumentParser( ) <argparse.ArgumentParser>` and have a comprehensive help that can be accessed via ``<cli_tool> -h``, where ``<cli_tool>`` refers to the the specific Python CLI.

The GUI tools all share common features. One can take a PNG screenshot of each widget and sub-widget with the ``Shift+Ctrl+P`` (or ``Shift+Command+P`` on Mac OS X computers) key combination. This helps to debug issues that may appear in the GUI, and helps to create useful documentation. I always try to put help screens into my GUIs, although not all the GUIs have working help dialogs.

Many of the GUIs and CLIs can be run with  a ``--noverify`` option to access SSL protected URLs and services without verification, which is needed when running in more restricted environments.

In fact, here is a summary of the 23 CLI's and GUI's currently in Plexstuff_.

.. |cbox| unicode:: U+2611 .. BALLOT BOX WITH CHECK

===============  =====================================================================  =============================================================
Functionality    CLI                                                                    GUI
===============  =====================================================================  =============================================================
``plexcore``     - :ref:`plex_core_cli <plex_core_cli_label>` |cbox|                    - :ref:`plex_config_gui <plex_config_gui_label>` |cbox|
                 - :ref:`plex_deluge_console <plex_deluge_console_label>` |cbox|        - :ref:`plex_core_gui <plex_core_gui_label>`
                 - :ref:`plex_resynclibs <plex_resynclibs_label>` |cbox|                - :ref:`plex_create_texts <plex_create_texts_label>`
                 - :ref:`plex_store_credentials <plex_store_credentials_label>` |cbox|
                 - :ref:`rsync_subproc <rsync_subproc_label>` |cbox|
``plextvdb``     - :ref:`get_plextvdb_batch <get_plextvdb_batch_label>` |cbox|          - :ref:`plex_tvdb_gui <plex_tvdb_gui_label>`
                 - :ref:`get_tv_tor <get_tv_tor_label>` |cbox|
                 - :ref:`plex_tvdb_epinfo <plex_tvdb_epinfo_label>` |cbox|
                 - :ref:`plex_tvdb_epname <plex_tvdb_epname_label>` |cbox|
                 - :ref:`plex_tvdb_futureshows <plex_tvdb_futureshows_label>` |cbox|
                 - :ref:`plex_tvdb_plots <plex_tvdb_plots_label>` |cbox|
		 - :ref:`plex_tvdb_excludes <plex_tvdb_excludes_label>` |cbox|
``plextmdb``     - :ref:`get_mov_tor <get_mov_tor_label>` |cbox|                        - :ref:`plex_tmdb_totgui <plex_tmdb_totgui_label>`
``plexmusic``    - :ref:`plex_music_album <plex_music_album_label>` |cbox|
                 - :ref:`plex_music_metafill <plex_music_metafill_label>` |cbox|
                 - :ref:`plex_music_songs <plex_music_songs_label>` |cbox|
                 - :ref:`upload_to_gmusic <upload_to_gmusic_label>` |cbox|
``plexemail``    - :ref:`plex_email_notif <plex_email_notif_label>` |cbox|              - :ref:`plex_email_gui <plex_email_gui_label>`
===============  =====================================================================  =============================================================

.. these are the links
.. _GitHub: https://github.com
.. _unofficial_plex_api: https://github.com/Arcanemagus/plex-api/wiki
.. _Plex: https://plex.tv
.. _PlexAPI: https://python-plexapi.readthedocs.io/en/latest/introduction.html
.. _PyQt5: https://www.riverbankcomputing.com/static/Docs/PyQt5/index.html
.. _PyQtWebEngine: https://www.riverbankcomputing.com/software/pyqtwebengine
.. _sshpass: https://linux.die.net/man/1/sshpass
.. _pandoc: https://pandoc.org
.. _sudo: https://en.wikipedia.org/wiki/Sudo
.. _LaTeX: https://www.latex-project.org
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
