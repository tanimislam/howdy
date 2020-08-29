================================================
Howdy Music Functionality
================================================
These command line executables, graphical user interfaces, and APIs are used to download and manage your music (even if the music has been spread between different main directories). This document is organized into sections on :ref:`command line tools <Music Command Line Utilities>`, the :ref:`lower level API <Howdy Music API>`, and finally the :ref:`TODO <Howdy Music TODO>`.

.. toctree::
   :maxdepth: 2
   :caption: Table of Contents

   cli_tools/howdy_music_cli
   howdy_music_api

Howdy Music TODO
-----------------

* Create a comprehensive GUI for the Plex_ music library similar to what I have made for the TV library (:ref:`plex_tvdb_gui`) and movie library (:ref:`plex_tmdb_totgui`).

* Fix the manner in which songs can be emailed to the recipient. Currently :ref:`howdy_music_songs` emails a collection of downloaded songs with the ``--email`` flag. I am turning off this functionality until such time as I can develop a way to do this for :ref:`howdy_music_songs` and :ref:`howdy_music_album`. There is a blog post, `Getting plex_music_songs to upload multiple songs <https://tanimislamblog.wordpress.com/2018/12/20/getting-plex_music_songs-to-upload-multiple-songs>`_, that describes this older and currently untested functionality.

* Design a better and more natural way to incorporate emailing song functionality, because emails require the following,

  * a custom setup of an SMTP relay on the Plex_ server, which I describe in this blog post, `Sendmail Relay Setup and Implementation <https://tanimislamblog.wordpress.com/2018/11/19/sendmail-relay-setup-and-implementation>`_.

  * The sender is currently the owner of the Plex_ server. Perhaps make this more transparent?

.. _Plex: https://plex.tv
.. _Tautulli: https://tautulli.com
