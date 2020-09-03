================================================
Howdy Core GUIs
================================================
These are the Howdy_ core GUIs.

* :ref:`howdy_config_gui <howdy_config_gui_label>` is the configuration tool used to get the full Howdy functionality.

* :ref:`howdy_core_gui_label` is a more archaic version of ``howdy_config_gui``. This only provides a GUI to set up the correct Plex_ server settings or to set up `Google OAuth2 authentication`_.

* :ref:`howdy_create_texts_label` tests the creation of prettified HTML using reStructuredText_.

.. _howdy_core_gui_label:

|howdy_core_gui_icon|\  |howdy_core_gui|
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
|howdy_core_gui| has two modes of operation: either return the Plex_ server token and URL; or set up `Google OAuth2 authentication`_. ``howdy_core_gui -h`` produces this help screen,

.. code-block:: console

   Usage: howdy_core_gui [-h] [--info] [--remote] {googleauth} ...

   positional arguments:
     {googleauth}  Can optionally choose to set up google oauth2 authentication.
       googleauth  Set up google oauth2 authentication.

   optional arguments:
     -h, --help    show this help message and exit
     --info        If chosen, run in INFO logging mode.
     --remote      If chosen, do not check localhost for running plex server.

At the top level, here are the options.

* ``--info``: print out the :py:const:`INFO <logging.INFO>` level :py:mod:`logging` output.

* ``--remote``: If chosen, do not check localhost for a running Plex_ server.

When running in standard mode, this tool prints out the current Plex_ server and token URL.

.. code-block:: console

   tanim-desktop $ howdy_core_gui
   token = XXXXXXXXXXXXXXXXXXXX
   url = http://localhost:32400

I mask the 20-character token with ``XXXXXXXXXXXXXXXXXXXX`` for privacy reasons.

When running with ``googleauth``, this GUI pulls up a `Google OAuth2 authentication`_ dialog window if we either choose to *bypass* any existing authentication, or if that authentication does not exist. Running ``howdy_core_gui googleauth -h`` produces this help screen,

.. code-block:: console

   usage: howdy_core_gui googleauth [-h] [--bypass]

   optional arguments:
     -h, --help  show this help message and exit
     --bypass    If chosen, then ignore any existing google oauth2 authentication
		 credentials.

The ``--bypass`` flag ignores any existing  `Google OAuth2 authentication`_.

This GUI is launched when running ``howdy_core_gui googleauth``.

.. _howdy_core_gui_mainwindow:

.. figure:: gui-tools-figures/howdy_core_gui_mainwindow.png
   :width: 100%
   :align: left

   Fill out the `Google OAuth2 authentication`_ credentials in the text box in the same manner as done in :numref:`google_step04_oauthtokenstring` in :numref:`Summary of Setting Up Google Credentials` for :ref:`howdy_config_gui <howdy_config_gui_label>`.

Here, a browser tab or new window is launched (see :numref:`google_step03_authorizeaccount`).

1. You will see a scary dialog window in the browser window (see :numref:`google_step05_scaryscreen`).

2. Click on the *Allow* button for the six Google services that Howdy requires (see :numref:`google_step06_allowbutton`).

3. The final browser window shows a text box with the `Google OAuth2 authentication`_ token string (see :numref:`google_step07_oauthtokencopy`). Copy that string into the GUI dialog widget in :numref:`howdy_core_gui_mainwindow`, and press return on the text box in this dialog window.

If all goes well, then all the Google services needed by Howdy will have been authorized.

.. _howdy_create_texts_label:

|howdy_create_texts_icon|\  |howdy_create_texts|
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This is a simple GUI that demonstrates the creation of prettified HTML using reStructuredText_. Optionally, one can also *save* the output of the created and rendered HTML. Here is the annotated main window that pops up when running ``howdy_create_texts``,

.. _howdy_create_texts_ANNOTATED:

.. figure:: gui-tools-figures/howdy_create_texts_ANNOTATED.png
   :width: 100%
   :align: left

   |howdy_create_texts| has a very simple user interface. Just type in your reStructuredText_ into here and render it by clicking on the ``CONVERT`` button.

Put in some valid reStructuredText_ into that text area, and then click on ``CONVERT`` to render the HTML. One can find some good tutorials on how to write valid reStructuredText_ online or on the Sphinx_ website.

Here is what happens when we render some *fairly complicated* reStructuredText_.

.. _howdy_create_texts_convert_ANNOTATED:

.. figure:: gui-tools-figures/howdy_create_texts_convert_ANNOTATED.png
   :width: 100%
   :align: left

   Clicking on ``CONVERT`` creates a window showing the accurately rendered rich HTML output of the valid reStructuredText_ in a new window.

Finally, clicking on the ``SAVE`` button opens up a file dialog where you can save the input reStructuredText_ into an ``.rst`` file.

.. _howdy_create_texts_save_ANNOTATED:

.. figure:: gui-tools-figures/howdy_create_texts_save_ANNOTATED.png
   :width: 100%
   :align: left

   Click on ``SAVE`` to save the reStructuredText_ into an ``.rst`` file.

I have included this :download:`example restructuredText file </_static/howdy_create_texts.rst>` that allows one to independently verify how this reStructuredText_ renders. This is the example file shown in :numref:`howdy_create_texts_convert_ANNOTATED` and :numref:`howdy_create_texts_save_ANNOTATED`.
   
.. |howdy_create_texts| replace:: ``howdy_create_texts``

.. |howdy_create_texts_icon| image:: gui-tools-figures/howdy_create_texts_SQUARE.png
   :width: 50
   :align: middle

.. |howdy_core_gui| replace:: ``howdy_core_gui``

.. |howdy_core_gui_icon| image:: gui-tools-figures/howdy_core_gui_SQUARE.png
   :width: 50
   :align: middle

.. 
	   
.. _Howdy: https://howdy.readthedocs.io
.. _reStructuredText: https://en.wikipedia.org/wiki/ReStructuredText
.. _`Google OAuth2 authentication`: https://developers.google.com/identity/protocols/oauth2
.. _Sphinx: https://www.sphinx-doc.org/en/master
.. _Plex: https://plex.tv
