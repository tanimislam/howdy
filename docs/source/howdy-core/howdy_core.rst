================================================
Howdy Core Functionality
================================================
These command line executables, graphical user interfaces, and APIs form the core functionality in Howdy. The API lives in ``howdy.core``. These tools form the infrastructural basis of higher level tools to manage :ref:`television shows <Howdy TV Functionality>`, :ref:`movies <Howdy Movie Functionality>`, :ref:`music <Howdy Music Functionality>`, and :ref:`email <Howdy Email Functionality>`.

This documentation is organized into sections on :ref:`command line tools <Howdy Core Command Line Utilities>`, :ref:`GUI tools <Howdy Core GUIs>`, :ref:`low level API <Howdy Core API>`, and finally the :ref:`TODO <Howdy Core TODO>`.

.. toctree::
   :maxdepth: 2
   :caption: Table of Contents

   cli_tools/howdy_core_cli
   gui_tools/howdy_core_gui
   howdy_core_api

Howdy Core TODO
------------------
* Enhance :ref:`howdy_create_texts` to allow for the more versatile reStructuredText_ to be converted into HTML documents. |cbox|

* Implement a PyQt5_ GUI to manipulate torrents on the remote Deluge_ server -- something much reduced from the full functionality of the `Deluge WebUI`_.

.. |cbox| unicode:: U+2611 .. BALLOT BOX WITH CHECK
  
.. _PyQt5: https://www.riverbankcomputing.com/static/Docs/PyQt5/index.html
.. _reStructuredText: https://en.wikipedia.org/wiki/ReStructuredText
.. _Deluge: https://en.wikipedia.org/wiki/Deluge_(software)
.. _`Deluge WebUI`: https://wiki.archlinux.org/index.php/deluge#Web

