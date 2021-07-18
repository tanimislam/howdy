================================================
Howdy Services Configuration
================================================
This document contains all the needed information to get started on getting set up with all the **services** you need to get up and running with Howdy. Here are the following **services** needed to get all the functionality here.

* Identifying movies using `the Movie Database <TMDB_>`_.
* Identifying television shows and episodes using `the Television Database <TVDB_>`_.
* Uploading images for emails using the `Imgur image service <Imgur_>`_.
* Populating music metadata using either the `Gracenote API`_ or the `LastFM API`_.
* Using the `Jackett proxy server`_ to consolidate torrent searches among 20-30 public torrent trackers (such as Torrentz2_, RARBG_, `Kickass Torrents`_, and `The Pirate Bay`_) through a single search API, and service without CAPTCHAs_ or other usability restrictions.
* A bevy of Google services to do the following.

  1. Sending out emails to your Plex users, using the `GMail API`_, and identifying them from your Google address book using the `Google Contacts API`_.
  2. Identifying songs on YouTube_ using the `YouTube API`_.
  3. Access to Google spreadsheets using the `Google Sheets API`_.
  4. Upload your music to your `Google Play Music`_ account using the `unofficial Google Music API <unofficial_google_music_api_>`_.

The document is organized into the following sections.

* :ref:`The Movie Database (TMDB_) API`.
* :ref:`The Television Database (TVDB_) API`.
* :ref:`The Imgur API`.
* :ref:`The Gracenote and LastFM APIs`.
* :ref:`The Jackett Server`.
* :ref:`Summary of Setting Up Google Credentials`.

.. _the_movie_database_api:
  
The Movie Database (TMDB_) API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Instructions on getting an access key for the `TMDB API`_ start with the `TMDB API link`_.

.. _the_television_database_api:

The Television Database (TVDB_) API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The TVDB API registration is more involved and (currently, as of 2 July 2019) not clearly documented. Here is how I got this to work.

1. Log in or register (if you don't have an account) onto the television database `login page <tvdb_login_page_>`_, as shown in :numref:`tvdb_step01_login`.

.. _tvdb_step01_login:

.. figure:: howdy-config-services-figures/tvdb_step01_login.png
  :width: 100%
  :align: left

  `The Movie Database <TMDB_>`_ login page.
	  
2. Select the **API ACCESS** sub menu option in the right most menu option, which is your TVDB_ username, **<USERNAME> → API ACCESS**, as shown in :numref:`tvdb_step02_apiselect`.

.. _tvdb_step02_apiselect:

.. figure:: howdy-config-services-figures/tvdb_step02_apiselect.png
  :width: 100%
  :align: left

  How to get TVDB_ API access.

3. This will send you to the API keys web page for your account. On the top, you will see two labels showing your **username**, and an **unique ID** that the TVDB assigns to you. A hopefully illuminating screen shot is shown in :numref:`tvdb_step03_apikeys_generated`.

.. _tvdb_step03_apikeys_generated:

.. figure:: howdy-config-services-figures/tvdb_step03_apikeys_generated.png
   :width: 100%
   :align: left

   In the middle section is a table showing the API keys you have created, if any. Each row is a project you have created that the TVDB uses to grant you API access. Each project has an *API key*, the *project name*, and *project website*.

4. Generate an API key by defining a *project name*, *project website*, and then click on the *Generate API key* button, as shown in :numref:`tvdb_step04_apikeys_generate`.

.. _tvdb_step04_apikeys_generate:

.. figure:: howdy-config-services-figures/tvdb_step04_apikeys_generate.png
   :width: 100%
   :align: left

   Make sure to record the TVDB_ *project name*, *API key*, and *unique ID*.

The final information one programmatically sends to the TVDB service, through REST commands, is represented by the following JSON data.

.. code-block:: python

   {
     "apikey":  "XXXXXXX",
     "username": "YYYYYY",
     "userkey":  "ZZZZZZ"
    }

The Imgur API
^^^^^^^^^^^^^^^
Incomplete information on setting up Imgur_ API access can be found on `this website`_. High level instructions to generate valid Imgur client credentials are described in :numref:`generate_imgur_credentials_using_howdy`. 

.. _generate_imgur_credentials_using_howdy:

Generate Imgur Credentials Using ``Howdy``
------------------------------------------------
Here are the steps used to get working Imgur API access using the :ref:`howdy_config_gui <howdy_config_gui_label>`. First register for an `Imgur account`_, if you have not already done so.

1. Once you have an account, `register an Imgur application`_. Specify an application name, choose the "OAuth2 authorization without a callback URL" option, provide an email address, and provide a basic description of the application. Here is a screen shot.

.. _imgur_step01_registerapp:

.. figure:: howdy-config-services-figures/imgur_step01_registerapp.png
   :width: 100%
   :align: center

2. Now go to your `Imgur application's webpage`_ and click on the *generate new secret* to generate an application Oauth2 secret ID. Here is a screen shot.

.. _imgur_step02_getclientsecret:

.. figure:: howdy-config-services-figures/imgur_step02_getclientsecret.png
   :width: 100%
   :align: left

   Generate the secret on the Imgur_\ 's application web page.

3. Then record the client ID and client secret, which will be used in ``howdy_config_gui``. Here is a screen shot.

.. _imgur_step03_clientsecret:
.. figure:: howdy-config-services-figures/imgur_step03_clientsecret.png
   :width: 100%
   :align: left

   The Imgur_ client secret widget.

4. Launch ``howdy_config_gui``, which starts with a three row table: *LOGIN*, *CREDENTIALS*, and *MUSIC*. Right click on the *CREDENTIALS* row to launch a context menu with a single item, *Plex config credentials*. Click on *Plex config credentials*. Here is a screen shot.

.. _imgur_step04_credentials:

.. figure:: howdy-config-services-figures/imgur_step04_credentials.png
   :width: 100%
   :align: left

   Click on *Plex config credentials*.
  
5. Fill in the Imgur client ID and Imgur client secret as shown in :numref:`imgur_step03_clientsecret` and then press the *REFRESH CLIENT* button. Here is a screen shot.

.. _imgur_step05_authorizeaccount:

.. figure:: howdy-config-services-figures/imgur_step05_authorizeaccount.png
  :width: 100%
  :align: center

6. At this point, two things occur. First, a new web browser window (or tab, if a browser window is open) that resolves to the URL that the Imgur client must use in order to finally authenticate the client. Copy the full URL in the browser's tab, as shown in :numref:`imgur_step06a_launchedURL` into the new dialog window shown in :numref:`imgur_step06b_copyURLdialog`. Press return in that dialog window.

.. _imgur_step06a_launchedURL:

.. figure:: howdy-config-services-figures/imgur_step06a_launchedURL.png
   :width: 100%
   :align: left

   This is the full URL in the browser's tab.

.. _imgur_step06b_copyURLdialog:

.. figure:: howdy-config-services-figures/imgur_step06b_copyURLdialog.png
   :width: 100%
   :align: left

   Copy the full URL in :numref:`imgur_step06a_launchedURL` into the Imgur_ configuration URL dialog.

7. This **should** work -- the *Plex config credentials* widget should show **WORKING** under the Imgur_ settings panel. If this does not work, then close the Imgur URL dialog in :numref:`imgur_step06b_copyURLdialog` with the ``Esc`` key, and generate a new client secret as shown in :numref:`imgur_step02_getclientsecret`, and repeat until you are able to generate good Imgur_ client credentials.

Low Level Imgur Credentials
---------------------------
The lower level generation of Imgur credentials use `requests-oauthlib <https://requests-oauthlib.readthedocs.io/en/latest>`_ to generate the Imgur credentials.

1. Follow steps 1-3 in :numref:`Generate Imgur Credentials Using ``Howdy``` to get the Imgur client ID and client secret.

2. Generate the Oauth2 ``authorization_url`` and ``state`` variables, using this piece of example Python code. We also allow one to choose whether to verify SSL connections with a ``verify`` boolean variable.

   .. code-block:: python

      from requests_oauthlib import Oauth2Session

      client_ID = "XXXXXXXX"
      client_SECRET = "YYYYYYY"
      variable = True
      auth_url = "https://api.imgur.com/oauth2/authorize"
      token_url = "https://api.imgur.com/oauth2/token"

      imgur = Oauth2Session( client_ID )
      authorization_url, state = authorization_url, state = imgur.authorization_url( auth_url, verify = False )

3. Launch a browser at the ``authorization_url`` either manually or by running

   .. code-block:: python

      import webbrowser

      webbrowser.open_new_tab( authorization_url )

4. Copy the browser URL, as described in :numref:`imgur_step06a_launchedURL`, into ``response_url``, and generate the final OAuth2 token into a ``token`` dictionary object.

   .. code-block:: python

      imgur = Oauth2Session( client_ID, state = state )
      token = imgur.fetch_token( token_url, authorization_response=response_url, client_secret=client_secret)

   If the process does not work, an Exception will be emitted. If successful, the final ``token`` object looks like the following,
   
   .. code-block:: python

      {'access_token': 'xxxxxx',
       'expires_in': 315360000,
       'token_type': 'bearer',
       'scope': None,
       'refresh_token': 'rrrrrr',
       'account_id': <account_ID>,
       'account_username': <account_username>,
       'expires_at': zzzzz }

   Copy ``token['refresh_token']`` with ``client_ID`` and ``secret_ID`` to authorize your Imgur client. Here, you can follow instructions as given in `the Imgur API page <https://apidocs.imgur.com>`_.

The Gracenote and LastFM APIs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Instructions for the Gracenote API registration can be found `here <https://developer.gracenote.com/web-api>`_. The implementation of metadata population using Gracenote uses the `pygn <https://github.com/cweichen/pygn>`_ Python module.

The instructions for the LastFM API registration start `here <lastfm_intro_>`_. Here are the steps to get an API key and register your service to use the LastFM API to get music metadata.

1. On the `API intro page <lastfm_intro_>`_, click on the  the *Add API account* link. Here is a screen shot.

.. _lastfm_step01_addapiaccount:

.. figure:: howdy-config-services-figures/lastfm_step01_addapiaccount.png
   :width: 100%
   :align: center

2. You will land on the `LastFM API creation page <lastfm_create_>`_. Fill in the forms for *Application name*, *Application description*, and *Application homepage*. Leave *Callback URL* empty because it is optional. Click on the *Submit* button once done. Here is a screen shot.

.. _lastfm_step02_registerapp:

.. figure:: howdy-config-services-figures/lastfm_step02_registerapp.png
   :width: 100%
   :align: center

If everything has worked out, after clicking *Submit* you will see the *Application name*, *API key*, *Shared secret*, and *Registered to* fields. Record this information. Here is a screen shot.

.. _lastfm_step03_success:

.. figure:: howdy-config-services-figures/lastfm_step03_success.png
  :width: 100%
  :align: center

.. _lastfm_intro:  https://www.last.fm/api/intro
.. _lastfm_create: https://www.last.fm/api/account/create

The Jackett Server
^^^^^^^^^^^^^^^^^^
`Jackett <https://github.com/Jackett/Jackett>`_ is a relatively successful proxy server that consolidates the torrent search from a large number of public, private, and semi-private torrent trackers and services into a single search user interface and API. It is used as the torrent searching back end for higher level media automated downloaders/maintainers such as `Sonarr <https://sonarr.tv/>`_, `Sickrage <https://www.sickrage.ca/>`_, `Radarr <https://radarr.video/>`_, `Lidarr <https://lidarr.audio/>`_, `Couchpotato <https://couchpota.to/>`_, and yet many others that I have not included.

Howdy needs the main URL prefix of the Jackett server, and the Jackett API key, in order to use Jackett programmatically to search for movie and television torrents. The URL prefix is the part of the Jackett Web UI page before the ``UI/dashboard`` in the address. The API key is clearly shown and can be copied.

.. _jackett_step01_webui:

.. figure:: howdy-config-services-figures/jackett_step01_webui.png
  :width: 100%
  :align: center
  :alt: Jackett WebUI

Summary of Setting Up Google Credentials
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
We set up `Google <https://www.google.com>`_ services that use `YouTube <https://www.youtube.com>`_, GMail, Google Contacts, Google Spreadsheets, and the `unofficial Google Music API <https://unofficial-google-music-api.readthedocs.io/en/latest/>`_.

Since these are all Google services, a single tool sets all of them up given a single Google account using Google's OAuth2_ authentication mechanism. The easiest way to do this is through the :ref:`howdy_config_gui executable <howdy_config_gui_label>`, which is part of Howdy.

1. Launch :ref:`howdy_config_gui <howdy_config_gui_label>`, which starts with a three row table: *LOGIN*, *CREDENTIALS*, and *MUSIC* (see :numref:`howdy_config_gui_serviceswidget`). Right click on the *CREDENTIALS* row to launch a context menu with a single item, *Plex config credentials*. Click on *Plex config credentials*. These instructions are the same as in :ref:`step 4 <imgur_step04_credentials>` in :numref:`The Imgur API` and in :ref:`step 4 <imgur_step04_credentials>`, which we reproduce here.

.. figure:: howdy-config-services-figures/google_step01_credentials.png
  :width: 100%
  :align: center

2. A *PLEX CREDENTIALS CONFIGURATION* widget will open. Click on the *CLIENT REFRESH* button in the Google section of this widget. Here is a screen shot.

.. _google_step02_refreshcredentials:
.. figure:: howdy-config-services-figures/google_step02_refreshcredentials.png
   :width: 800
   :align: left

   Refresh Google credentials.

3. A browser window in your default internet browser will launch, asking you to authorize access to a Google account. Here is the first screen shot.

.. _google_step03_authorizeaccount:

.. figure:: howdy-config-services-figures/google_step03_authorizeaccount.png
   :width: 100%
   :align: left

   First authorize your Google account.

4. Also, a new dialog widget will open asking you to put in an OAuth2_ token string once you have given permission. Here is the second screen shot.

.. _google_step04_oauthtokenstring:

.. figure:: howdy-config-services-figures/google_step04_oauthtokenstring.png
   :width: 800
   :align: left

   Next copy and paste in your Oauth2_ token string.

5. In :ref:`step 3 <google_step03_authorizeaccount>`, when you choose a Google account, currently you will be redirected to a scary browser page that says "this app isn't verified". It isn't, but the services still work. If you use Google Chrome or derived browser, click on the *Show Advanced* toggling link. Then click on *Go to Project Default Service Account (unsafe)* to go forward. Here is a screen shot.

.. _google_step05_scaryscreen:

.. figure:: howdy-config-services-figures/google_step05_scaryscreen.png
   :width: 100%
   :align: left

   The *very* scary screen that Google spits out, saying your app is **not** verified.

6. Howdy asks for six different Google authorizations. Click on the *Allow* button.

.. _google_step06_allowbutton:

.. figure:: howdy-config-services-figures/google_step06_allowbutton.png
   :width: 800
   :align: left

   Allow Howdy to access these *six* Google APIs through your Google account.

7. The final browser window shows a text box with the OAuth2_ token string. Copy that string into the GUI dialog widget in :ref:`step 4 <google_step04_oauthtokenstring>`, and press return on the text box in that widget.

.. _google_step07_oauthtokencopy:

.. figure:: howdy-config-services-figures/google_step07_oauthtokencopy.png
   :width: 800
   :align: left

   Copy this string into the GUI dialog widget in :ref:`step 4 <google_step04_oauthtokenstring>`.
	   
If all goes well, then you will have authorized all the Google services needed by Howdy.

.. _OAuth2: https://en.wikipedia.org/wiki/OAuth#OAuth_2.0
.. _unofficial_google_music_api: https://unofficial-google-music-api.readthedocs.io/en/latest
.. _Imgur: https://imgur.com
.. _`register an Imgur application`: https://api.imgur.com/oauth2/addclient
.. _`Imgur account`: https://imgur.com/register?redirect=https%3A%2F%2Fimgur.com%2F
.. _`Imgur application's webpage`: https://imgur.com/account/settings/apps
.. _`this website`: https://apidocs.imgur.com/?version=latest
.. _tvdb_login_page: https://www.thetvdb.com/login
.. _`TMDB API`: https://developers.themoviedb.org/3/getting-started/introduction
.. _`TMDB API link`: https://www.themoviedb.org/settings/api
.. _TMDB: https://www.themoviedb.org
.. _TVDB: https://www.thetvdb.com
..
.. _`Gracenote API`: https://developer.gracenote.com/web-api
.. _`LastFM API`: https://www.last.fm/api
.. _`Jackett proxy server`: https://github.com/Jackett/Jackett
.. _Torrentz2: https://torrentz2.eu
.. _RARBG: http://rarbg.to/index70.php
.. _`Kickass Torrents`: https://en.wikipedia.org/wiki/KickassTorrents
.. _`The Pirate Bay`: https://thepiratebay.org
.. _CAPTCHAs: https://en.wikipedia.org/wiki/CAPTCHA
..
.. _`GMail API`: https://developers.google.com/gmail/api
.. _`Google Contacts API`: https://developers.google.com/contacts/v3
.. _YouTube: https://www.youtube.com
.. _`YouTube API`: https://developers.google.com/youtube/v3
.. _`Google Sheets API`: https://developers.google.com/sheets/api
.. _`Google Play Music`: https://play.google.com/store/music?hl=en
