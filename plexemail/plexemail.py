import os, sys, titlecase, datetime, re, urllib, time, requests
import mutagen.mp3, mutagen.mp4, glob, multiprocessing, lxml.html
import oauth2client.file, httplib2
import smtplib, re, urllib, base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from plexcore import session, plexcore

def send_email_movie_torrent( movieName, data, isKickass = False):
    dtstring = datetime.datetime.now( ).strftime('%d %B %Y, %I:%M %p')
    msg = MIMEMultipart( )
    msg['From'] = 'Tanim Islam <***REMOVED***.islam@gmail.com>'
    msg['To']  = 'Tanim Islam <***REMOVED***.islam@gmail.com>'
    msg['Subject'] = 'Tanim, can you download this movie, %s, requested on %s?' % (
        movieName, dtstring )
    if not isKickass:
        torfile = '%s.torrent' % '_'.join( movieName.split( ) ) 
        tup_formatting = ( '%s.' % torfile, '%s.' % dtstring )                           
        wholestr = open( os.path.join( mainDir, 'resources',
                                       'plextmdb_sendmovie_torrent.tex' ), 'r' ).read( )
        wholestr = wholestr % tup_formatting
        htmlString = plexcore.latexToHTML( wholestr )
        htmlString = unicode( htmlString.replace('strong>', 'B>') )
        body = MIMEText( htmlString, 'html', 'utf-8' )
        att = MIMEApplication( data, _subtype = 'torrent' )
        att.add_header( 'content-disposition', 'attachment', filename = torfile )
        msg.attach( body )
        msg.attach( att )
    else:
        tree = lxml.html.fromstring( requests.get( data ).content )
        mag_elems = filter(lambda elem: 'href' in elem.keys() and
                           elem.get('href').startswith('magnet:'),
                           tree.iter('a'))
        if len(mag_elems) == 0:
            return 'FALURE, COULD FIND NO MAGNET LINKS FOR %s.' % movieName
        mag_link = mag_elems[0].get('href').strip()
        wholestr = open( os.path.join( mainDir, 'resources',
                                       'plextmdb_sendmovie_magnet.tex' ), 'r' ).read( )
        wholestr = wholestr.replace('ZZZZ', dtstring )
        htmlString = plexcore.latexToHTML( wholestr )
        htmlString = htmlString.replace('XXXX', mag_link )
        htmlString = htmlString.replace('YYYY', movieName )
        htmlString = unicode( htmlString.replace('strong>', 'B>') )
        body = MIMEText( htmlString, 'html', 'utf-8' )
        msg.attach( body )
        
    #
    access_token = plexcore.oauth_get_access_token( )
    auth_string = 'user=%s\1auth=Bearer %s\1\1' % (
        '***REMOVED***.islam@gmail.com', access_token)
    auth_string = base64.b64encode( auth_string )
    smtp_conn = smtplib.SMTP('smtp.gmail.com', 587)
    smtp_conn.ehlo( 'test' )
    smtp_conn.starttls( )
    smtp_conn.docmd( 'AUTH', 'XOAUTH2 ' + auth_string )
    smtp_conn.sendmail( msg['From'], [ msg['To'], ], msg.as_string( ) )
    smtp_conn.quit( )
    return 'SUCCESS'

def send_email_movie_none( movieName ):
    dtstring = datetime.datetime.now( ).strftime('%d %B %Y, %I:%M %p')
    msg = MIMEMultipart( )
    msg['From'] = 'Tanim Islam <***REMOVED***.islam@gmail.com>'
    msg['To']  = 'Tanim Islam <***REMOVED***.islam@gmail.com>'
    msg['Subject'] = 'Tanim, can you download this movie, %s, requested on %s?' % (
        movieName, dtstring )
    #
    wholestr = open( os.path.join( mainDir, 'resources',
                                   'plextmdb_sendmovie_none.tex' ), 'r' ).read( )
    wholestr = wholestr.replace('XXXX', movieName )
    wholestr = wholestr.replace('YYYY', dtstring )
    htmlString = plexcore.latexToHTML( wholestr )
    htmlString = unicode( htmlString.replace('strong>', 'B>') )
    body = MIMEText( htmlString, 'html', 'utf-8' )
    msg.attach( body )
    #
    access_token = plexcore.oauth_get_access_token( )
    auth_string = 'user=%s\1auth=Bearer %s\1\1' % (
        '***REMOVED***.islam@gmail.com', access_token)
    auth_string = base64.b64encode( auth_string )
    smtp_conn = smtplib.SMTP('smtp.gmail.com', 587)
    smtp_conn.ehlo( 'test' )
    smtp_conn.starttls( )
    smtp_conn.docmd( 'AUTH', 'XOAUTH2 ' + auth_string )
    smtp_conn.sendmail( msg['From'], [ msg['To'], ], msg.as_string( ) )
    smtp_conn.quit( )
    return 'SUCCESS'

def set_date_newsletter( ):
    query = session.query( plexcore.LastNewsletterDate )
    backthen = datetime.datetime.strptime( '1900-01-01', '%Y-%m-%d' ).date( )
    val = query.filter( plexcore.LastNewsletterDate.date >= backthen ).first( )
    if val:
        session.delete( val )
        session.commit( )
    datenow = datetime.datetime.now( ).date( )
    lastnewsletterdate = plexcore.LastNewsletterDate( date = datenow )
    session.add( lastnewsletterdate )
    session.commit( )
        
def get_email_contacts_dict( emailList ):
    import gdata.contacts, gdata.contacts.client
    token = plexcore.oauth_get_contact_access_token( )
    if token is None: return None
    gd_client = gdata.contacts.client.ContactsClient( source = '***REMOVED***-islam-cloud-storage-2' )
    gd_client.auth_token = token
    #
    ## copy nprstuff/oldstuff/google_pull_contacts.py#GoogleContactsSimple
    query = gdata.contacts.client.ContactsQuery( )
    query.max_results = 50000
    contacts = gd_client.GetContacts( q = query )
    contacts_dict = { entry.title.text : entry for entry in contacts.entry }
    contacts_val = filter(lambda name: len(contacts_dict[name].email) > 0, contacts_dict )
    emails_dict = { name : sorted(set([ eml.address.lower() for eml in contacts_dict[name].email ])) for
                    name in contacts_val }
    #
    emails_dict_rev = {}
    for contact in emails_dict:
        for email in emails_dict[contact]:
            emails_dict_rev[ email ] = contact
    emails_array = []
    for email in emailList:
        if email in emails_dict_rev:
            emails_array.append((emails_dict_rev[ email ], email) )
        else:
            emails_array.append( (None, email) )
    return emails_array

def get_summary_body( token, nameSection = False, fullURL = 'http://localhost:32400' ):
    # allrows = plexcore.get_allrows( )
    tup_formatting = (
        plexcore.get_lastupdated_string( dt = plexcore.get_updated_at( token,
            fullURLWithPort = fullURL ) ), #0
        get_summary_data_freshair_remote( fullURLWithPort = fullURL, token = token ), #1
        _get_itemized_string( get_summary_data_thisamericanlife_remote( fullURLWithPort = fullURL,
                                                                        token = token ) ), #2
        get_summary_data_music_remote( fullURLWithPort = fullURL, token = token ), #3
        _get_itemized_string( get_summary_data_movies_remote( fullURLWithPort = fullURL, token = token ) ), #4
        get_summary_data_television_remote( fullURLWithPort = fullURL, token = token ), #5
    )
    wholestr = open( os.path.join( mainDir, 'resources', 'plexstuff_body_template.tex' ), 'r' ).read( )
    wholestr = wholestr % tup_formatting
    if nameSection:
        wholestr = '\n'.join([ '\section{Summary}', wholestr ])
    return wholestr

def send_individual_email_perproc( input_tuple ):
    mainHTML, access_token, email, name = input_tuple
    while True:
        try:
            send_individual_email( mainHTML, access_token, email, name = name )
            return
        except Exception as e:
            if name is None:
                print('Problem sending to %s. Trying again...' % email)
            else:
                print('Problem sending to %s <%s>. Trying again...' % ( name, email ) )
                
def test_email( ):
    mydate = datetime.datetime.now( ).date( )
    fromEmail = 'Tanim Islam <***REMOVED***.islam@gmail.com>'
    subject = titlecase.titlecase( 'Plex Email Newsletter For %s' % mydate.strftime( '%B %Y' ) )
    msg = MIMEMultipart( )
    msg['From'] = fromEmail
    msg['Subject'] = subject
    msg['To'] = '***REMOVED***.islam@gmail.com'
    body = MIMEText( 'This is a test.' )
    msg.attach( body )
    #    
    access_token = plexcore.oauth_get_access_token( )
    #
    auth_string = 'user=%s\1auth=Bearer %s\1\1' % (
        '***REMOVED***.islam@gmail.com', access_token)
    auth_string = base64.b64encode( auth_string )
    smtp_conn = smtplib.SMTP('smtp.gmail.com', 587)
    smtp_conn.ehlo( 'test' )
    smtp_conn.starttls( )
    smtp_conn.docmd( 'AUTH', 'XOAUTH2 ' + auth_string )
    smtp_conn.sendmail( fromEmail, [ msg['To'], ], msg.as_string( ) )
    smtp_conn.quit( )

def test_email_full( subject, htmlstring ):
    fromEmail = 'Tanim Islam <***REMOVED***.islam@gmail.com>'
    # subject = titlecase.titlecase( 'Plex Email Newsletter For %s' % mydate.strftime( '%B %Y' ) )
    msg = MIMEMultipart( )
    msg['From'] = fromEmail
    msg['Subject'] = subject
    msg['To'] = '***REMOVED***.islam@gmail.com'
    body = MIMEText( htmlstring, 'html', 'utf-8' )
    msg.attach( body )
    #
    access_token = plexcore.oauth_get_access_token( )
    #
    auth_string = 'user=%s\1auth=Bearer %s\1\1' % (
        '***REMOVED***.islam@gmail.com', access_token)
    auth_string = base64.b64encode( auth_string )
    smtp_conn = smtplib.SMTP('smtp.gmail.com', 587)
    smtp_conn.ehlo( 'test' )
    smtp_conn.starttls( )
    smtp_conn.docmd( 'AUTH', 'XOAUTH2 ' + auth_string )
    smtp_conn.sendmail( fromEmail, [ msg['To'], ], msg.as_string( ) )
    smtp_conn.quit( )

def send_individual_email_full( mainHTML, subject, access_token, email, name = None):
    fromEmail = 'Tanim Islam <***REMOVED***.islam@gmail.com>'
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
    #
    auth_string = 'user=%s\1auth=Bearer %s\1\1' % (
        '***REMOVED***.islam@gmail.com', access_token)
    auth_string = base64.b64encode( auth_string )
    smtp_conn = smtplib.SMTP('smtp.gmail.com', 587)
    smtp_conn.ehlo( 'test' )
    smtp_conn.starttls( )
    smtp_conn.docmd( 'AUTH', 'XOAUTH2 ' + auth_string )
    smtp_conn.sendmail( fromEmail, [ msg['To'], ], msg.as_string( ) )
    smtp_conn.quit( )

def send_individual_email( mainHTML, access_token, email,
                           name = None, mydate = datetime.datetime.now().date() ):
    fromEmail = 'Tanim Islam <***REMOVED***.islam@gmail.com>'
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
    #
    auth_string = 'user=%s\1auth=Bearer %s\1\1' % (
        '***REMOVED***.islam@gmail.com', access_token)
    auth_string = base64.b64encode( auth_string )
    smtp_conn = smtplib.SMTP('smtp.gmail.com', 587)
    smtp_conn.ehlo( 'test' )
    smtp_conn.starttls( )
    smtp_conn.docmd( 'AUTH', 'XOAUTH2 ' + auth_string )
    smtp_conn.sendmail( fromEmail, [ msg['To'], ], msg.as_string( ) )
    smtp_conn.quit( )

def get_summary_html( preambleText = '', postambleText = '', pngDataDict = { },
                      name = None, token = None, doLocal = True ):
    data = plexcore.checkServerCredentials( doLocal = doLocal )
    if data is None:
        print('Sorry, now we need to provide an user name and password. Please get one!')
        return
    fullURL, token = data
    nameSection = False
    if len(preambleText.strip()) != 0:
        nameSection = True
    if name is None:
        name = 'Friend'
    tup_formatting = (
        name,
        preambleText,
        get_summary_body( token, nameSection = nameSection, fullURL = fullURL ),
        postambleText,
    )
    wholestr = open( os.path.join( mainDir, 'resources', 'plexstuff_template.tex' ), 'r' ).read( )
    wholestr = wholestr % tup_formatting
    wholestr = wholestr.replace('textbf|', 'textbf{')
    wholestr = wholestr.replace('ZZX|', '}')
    htmlString = plexcore.latexToHTML( wholestr )
    htmlString = htmlString.replace('strong>', 'B>')
    #
    ## now process PNG IMG data
    htmlString = plexcore.processValidHTMLWithPNG( htmlString, pngDataDict )
    return htmlString

def _get_itemized_string( stringtup ):
    mainstring, maindict = stringtup
    stringelems = [ mainstring, '\\begin{itemize}' ]
    for itm in sorted( maindict ):
        stringelems.append( '\item \\textbf|%sZZX|: %s' % ( itm, maindict[itm] ) )
    stringelems.append('\\end{itemize}')
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

def get_summary_data_freshair_remote( token, fullURLWithPort = 'http://localhost:32400' ):
    libraries_dict = plexcore.get_libraries( token = token, fullURL = fullURLWithPort )
    keynum = max([ key for key in libraries_dict if libraries_dict[key] == 'NPR Fresh Air' ])
    sinceDate = plexcore.get_current_date_newsletter( )
    key, num_songs, _, _, totdur, totsizebytes = plexcore._get_library_stats_artist( keynum, token, fullURL = fullURLWithPort )
    mainstring = 'There are %d episodes of NPR Fresh Air.'  % num_songs
    sizestring = 'The total size of Fresh Air media is %s.' % \
                 get_formatted_size( totsizebytes )
    durstring = 'The total duration of Fresh Air media is %s.' % \
                get_formatted_duration( totdur )
    if sinceDate is not None:
        key, num_songs_since, _, _, \
            totdur_since, totsizebytes_since = plexcore._get_library_stats_artist( keynum, token, fullURL = fullURLWithPort,
                                                                                   sinceDate = sinceDate )
        if num_songs_since > 0:
            mainstring_since = ' '.join([ 'Since %s, I have added %d new Fresh Air episodes.' %
                                          ( sinceDate.strftime('%B %d, %Y'), num_songs_since ),
                                          'The total size of Fresh Air media I have added is %s.' %
                                          get_formatted_size( totsizebytes_since ),
                                          'The total duration of Fresh Air media I have added is %s.' %
                                          get_formatted_duration( totdur_since ) ] )
            return ' '.join([ mainstring, sizestring, durstring, mainstring_since ])
    return ' '.join([ mainstring, sizestring, durstring ])

def get_summary_data_freshair( allrows ):
    freshair_rows = list(filter(lambda row: '/mnt/media/freshair' in row[5] and
                                row[7] is not None and row[8] is not None, allrows ) )
    totdur = 1e-3 * sum([ row[8] for row in freshair_rows ])
    totsizebytes = sum([ row[7] for row in freshair_rows ])
    mainstring = 'There are %d episodes of NPR Fresh Air.' % len(freshair_rows)
    sizestring = 'The total size of Fresh Air media is %s.' % \
                 get_formatted_size( totsizebytes )
    durstring = 'The total duration of Fresh Air media is %s.' % \
                get_formatted_duration( totdur )
    return ' '.join([ mainstring, sizestring, durstring ])

def get_summary_data_thisamericanlife_remote( token, fullURLWithPort = 'http://localhost:32400' ):
    libraries_dict = plexcore.get_libraries( token = token, fullURL = fullURLWithPort )
    keynum = max([ key for key in libraries_dict if libraries_dict[key] == 'This American Life' ])
    sinceDate = plexcore.get_current_date_newsletter( )
    key, song_data = plexcore._get_library_data_artist( keynum, token, fullURL = fullURLWithPort )
    num_episodes = 0
    totdur = 0.0
    totsizebytes = 0.0
    for key in song_data:
        for key2 in song_data[key]:
            num_episodes += len( song_data[ key ][ key2 ] )
            for track in song_data[ key ][ key2 ]:
                name, dt, dur, sizebytes = track
                totdur += dur
                totsizebytes += sizebytes
    mainstring = 'There are %d episodes in %d series in This American Life.' % (
        num_episodes, len( song_data ) )
    sizestring = 'The total size of This American Life media is %s.' % \
                 get_formatted_size( totsizebytes )
    durstring = 'The total duration of This American Life media is %s.' % \
                get_formatted_duration( totdur )
    if sinceDate is None:
        pristrings = [ ' '.join([ mainstring, sizestring, durstring ]), ]
    else:
        key, song_data_since = plexcore._get_library_data_artist( keynum, token, fullURL = fullURLWithPort,
                                                                  sinceDate = sinceDate )
        num_episodes_since = 0
        totdur_since = 0.0
        totsizebytes_since = 0.0
        for key in song_data_since:
            for key2 in song_data_since[key]:
                num_episodes_since += len( song_data_since[ key ][ key2 ] )
                for track in song_data_since[ key ][ key2 ]:
                    name, dt, dur, sizebytes = track
                    totdur_since += dur
                    totsizebytes_since += sizebytes
        if num_episodes_since > 0:        
            mainstring_since = ' '.join([ 'Since %s, I have added %d new This American Life episodes.' %
                                          ( sinceDate.strftime( '%B %d, %Y' ), num_episodes_since ),
                                          'The total size of This American Life media I added is %s.' %
                                          get_formatted_size( totsizebytes_since ),
                                          'The total duration of This American Life media I added is %s.' %
                                          get_formatted_duration( totdur_since ) ])
            pristrings = [ ' '.join([ mainstring, sizestring, durstring, mainstring_since ]), ]
        else:
            pristrings = [ ' '.join([ mainstring, sizestring, durstring ]), ]           
    #
    catpristrings = {}
    for album in song_data:
        if album == 'Ira Glass':
            actalbum = 'This American Life'
        else:
            actalbum = album
        totdur = 0.0
        totsizebytes = 0.0
        num_episodes = 0
        for key2 in song_data[ album ]:
            num_episodes += len( song_data[ album ][ key2 ] )
            for track in song_data[ album ][ key2 ]:
                name, dt, dur, sizebytes = track
                totdur += dur
                totsizebytes += sizebytes
        mainstring = 'There are %d episodes in this category.' % num_episodes
        sizestring = 'The total size of media here is %s.' % \
                     get_formatted_size( totsizebytes )
        durstring = 'The total duration of media here is %s.' % \
                    get_formatted_duration( totdur )
        if sinceDate is None:
            mystring = ' '.join([ mainstring, sizestring, durstring ])
        else:
            if album not in song_data_since:
                mystring = ' '.join([ mainstring, sizestring, durstring ])
            else:
                totdur_since = 0.0
                totsizebytes_since = 0.0
                num_episodes_since = 0
                for key2 in song_data_since[ album ]:
                    num_episodes_since += len( song_data_since[ album ][ key2 ] )
                    for track in song_data_since[ album ][ key2 ]:
                        name, dt, dur, sizebytes = track
                        totdur_since += dur
                        totsizebytes_since += sizebytes
                if num_episodes_since > 0:
                    mainstring_since = ' '.join([ 'Since %s, I have added %d new episodes in this category.' %
                                          ( sinceDate.strftime( '%B %d, %Y' ), num_episodes_since ),
                                          'The total size of media I added here is %s.' %
                                          get_formatted_size( totsizebytes_since ),
                                          'The total duration of media I added here is %s.' %
                                          get_formatted_duration( totdur_since ) ])
                    mystring = ' '.join([ mainstring, sizestring, durstring, mainstring_since ])
                else:
                    mystring = ' '.join([ mainstring, sizestring, durstring ])
        catpristrings[ actalbum ] = mystring
    pristrings.append( catpristrings )
    return pristrings

def get_summary_data_thisamericanlife( allrows ):
    pri_rows = list(filter(lambda row: '/mnt/media/thisamericanlife' in row[5] and
                           row[7] is not None and row[8] is not None, allrows ) )
    rowdict = { row[5] : row for row in pri_rows }
    albumdata = dict(filter(None, map(_get_album_prifile, rowdict.keys() ) ) )
    albums = set( albumdata.values( ) )
    albumdict = {}
    for prifile in albumdata:
        albumdict.setdefault( albumdata[ prifile ], []).append( prifile )
    mainstring = 'There are %d episodes in %d series in This American Life.' % (
        len( pri_rows ), len( albums ) )        
    totdur = 1e-3 * sum([ row[8] for row in pri_rows ])
    totsizebytes = sum([ row[7] for row in pri_rows ])
    sizestring = 'The total size of This American Life media is %s.' % \
                 get_formatted_size( totsizebytes )
    durstring = 'The total duration of This American Life media is %s.' % \
                get_formatted_duration( totdur )
    pristrings = [ ' '.join([ mainstring, sizestring, durstring ]), ]
    catpristrings = {}
    for album in albumdict:
        totdur = 1e-3 * sum([ rowdict[ prifile ][ 8 ] for prifile in albumdict[ album ] ])
        totsizebytes = sum([ rowdict[ prifile ][ 7 ] for prifile in albumdict[ album ] ] )
        mainstring = 'There are %d episodes in this category.' % len( albumdict[ album ] )
        sizestring = 'The total size of media here is %s.' % \
                     get_formatted_size( totsizebytes )
        durstring = 'The total duration of media here is %s.' % \
                    get_formatted_duration( totdur )
        catpristrings[ album ] = ' '.join([ mainstring, sizestring, durstring ])
    pristrings.append( catpristrings )
    return pristrings

def get_summary_data_music( allrows ):
    music_rows = list(filter(lambda row:  '/mnt/media/aacmusic' in row[5] and
                             row[8] is not None and row[7] is not None, allrows ) )
    allmusicfiles = [ row[5] for row in music_rows ]
    #pool = multiprocessing.Pool( processes = multiprocessing.cpu_count( ) )
    #artists, albums = zip(*filter(None, pool.map( _get_artistalbum, allmusicfiles )))
    artists, albums = zip(*list(filter(None, map( _get_artistalbum, allmusicfiles ) ) ) )
    artists = set( artists )
    albums = set( albums )
    mainstring = 'There are %d songs made by %d artists in %d albums.' % ( len( music_rows ),
                                                                           len( artists),
                                                                           len( albums ) )
    totdur = 1e-3 * sum([ row[8] for row in music_rows ])
    totsizebytes = sum([ row[7] for row in music_rows ])
    sizestring = 'The total size of music media is %s.' % \
                 get_formatted_size( totsizebytes )
    durstring = 'The total duration of music media is %s.' % \
                get_formatted_duration( totdur )
    musicstring = ' '.join([ mainstring, sizestring, durstring ])
    return musicstring

def get_summary_data_music_remote( token, fullURLWithPort = 'http://localhost:32400' ):
    libraries_dict = plexcore.get_libraries( token = token, fullURL = fullURLWithPort )
    keynum = max([ key for key in libraries_dict if libraries_dict[key] == 'Music' ])
    sinceDate = plexcore.get_current_date_newsletter( )
    key, num_songs, num_albums, num_artists, totdur, totsizebytes = plexcore._get_library_stats_artist( keynum, token, fullURL = fullURLWithPort )
    mainstring = 'There are %d songs made by %d artists in %d albums.' % ( num_songs, num_artists, num_albums )
    sizestring = 'The total size of music media is %s.' % \
                 get_formatted_size( totsizebytes )
    sizestring = 'The total size of music media is %s.' % \
                 get_formatted_size( totsizebytes )
    durstring = 'The total duration of music media is %s.' % \
                get_formatted_duration( totdur )
    if sinceDate is not None:
        key, num_songs_since, num_albums_since, num_artists_since, \
            totdur_since, totsizebytes_since = plexcore._get_library_stats_artist( keynum, token, fullURL = fullURLWithPort,
                                                                                   sinceDate = sinceDate )
        if num_songs_since > 0:
            mainstring_since = ' '.join([ 'Since %s, I have added %d songs made by %d artists in %d albums.' %
                                          ( sinceDate.strftime( '%B %d, %Y' ), num_songs_since, num_artists_since, num_albums_since ),
                                          'The total size of music media I added is %s.' % get_formatted_size( totsizebytes_since ),
                                          'The total duration of music media I added is %s.' %
                                          get_formatted_duration( totdur_since ) ])
            musicstring = ' '.join([ mainstring, sizestring, durstring, mainstring_since ])
            return musicstring
    musicstring = ' '.join([ mainstring, sizestring, durstring ])
    return musicstring

def get_summary_data_television( allrows ):
    tv_rows = filter(lambda row: '/mnt/media/television' in row[5] and
                     row[8] is not None and row[7] is not None, allrows )
    tvshows = sorted(set([ row[5].split('/')[4].strip( ) for row in tv_rows ]) )
    totdur = 1e-3 * sum([ row[8] for row in tv_rows ])
    totsizebytes = sum([ row[7] for row in tv_rows ])    
    #
    sizestring = 'The total size of TV media is %s.' % \
                 get_formatted_size( totsizebytes )
    durstring = 'The total duration of TV media is %s.' % \
                get_formatted_duration( totdur )
    mainstring = 'There are %d TV files in %d TV shows.' % ( len(tv_rows), len(tvshows) )
    tvstring = ' '.join([ mainstring, sizestring, durstring ])
    return tvstring

def get_summary_data_television_remote( token, fullURLWithPort = 'http://localhost:32400' ):
    libraries_dict = plexcore.get_libraries( token = token, fullURL = fullURLWithPort )
    keynum = max([ key for key in libraries_dict if libraries_dict[key] == 'TV Shows' ])
    sinceDate = plexcore.get_current_date_newsletter( )
    key, numTVeps, numTVshows, totdur, totsizebytes = plexcore._get_library_stats_show( keynum, token, fullURL = fullURLWithPort )
    sizestring = 'The total size of TV media is %s.' % \
                 get_formatted_size( totsizebytes )
    durstring = 'The total duration of TV media is %s.' % \
                get_formatted_duration( totdur )
    mainstring = 'There are %d TV files in %d TV shows.' % ( numTVeps, numTVshows )
    if sinceDate is not None:
        key, numTVeps_since, numTVshows_since, \
            totdur_since, totsizebytes_since = plexcore._get_library_stats_show( keynum, token, fullURL = fullURLWithPort,
                                                                                 sinceDate = sinceDate )
        if numTVeps_since > 0:
            mainstring_since = ' '.join([ 'Since %s, I have added %d TV files in %d TV shows.' %
                                          ( sinceDate.strftime('%B %d, %Y'), numTVeps_since, numTVshows_since ),
                                          'The total size of TV media I added is %s.' % get_formatted_size( totsizebytes_since ),
                                          'The total duration of TV media I added is %s.' % get_formatted_duration( totdur_since ) ] )
            tvstring = ' '.join([ mainstring, sizestring, durstring, mainstring_since ])
            return tvstring
    tvstring = ' '.join([ mainstring, sizestring, durstring ])
    return tvstring

def get_summary_data_movies_remote( token, fullURLWithPort = 'http://localhost:32400' ):
    libraries_dict = plexcore.get_libraries( token = token, fullURL = fullURLWithPort )
    keynum = max(zip(*filter(lambda tup: tup[1] == 'Movies', libraries_dict.items()))[0])
    sinceDate = plexcore.get_current_date_newsletter( )
    _, num_movies, totsizebytes, totdur, \
        sorted_by_genres = plexcore._get_library_stats_movie( keynum, token, fullURL = fullURLWithPort )
    if sinceDate is not None:
        _, num_movies_since, totsizebytes_since, totdur_since, \
            sorted_by_genres_since = plexcore._get_library_stats_movie( keynum, token, fullURL = fullURLWithPort,
                                                                        sinceDate = sinceDate )
        if num_movies_since > 0:
            mainstring_since = ' '.join([ 'Since %s, I have added %d movies in %d categories.' %
                                          ( sinceDate.strftime('%B %d, %Y'), num_movies_since, len( sorted_by_genres_since ) ),
                                          'The total size of movie media I added is %s.' % get_formatted_size( totsizebytes_since ),
                                          'The total duration of movie media I added is %s.' %
                                          get_formatted_duration( totdur_since ) ] )
    categories = sorted( sorted_by_genres )
    mainstring = 'There are %d movies in %d categories.' % ( num_movies, len( categories ) )
    sizestring = 'The total size of movie media is %s.' % get_formatted_size( totsizebytes )
    durstring = 'The total duration of movie media is %s.' % get_formatted_duration( totdur )
    #
    ## get last 7 movies that I have added
    lastN_movies = plexcore.get_lastN_movies( 7, token, fullURLWithPort = fullURLWithPort )
    lastNstrings = [ '', '',
                     'Here are the last %d movies I have added.' % len( lastN_movies ),
                     '\\begin{itemize}' ]
    for title, year, date, url in lastN_movies:
        if url is None:
            lastNstrings.append( '\item %s (%d), added on %s.' %
                                 ( title, year, date.strftime( '%d %B %Y' ) ) )
        else:
            lastNstrings.append( '\item \href{%s}{%s (%d)}, added on %s.' %
                                 ( url, title, year, date.strftime( '%d %B %Y' ) ) )
    lastNstrings.append( '\end{itemize}' )
    lastNstring = '\n'.join( lastNstrings )
    finalstring = 'Here is a summary by category.'
    if sinceDate is not None and num_movies_since > 0:
        movstring = ' '.join([ mainstring, sizestring, durstring, mainstring_since,
                               lastNstring, finalstring ])
    else:
        movstring = ' '.join([ mainstring, sizestring, durstring, lastNstring, finalstring ])
    movstrings = [ movstring, ]
    catmovstrings = {}
    for cat in categories:
        num_movies, totdur, totsizebytes = sorted_by_genres[ cat ]
        mainstring = 'There are %d movies in this category.' % num_movies
        sizestring = 'The total size of movie media here is %s.' % \
                     get_formatted_size( totsizebytes )
        durstring = 'The total duration of movie media here is %s.' % \
                    get_formatted_duration( totdur )
        if sinceDate is not None and cat in sorted_by_genres_since and num_movies_since > 0:
            num_movies_since, totdur_since, totsizebytes_since = sorted_by_genres_since[ cat ]
            mainstring_since = ' '.join([  'Since %s, I have added %d movies in this category.' %
                                           ( sinceDate.strftime( '%B %d, %Y' ), num_movies_since ),
                                           'The total size of movie media I added here is %s.' % get_formatted_size( totsizebytes_since ),
                                           'The total duration of movie media I added here is %s.' %
                                           get_formatted_duration( totdur_since ) ] )
            movstring = ' '.join([ mainstring, sizestring, durstring, mainstring_since ])
        else:
            movstring = ' '.join([ mainstring, sizestring, durstring ])
        catmovstrings[cat] = movstring    
    movstrings.append( catmovstrings )    
    return movstrings
    
def get_summary_data_movies( allrows ):
    movie_rows = filter(lambda row: '/mnt/media/movies' in row[5] and
                        row[8] is not None and row[7] is not None, allrows )
    totdur = 1e-3 * sum(map(lambda row: row[8], movie_rows ) )
    totsizebytes = sum(map(lambda row: row[7], movie_rows ) )
    categories = set(map(lambda row: row[5].split('/')[4].strip(), movie_rows ) )
    mainstring = 'There are %d movies in %d categories.' % ( len( movie_rows ), len( categories ) )
    sizestring = 'The total size of movie media is %s.' % \
                 get_formatted_size( totsizebytes )
    durstring = 'The total duration of movie media is %s.' % \
                get_formatted_duration( totdur )    
    #
    ## get last 7 movies that I have added
    lastN_movies = plexcore.get_lastN_movies( 7 )
    lastNstrings = [ '', '',
                     'Here are the last %d movies I have added.' % len( lastN_movies ),
                     '\\begin{itemize}' ]
    for title, year, date in lastN_movies:
        lastNstrings.append( '\item %s (%d), added on %s.' %
                             ( title, year, date.strftime( '%d %B %Y' ) ) )
    lastNstrings.append( '\end{itemize}' )
    lastNstring = '\n'.join( lastNstrings )
    finalstring = 'Here is a summary by category.'
    movstring = ' '.join([ mainstring, sizestring, durstring, lastNstring, finalstring ])
    movstrings = [ movstring, ]
    catmovstrings = {}
    for cat in categories:
        cat_mov_rows = filter(lambda row: '/mnt/media/movies/%s' % cat in row[5], movie_rows )
        totdur = 1e-3 * sum([ row[8] for row in cat_mov_rows ])
        totsizebytes = sum([ row[7] for row in cat_mov_rows ])
        mainstring = 'There are %d movies in this category.' % len( cat_mov_rows )
        sizestring = 'The total size of movie media here is %s.' % \
                     get_formatted_size( totsizebytes )
        durstring = 'The total duration of movie media here is %s.' % \
                    get_formatted_duration( totdur )
        movstring = ' '.join([ mainstring, sizestring, durstring ])
        catmovstrings[cat] = movstring
    movstrings.append( catmovstrings )    
    return movstrings

def get_formatted_duration( totdur ):
    dt = datetime.datetime.utcfromtimestamp( totdur )
    durstringsplit = []
    month_off = 1
    day_off = 1
    hour_off = 1
    min_off = 1
    if dt.year - 1970 != 0:
        durstringsplit.append('%d years' % ( dt.year - 1970 ) )
        month_off = 0
    if dt.month != month_off:
        durstringsplit.append('%d months' % ( dt.month - month_off ) )
        day_off = 0
    if dt.day != day_off:
        durstringsplit.append('%d days' % ( dt.day - day_off ) )
        hour_off = 0
    if dt.hour != hour_off:
        durstringsplit.append('%d hours' % ( dt.hour - hour_off ) )
        min_off = 0
    if dt.minute != min_off:
        durstringsplit.append('%d minutes' % ( dt.minute - min_off ) )
    if len(durstringsplit) != 0:
        durstringsplit.append('and %0.3f seconds' % ( dt.second + 1e-6 * dt.microsecond ) )
    else:
        durstringsplit.append('%0.3f seconds' % ( dt.second + 1e-6 * dt.microsecond ) )
    return ', '.join( durstringsplit )

def get_formatted_size( totsizebytes ):
    sizestring = ''
    if totsizebytes >= 1024**3:
        size_in_gb = totsizebytes * 1.0 / 1024**3
        sizestring = '%0.3f GB' % size_in_gb
    elif totsizebytes >= 1024**2:
        size_in_mb = totsizebytes * 1.0 / 1024**2
        sizestring = '%0.3f MB' % size_in_mb
    elif totsizebytes >= 1024:
        size_in_kb = totsizebytes * 1.0 / 1024
        sizestring = '%0.3f kB' % size_in_kb
    return sizestring
