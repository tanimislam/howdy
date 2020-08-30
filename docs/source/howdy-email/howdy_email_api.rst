================================================
Howdy Email API
================================================

This document describes the lower level Plex emailing API, upon which the :ref:`command line tol <howdy_email_notif>` and  the :ref:`GUI tool <howdy_email_gui>` are built. It lives in ``howdy.email``.

howdy.email module
----------------------------
This contains the lowest level methods to send email using either the `Google Contacts API`_ or through Python's :py:class:`SMTP <smtplib.SMTP>` functionality, and to find the Google contact names of friend emails on the Plex_ server. :py:class:`HowdyIMGClient <howdy.email.HowdyIMGClient>` and :py:class:`PNGPicObject <howdy.email.PNGPicObject>` allow one to add or remove images from one's Imgur_ acount.

.. automodule:: howdy.email
   :members:

howdy.email.email module
----------------------------------------
This implements the following functionality: sending emails of torrent files and magnet links; sending :py:class:`MIMEMultiPart <email.mime.multipart.MIMEMultiPart>` newsletter or more general style emails to friends of the Plex_ server; and sending general emails with attachments.

.. automodule:: howdy.email.email
   :members:

.. _`Google Contacts API`: https://developers.google.com/contacts/v3
.. _Plex: https://plex.tv
.. _Imgur: https://imgur.com
