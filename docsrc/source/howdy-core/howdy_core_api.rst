================================================
Howdy Core API
================================================
This document describes the lower level Plex core API, upon which all the command line and GUI tools are based. It lives in ``howdy.core``.

howdy.core module
--------------------------
This module implements the lower-level functionality that does or has the following:

* access and retrieve configuration and other data from an SQLite3_ database using SQLAlchemy_ object relational mapping (ORM) classes. The SQLite3_ database is stored in ``~/.config/howdy/app.db``.

* :py:class:`PlexConfig <howdy.core.PlexConfig>` is an ORM class that stores configuration information.

* :py:class:`PlexGuestEmailMapping <howdy.core.PlexGuestEmailMapping>` is an ORM class that stores all the email addresses that will receive Howdy email notifications.

* :py:class:`LastNewsletterDate <howdy.core.LastNewsletterDate>` is an ORM class that store one member (or row) -- the :py:class:`datetime <datetime.datetime>` of when the Howdy newsletter was last updated.

* :py:meth:`create_all <howdy.core.create_all>` instantiates necessary SQLite3_ tables in the configuration table if they don't already exist.

* low level PyQt5_ derived widgets used for the other GUIs in Howdy: :py:class:`ProgressDialog <howdy.core.ProgressDialog>`, :py:class:`QDialogWithPrinting <howdy.core.QDialogWithPrinting>`, and :py:class:`QLabelWithSave <howdy.core.QLabelWithSave>`.

* initialization, in order to check for necessary prerequisites (see :ref:`Prerequisites`) and to install missing Python modules and packages (see :ref:`Installation`). This initialization is handled via a :py:class:`HowdyInitialization <howdy.initialization.HowdyInitialization>` singleton object.

.. automodule:: howdy.core
   :members:

howdy.core.core module
-----------------------------------------
This module implements the functionality to do the following:

* access your Plex_ server, and determine those Plex_ servers to which you have access.

* retrieve and summarize data in the Plex_ libraries.

* miscellaneous functionalities, such as the following: getting formatted date strings from a :py:class:`date <datetime.date>` object.

.. automodule:: howdy.core.core
   :members:

howdy.core.core_deluge module
--------------------------------------------
This module implements the functionality to interact with a Seedhost_ seedbox_ `Deluge torrent server`_, by copying a minimal set of the functionality of a `Deluge torrent client`_. The data formatting in this module is largely or wholly copied from the `Deluge SDK <https://deluge.readthedocs.io/en/latest>`_. The much reduced Deluge torrent client, :ref:`howdy_deluge_console`, is a CLI front-end to this module.

.. automodule:: howdy.core.core_deluge
   :members:

howdy.core.core_rsync module
--------------------------------------------
This module implements the functionality to interact with a Seedhost_ seedbox_ SSH server to download or upload files and directories using the rsync_ protocol tunneled through SSH. :ref:`rsync_subproc` is a CLI front-end to this module.

.. automodule:: howdy.core.core_rsync
   :members:

howdy.core.core_torrents module
----------------------------------------------
This is a newer module. It implements higher level interfaces to the Jackett_ torrent searching server to search for ebooks. :ref:`get_book_tor` is its only CLI front-end.

.. automodule:: howdy.core.core_torrents
   :members:

howdy.core.core_admin module
----------------------------------------------
This is a newer module. It implements the low-level tooling to monitor the Tautulli_ server that looks at the Plex_ server, and to check for updates, and download updates to, the current Plex_ server.

.. automodule:: howdy.core.core_admin
   :members:

howdy.core.deluge_client_tanim module
-------------------------------------------
This is a newer module. This is a copy of the `deluge-client`_ repository and module. Instead of creating a special branch, I had to modify its ``DelugeRPCClient`` object to work in a custom way, because of *much* stricter SSL policies in Python 3.10.

The relevant code that I modify now lives in my :py:class:`DelugeRPCClient <howdy.core.deluge_client_tanim.client.DelugeRPCClient>`. I followed advice from `this StackOverflow article on how to set ciphers in SSL Python sockets <so_article_>`_. I created an SSL context, allowed *all* ciphers, and then passed the all-ciphers list into the low-level socket that performs RPC communications.

.. automodule:: howdy.core.deluge_client_tanim.client
   :members:

howdy.core.deluge_client_tanim.rencode submodule
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: howdy.core.deluge_client_tanim.rencode
   :members:


.. these are some URLs

.. _SQLite3: https://www.sqlite.org/index.html
.. _SQLAlchemy: https://www.sqlalchemy.org
.. _PyQt5: https://www.riverbankcomputing.com/static/Docs/PyQt5
.. _Subscene: https://subscene.com
.. _Subliminal: https://subliminal.readthedocs.io/en/latest
.. _cfscrape: https://github.com/Anorov/cloudflare-scrape
.. _CAPTCHA: https://en.wikipedia.org/wiki/CAPTCHA
.. _Seedhost: https://www.seedhost.eu
.. _seedbox: https://en.wikipedia.org/wiki/Seedbox
.. _`Deluge torrent server`: https://deluge-torrent.org
.. _`Deluge torrent client`: https://en.wikipedia.org/wiki/Deluge_(software)
.. _rsync: https://en.wikipedia.org/wiki/Rsync
.. _Plex: https://plex.tv
.. _`deluge-client`: https://github.com/JohnDoee/deluge-client
.. _so_article: https://stackoverflow.com/questions/49774366/how-to-set-ciphers-in-ssl-python-socket