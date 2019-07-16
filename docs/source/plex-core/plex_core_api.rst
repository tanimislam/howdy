================================================
Core API
================================================

This document describes the lower level Plex emailing API, upon which all the command line and GUI tools are based. It lives in ``plexstuff.plexcore``.

``plexstuff.plexcore``
----------------------

This module implements the lower-level functionality to do the following:

* to access and retrieve configuration and other data from an SQLite3_ database using SQLAlchemy_ classes.
* provide glue functionality for the rest of the Plexstuff SDK, command line tools, and GUIs.

.. _SQLite3: https://www.sqlite.org/index.html
.. _SQLAlchemy: https://www.sqlalchemy.org

.. automodule:: plexstuff.plexcore
  :members:

``plexstuff.plexcore.plexcore``
-----------------------------------------

.. automodule:: plexstuff.plexcore.plexcore
  :members:
