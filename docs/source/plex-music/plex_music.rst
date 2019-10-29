================================================
Plex Music Functionality
================================================

These command line executables, graphical user interfaces, and APIs are used to download and manage your music (even if the music has been spread between different main directories). This document is organized into sections on :ref:`command line tools <Music Command Line Utilities>` and the :ref:`lower level API <Plex Music API>`.

.. toctree::
   :maxdepth: 2
   :caption: Table of Contents

   cli_tools/plex_music_cli
   plex_music_api

Plex Music TODO
-----------------

* Create a comprehensive GUI for the Plex_ music library similar to what I have made for the TV library (:ref:`plex_tvdb_totgui.py`) and movie library (:ref:`plex_tmdb_totgui.py`).

* Fix the manner in which songs can be emailed to the recipient. Currently :ref:`plex_music_songs.py` emails a collection of downloaded songs with the ``--email`` flag. I am turning off this functionality until such time as I can develop a way to do this for :ref:`plex_music_songs.py` and :ref:`plex_music_album.py`. There is a blog post, `Getting plex_music_songs.py to upload multiple songs <https://tanimislamblog.wordpress.com/2018/12/20/getting-plex_music_songs-py-to-upload-multiple-songs>`_, that describes this older and currently untested functionality.

* Design a better and more natural way to incorporate emailing song functionality, because emails require the following,

  * a custom setup of an SMTP relay on the Plex_ server, which I describe in this blog post, `Sendmail Relay Setup and Implementation <https://tanimislamblog.wordpress.com/2018/11/19/sendmail-relay-setup-and-implementation>`_.

  * The sender is currently the owner of the Plex_ server. Perhaps make this more transparent?

.. _Plex: https://plex.tv
.. _Tautulli: https://tautulli.com
