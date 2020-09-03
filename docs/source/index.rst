.. include:: ../../README.rst

Table of Contents
-----------------

.. toctree::
  :maxdepth: 2
  :numbered:

  howdy_prereqs
  howdy-config/howdy_config
  howdy_api
  howdy-core/howdy_core
  howdy-tv/howdy_tv
  howdy-movie/howdy_movie
  howdy-music/howdy_music
  howdy-email/howdy_email
  genindex

TODO
-------
Here are some things I would like to finish.

* Fill out documentation for all the CLIs (|cbox|) and GUIs (|cbox| *except for* :ref:`howdy_tv_gui_label` and :ref:`howdy_movie_totgui_label`).
* Fill out documentation for the lower level APIs (|cbox|) and the GUI APIs.
* Setup-ify this repository as a ``howdy`` Python module (|cbox|).
* Fill out help dialogs for the GUIs.
* Complete the testing suite.
* Streamline the OAuth2_ authentication process, and provide more logical authorization and verification work flows.
* Transition GUIs to use PyQt5_ (|cbox|), with the eventual use of fbs_.

.. |cbox| unicode:: U+2611 .. BALLOT BOX WITH CHECK

..
   Followed instructions from https://stackoverflow.com/questions/36235578/how-can-i-include-the-genindex-in-a-sphinx-toc to create a numbered INDEX section that contains an index of all called methods.
