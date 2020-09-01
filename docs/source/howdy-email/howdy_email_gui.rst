.. _howdy_email_gui_label:

================================================
|howdy_email_gui_icon| |howdy_email_gui|
================================================
This is documentation for the Howdy one-off and newslettering email announcement GUI, |howdy_email_gui|. The help output, when running ``howdy_email_notif -h``, produces the following output,

.. code-block:: console

   usage: howdy_email_gui [-h] [--info] [--local] [--large] [--noverify]
			  [--extraemails EXTRAEMAILS] [--extranames EXTRANAMES]
			  {n,o} ...

   positional arguments:
     {n,o}                 Choose one of two options: (o) do only the email. (n)
			   do the newslettering functionality.
       n                   Do the newsletter one.
       o                   Only do a straightforward email.

   optional arguments:
     -h, --help            show this help message and exit
     --info                Run info mode if chosen.
     --local               Check for locally running plex server.
     --large               If chosen, make the GUI (widgets and fonts) LARGER to
			   help with readability.
     --noverify            Do not verify SSL transactions if chosen.

The ``(n)`` choice means do a :ref:`newsletter <Newsletter Mode>`, while the ``(o)`` choice means do :ref:`only the email <Only Email Mode>`. Here are the common arguments.

* ``--info`` prints out :py:const:`INFO <logging.INFO>` level :py:mod:`logging` output.

* ``--local`` specifies that we look for a local (``https://localhost:3400``) running Plex_ server.

* ``--large`` specifies that one should make the GUI (widgets and fonts) *LARGER* to aid in readibility.

* ``--noverify`` is a standard option in many of the Howdy CLI and GUIs to ignore verification of SSL transactions. It is optional and will default to ``False``.

Only Email Mode
^^^^^^^^^^^^^^^^
When running with the ``(o)`` choice, this GUI only sends a non-newsletter email to either yourself or to all the friends of your Plex_ server. This GUI is launched when running ``howdy_email_gui o``.

.. _onlyemail_mainwindow_ANNOTATED:

.. figure:: howdy-email-gui-figs/howdy_email_gui_onlyemail_mainwindow_ANNOTATED.png
   :width: 100%
   :align: left

   The main window launched when running ``howdy_email_gui o``. Annotations show where one puts in the email body and email text.

The :ref:`main window <onlyemail_mainwindow_ANNOTATED>` has the following buttons and text fields. The subject and body fields go into their respective text areas.

* The ``CHECK EMAIL`` button displays the rich HTML output of the email body, if there are no errors.

* The ``SHOW PNGS`` button displays the PNG_ images located in your Imgur_ library. See, e.g., :numref:`Choosing Main Imgur_ Album` to demonstrate its functionality.

* There is a subject and body that you can specify. The email body is written in reStructuredText_ and then converted into HTML.

* ``PLEX GUESTS`` displays the list of friends of your Plex_ server. See :numref:`howdy_core_cli_example` for an example of what the friends of your Plex_ server looks like.

* ``SEND TEST EMAIL`` only sends an email to yourself.

* ``SEND ALL EMAIL`` sends an email to you and all the friends of your Plex_ server.

Here we construct and send a rudimentary email that demonstrates an interesting amount of functionality available with reStructuredText_. The work flow is ordered as follows,

1. :ref:`Write, and test, the email <Write and Test Email>`.

2. :ref:`Verify friends of your Plex server <Verify Plex_ Friends>`.

3. :ref:`Send email <Send Email>`.

Write and Test Email
----------------------
Here, we write an email that consists of some stylized text, some LaTeX_ math, and an inset image with caption using our Imgur_ library! The subject of the email is ``test``. The body is reStructuredText_, and is given by,

.. _example_email_body:

.. code-block:: RST

   I am showing some example code. Here is some *bold* code.

   This is an inline equation, :math:`2x - 5y e^{-x} = 4`.

   This is the `Black-Scholes equation`_.

   .. math::

      \frac{\partial V}{\partial t} + \frac{1}{2}\sigma^2 S^2\frac{\partial^2 V}{\partial S^2} + r S \frac{\partial V}{\partial S} - rV = 0

   Finally, one can insert an image into here. Here is what I will do.

   .. figure:: https://i.imgur.com/raP42Rz.png
      :width: 100%
      :align: left

      Look at me! I have a caption!
	      
   .. _`Black-Scholes equation`: https://en.wikipedia.org/wiki/Black–Scholes_equation

One can find some good tutorials on how to write valid reStructuredText_ online or on the Sphinx_ website. The biggest, undocumented subtlety here comes from adding images from our Imgur_ library -- how do we know that the URL of the image is ``https://i.imgur.com/raP42Rz.png``? We are looking for the ``HOWDY! EMAIL GUI`` icon, which has a cowboy hat inside it.

* First click on ``SHOW PNGS`` to pop up a table that shows the available PNG_ images in our Imgur_ library.

  .. figure:: howdy-email-gui-figs/onlyemail_show_pngs_information_ANNOTATED.png
     :width: 100%
     :align: left

     There are *nine* images in the main album of our Imgur_ library. Here, we wish to select ``howdy_email_gui_SQUARE.png``.

* Second, right-click on the row that has ``howdy_email_gui_SQUARE.png``, which will pop up a context menu. Select the ``Information`` context menu event to verify that we have the right image.

  .. figure:: howdy-email-gui-figs/onlyemail_show_pngs_information_ANNOTATED.png
     :width: 100%
     :align: left

     Select the ``Information`` context menu event on ``howdy_email_gui_SQUARE.png``. This will pop up another window that shows the URL and verifies this is the correct image.

* Third, we see that ``howdy_email_gui_SQUARE.png`` is the correct image, and we get its URL.

  .. _onlyemail_show_pngs_information_ANNOTATED:
  
  .. figure:: howdy-email-gui-figs/onlyemail_show_pngs_information_ANNOTATED.png
     :width: 100%
     :align: left

     This is the correct image for the icon. It has a neon green cowboy hat in the middle, and the name ``HOWDY! EMAIL GUI``. We also see that its URL is ``https://i.imgur.com/raP42Rz.png``.

* Finally, copy that email using the ``Copy Image URL`` context menu event.

  .. figure:: howdy-email-gui-figs/onlyemail_show_pngs_copyurl_ANNOTATED.png
     :width: 100%
     :align: left

     We don't need to transcribe the URL as shown in :numref:`onlyemail_show_pngs_information_ANNOTATED`, by right-clicking on the ``howdy_email_gui_SQUARE.png`` row and choosing the ``Copy Image URL`` context menu event. This will copy its URL to the clipboard.

The movie below demonstrates the step-by-step workflow in :ref:`writing and testing email <Write and Test Email>`.

.. _onlyemail_write_test_email:

.. youtube:: K2EKQUldBD8
   :width: 100%

After we have our URL copied and pasted, we click on ``CHECK EMAIL`` to pop up the rich HTML representation of the email body.

.. figure:: howdy-email-gui-figs/onlyemail_write_test_email_showHTML_ANNOTATED.png
   :width: 100%
   :align: left

   Finally, click on ``CHECK EMAIL``. If the email body text is valid, then ``VALID RESTRUCTUREDTEXT`` will appear and a rich HTML rendering of the email body will pop up.

Furthermore, if the email body text is *valid*, then the buttons ``SEND ALL EMAIL`` and ``SEND TEST EMAIL`` will be active. If the email body text is *invalid*, then those two buttons will be inactive.

This other movie shows the *full* rendered HTML.

.. _onlyemail_write_test_email_showHTML:

.. youtube:: yRzKNJ006dg
   :width: 100%

Verify Plex_ Friends
---------------------
Once you verify that your email is valid, you should check that your list of friends on your Plex_ server is valid. Just click on ``PLEX GUESTS`` to get the list of friends, one per row and ordered by name. First column is the full name, and the second column is the email address for their Plex_ account.

.. figure:: howdy-email-gui-figs/onlyemail_show_plex_friends_ANNOTATED.png
   :width: 100%
   :align: left

   Click on ``PLEX GUESTS`` to show the list of people who have access to your Plex_ server, and who will receive your email. For privacy reasons, I blank out these friends just as in :numref:`howdy_core_cli_example`.

Send Email
------------
Once your email body text is valid, and you are satisfied that you may want to send this email out to people who have access to your Plex_ server, then you can click on either ``SEND TEST EMAIL`` (sends the email *only* to you) or ``SEND ALL EMAIL`` (sends the email to all your Plex_ friends).

I always verify that the email is valid, by clicking ``SEND TEST EMAIL`` first, before sending the email to everyone.

	     
Newsletter Mode
^^^^^^^^^^^^^^^^

.. |howdy_email_gui_icon| image:: howdy-email-gui-figs/howdy_email_gui_SQUARE.png
   :width: 50
   :align: middle

.. |howdy_email_gui| replace:: ``howdy_email_gui``

.. _Plex: https://plex.tv
.. _Imgur: https://imgur.com
.. _PNG: https://en.wikipedia.org/wiki/Portable_Network_Graphics
.. _LaTeX: https://en.wikipedia.org/wiki/LaTeX
.. _reStructuredText: https://en.wikipedia.org/wiki/ReStructuredText
.. _Sphinx: https://www.sphinx-doc.org/en/master
