================================================
Plex Core Functionality
================================================

These command line executables, graphical user interfaces, and APIs form the core functionality in Plexstuff. The API lives in ``plexstuff.plexcore``. These tools form the infrastructural basis of higher level tools to manage :ref:`television shows <Plex TVDB Functionality>`, :ref:`movies <Plex TMDB Functionality>`, :ref:`music <Plex Music Functionality>`, and :ref:`email <Plex Email Functionality>`.

This documentation is organized into sections on :ref:`command line tools <Core Command Line Utilities>`, :ref:`GUI tools <Core GUIs>`, and finally on the :ref:`low level API <Core API>`.

.. toctree::
   :maxdepth: 2
   :caption: Table of Contents

   cli_tools/plex_core_cli
   gui_tools/plex_core_gui
   plex_core_api

Plex Core TODO
------------------

* Enhance :ref:`plex_create_texts.py` to allow for the more versatile reStructuredText_ to be converted into HTML documents.

* Implement a PyQt4_ GUI to manipulate torrents on the remote Deluge_ server -- something much reduced from the full functionality of the `Deluge WebUI`_.

.. _PyQt4: https://www.riverbankcomputing.com/static/Docs/PyQt4/index.html
.. _reStructuredText: https://en.wikipedia.org/wiki/ReStructuredText
.. _Deluge: https://en.wikipedia.org/wiki/Deluge_(software)
.. _`Deluge WebUI`: https://wiki.archlinux.org/index.php/deluge#Web
