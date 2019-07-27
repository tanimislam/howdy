================================================
Core API
================================================

This document describes the lower level Plex emailing API, upon which all the command line and GUI tools are based. It lives in ``plexstuff.plexcore``.

``plexcore``
----------------------

This module implements the lower-level functionality to do the following:

  * to access and retrieve configuration and other data from an SQLite3_ database using SQLAlchemy_ ORM classes. The SQLite3_ database is stored in ``~/.config/plexstuff/app.db``.

  * :py:class:`PlexConfig <plexcore.PlexConfig>` is an ORM class that stores configuration information.
  * :py:class:`PlexGuestEmailMapping <plexcore.PlexGuestEmailMapping>` is an ORM class that stores all the email addresses that will receive Plexstuff email notifications.
  * :py:class:`LastNewsletterDate <plexcore.LastNewsletterDate>` is an ORM class that store one member (or row) -- the :py:class:`datetime <datetime.datetime>` of when the Plexstuff newsletter was last updated.
  * :py:meth:`create_all <plexcore.create_all>` instantiates necessary SQLite3_ tables in the configuration table if they don't already exist.
  
* low level PyQt4_ derived widgets used for the other GUIs in Plexstuff: 
* initialization, in order to check for necessary prerequisites (see :ref:`Prerequisites`) and to install missing Python modules and packages (see :ref:`Installation`). This initialization is handled via a :py:class:`PlexInitialization <plexcore.plexinitialization.PlexInitialization>` singleton object.

.. _SQLite3: https://www.sqlite.org/index.html
.. _SQLAlchemy: https://www.sqlalchemy.org

.. automodule:: plexcore
   :members:

``plexcore.plexinitialization``
-----------------------------------------

.. automodule:: plexcore.plexinitialization
   :members:

``plexcore.plexcore``
-----------------------------------------

This module implements the following 

.. automodule:: plexcore.plexcore
   :members:

