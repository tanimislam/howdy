.. toctree::
   :maxdepth: 2
   :caption: Contents:

========================
Plex Configuration
========================

This document contains all the needed information to get started on getting set up with all the **services** and **Plex server settings** you need to get up and running with all my Plex goodnesses. Here are the following **services** needed to get all the functionality here.

* Identifying movies using `the Movie Database <https://www.themoviedb.org/>`_.
* Identifying television shows and episodes using `the Televion Database <https://www.thetvdb.com/>`_.
* Uploading images for emails using the `Imgur image service <https://imgur.com/>`_.
* Populating music metadata using either the `Gracenote API <https://developer.gracenote.com/web-api>`_ or the `LastFM API <https://www.last.fm/api/>`_.
* A bevy of many Google services that do the following.
  1. Sending out emails to your Plex users, using the `GMail API <https://developers.google.com/gmail/api/>`_, and identifying them from your Google address book using the `Google Contacts API <https://developers.google.com/contacts/v3/>`_.
  2. Identifying songs on `YouTube <https://www.youtube.com>`_ using the `YouTube API <https://developers.google.com/youtube/v3/>`_.
  3. Access to Google spreadsheets using the `Google Sheets API <https://developers.google.com/sheets/api/>`_.
  4. Upload your music to your `Google Play Music <https://play.google.com/store/music?hl=en>`_ account using the `unofficial Google Music API <https://unofficial-google-music-api.readthedocs.io/en/latest/>`_.

The document is organized into the following sections.

* `Setting up the Movie Database API <moviedb>`_.
* `Setting up the the Television Database API <tvdb>`_.

.. _moviedb::
Setting Up the Movie Database API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Follow instructions on getting an access key for the Movie Database `here <https://developers.themoviedb.org/3/getting-started/introduction>`_. Click on the `API link <https://www.themoviedb.org/settings/api>`_.

.. _tvdb::
Setting up the the Television Database API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The television database API registration is more involved and (currently, as of 2 July 2019) not clearly documented. Here is how I got this to work.

1. Log in or register (if you don't have an account) onto the television database `login page <https://www.thetvdb.com/login>`_. Here is a screen shot.

.. image:: plex_config_figures/tmdb_step01_login.png
  :width 400
  :align left

2. Select the **API ACCESS** sub menu option in the right most menu option, which is your Television Database username, **<USERNAME> → API ACCESS**. Here is a screen shot.

.. image:: plex_config_figures/tmdb_step02_apiselect.png
  :width 400
  :align left
