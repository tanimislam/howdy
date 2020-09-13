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
When running with the ``(o)`` choice, this GUI only sends a non-newsletter email to either yourself or to all the friends of your Plex_ server. This GUI is launched when running ``howdy_email_gui --noverify --local o``.

.. _onlyemail_mainwindow_ANNOTATED:

.. figure:: howdy-email-gui-figures/howdy_email_gui_onlyemail_mainwindow_ANNOTATED.png
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

.. _write_and_test_email_label:
   
Write and Test Email
----------------------
Here, we write an email that consists of some stylized text, some LaTeX_ math, and an inset image with caption using our Imgur_ library. The subject of the email is ``test``. The body is reStructuredText_, and is given by,

.. code-block:: RST
   :name: example_email_body

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

.. _adding_PNG_to_text:

* First click on ``SHOW PNGS`` to pop up a table that shows the available PNG_ images in our Imgur_ library.

  .. figure:: howdy-email-gui-figures/onlyemail_show_pngs_information_ANNOTATED.png
     :width: 100%
     :align: left

     There are *nine* images in the main album of our Imgur_ library. Here, we wish to select ``howdy_email_gui_SQUARE.png``.

* Second, right-click on the row that has ``howdy_email_gui_SQUARE.png``, which will pop up a context menu. Select the ``Information`` context menu event to verify that we have the right image.

  .. figure:: howdy-email-gui-figures/onlyemail_show_pngs_information_ANNOTATED.png
     :width: 100%
     :align: left

     Select the ``Information`` context menu event on ``howdy_email_gui_SQUARE.png``. This will pop up another window that shows the URL and verifies this is the correct image.

* Third, we see that ``howdy_email_gui_SQUARE.png`` is the correct image, and we get its URL.

  .. _onlyemail_show_pngs_information_ANNOTATED:
  
  .. figure:: howdy-email-gui-figures/onlyemail_show_pngs_information_ANNOTATED.png
     :width: 100%
     :align: left

     This is the correct image for the icon. It has a neon green cowboy hat in the middle, and the name ``HOWDY! EMAIL GUI``. We also see that its URL is ``https://i.imgur.com/raP42Rz.png``.

* Finally, copy that email using the ``Copy Image URL`` context menu event.

  .. figure:: howdy-email-gui-figures/onlyemail_show_pngs_copyurl_ANNOTATED.png
     :width: 100%
     :align: left

     We don't need to transcribe the URL as shown in :numref:`onlyemail_show_pngs_information_ANNOTATED`, by right-clicking on the ``howdy_email_gui_SQUARE.png`` row and choosing the ``Copy Image URL`` context menu event. This will copy its URL to the clipboard.

The movie below demonstrates the step-by-step workflow in :ref:`writing and testing email <Write and Test Email>`.

.. _onlyemail_write_test_email:

.. youtube:: K2EKQUldBD8
   :width: 100%

.. _check_email_to_see_text:
	   
After we have our URL copied and pasted, we click on ``CHECK EMAIL`` to pop up the rich HTML representation of the email body.

.. figure:: howdy-email-gui-figures/onlyemail_write_test_email_showHTML_ANNOTATED.png
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

.. figure:: howdy-email-gui-figures/onlyemail_show_plex_friends_ANNOTATED.png
   :width: 100%
   :align: left

   Click on ``PLEX GUESTS`` to show the list of people who have access to your Plex_ server, and who will receive your email. For privacy reasons, I blank out these friends just as in :numref:`howdy_core_cli_example`.

Send Email
------------
Once your email body text is valid, and you are satisfied that you may want to send this email out to people who have access to your Plex_ server, then you can click on either ``SEND TEST EMAIL`` (sends the email *only* to you) or ``SEND ALL EMAIL`` (sends the email to all your Plex_ friends).

I always verify that the email is valid, by clicking ``SEND TEST EMAIL`` first, before sending the email to everyone.


Newsletter Mode
^^^^^^^^^^^^^^^^
When running with the ``(n)`` choice, this GUI only sends a non-newsletter email to either yourself or to all the friends of your Plex_ server. The Plex_ newsletter email has this format,

.. code-block:: console

   Hello <name>,

   <PREAMBLE PART>

   <SUMMARY OF MEDIA ON PLEX SERVER>

   <POSTAMBLE PART>

Here, ``<name>`` is the person receiving the email, ``<PREAMBLE PART>`` is an optional introductory section, ``<SUMMARY OF MEDIA ON PLEX SERVER>`` summarizes the current media on the Plex_ server, and ``<POSTAMBLE PART>`` is an optional final section.

This GUI is launched when running ``howdy_email_gui --noverify --local n``.

.. _newsletter_mainwindow:

.. figure:: howdy-email-gui-figures/howdy_email_gui_newsletter_mainwindow.png
   :width: 100%
   :align: left

   The main window launched when running ``howdy_email_gui n``. This beginning window has only five buttons, and no text fields such as the ``only email functionality`` described in :numref:`onlyemail_mainwindow_ANNOTATED`.

The :ref:`main window <newsletter_mainwindow>` has the following buttons.

* The ``CHECK EMAIL`` button displays the *full* rich HTML output of the email body, if there are no errors.

* The ``PREAMBLE`` and ``POSTAMBLE`` buttons set up the ``<PREAMBLE PART>`` and ``<POSTAMBLE PART>``, respectively. It is described in more detail in :ref:`Setting up the PREAMBLE and POSTAMBLE parts`.
  
* ``PLEX GUESTS`` displays the list of friends of your Plex_ server. It has the same functionality described in :numref:`Verify Plex_ Friends`.

* ``EMAIL DIALOG`` launches the email dialog window, where you select whether to send a test email or an email to all your Plex_ friends.

Just as in :numref:`Only Email Mode`, here we describe the work flow to send a *newsletter* email.

1. :ref:`Set up the PREAMBLE and POSTAMBLE parts <Setting up the PREAMBLE and POSTAMBLE parts>`.

2. :ref:`Check that the newsletter email looks good <Checking Newsletter Email>`.

3. :ref:`Send email <Send Newsletter Email>`.

Setting up the PREAMBLE and POSTAMBLE parts
--------------------------------------------
Click on the ``PREAMBLE`` button to write up an introductory section in the newsletter, and the ``POSTAMBLE`` button to write up a concluding section. The ``PREAMBLE`` and ``POSTAMBLE`` dialog windows are nearly identical, and differ *only* in where the text is placed in the newsletter. :numref:`newsletter_preamble_postamble_window` shows both together, but subsequent instructions focus only on describing the ``PREAMBLE``.

.. _newsletter_preamble_postamble_window:

.. figure:: howdy-email-gui-figures/newsletter_preamble_postamble_window.png
   :width: 100%
   :align: left

   The ``PREAMBLE`` and ``POSTAMBLE`` windows launched when clicking on either the ``PREAMBLE`` or ``POSTAMBLE`` main window buttons in :numref:`newsletter_mainwindow`.

The ``PREAMBLE`` window has a similar functionality as the :ref:`main email window <onlyemail_mainwindow_ANNOTATED>` when running in :ref:`Only Email Mode`.

.. _newsletter_preamble_ANNOTATED:

.. figure:: howdy-email-gui-figures/newsletter_preamble_ANNOTATED.png
   :width: 100%
   :align: left

   A cropped and annotated screenshot of the ``PREAMBLE`` dialog showing functionality similar to :numref:`onlyemail_mainwindow_ANNOTATED`.

Here, the reStructuredText_ of the introduction goes into the text box. The title of the introduction goes into the text label after ``SECTION``. Toggle between the ``YES`` and ``NO`` radio buttons. If you want the introduction title in the newsletter email, choose ``YES``; otherwise, choose ``NO``.

To add PNG_ images from your Imgur_ library, just click on ``ADD PNGS`` and follow instructions just like in :ref:`adding PNG to text <adding_PNG_to_text>`. in :numref:`Write and Test Email`.

Finally, test your introductory text by clicking on the ``TEST TEXT`` button. Its functionality is the same as described in :ref:`checking email to see text <check_email_to_see_text>` in :numref:`Write and Test Email`.

:numref:`newsletter_preamble_showtext` and :numref:`newsletter_postamble_showtext` show the rich HTML for the introductory and final sections, respectively. If the text is valid, then ``VALID RESTRUCTUREDTEXT`` appears on the bottom left corner of the ``PREAMBLE`` and ``POSTAMBLE`` dialog windows.

.. _newsletter_preamble_showtext:
	
.. figure:: howdy-email-gui-figures/newsletter_preamble_showtext.png
   :width: 100%
   :align: left

   The fancy-looking introductory text that will go into the Plex_ newsletter. Here we chosen ``YES`` to show the introductory section title, which is ``Introduction``.

.. _newsletter_postamble_showtext:

.. figure:: howdy-email-gui-figures/newsletter_postamble_showtext.png
   :width: 100%
   :align: left

   An even-more fancy-looking final text that will go into the Plex_ newsletter. Here we chosen ``YES`` to show the final section title, which is ``Final Thoughts``.

Checking Newsletter Email
--------------------------
After choosing the form of the introductory (:numref:`newsletter_preamble_showtext`) and final (:numref:`newsletter_postamble_showtext`) sections, click on ``CHECK EMAIL`` to (**wait a long time and**)  show the rich HTML email of the Plex_ newsletter.

.. _newsletter_checkemail_ANNOTATED:

.. figure:: howdy-email-gui-figures/newsletter_checkemail_ANNOTATED.png
   :width: 100%
   :align: left

   The full HTML Plex_ newsletter email that will go out, as shown in the ``HTML EMAIL BODY`` window.

Although the email is too long to fit into the ``HTML EMAIL BODY`` window and the ``RENDERED HTML`` tab, we first identify the ``Introduction`` section name for the ``PREAMBLE`` and the ``Final Thoughts`` section name for the ``POSTAMBLE``. The Plex_ server summary part, in the middle is structured as follows.

* ``SUMMARY`` is its title.

* There are subsections on the Plex_ server's music, movies, and television libraries collectively. For example, information on multiple music libraries are joined together.

* Each section shows the current status of media on that type of library, in total and those media added *after* the date of the previous newsletter.

Furthermore, to aid in debugging, you can click on the ``RESTRUCTURED TEXT`` tab in the ``HTML EMAIL BODY`` window to show the reStructuredText_ used to create this email. I have also included this :download:`example restructuredText newsletter </_static/howdy_email_gui_newsletter_restructuredtext.rst>` to inspect, and independently verify, that it creates proper HTML.

.. _newsletter_checkemail_restructuredtext_ANNOTATED:

.. figure:: howdy-email-gui-figures/newsletter_checkemail_restructuredtext_ANNOTATED.png
   :width: 100%
   :align: left

   To those who know it, the reStructuredText_ can be very helpful in figuring out why the HTML does not look as intended.

The movie below demonstrates the usually long process in in :ref:`checking that the newsletter email looks good <Checking Newsletter Email>`.

.. youtube:: AgTGYA-bfI0
   :width: 100%

Send Newsletter Email
----------------------
Once your email body is valid (it generated HTML), and you are satisfied, that you may want to send this email out to people who have access to your Plex_ server, then you click on the ``EMAIL DIALOG`` button to launch an email dialog. This dialog allows you to send the email only to yourself, to specific Plex_ friends, or to all your Plex_ friends and yourself.

.. _newsletter_sendemail_ANNOTATED:

.. figure:: howdy-email-gui-figures/newsletter_sendemail_ANNOTATED.png
   :width: 100%
   :align: left

   Clicking on ``EMAIL DIALOG`` launches the sending email dialog window. You can click on specific friends to toggle whether to send them a newsletter email. Clicking on the ``TEST EMAIL`` button selects only yourself (top row). Clicking on the ``ALL ADDRESSES`` button selects all your friends and yourself.

The email dialog window starts with yourself on the top row. Subsequent rows are your Plex_ friends.

Once you have made your selection, click on ``SEND EMAIL`` to send the Plex_ newsletter emails to your group of selected friends and/or yourself. Just as in :numref:`Send Email`, I alway verify that the email is valid, by first clicking ``TEST EMAIL`` and then clicking ``SEND EMAIL``, before sending the newsletter email to everyone.
  
.. |howdy_email_gui_icon| image:: howdy-email-gui-figures/howdy_email_gui_SQUARE_VECTA.svg
   :width: 50
   :align: middle

.. |howdy_email_gui| replace:: ``howdy_email_gui``

.. _Plex: https://plex.tv
.. _Imgur: https://imgur.com
.. _PNG: https://en.wikipedia.org/wiki/Portable_Network_Graphics
.. _LaTeX: https://en.wikipedia.org/wiki/LaTeX
.. _reStructuredText: https://en.wikipedia.org/wiki/ReStructuredText
.. _Sphinx: https://www.sphinx-doc.org/en/master
