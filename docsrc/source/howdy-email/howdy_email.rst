================================================
Howdy Email Functionality
================================================
These command line executables, graphical user interfaces, and APIs are used to send one-off announcement, or newsletter style emails. Tautulli_ is a much better tool for sending out newsletter style emails, although this functionality still exists.

This documentation is organized into sections on :ref:`howdy_email_notif_label`, the Howdy one-off emailing command line interface; :ref:`howdy_email_gui_label`, the Howdy one-off emailing and newslettering GUI; and :ref:`howdy_email_demo_gui_label`, the Howdy test-bed demonstation email client, that sends out rich HTML email using reStructuredText_; the :ref:`low level API <Howdy Email API>`; and finally the :ref:`TODO <Howdy Email TODO>`.

.. toctree::
   :maxdepth: 2
   :caption: Table of Contents

   cli-tools/howdy_email_notif
   gui-tools/howdy_email_gui
   gui-tools/howdy_email_demo_gui
   howdy_email_api

Howdy Email TODO
------------------
* Enhance :ref:`howdy_email_demo_gui_label` to allow for the more versatile reStructuredText_ to be converted into HTML documents and email out. |cbox|

The Howdy! Email CLI and API functionality are fairly robust. I may see the need to enhance its functionality, or fix pressing bugs, as I reexamine this space.

.. |cbox| unicode:: U+2611 .. BALLOT BOX WITH CHECK
.. _Tautulli: https://tautulli.com
.. _reStructuredText: https://en.wikipedia.org/wiki/ReStructuredText
