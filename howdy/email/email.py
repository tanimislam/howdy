import os, sys, titlecase, datetime, re, time, requests, mimetypes, logging
import mutagen.mp3, mutagen.mp4, glob, multiprocessing, re, httplib2
from email.utils import formataddr
from docutils.examples import html_parts
from itertools import chain
from bs4 import BeautifulSoup
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.audio import MIMEAudio
from email.mime.image import MIMEImage
from jinja2 import Environment, FileSystemLoader, Template
#
from howdy import resourceDir
from howdy.core import session, core, get_lastupdated_string
from howdy.core import get_formatted_size, get_formatted_duration
from howdy.email import get_email_service, send_email_lowlevel, emailAddress, emailName
from ive_tanim.core.rst2html import send_email_localsmtp
#
def send_email_movie_torrent( movieName, data, isJackett = False, verify = True ):
    """
    Sends an individual torrent file or magnet link to the Plex_ user's email, using the `GMail API`_.

    :param str movieName: the name of the movie.
    :param str data: the Base64_ encoded file, if torrent file. Otherwise the magnet URI link if magnet link.
    :param bool isJackett: :py:class:`boolean <bool>` flag used to determine whether ``data`` is a torrent file or magnet link. If ``False``, then expects a torrent file. If ``True``, then expects a magnet link. Default is ``False``.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: the string ``"SUCCESS"`` if nothing goes wrong.
    :rtype: str
    
    :raise AssertionError: if the current Plex_ account user's email address does not exist.
    
    .. _`GMail API`: https://developers.google.com/gmail/api
    """
    assert( emailAddress is not None ), "Error, email address must not be None"
    if emailName is None:
        emailString = emailAddress
        name = 'Friend'
    else:
        emailString = '%s <%s>' % ( emailName, emailAddress )
        name = emailName.split( )[ 0 ].strip( )
    dtstring = datetime.datetime.now( ).strftime('%d %B %Y, %I:%M %p')
    msg = MIMEMultipart( )
    msg['From'] = emailString
    msg['To']  = emailString
    if emailName is not None:
        template = Template('{{ name }}, can you download this movie, {{ movieName }}, requested on {{ dtstring }}?' )
        msg[ 'Subject' ] = template.render( name = name, movieName = movieName, dtstring = dtstring )
    else:
        template = Template('Can you download this movie, {{ movieName }}, requested on {{ dtstring }}?' )
        msg[ 'Subject' ] = template.render( movieName = movieName, dtstring = dtstring )

    #
    ## JINJA load in the directory in which these templates live, http://zetcode.com/python/jinja/
    env = Environment( loader = FileSystemLoader( resourceDir ) )
    if not isJackett:
        torrent_data = data
        torfile = '%s.torrent' % '_'.join( movieName.split( ) ) # change to get to work
        torfile_mystr = '%s.torrent' % '_'.join( movieName.split( ) ) # change to get to work
        email_torrent = { 'name' : name, 'torfile_mystr' : torfile_mystr, 'dtstring' : dtstring }
        template = env.get_template( 'howdy_sendmovie_torrent.rst' )
        wholestr = template.render( email_torrent = email_torrent )
        #
        htmlString = core.rstToHTML( wholestr )
        body = MIMEText( htmlString, 'html', 'utf-8' )
        att = MIMEApplication( torrent_data, _subtype = 'torrent' )
        att.add_header(
            'content-disposition', 'attachment',
            filename = torfile )
        msg.attach( body )
        msg.attach( att )
    else:
        mag_link = data
        email_magnet = { 'name' : name, 'mag_link' : data, 'movieName' : movieName, 'dtstring' : dtstring }
        template = env.get_template(  'howdy_sendmovie_magnet.rst' )
        wholestr = template.render( email_magnet = email_magnet )
        #
        htmlString = core.rstToHTML( wholestr )
        body = MIMEText( htmlString, 'html', 'utf-8' )
        msg.attach( body )
    #
    ## now send the email
    send_email_lowlevel( msg, verify = verify )
    return 'SUCCESS'

def send_email_movie_none( movieName, verify = True ):
    """
    Request an individual movie from the Plex_ server's administrator, using the `GMail API`_.

    :param str movieName: the name of the movie.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: the string ``"SUCCESS"`` if nothing goes wrong.
    :rtype: str
    
    :raise AssertionError: if the current Plex_ account user's email address does not exist.
    """
    assert( emailAddress is not None ), "Error, email address must not be None"
    if emailName is None:
        emailString = emailAddress
        name = 'Friend'
    else:
        emailString = '%s <%s>' % ( emailName, emailAddress )
        name = emailName.split( )[ 0 ].strip( )
    dtstring = datetime.datetime.now( ).strftime('%d %B %Y, %I:%M %p')
    msg = MIMEMultipart( )
    msg['From'] = emailString
    msg['To']  = emailString
    if emailName is not None:
        template = Template('{{ name }}, can you download this movie, {{ movieName }}, requested on {{ dtstring }}?' )
        msg[ 'Subject' ] = template.render( name = name, movieName = movieName, dtstring = dtstring )
    else:
        template = Template('Can you download this movie, {{ movieName }}, requested on {{ dtstring }}?' )
        msg[ 'Subject' ] = template.render( movieName = movieName, dtstring = dtstring )
    #
    env = Environment( loader = FileSystemLoader( resourceDir ) )
    template = env.get_template( 'howdy_sendmovie_none.rst' )
    email_none = { 'name' : name, 'movieName' : movieName, 'dtstring' : dtstring }
    wholestr = template.render( email_none = email_none )
    #
    htmlString = core.rstToHTML( wholestr )
    body = MIMEText( htmlString, 'html', 'utf-8' )
    msg.attach( body )
    #
    send_email_lowlevel( msg, verify = verify )
    return 'SUCCESS'

def get_summary_body( token, nameSection = False, fullURL = 'http://localhost:32400', verify = True ):
    """
    Returns the summary body of the Plex_ newsletter email as a reStructuredText_ string document, for the Plex_ server.

    :param str token: the Plex_ access token.
    :param bool nameSection: if ``True``, then include this summary in its own section called ``"Summary"``. If not, then return as a stand-alone reStructuredText_ document.
    :param str fullURL: the Plex_ server URL.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: the reStructuredText_ document representing the summary of the media on the Plex_ server.
    :rtype: str

    .. seealso::
    
       * :py:meth:`get_summary_data_music_remote <howdy.email.email.get_summary_data_music_remote>`.
       * :py:meth:`get_summary_data_movies_remote <howdy.email.email.get_summary_data_movies_remote>`.
       * :py:meth:`get_summary_data_television_remote <howdy.email.email.get_summary_data_television_remote>`.

    .. _reStructuredText: https://en.wikipedia.org/wiki/ReStructuredText
    """
    tup_formatting = (
        get_lastupdated_string( dt = core.get_updated_at(
            token, fullURL = fullURL ) ), #0
        get_summary_data_music_remote( fullURL = fullURL, token = token ), #1
        _get_itemized_string( get_summary_data_movies_remote(
            fullURL = fullURL, token = token ) ), #2
        get_summary_data_television_remote( fullURL = fullURL, token = token ), #3
    )
    wholestr = open( os.path.join( resourceDir, 'howdy_body_template.rst' ), 'r' ).read( )
    wholestr = wholestr % tup_formatting
    if nameSection: wholestr = '\n'.join([ 'SUMMARY', '==========', wholestr ])
    return wholestr

def send_individual_email_perproc( input_tuple ):
    """
    A tuple-ized version of :py:meth:`send_individual_email <howdy.email.email.send_individual_email>` used by the :py:mod:`multiprocessing` module to send out emails.

    :param tuple input_tuple: an expected four-element :py:class:`tuple`: the HTML email body, the recipient's email, the recipient's name, and the :py:class:`email service resource <googleapiclient.discovery.Resource>`.

    .. seealso:: :py:meth:`send_individual_email <howdy.email.email.send_individual_email>`.
    """
    mainHTML, email, name, email_service = input_tuple
    while True:
        try:
            send_individual_email( mainHTML, email, name = name, email_service = email_service )
            return
        except Exception as e:
            if name is None:
                print('Problem sending to %s. Trying again...' % email)
            else:
                print('Problem sending to %s <%s>. Trying again...' % ( name, email ) )
    
def test_email( subject = None, htmlstring = None, verify = True ):
    """
    Sends a test email to the Plex_ user's email address.
    
    :param str subject: optional argument. The email subject. If not defined, the subject is ``"Plex Email Newsletter for <MONTH> <YEAR>"``.
    :param str htmlstring: optional argument. The email body as an HTML :py:class:`str` document. If not defined, the body is ``"This is a test."``.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    """
    assert( emailAddress is not None ), "Error, email address must not be None"
    if emailName is None: emailString = emailAddress
    else: emailString = '%s <%s>' % ( emailName, emailAddress )
    fromEmail = emailString
    if subject is None:
        subject = titlecase.titlecase( 'Plex Email Newsletter for %s' % mydate.strftime( '%B %Y' ) )
    msg = MIMEMultipart( )
    msg['From'] = fromEmail
    msg['Subject'] = subject
    msg['To'] = emailAddress
    if htmlstring is None: body = MIMEText( 'This is a test.' )
    else: body = MIMEText( htmlstring, 'html', 'utf-8' )
    msg.attach( body )
    send_email_lowlevel( msg, verify = verify )

def send_collective_email_full(
    mainHTML, subject, fromEmail, to_emails, cc_emails, bcc_emails, verify = True, email_service = None ):
    """
    Sends the HTML email to the following ``TO`` recipients, ``CC`` recipients, and ``BCC`` recipients altogether. It uses the `GMail API`_.

    :param str mainHTML: the email body as an HTML :py:class:`string <str>` document.
    :param str subject: the email subject.
    :param str fromEmail: the `RFC 2047`_ sender's email with name.
    :param set to_emails: the `RFC 2047`_ :py:class:`set` of ``TO`` recipients.
    :param set cc_emails: the `RFC 2047`_ :py:class:`set` of ``CC`` recipients.
    :param set bcc_emails: the `RFC 2047`_ :py:class:`set` of ``BCC`` recipients.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :param email_service: optional argument, the :py:class:`Resource <googleapiclient.discovery.Resource>` representing the Google email service used to send and receive emails. If ``None``, then generated here.

    .. _`RFC 2047`: https://tools.ietf.org/html/rfc2047.html
    """
    #
    ## get the RFC 2047 sender stuff
    eName = ''
    if emailName is not None: eName = emailName
    fromEmail = formataddr( ( eName, emailAddress ) )
    msg = MIMEMultipart( )
    msg[ 'From' ] = fromEmail
    msg[ 'Subject' ] = subject
    msg[ 'To' ] = ', '.join( sorted(to_emails ) )
    msg[ 'Cc' ] = ', '.join( sorted(cc_emails ) )
    msg[ 'Bcc'] = ', '.join( sorted(bcc_emails ) )
    logging.info( 'to_emails: %s.' % msg['To'] )
    logging.info( 'cc_emails: %s.' % msg['Cc'] )
    logging.info('bcc_emails: %s.' % msg['Bcc'])
    msg.attach( MIMEText( mainHTML, 'html', 'utf-8' ) )
    send_email_lowlevel( msg, email_service = email_service, verify = verify )

def send_individual_email_full(
    mainHTML, subject, emailAddress, name = None, attach = None,
    attachName = None, attachType = 'txt', verify = True, email_service = None ):
    """
    Sends the HTML email, with optional *single* attachment, to a single recipient email address, using the `GMail API`_. Unlike :py:meth:`send_individual_email_full_withsingleattach <howdy.email.email.send_individual_email_full_withsingleattach>`, the attachment type is *also* set.

    :param str mainHTML: the email body as an HTML :py:class:`str` document.
    :param str subject: the email subject.
    :param str emailAddress: the recipient email address.
    :param str name: optional argument. If given, the recipient's name.
    :param date mydate: optional argument. The :py:class:`date <datetime.date>` at which the email is sent. Default is :py:meth:`now( ) <datetime.datetime.now>`.
    :param str attach: optional argument. If defined, the Base64_ encoded attachment.
    :param str attachName: optional argument. The :py:class:`list` of attachment names, if there is an attachment. If defined, then ``attachData`` must also be defined.
    :param str attachType: the attachment type. Default is ``txt``.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :param email_service: optional argument, the :py:class:`Resource <googleapiclient.discovery.Resource>` representing the Google email service used to send and receive emails. If ``None``, then generated here.

    :raise AssertionError: if the current Plex_ account user's email address does not exist.
    """
    assert( emailAddress is not None ), "Error, email address must not be None"
    emailName = ''
    if name is not None: emailName = name
    fromEmail = formataddr( ( emailName, emailAddress ) )
    msg = MIMEMultipart( )
    msg['From'] = fromEmail
    msg['Subject'] = subject
    if name is None:
        msg['To'] = emailAddress
        htmlstring = mainHTML
    else:
        msg['To'] = formataddr( ( name, emailAddress ) )
        firstname = name.split()[0].strip()
        htmlstring = re.sub( 'Hello Friend,', 'Hello %s,' % firstname, mainHTML )
    body = MIMEText( htmlstring, 'html', 'utf-8' )
    msg.attach( body )
    if attach is not None and attachName is not None:
        att = MIMEApplication( attach, _subtype = 'text' )
        att.add_header( 'content-disposition', 'attachment', filename = attachName )
        msg.attach( att )
    send_email_lowlevel( msg, email_service = email_service, verify = verify )

def send_individual_email_full_withsingleattach(
        mainHTML, subject, email, name = None,
        attachData = None, attachName = None,
        verify = True, email_service = None ):
    """
    Sends the HTML email, with optional *single* attachment, to a single recipient email address, using the `GMail API`_.

    :param str mainHTML: the email body as an HTML :py:class:`str` document.
    :param str subject: the email subject.
    :param str email: the recipient email address.
    :param str name: optional argument. If given, the recipient's name.
    :param date mydate: optional argument. The :py:class:`date <datetime.date>` at which the email is sent. Default is :py:meth:`now( ) <datetime.datetime.now>`.
    :param str attachData: optional argument. If defined, the Base64_ encoded attachment.
    :param str attachName: optional argument. The :py:class:`list` of attachment names, if there is an attachment. If defined, then ``attachData`` must also be defined.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :param email_service: optional argument, the :py:class:`Resource <googleapiclient.discovery.Resource>` representing the Google email service used to send and receive emails. If ``None``, then generated here.

    :raise AssertionError: if the current Plex_ account user's email address does not exist.
    """
    assert( emailAddress is not None ), "Error, email address must not be None"
    if emailName is None: emailString = emailAddress
    else: emailString = '%s <%s>' % ( emailName, emailAddress )
    fromEmail = emailString
    msg = MIMEMultipart( )
    msg['From'] = fromEmail
    msg['Subject'] = subject
    if name is None:
        msg['To'] = email
        htmlstring = mainHTML
    else:
        msg['To'] = '%s <%s>' % ( name, email )
        firstname = name.split()[0].strip()
        htmlstring = re.sub( 'Hello Friend,', 'Hello %s,' % firstname, mainHTML )
    body = MIMEText( htmlstring, 'html', 'utf-8' )
    msg.attach( body )
    if attachData is not None:
        assert( attachName is not None )
        attachName = os.path.basename( attachName )
        content_type, encoding = mimetypes.guess_type(attachName)
        if content_type is None or encoding is not None:
            content_type = 'application/octet-stream'
        main_type, sub_type = content_type.split('/', 1)
        att = MIMEApplication( attachData, _subtype = sub_type )
        att.add_header( 'content-disposition', 'attachment', filename = attachName )
        msg.attach( att )
    send_email_lowlevel( msg, email_service = email_service, verify = verify )
        
def send_individual_email_full_withattachs(
        mainHTML, subject, email, name = None,
        attachNames = None, attachDatas = None ):
    """
    Sends the HTML email, with optional attachments, to a single recipient email address. This uses the :py:class:`SMTP <smtplib.SMTP>` Python functionality to send through a local SMTP_ server (see :py:meth:`send_email_localsmtp <howdy.email.send_email_localsmtp>`).

    :param str mainHTML: the email body as an HTML :py:class:`str` document.
    :param str subject: the email subject.
    :param str email: the recipient email address.
    :param str name: optional argument. If given, the recipient's name.
    :param date mydate: optional argument. The :py:class:`date <datetime.date>` at which the email is sent. Default is :py:meth:`now( ) <datetime.datetime.now>`.
    :param list attachNames: optional argument. The :py:class:`list` of attachment names, if attachments are used. If defined, then ``attachDatas`` must also be defined.
    :param list attachDatas: optional argument. If defined, the :py:class:`list` of attachments with corresponding name described in ``attachNames``. Each entry is a Base64_ encoded attachment.

    :raise AssertionError: if the current Plex_ account user's email address does not exist.

    .. _Base64: https://en.wikipedia.org/wiki/Base64
    """
    assert( emailAddress is not None ), "Error, email address must not be None"
    if emailName is None: fromEmail = emailAddress
    else: fromEmail = '%s <%s>' % ( emailName, emailAddress )
    msg = MIMEMultipart( )
    msg['From'] = fromEmail
    msg['Subject'] = subject
    if name is None:
        msg['To'] = email
        htmlstring = mainHTML
    else:
        msg['To'] = '%s <%s>' % ( name, email )
        firstname = name.split()[0].strip()
        htmlstring = re.sub( 'Hello Friend,', 'Hello %s,' % firstname, mainHTML )
    body = MIMEText( htmlstring, 'html', 'utf-8' )
    msg.attach( body )
    if attachNames is not None:
        assert( attachDatas is not None )
        for attachName, data in filter(None, zip( attachNames, attachDatas ) ):
            #
            ## gotten code from https://developers.google.com/gmail/api/guides/sending
            attachName = os.path.basename( attachName )
            content_type, encoding = mimetypes.guess_type(attachName)
            if content_type is None or encoding is not None:
                content_type = 'application/octet-stream'
            main_type, sub_type = content_type.split('/', 1)
            if main_type == 'text': att = MIMEText(data, _subtype=sub_type)
            elif main_type == 'image': att = MIMEImage(data, _subtype=sub_type)
            elif main_type == 'audio': att = MIMEAudio(data, _subtype=sub_type)
            else:
                att = MIMEBase(main_type, sub_type)
                att.set_payload(data)
            att.add_header( 'content-disposition', 'attachment', filename = attachName )
            msg.attach( att )
    #send_email_lowlevel( msg )
    send_email_localsmtp( msg ) # google has problems sending "big" emails (lots of attachments)

def send_individual_email(
        mainHTML, email, name = None,
        mydate = datetime.datetime.now().date( ),
        verify = True, email_service = None ):
    """
    sends the HTML email to a single recipient email address using the `GMail API`_. The subject is ``"Plex Email Newsletter for <MONTH> <YEAR>"``.

    :param str mainHTML: the email body as an HTML :py:class:`str` document.
    :param str email: the recipient email address.
    :param str name: optional argument. If given, the recipient's name.
    :param date mydate: optional argument. The :py:class:`date <datetime.date>` at which the email is sent. Default is :py:meth:`now( ) <datetime.datetime.now>`.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :param email_service: optional argument, the :py:class:`Resource <googleapiclient.discovery.Resource>` representing the Google email service used to send and receive emails. If ``None``, then generated here.

    :raise AssertionError: if the current Plex_ account user's email address does not exist.
    """
    assert( emailAddress is not None ), "Error, email address must not be None"
    if emailName is None: fromEmail = emailAddress
    else: fromEmail = '%s <%s>' % ( emailName, emailAddress )
    subject = titlecase.titlecase( 'Plex Email Newsletter For %s' % mydate.strftime( '%B %Y' ) )
    msg = MIMEMultipart( )
    msg['From'] = fromEmail
    msg['Subject'] = subject
    if name is None:
        msg['To'] = email
        htmlstring = mainHTML
    else:
        msg['To'] = '%s <%s>' % ( name, email )
        firstname = name.split()[0].strip()
        htmlstring = re.sub( 'Hello Friend,', 'Hello %s,' % firstname, mainHTML )
    #
    body = MIMEText( htmlstring, 'html', 'utf-8' )
    msg.attach( body )
    send_email_lowlevel( msg, email_service = email_service, verify = verify )

def get_summary_html(
    token, fullURL = 'http://localhost:32400',
    preambleText = '', postambleText = '', name = None ):
    """
    Creates a Plex_ newsletter summary HTML email of the media on the Plex_ server. Used by the email GUI to send out summary emails.
    
    :param str token: the Plex_ access token.
    :param str fullURL: the Plex_ server URL.
    :param str preambleText: optional argument. The reStructuredText_ formatted preamble text (text section *before* summary), if non-empty. Default is ``""``.
    :param str postambleText: optional argument. The reStructuredText_ formatted text, in a section *after* the summary. if non-empty. Default is ``""``.
    :param str name: optional argument. If given, the recipient's name.

    :returns: a two-element :py:class:`tuple`. The first element is an HTML :py:class:`string <str>` document of the Plex_ newletter email. The second element is the full reStructuredText_ :py:class:`string <str>`.
    :rtype: str
    
    .. seealso:: :py:meth:`get_summary_body <howdy.email.email.get_summary_body>`.

    .. _reStructuredText: https://en.wikipedia.org/wiki/ReStructuredText
    """
    nameSection = False
    if len(preambleText.strip( ) ) != 0: nameSection = True
    if name is None:
        name = 'Friend'
    tup_formatting = (
        name,
        preambleText,
        get_summary_body( token, nameSection = nameSection, fullURL = fullURL ),
        postambleText,
    )
    wholestr = open( os.path.join( resourceDir, 'howdy_template.rst' ), 'r' ).read( )
    wholestr = wholestr % tup_formatting
    htmlString = html_parts( wholestr )[ 'whole' ]
    html = BeautifulSoup( htmlString, 'lxml' )
    return html.prettify( ), wholestr

def _get_itemized_string( stringtup ):
    mainstring, maindict = stringtup
    stringelems = [ mainstring, '' ]
    for itm in sorted( maindict ):
        stringelems.append( '* **%s**: %s' % ( itm, maindict[itm] ) )
    stringelems.append('')
    return '\n'.join( stringelems )

def _get_artistalbum( filename ):
    if os.path.basename( filename ).endswith( '.m4a' ):
        mp4tag = mutagen.mp4.MP4( filename )
        if not all([ key in mp4tag for key in ( '\xa9alb', '\xa9ART' ) ]):
            return None
        album = max(mp4tag['\xa9alb']).strip()
        artist = max(mp4tag['\xa9ART']).strip()        
    elif os.path.basename( filename ).endswith( '.mp3' ):
        mp3tag = mutagen.mp3.MP3( filename )
        if not all ([ key in mp3tag for key in ( 'TPE1', 'TALB' )]):
            return None
        album = max(mp3tag['TALB'].text).strip( )
        artist = max(mp3tag['TPE1'].text).strip( )
    else:
        return None
    if len(album) == 0:
        return None
    if len(artist) == 0:
        return None
    return ( artist, album )

def _get_album_prifile( prifile ):
    if os.path.basename( prifile ).endswith( '.mp3' ):
        mp3tag = mutagen.mp3.MP3( prifile )
        if not all ([ key in mp3tag for key in ( 'TPE1', 'TALB' )]):
            return None
        album = max(mp3tag['TALB'].text).strip( )
        return ( prifile, album )
    elif os.path.basename( prifile ).endswith( '.m4a' ):
        mp4tag = mutagen.mp4.MP4( prifile )
        if '\xa9ART' not in mp4tag: return None
        album = max( mp4tag['\xa9ART'] ).strip( )
        return ( prifile, album )
    else: return None

def get_summary_data_music_remote(
    token, fullURL = 'http://localhost:32400',
    sinceDate = datetime.datetime.strptime('January 1, 2020', '%B %d, %Y' ).date( ) ):
    """
    This returns summary information on songs from all music libraries on the Plex_ server, for use as part of the Plex_ newsletter sent out to one's Plex_ server friends. The email first summarizes ALL the music data, and then summarizes the music data uploaded and processed since a previous date. For example,
    
       As of December 29, 2020, there are 17,853 songs made by 889 artists in 1,764 albums. The total size of music media is 306.979 GB. The total duration of music media is 7 months, 18 days, 15 hours, 8 minutes, and 15.785 seconds.

       Since January 01, 2020, I have added 7,117 songs made by 700 artists in 1,180 albums. The total size of music media that I have added is 48.167 GB. The total duration of music media that I have added is 28 days, 15 hours, 25 minutes, and 37.580 seconds.
    
    :param str token: the Plex_ access token.
    :param str fullURL: the Plex_ server URL.
    :param date sinceDate: the :py:class:`datetime <datetime.date>` from which we have added songs. Default is :py:class:`date <datetime.date>` corresponding to ``January 1, 2020``.
    
    :returns: a :py:class:`string <str>` description of music media in all music libraries on the Plex_ server. If there is no Plex_ server or music library, returns ``None``.
    :rtype: str

    .. seealso:: :py:meth:`get_summary_body <howdy.email.email.get_summary_body>`.
    """
    libraries_dict = core.get_libraries( token, fullURL = fullURL, do_full = True )
    if libraries_dict is None: return None
    keynums = set(filter(lambda keynum: libraries_dict[ keynum ][ 1 ] == 'artist', libraries_dict ) )
    if len( keynums ) == 0: return None
    # sinceDate = core.get_current_date_newsletter( )
    datas = list(map(lambda keynum: core.get_library_stats( keynum, token, fullURL = fullURL ), keynums))
    music_summ = {
        'current_date_string' : datetime.datetime.now( ).date( ).strftime( '%B %d, %Y' ),
        'num_songs' : f'{sum(list(map(lambda data: data[ "num_songs" ], datas))):,}',
        'num_artists' : f'{sum(list(map(lambda data: data[ "num_artists" ], datas))):,}',
        'num_albums' : f'{sum(list(map(lambda data: data[ "num_albums" ], datas))):,}',
        'formatted_size' : get_formatted_size(sum(list(map(lambda data: data[ 'totsize' ], datas)))),
        'formatted_duration' : get_formatted_duration(sum(list(map(lambda data: data[ 'totdur' ], datas)))) }
    #
    ## now since sinceDate
    datas_since = list(filter(
        lambda data_since: data_since[ 'num_songs' ] > 0,
        map(lambda keynum: core.get_library_stats(
            keynum, token, fullURL = fullURL, sinceDate = sinceDate ), keynums ) ) )
    music_summ[ 'len_datas_since' ] = len( datas_since )
    if len( datas_since ) > 0:
        music_summ[ 'since_date_string' ] = sinceDate.strftime( '%B %d, %Y' )
        music_summ[ 'num_songs_since' ] = f'{sum(list(map(lambda data_since: data_since[ "num_songs" ], datas_since))):,}'
        music_summ[ 'num_artists_since' ] = f'{sum(list(map(lambda data_since: data_since[ "num_artists" ], datas_since))):,}'
        music_summ[ 'num_albums_since' ] = f'{sum(list(map(lambda data_since: data_since[ "num_albums" ], datas_since))):,}'
        music_summ[ 'formatted_size_since' ] = get_formatted_size( sum(list(map(lambda data_since: data_since[ 'totsize'], datas_since))))
        music_summ[ 'formatted_duration_since' ] = get_formatted_duration( sum(list(map(lambda data_since: data_since[ 'totdur' ], datas_since))) )
    #
    env = Environment( loader = FileSystemLoader( resourceDir ) )
    template = env.get_template( 'summary_data_music_template.rst' )
    musicstring = template.render( music_summ = music_summ )
    return musicstring

def get_summary_data_television_remote(
    token, fullURL = 'http://localhost:32400',
    sinceDate = datetime.datetime.strptime('January 1, 2020', '%B %d, %Y' ).date( ) ):
    """
    This returns summary information on TV media from all television libraries on the Plex_ server, for use as part of the Plex_ newsletter sent out to one's Plex_ server friends. The email first summarizes ALL the TV data, and then summarizes the TV data uploaded and processed since a previous date. For example,

       As of December 29, 2020, there are 25,195 TV episodes in 298 TV shows. The total size of TV media is 6.690 TB. The total duration of TV media is 1 year, 5 months, 19 days, 9 hours, 29 minutes, and 13.919 seconds.

       Since January 01, 2020, I have added 5,005 TV epsisodes in 298 TV shows. The total size of TV media that I have added is 1.571 TB. The total duration of TV media that I have added is 3 months, 16 days, 4 hours, 52 minutes, and 15.406 seconds.

    :param str token: the Plex_ access token.
    :param str fullURL: the Plex_ server URL.
    :param date sinceDate: the :py:class:`datetime <datetime.date>` from which we have added songs. Default is :py:class:`date <datetime.date>` corresponding to ``January 1, 2020``.
    
    :returns: a :py:class:`string <str>` description of TV media in all TV libraries on the Plex_ server. If there is no Plex_ server or TV library, returns ``None``.
    :rtype: str

    .. seealso:: :py:meth:`get_summary_body <howdy.email.email.get_summary_body>`.
    """
    libraries_dict = core.get_libraries( token, fullURL = fullURL, do_full = True )
    if libraries_dict is None: return None
    keynums = set(filter(lambda keynum: libraries_dict[ keynum ][ 1 ] == 'show', libraries_dict ) )
    if len( keynums ) == 0: return None
    #
    # sinceDate = core.get_current_date_newsletter( )
    datas = list(map(lambda keynum: core.get_library_stats( keynum, token, fullURL = fullURL ), keynums))
    tv_summ = {
        'current_date_string' : datetime.datetime.now( ).date( ).strftime( '%B %d, %Y' ),
        'num_episodes' : f'{sum(list(map(lambda data: data[ "num_tveps" ], datas))):,}',
        'num_shows' : f'{sum(list(map(lambda data: data[ "num_tvshows" ], datas))):,}',
        'formatted_size' : get_formatted_size(sum(list(map(lambda data: data[ 'totsize' ], datas)))),
        'formatted_duration' : get_formatted_duration(sum(list(map(lambda data: data[ 'totdur' ], datas)))) }
    datas_since = list(filter(
        lambda data_since: data_since[ 'num_tveps' ] > 0,
        map(lambda keynum: core.get_library_stats(
            keynum, token, fullURL = fullURL, sinceDate = sinceDate ), keynums) ) )
    tv_summ[ 'len_datas_since' ] = len( datas_since )
    if len( datas_since ) > 0:
        tv_summ[ 'since_date_string' ] = sinceDate.strftime( '%B %d, %Y' )
        tv_summ[ 'num_episodes_since' ] = f'{sum(list(map(lambda data_since: data_since[ "num_tveps" ], datas_since))):,}'
        tv_summ[ 'num_shows_since' ] = f'{sum(list(map(lambda data_since: data_since[ "num_tvshows" ], datas_since))):,}'
        tv_summ[ 'formatted_size_since' ] = get_formatted_size( sum(list(map(lambda data_since: data_since[ 'totsize'], datas_since))))
        tv_summ[ 'formatted_duration_since' ] = get_formatted_duration( sum(list(map(lambda data_since: data_since[ 'totdur' ], datas_since))) )
    env = Environment( loader = FileSystemLoader( resourceDir ) )
    template = env.get_template( 'summary_data_tv_template.rst' )
    tvstring = template.render( tv_summ = tv_summ )
    return tvstring

def get_summary_data_movies_remote(
    token, fullURL = 'http://localhost:32400',
    sinceDate = datetime.datetime.strptime('January 1, 2020', '%B %d, %Y' ).date( ) ):
    """
    This returns summary information on movie media from all movie libraries on the Plex_ server, for use as part of the Plex_ newsletter sent out to one's Plex_ server friends. The email first summarizes ALL the movie data, and then summarizes the movie data uploaded and processed since the last newsletter's date. Unlike :py:meth:`get_summary_data_music_remote <howdy.email.email.get_summary_data_music_remote>` and :py:meth:`get_summary_data_television_remote <howdy.email.email.get_summary_data_television_remote>`, this returns a :py:class:`list` of strings rather than a string.

    :param str token: the Plex_ access token.
    :param str fullURL: the Plex_ server URL.
    
    :returns: a :py:class:`string <str>` description of TV media in all TV libraries on the Plex_ server. If there is no Plex_ server or TV library, returns ``None``.
    :rtype: list

    .. seealso:: :py:meth:`get_summary_body <howdy.email.email.get_summary_body>`.
    """
    libraries_dict = core.get_libraries( token, fullURL = fullURL, do_full = True )
    if libraries_dict is None:
        return None
    keynums = set(filter(lambda keynum: libraries_dict[ keynum ][ 1 ] == 'movie', libraries_dict ) )
    if len( keynums ) == 0:
        return None
    #
    # sinceDate = core.get_current_date_newsletter( )
    #
    ## hard coding (for now) how to join by genres
    join_genres = { 'action' : [ 'thriller', 'western' ], 'comedy' : [ 'family', ], 'drama' : [ 'drame', ] }
    def _join_by_genre( sort_by_genre, join_genres ):
        alljoins = list(chain.from_iterable(map(lambda genre: join_genres[ genre ], join_genres ) ) )
        assert( len( alljoins ) == len( set( alljoins ) ) )
        assert( len( set( alljoins ) & set( join_genres ) ) == 0 )
        for genre in join_genres:
            g2s = set( join_genres[ genre ] ) & set( sort_by_genre )
            if len( g2s ) == 0: continue
            if genre not in sort_by_genre:
                sort_by_genre[ genre ][ 'totnum' ] = 0
                sort_by_genre[ genre ][ 'totdur' ] = 0.0
                sort_by_genre[ genre ][ 'totsize' ] = 0.0
            for g2 in g2s:
                sort_by_genre[ genre ][ 'totnum' ] += sort_by_genre[ g2 ][ 'totnum' ]
                sort_by_genre[ genre ][ 'totdur' ] += sort_by_genre[ g2 ][ 'totdur' ]
                sort_by_genre[ genre ][ 'totsize' ] += sort_by_genre[ g2 ][ 'totsize' ]
            for g2 in g2s:
                sort_by_genre.pop( g2 )
    #
    current_date_string = datetime.datetime.now( ).date( ).strftime( '%B %d, %Y' )
    datas = list(map(lambda keynum: core.get_library_stats( keynum, token, fullURL = fullURL ), keynums ) )
    num_movies_since = -1
    sorted_by_genres = { }
    sorted_by_genres_since = { }
    for data in datas:
        data_sorted_by_genre = data[ 'genres' ]
        for genre in data_sorted_by_genre:
            if genre not in sorted_by_genres:
                sorted_by_genres[ genre ] = data_sorted_by_genre[ genre ].copy( )
                continue
            sorted_by_genres[ genre ][ 'totum'  ] += data_sorted_by_genre[ genre ][ 'totnum'  ]
            sorted_by_genres[ genre ][ 'totdur' ] += data_sorted_by_genre[ genre ][ 'totdur'  ]
            sorted_by_genres[ genre ][ 'totsize'] += data_sorted_by_genre[ genre ][ 'totsize' ]
    _join_by_genre( sorted_by_genres, join_genres )
    categories = set( sorted_by_genres )
    num_movies = f'{sum(list(map(lambda data: data[ "num_movies" ], datas ) ) ):,}'
    totdur = get_formatted_duration( sum(list(map(lambda data: data[ 'totdur' ], datas ) ) ) )
    totsize = get_formatted_size( sum(list(map(lambda data: data[ 'totsize' ], datas ) ) ) )
    movie_summ = {
        'current_date_string' : current_date_string,
        'num_movies' : num_movies,
        'num_categories' : len( categories ),
        'formatted_size' : totsize,
        'formatted_duration' : totdur }
    #
    datas_since = list(filter(
        lambda data_since: data_since[ 'num_movies' ] > 0,
        map(lambda keynum: core.get_library_stats(
            keynum, token, fullURL = fullURL, sinceDate = sinceDate ), keynums ) ) )
    movie_summ[ 'len_datas_since' ] = len( datas_since )
    if len( datas_since ) != 0:
        for data_since in datas_since:
            data_since_sorted_by_genre = data_since[ 'genres' ]
            for genre in data_since_sorted_by_genre:
                if genre not in sorted_by_genres_since:
                    sorted_by_genres_since[ genre ] = data_since_sorted_by_genre[ genre ].copy( )
                    continue
                sorted_by_genres_since[ genre ][ 'totum'  ] += data_since_sorted_by_genre[ genre ][ 'totnum'  ]
                sorted_by_genres_since[ genre ][ 'totdur' ] += data_since_sorted_by_genre[ genre ][ 'totdur'  ]
                sorted_by_genres_since[ genre ][ 'totsize'] += data_since_sorted_by_genre[ genre ][ 'totsize' ]
        _join_by_genre( sorted_by_genres_since, join_genres )
        num_movies_since = f'{sum(list(map(lambda data_since: data_since[ "num_movies" ], datas_since ) ) ):,}'
        categories_since = set( sorted_by_genres_since )
        totsize_since = get_formatted_size( sum(list(map(lambda data_since: data_since[ 'totsize' ], datas_since ) ) ) )
        totdur_since = get_formatted_duration( sum(list(map(lambda data_since: data_since[ 'totdur' ], datas_since ) ) ) )
        movie_summ[ 'since_date_string' ] = sinceDate.strftime( '%B %d, %Y' )
        movie_summ[ 'num_movies_since' ] = num_movies_since
        movie_summ[ 'num_categories_since' ] = len( categories_since )
        movie_summ[ 'formatted_size_since' ] = totsize_since
        movie_summ[ 'formatted_duration_since' ] =  totdur_since
        
    #
    ## get last 7 movies that I have added, to pass to JINJA template
    lastN_movies = core.get_lastN_movies( 7, token, fullURL = fullURL, useLastNewsletterDate = False )
    last_N_movies = [ ]
    def _get_nth_movie( lastN_entry ):
        title, year, date, url = lastN_entry
        if url is None:
            return {
                'hasURL' : False,
                'name' : title,
                'year' : year,
                'added_date_string' : date.strftime( '%B %d, %Y' ),
                'url' : '' }
        return {
            'hasURL' : True,
            'name' : title,
            'year' : year,
            'added_date_string' : date.strftime( '%B %d, %Y' ),
            'url' : url }
    last_N_movies = list(map(_get_nth_movie, lastN_movies ) )
    #
    ## catmovstrings list to pass to JINJA template
    template_mainstring = Template(' '.join([
        'As of ``{{ current_date_string }}``, there are {{ num_movies }} movies in this category.',
        'The total size of movie media here is {{ totsize }}.',
        'The total duration of movie media here is {{ totdur }}.' ]) )
    template_sincestring = Template(' '.join([
        'Since ``{{ since_date_string }}``, I have added {{ num_movies_since }} movies in this category.',
        'The total size of movie media I added here is {{ totsize_since }}.',
        'The total duration of movie media I added here is {{ totdur_since }}.' ] ) )
    def _get_category_entry( cat ):
        mainstring = template_mainstring.render(
            current_date_string = current_date_string,
            num_movies = f'{sorted_by_genres[ cat ][ "totnum" ]:,}',
            totsize = get_formatted_size( sorted_by_genres[ cat ][ 'totsize' ] ),
            totdur = get_formatted_duration( sorted_by_genres[ cat ][ 'totdur' ] ) )
        if cat in sorted_by_genres_since and sorted_by_genres_since[ cat ][ 'totnum' ] > 0:
            num_movies_since = f'{sorted_by_genres_since[ cat ][ "totnum" ]:,}'
            totsize_since    = get_formatted_size( sorted_by_genres_since[ cat ][ 'totsize' ] )
            totdur_since     = get_formatted_duration( sorted_by_genres_since[ cat ][ 'totdur'  ] )
            mainstring_since = template_sincestring.render(
                since_date_string = sinceDate.strftime( '%B %d, %Y' ),
                num_movies_since = num_movies_since,
                totsize_since = totsize_since,
                totdur_since = totdur_since )
            description = ' '.join([ mainstring, mainstring_since ])
            return { 'category' : cat, 'description' : description }
        return { 'category' : cat, 'description' : mainstring }
    catmovs = list(map(_get_category_entry, sorted( sorted_by_genres ) ) )
    env = Environment( loader = FileSystemLoader( resourceDir ) )
    template = env.get_template( 'summary_data_movie_template.rst' )
    movstring = template.render( movie_summ = movie_summ, last_N_movies = last_N_movies, catmovs = catmovs )
    return movstring
