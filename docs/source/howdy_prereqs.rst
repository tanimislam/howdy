================================================
Prerequisites and Overall Design Philosophy
================================================
To get started, I assume you have your own Plex_ server. In order to get started with Plex, start at the `Plex website <Plex_>`_ and put your media into it. Next, follow the :ref:`Installation` instructions. Join or identify the music, television, and movie based services described in :numref:`Howdy Services Configuration`, and server settings described in :numref:`Howdy Settings Configuration`. Use ``howdy_config_gui`` to save your services and settings information, and then you will be good to go in using the ~25 or so command line and graphical user interface (GUI) tools to manage your Plex server.

Prerequisites
-------------
You will need to have PyQt5_, PyQtWebEngine_, and sshpass_. On Debian based systems (such as Ubuntu_. Mint_, or Debian_), you can install PyQt5_ and sshpass_ with the following command (as sudo_ or root).

.. code-block:: console

   sudo apt install python3-pyqt5 python3-pyqt5.qtwebengine sshpass

Equivalent commands to install PyQt5_ and sshpass_ exist on `Red Hat`_ based systems, such as Fedora_ or CentOS_. *An even easier way to install the latest version of PyQt5 on your user account is with this command*,

.. code-block:: console

   pip3 install --user pyqt5

.. note::

   The installation of PyQtWebEngine_ is relatively difficult. On my Ubuntu 20.04 machine, I had to run ``sudo apt install python3-pyqt5.qtwebengine`` to get this to work. More portable and universal commands, such as ``pip3 install --user pyqtwebengine``, will *install* PyQtWebEngine_, but imports *may not work*.

Installation
------------
Since this package has been setup-ified, installation is very easy. Just ``cd`` into the ``howdy`` directory, and run,

.. code-block:: console

   python3 setup.py install --user

Or you can run pip from that directory. This installation process is especially suited for active development; you make changes to your code, and interactive tests of the API or of the executables are *immediately* reflected.

.. code-block:: console

   pip3 install --user -e .

Or, if you feel ridiculously brave, you can install from the GitHub_ URL.

.. code-block:: console

   pip3 install --user git+https://github.com/tanimislam/howdy.git#egg=howdy


Common Design Philosophies and Features for Command Line and GUIs
----------------------------------------------------------------------------------------------------------
Since I am forced to use the tools I developed to manage my Plex server, my command line interfaces (CLIs) and GUIs share common features that I hope make these tools *discoverable* and more easily *debuggable*.

The CLIs are programmed with :py:class:`argparse's ArgumentParser( ) <argparse.ArgumentParser>` and have a comprehensive help that can be accessed via ``<cli_tool> -h``, where ``<cli_tool>`` refers to the the specific Python CLI.

The GUI tools all share common features. One can take a PNG screenshot of each widget and sub-widget with the ``Shift+Ctrl+P`` (or ``Shift+Command+P`` on Mac OS X computers) key combination. This helps to debug issues that may appear in the GUI, and helps to create useful documentation. I always try to put help screens into my GUIs, although not all the GUIs have working help dialogs.

Many of the GUIs and CLIs can be run with  a ``--noverify`` option to access SSL protected URLs and services without verification, which is needed when running in more restricted environments.

In fact, here is a summary of the 25 CLI's and GUI's currently in Howdy_. The |cbox| after the name (or name and icon) means that I have completed the documentation for that CLI or GUI.

.. |cbox| unicode:: U+2611 .. BALLOT BOX WITH CHECK

.. _table_functionality_list:

.. list-table::
   :widths: auto

   * - Functionality
     - CLI
     - GUI
	    
   * - ``core``
     - :ref:`howdy_core_cli <howdy_core_cli_label>` |cbox|
     - |howdy_config_gui_icon| :ref:`howdy_config_gui <howdy_config_gui_label>` |cbox|
   * -
     - :ref:`howdy_deluge_console <howdy_deluge_console_label>` |cbox|
     - |howdy_core_gui_icon| :ref:`howdy_core_gui <howdy_core_gui_label>` |cbox|
   * -
     - :ref:`howdy_resynclibs <howdy_resynclibs_label>` |cbox|
     - |howdy_create_texts_icon| :ref:`howdy_create_texts <howdy_create_texts_label>` |cbox|
   * -
     - :ref:`howdy_store_credentials <howdy_store_credentials_label>` |cbox|
     -
   * -
     - :ref:`rsync_subproc <rsync_subproc_label>` |cbox|
     -

   * - ``tv``
     - :ref:`get_tv_batch <get_tv_batch_label>` |cbox|
     - |howdy_tv_gui_icon| :ref:`howdy_tv_gui <howdy_tv_gui_label>`
   * -
     - :ref:`get_tv_tor <get_tv_tor_label>` |cbox|
     -
   * -
     - :ref:`howdy_tv_epinfo <howdy_tv_epinfo_label>` |cbox|
     -
   * -
     - :ref:`howdy_tv_epname <howdy_tv_epname_label>` |cbox|
     -
   * -
     - :ref:`howdy_tv_futureshows <howdy_tv_futureshows_label>` |cbox|
     -
   * -
     - :ref:`howdy_tv_plots <howdy_tv_plots_label>` |cbox|
     -
   * -
     - :ref:`howdy_tv_excludes <howdy_tv_excludes_label>` |cbox|
     -
   
   * - ``movie``
     - :ref:`get_mov_tor <get_mov_tor_label>` |cbox|
     - |howdy_movie_totgui_icon| :ref:`howdy_movie_totgui <howdy_movie_totgui_label>`
   
   * - ``music``
     - :ref:`howdy_music_album <howdy_music_album_label>` |cbox|
     -
   * -
     - :ref:`howdy_music_metafill <howdy_music_metafill_label>` |cbox|
     -
   * -
     - :ref:`howdy_music_songs <howdy_music_songs_label>` |cbox|
     -
   * -
     - :ref:`upload_to_gmusic <upload_to_gmusic_label>` |cbox|
     -
   * - ``email``
     - :ref:`howdy_email_notif <howdy_email_notif_label>` |cbox|
     - |howdy_email_gui_icon| :ref:`howdy_email_gui <howdy_email_gui_label>` |cbox| 


.. these are the links
.. _GitHub: https://github.com
.. _unofficial_plex_api: https://github.com/Arcanemagus/plex-api/wiki
.. _Plex: https://plex.tv
.. _PlexAPI: https://python-plexapi.readthedocs.io/en/latest/introduction.html
.. _PyQt5: https://www.riverbankcomputing.com/static/Docs/PyQt5/index.html
.. _PyQtWebEngine: https://www.riverbankcomputing.com/software/pyqtwebengine
.. _sshpass: https://linux.die.net/man/1/sshpass
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
.. _Howdy: https://howdy.readthedocs.io

.. |howdy_config_gui_icon| image:: howdy-config/howdy-config-gui-figures/howdy_config_gui_SQUARE.png
   :width: 50
   :align: middle

.. |howdy_core_gui_icon| image:: howdy-core/gui_tools/gui-tools-figures/howdy_core_gui_SQUARE.png
   :width: 50
   :align: middle

.. |howdy_create_texts_icon| image:: howdy-core/gui_tools/gui-tools-figures/howdy_create_texts_SQUARE.png
   :width: 50
   :align: middle

.. |howdy_tv_gui_icon| image:: howdy-tv/howdy-tv-gui-figs/howdy_tv_gui_SQUARE.png
   :width: 50
   :align: middle

.. |howdy_movie_totgui_icon| image:: howdy-movie/howdy-movie-totgui-figs/howdy_movie_gui_SQUARE.png
   :width: 50
   :align: middle
	   
.. |howdy_email_gui_icon| image:: howdy-email/howdy-email-gui-figs/howdy_email_gui_SQUARE.png
   :width: 50
   :align: middle
