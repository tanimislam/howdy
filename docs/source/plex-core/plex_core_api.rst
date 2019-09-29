================================================
Core API
================================================

This document describes the lower level Plex emailing API, upon which all the command line and GUI tools are based. It lives in ``plexstuff.plexcore``.

plexcore module
----------------------

This module implements the lower-level functionality that does or has the following:

     * access and retrieve configuration and other data from an SQLite3_ database using SQLAlchemy_ object relational mapping (ORM) classes. The SQLite3_ database is stored in ``~/.config/plexstuff/app.db``.

     * :py:class:`PlexConfig <plexcore.PlexConfig>` is an ORM class that stores configuration information.

     * :py:class:`PlexGuestEmailMapping <plexcore.PlexGuestEmailMapping>` is an ORM class that stores all the email addresses that will receive Plexstuff email notifications.

     * :py:class:`LastNewsletterDate <plexcore.LastNewsletterDate>` is an ORM class that store one member (or row) -- the :py:class:`datetime <datetime.datetime>` of when the Plexstuff newsletter was last updated.

     * :py:meth:`create_all <plexcore.create_all>` instantiates necessary SQLite3_ tables in the configuration table if they don't already exist.

     * low level PyQt4_ derived widgets used for the other GUIs in Plexstuff: :py:class:`ProgressDialog <plexcore.ProgressDialog>`, :py:class:`QDialogWithPrinting <plexcore.QDialogWithPrinting>`, and :py:class:`QLabelWithSave <plexcore.QLabelWithSave>`.

     * initialization, in order to check for necessary prerequisites (see :ref:`Prerequisites`) and to install missing Python modules and packages (see :ref:`Installation`). This initialization is handled via a :py:class:`PlexInitialization <plexcore.plexinitialization.PlexInitialization>` singleton object.


.. automodule:: plexcore
   :members:

plexcore.plexinitialization module
-----------------------------------------

.. automodule:: plexcore.plexinitialization
   :members:

plexcore.plexcore module
-----------------------------------------

This module implements the functionality to do the following:

     * access your Plex_ server, and determine those Plex_ servers to which you have access.

     * retrieve and summarize data in the Plex_ libraries.

     * miscellaneous functionalities, such as the following: getting formatted date strings from a :py:class:`date <datetime.date>` object.

.. automodule:: plexcore.plexcore
   :members:


plexcore.plexcore_deluge module
-----------------------------------------

This module implements the functionality to interact with a Seedhost_ seedbox_ `Deluge torrent server`_, by copying a minimal set of the functionality of a `Deluge torrent client`_. The data formatting in this module is largely or wholly copied from the `Deluge SDK <https://deluge.readthedocs.io/en/latest>`_. The much reduced Deluge torrent client, :ref:`plex_deluge_console.py`, is a CLI to this module.

.. automodule:: plexcore.plexcore_deluge
   :members:

.. these are some URLs

.. _SQLite3: https://www.sqlite.org/index.html
.. _SQLAlchemy: https://www.sqlalchemy.org
.. _PyQt4: https://www.riverbankcomputing.com/static/Docs/PyQt4/index.html
.. _Subscene: https://subscene.com
.. _Subliminal: https://subliminal.readthedocs.io/en/latest
.. _cfscrape: https://github.com/Anorov/cloudflare-scrape
.. _CAPTCHA: https://en.wikipedia.org/wiki/CAPTCHA
.. _Seedhost: https://www.seedhost.eu
.. _seedbox: https://en.wikipedia.org/wiki/Seedbox
.. _`Deluge torrent server`: https://deluge-torrent.org
.. _`Deluge torrent client`: https://en.wikipedia.org/wiki/Deluge_(software)
