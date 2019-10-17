import os, glob, datetime, gspread, logging, sys, numpy, urllib3
from functools import reduce
_mainDir = reduce(lambda x,y: os.path.dirname( x ), range( 2 ),
                   os.path.abspath( __file__ ) )
sys.path.append( _mainDir )
import uuid, requests, pytz, pypandoc, time, json, validators
import pathos.multiprocessing as multiprocessing
# oauth2 stuff
import oauth2client.client
from google_auth_oauthlib.flow import Flow # does not yet work
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
#
from html import unescape
from bs4 import BeautifulSoup
from urllib.request import urlopen
from urllib.parse import urlencode, urljoin, urlparse
from itertools import chain
from multiprocessing import Manager

from plexcore import mainDir, session
from plexcore import PlexConfig, LastNewsletterDate, PlexGuestEmailMapping
from plextmdb import plextmdb

# disable insecure request warnings, because do not recall how to get the name of the certificate for a 
# given plex server
requests.packages.urllib3.disable_warnings( )
urllib3.disable_warnings( )

def add_mapping( plex_email, plex_emails, new_emails, replace_existing ):
    """
    Changes the mapping of one member of the Plex_ server's emails from an old set of emails to a new set of emails. The command line tool, ``plex_config_cli.py``, is a front end to the lower-level functionality implemented here. That command line's tool functionality is described in some detail in the Sphinx documentation for that tool.

    :param str plex_email: the email of a Plex_ server member whose mapping of emails is to be changed.
    
    :param list plex_emails: the emails of all members of the Plex_ server.
    
    :param list new_emails: the mapping to be done. None of the emails in ``new_emails`` can be in the Plex_ server.
    """
    assert( plex_email in plex_emails )
    assert( len( set( new_emails ) & set( plex_emails ) ) == 0 )
    query = session.query( PlexGuestEmailMapping )
    val = query.filter( PlexGuestEmailMapping.plexemail == plex_email ).first( )
    if val is not None:
        session.delete( val )
        session.commit( )
    newval = PlexGuestEmailMapping(
        plexemail = plex_email,
        plexmapping = ','.join( sorted( set( new_emails ) ) ),
        plexreplaceexisting = replace_existing )
    session.add( newval )
    session.commit( )

def get_date_from_datestring( dstring ):
    """Returns a :py:class:`date <datetime.date>` object from
    a date string with the format, "January 1, 2000".
    
    :param str dstring: the initial date string.
    
    :returns: its :py:class:`date <datetime.date>` object representation.
    
    :rtype: :py:class:`date <datetime.date>`

    """
    try: return datetime.datetime.strptime( dstring, '%B %d, %Y' ).date( )
    except Exception:
        logging.error("Error, could not parse %s into a date." % dstring )
        return None

def latexToHTML( latexString ):
    """Converts a LaTeX_ string into HTML using Pandoc_, then prettifies the
    intermediate HTML using BeautifulSoup_.

    :param str latexString: the initial LaTeX_ string.
    
    :returns: the final prettified, formatted HTML string.
    
    :rtype: str

    .. _LaTeX: https://www.latex-project.org
    .. _Pandoc: https://pandoc.org
    .. _BeautifulSoup: https://www.crummy.com/software/BeautifulSoup/bs4/doc
    
    """
    try:
        htmlstring = pypandoc.convert( latexString, 'html', format = 'latex',
                                       extra_args = [ '-s' ] )
        return BeautifulSoup( htmlstring, 'lxml' ).prettify( )
    except RuntimeError as e:
        logging.debug( '%s' % e )
        return None

def processValidHTMLWithPNG( html, pngDataDict, doEmbed = False ):
    """Returns a prettified HTML document, using BeautifulSoup_, including all PNG image data (whether URLs or `Base 64 encoded`_ data) in ``<img>`` tags.

    :param str html: the initial HTML document into which images are to be embedded.
    
    :param dict pngDataDict: dictionary of PNG data. Key is the name of the PNG file (must end in .png). Value is a tuple of type ``(b64data, widthInCM, url)``. ``b64data`` is the `Base 64 encoded`_ binary representation of the PNG image. ``widthInCm`` is the image width in cm. ``url`` is thje URL address of the image.
    
    :param bool doEmbed: If ``True``, then the image source tag uses the `Base 64 encoded` data. If ``False``, the image source tag is the URL.
    :returns: prettified HTML document with the images located in it.
    :rtype: str

    .. _Base 64 encoded: https://en.wikipedia.org/wiki/Base64
    """
    htmlData = BeautifulSoup( html, 'lxml' )
    pngNames = set(filter(
        lambda name: name.endswith('.png'),
        map(lambda img: img['src'], htmlData.find_all('img'))))
    if len( pngNames ) == 0: return htmlData.prettify( )
    if len( pngNames - set( pngDataDict ) ) != 0:
        logging.debug(
            'error, some defined figures in latex do not have images.' )
        return htmldata.prettify( )
    for img in htmlData.find_all('img'):
        name = img['src']
        b64data, widthInCM, url = pngDataDict[ name ]
        if doEmbed: img['src'] = "data:image/png;base64,%s" % b64data
        else: img['src'] = url
        img['width'] = "%d" % ( widthInCM / 2.54 * 300 )
    return htmlData.prettify( )

def getTokenForUsernamePassword( username, password, verify = True ):
    """get the Plex_ access token for the Plex_ server given an username and password for the user account.

    :param str username: the Plex_ account username.
    :param str password: the Plex_ account password.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :returns: the Plex_ access token.
    :rtype: str

    .. seealso::
    
      * :py:meth:`checkServerCredentials <plexcore.plexcore.checkServerCredentials>`
      * :py:meth:`getCredentials <plexcore.plexcore.getCredentials>`
      * :py:meth:`pushCredentials <plexcore.plexcore.pushCredentials>`

    """
    headers = { 'X-Plex-Client-Identifier' : str( uuid.uuid4( ) ),
                'X-Plex-Platform' : 'Linux',
                'X-Plex-Provides' : 'server' }
    response = requests.post(
        'https://plex.tv/users/sign_in.json',
        auth = ( username, password ),
        headers = headers,
        verify = verify )
    if response.status_code != 201:
        logging.debug( 'status code = %d' % response.status_code )
        logging.debug( 'content = %s' %  response.content )
        return None
    return response.json()['user']['authentication_token']
    
def checkServerCredentials( doLocal = False, verify = True, checkWorkingServer = True ):
    """Returns get a local or remote URL and Plex_ access token to allow for API access to the server. If there is already a VALID token in the SQLite3_ configuration database, then uses that. Otherwise, tries to acquire a Plex_ access token.

    :param bool doLocal: optional argument, whether to get a local (``http://localhost:32400``) or remote URL. Default is ``False`` (look for the remote URL).
    
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.

    :param bool checkWorkingServer: optional argument, whether to check if the server is working. Default is ``True``.
    
    :returns: a tuple of server URL and Plex_ access token.
    :rtype: tuple

    .. seealso:: :py:meth:`getCredentials <plexcore.plexcore.getCredentials>`

    .. _Plex: https://plex.tv

    """

    #
    ## first see if there are a set of valid login tokens
    def _get_stored_plexlogin( doLocal, verify ):
        val = session.query( PlexConfig ).filter(
            PlexConfig.service == 'plexlogin' ).first( )
        if val is None: return None
        
        data = val.data
        token = data[ 'token' ]
        if doLocal: fullURL = 'http://localhost:32400'
        else:
            dat = get_all_servers( token, verify = verify )
            if dat is None: return None
            name = max(filter(lambda name: dat[ name ][ 'owned' ], dat ) )
            fullURL = dat[ name ][ 'url' ]
        #
        ## now see if this works
        if not checkWorkingServer: return fullURL, token
        try:
            updated_at = get_updated_at( token, fullURL )
            if updated_at is None: return None
        except: return None
        return fullURL, token

    dat = _get_stored_plexlogin( doLocal, verify )
    if dat is not None: return dat

    #
    ## instead, must get a new set of tokens
    val = session.query( PlexConfig ).filter(
        PlexConfig.service == 'login' ).first( )
    if val is None: return None
    data = val.data
    username = data['username'].strip( )
    password = data['password'].strip( )
    token = getTokenForUsernamePassword(
        username, password, verify = verify )
    if token is None: return None
    if not doLocal:
        _, fullURL = max( get_owned_servers( token, verify = verify ).items( ) )
        fullURL = 'https://%s' % fullURL
    else: fullURL = 'http://localhost:32400'
    if not checkWorkingServer: return fullURL, token # don't store into plexlogin database
    #
    ## now see if this works
    try:
        updated_at = get_updated_at( token, fullURL )
        if updated_at is None: return None
    except: return None

    #
    ## now put into the 'plexlogin' service in the 'plexconfig' database
    val = session.query( PlexConfig ).filter(
        PlexConfig.service == 'plexlogin' ).first( )
    if val is not None:
        session.delete( val )
        session.commit( )

    newval = PlexConfig( service = 'plexlogin',
                         data = { 'token' : token } )
    session.add( newval )
    session.commit( )
        
    return fullURL, token

def getCredentials( verify = True, checkWorkingServer = True ):
    """Returns the Plex_ user account information stored in ``~/.config/plexstuff/app.db``.

    :param bool verify: optional argument, whether to use SSL verification. Default is ``True``.
    :param bool checkWorkingServer: optional argument, whether to check if the server is working. Default is ``True``.
    :returns: the Plex_ account tuple of ``(username, password)``.
    :rtype: tuple

    .. seealso:: :py:meth:`pushCredentials <plexcore.plexcore.pushCredentials>`

    """
    val = session.query( PlexConfig ).filter(
        PlexConfig.service == 'login' ).first( )
    if val is None: return None
    data = val.data
    username = data['username'].strip( )
    password = data['password'].strip( )
    if checkWorkingServer:
        token = getTokenForUsernamePassword(
            username, password, verify = verify )
        if token is None: return None
    return username, password

def pushCredentials( username, password ):
    """replace the Plex_ server credentials, located in ``~/.config/plexstuff/app.db``, with a new ``username`` and ``password``.

    :param str username: the Plex_ account username.
    :param str password: the Plex_ account password.
    :returns: if successful, return a string, ``SUCCESS``. If unsuccessful, returns a string reason of why it failed.
    :rtype: str

    .. seealso:: :py:meth:`getCredentials <plexcore.plexcore.getCredentials>`

    """
    #
    ## first see if these work
    token = getTokenForUsernamePassword( username, password )
    if token is None:
        return "error, username and password do not work."
    val = session.query( PlexConfig ).filter(
        PlexConfig.service == 'login' ).first( )
    if val is not None:
        data = val.data
        session.delete( val )
        session.commit( )
    data = { 'username' : username.strip( ),
             'password' : password.strip( ) }
    newval = PlexConfig( service = 'login', data = data )
    session.add( newval )
    session.commit( )
    return "SUCCESS"

def get_all_servers( token, verify = True ):
    """Find all the Plex_ servers for which you have access.

    :param str token: the Plex str access token, returned by :py:meth:`checkServerCredentials <plexcore.checkServerCredentials>`.
    :param bool verify: optional bool argument, whether to verify SSL connections. Default is ``True``.
    :returns: a dictionary of servers accessible to you. Each key is the Plex_ server's name, and the value is a :py:class:`dict` that looks like this.
    
    .. code-block:: python
       
       {
         'owned'        : OWNED, # boolean on whether server owned by you
         'access token' : TOKEN, # string access token to server
         'url'          : URL    # remote URL of the form https://IP-ADDRESS:PORT
       }
    
    :rtype: dict

    .. seealso::
       * :py:meth:`checkServerCredentials <plexcore.plexcore.checkServerCredentials>`

    .. _Plex: https://plex.tv

    """
    response = requests.get( 'https://plex.tv/api/resources',
                             params = { 'X-Plex-Token' : token },
                             verify = verify )
    if response.status_code != 200:
        return None
    myxml = BeautifulSoup( response.content, 'lxml' )
    server_dict = { }
    for server_elem in filter(lambda se: len(set([ 'product', 'publicaddress', 'owned', 'accesstoken' ]) - set( se.attrs ) ) == 0 and
                              se['product'] == 'Plex Media Server', myxml.find_all('device') ):
        #
        ## is device owned by me?
        is_owned = bool( int( server_elem[ 'owned' ] ) )
        connections = list( filter(lambda elem: elem['local'] == '0', server_elem.find_all('connection') ) )
        if len( connections ) != 1:
            continue
        connection = max( connections )
        name = server_elem[ 'name' ]
        host = connection[ 'address' ]
        port = int( connection[ 'port' ] )
        server_dict[ name ] = {
            'owned' : is_owned,
            'access token' : server_elem[ 'accesstoken' ],
            'url' : 'https://%s:%d' % ( host, port ) }
    return server_dict

def get_pic_data( plexPICURL, token = None ):
    """Get the PNG data as a :py:class:`Response <requests.Response>` object, from a movie picture URL on the Plex_ server.

    :param str plexPICURL: the movie picture URL.
    :param str token: the Plex_ access token.
    :returns: the PNG data for the movie image.
    :rtype: :py:class:`Response <requests.Response>`

    """
    if token is None: params = { }
    else: params = { 'X-Plex-Token' : token }
    response = requests.get( plexPICURL, params = params, verify = False )
    logging.debug( 'FULLMOVIEPATH: %s, size = %d' %
                   ( plexPICURL, len( response.content ) ) )
    return response.content

def get_updated_at( token, fullURL = 'http://localhost:32400' ):
    """Get the date and time at which the Plex_ server was last updated, as a :py:class:`datetime <datetime.datetime>` object.

    :param str token: the Plex_ access token.
    :param str fullURL: the Plex_ server URL.
    :returns: the date and time of the Plex_ server's last update.
    :rtype: :py:class:`datetime <datetime.datetime>`

    """
    params = { 'X-Plex-Token' : token }
    response = requests.get( fullURL, params = params, verify = False )
    if response.status_code != 200:
        logging.error( 'Error, could not get updated at status with token = %s, URL = %s.' % (
            token, fullURL ) )
        return None
    myxml = BeautifulSoup( response.content, 'lxml' )
    media_elem = max( myxml.find_all( 'mediacontainer' ) )
    assert( 'updatedat' in media_elem.attrs )
    return datetime.datetime.fromtimestamp( int( media_elem['updatedat'] ) )

def get_email_contacts( token, verify = True ):
    """list of all email addresses of friends who have stream access to your Plex_ server.

    :param str token: Plex_ access token.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :returns: list of email addresses of Plex_ friends.
    :rtype: list 

    .. seealso: :py:method:`get_mapped_email_contacts <plexcore.plexcore.get_mapped_email_contacts>`

    """
    
    response = requests.get( 'https://plex.tv/pms/friends/all',
                             headers = { 'X-Plex-Token' : token },
                             verify = verify )
    if response.status_code != 200: return None
    myxml = BeautifulSoup( response.content, 'lxml' )
    return sorted(set(map(lambda elem: elem['email'],
                          filter(lambda elem: 'email' in elem.attrs,
                                 myxml.find_all( 'user' ) ) ) ) )

def get_mapped_email_contacts( token, verify = True ):
    """list of all email addresses (including Plex_ server friends and mapped emails) to send Plexstuff related emails.

    :param str token: Plex_ access token.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :returns: a list of email addresses for Plexstuff emails.
    :rtype: list

    .. seealso: :py:method:`get_email_contacts <plexcore.plexcore.get_email_contacts>`

    """
    emails = get_email_contacts( token, verify = verify )
    query = session.query( PlexGuestEmailMapping )
    subtracts = [ ]
    extraemails = [ ]
    for mapping in query.all( ):
        replace_existing = mapping.plexreplaceexisting
        plex_email = mapping.plexemail
        if replace_existing: subtracts.append( plex_email )
        extraemails += map(lambda tok: tok.strip(), mapping.plexmapping.strip().split(','))
    extraemails = sorted(set(extraemails))    
    mapped_emails = sorted( set( emails ) - set( subtracts ) )
    mapped_emails = sorted( mapped_emails + extraemails )
    return mapped_emails
    
def get_current_date_newsletter( ):
    """the last date and time at which the Plexstuff email newsletter was updated.

    :returns: the date and time of the most recent previous email newsletter.
    :rtype: :py:class:`datetime <datetime.datetime>`.
    
    .. seealso:: :py:meth:`set_date_newsletter <plexcore.plexcore.set_date_newsletter>`
    
    """
    query = session.query( LastNewsletterDate )
    backthen = datetime.datetime.strptime( '1900-01-01', '%Y-%m-%d' ).date( )
    val = query.filter( LastNewsletterDate.date >= backthen ).first( )
    if val is None:
        return None
    return val.date

def _get_library_data_movie( key, token, fullURL = 'http://localhost:32400', sinceDate = None,
                             num_threads = 2 * multiprocessing.cpu_count( ), timeout = None ):
    assert( num_threads >= 1 )
    params = { 'X-Plex-Token' : token }
    if sinceDate is None:
        sinceDate = datetime.datetime.strptime( '1900-01-01', '%Y-%m-%d' ).date( )
        
    response = requests.get( '%s/library/sections/%d/all' % ( fullURL, key ),
                             params = params, verify = False, timeout = timeout )
    if response.status_code != 200: return None
    def _get_bitrate_size( movie_elem ):
        bitrate_elem = list(filter(lambda elem: 'bitrate' in elem.attrs, movie_elem.find_all('media')))
        if len( bitrate_elem ) != 0: bitrate = int( bitrate_elem[0]['bitrate'] ) * 1e3 / 8.0
        else: bitrate = -1
        size_elem = list( chain.from_iterable(
            map(lambda media_elem: media_elem.find_all('part'),
                movie_elem.find_all('media'))))
        size_elem = list(filter(lambda elem: 'size' in elem.attrs, size_elem) )
        if len(size_elem) != 0: totsize = int( size_elem[0]['size'] ) * 1.0
        else: totsize = -1
        return bitrate, totsize
    #
    def _get_movie_data( input_tuple ):
        cont, indices = input_tuple
        html = BeautifulSoup( cont, 'lxml' )
        movie_elems = html.find_all('video' )
        movie_data_sub = [ ]
        for idx in indices:
            movie_elem = movie_elems[ idx ]
            if datetime.datetime.fromtimestamp( float( movie_elem.get('addedat') ) ).date() < sinceDate:
                continue
            genres = list(map(lambda elem: elem.get('tag').lower( ),
                              filter(lambda elem: 'tag' in elem.attrs, movie_elem.find_all('genre'))))
            #if len( genres ) != 0:
            #    first_genre = genres[ 0 ]
            #else:
            #    logging.debug( 'genre not found for %s.' % movie_elem[ 'title' ] )
            first_genre = plextmdb.get_main_genre_movie( movie_elem )
            title = movie_elem['title']
            if 'rating' in movie_elem.attrs:
                rating = float( movie_elem.get('rating') )
            else: rating = None
            summary = movie_elem.get('summary')
            if 'art' in movie_elem.attrs: picurl = '%s%s' % ( fullURL, movie_elem.get('art') )
            else: picurl = None
            if 'originallyavailableat' in movie_elem.attrs:
                releasedate = datetime.datetime.strptime(
                    movie_elem.get( 'originallyavailableat' ), '%Y-%m-%d' ).date( )
            else: releasedate = None
            addedat = datetime.datetime.fromtimestamp( float( movie_elem.get( 'addedat' ) ) ).date( )
            if 'contentrating' in movie_elem.attrs:
                contentrating = movie_elem.get('contentrating')
            else: contentrating = 'NR'
            duration = 1e-3 * int( movie_elem[ 'duration' ] )
            bitrate, totsize = _get_bitrate_size( movie_elem )
            if bitrate == -1 and totsize != -1: bitrate = 1.0 * totsize / duration
            imdb_id = None
            if 'guid' in movie_elem.attrs:
                guid = movie_elem.get( 'guid' )
                if 'imdb' in guid: imdb_id = urlparse( guid ).netloc
                
            data = {
                'title' : title,
                'rating' : rating,
                'contentrating' : contentrating,
                'picurl' : picurl,
                'releasedate' : releasedate,
                'addedat' : addedat,
                'summary' : summary,
                'duration' : duration,
                'totsize' : totsize,
                'localpic' : True,
                'imdb_id' : imdb_id }
            
            movie_data_sub.append( ( first_genre, data ) )
        return movie_data_sub

    act_num_threads = max( num_threads, multiprocessing.cpu_count( ) )
    len_movie_elems = len( BeautifulSoup( response.content, 'lxml' ).find_all('video') )
    with multiprocessing.Pool( processes = act_num_threads ) as pool:
        input_tuples = list(
            map(lambda idx: ( response.content, list(
                range(idx, len_movie_elems, act_num_threads ) ) ),
                range( act_num_threads ) ) )
        movie_data = { }
        movie_data_list = list( chain.from_iterable(
            map( _get_movie_data, input_tuples ) ) ) # change back to pool.map
        for first_genre, data in movie_data_list:
            movie_data.setdefault( first_genre, [ ] ).append( data )
        return key, movie_data
        
def _get_library_stats_movie( key, token, fullURL ='http://localhost:32400', sinceDate = None ):
    tup = _get_library_data_movie( key, token, fullURL = fullURL, sinceDate = sinceDate )
    if tup is None: return None
    _, movie_data = tup
    sorted_by_genres = {
        genre : { 'totnum' : len( movie_data[ genre ] ),
                  'totdur' : sum(list(map(lambda entry: entry['duration'], movie_data[ genre ] ) ) ),
                  'totsize': sum(list(map(lambda entry: entry['totsize'],  movie_data[ genre ] ) ) ) } for
        genre in movie_data }
    totnum  = sum(list(map(lambda genre: sorted_by_genres[ genre ][ 'totnum' ], sorted_by_genres ) ) )
    totdur  = sum(list(map(lambda genre: sorted_by_genres[ genre ][ 'totdur' ], sorted_by_genres ) ) )
    totsize = sum(list(map(lambda genre: sorted_by_genres[ genre ][ 'totsize'], sorted_by_genres ) ) )
    return key, totnum, totdur, totsize, sorted_by_genres

def _get_library_data_show(
        key, token, fullURL = 'http://localhost:32400',
        sinceDate = None, num_threads = 2 * multiprocessing.cpu_count( ),
        timeout = None ):
    assert( num_threads >= 1 )
    params = { 'X-Plex-Token' : token }
    if sinceDate is None:
        sinceDate = datetime.datetime.strptime( '1900-01-01', '%Y-%m-%d' ).date()
    response = requests.get( '%s/library/sections/%d/all' % ( fullURL, key ),
                             params = params, verify = False, timeout = timeout )
    if response.status_code != 200:
        logging.debug('ERROR TANIM: COULD NOT REACH PLEX LIBRARIES AT %s/library/sections/%d/all' % ( fullURL, key ) )
        return None

    logging.debug('SUCCESS AT %s/library/sections/%d/all' %
                  ( fullURL, key ) )
    
    def _valid_videlem( elem ):
        if elem.name != 'video':
            return False
        if len( elem.find_all('media')) != 1:
            return False
        media_elem = elem.find( 'media' )
        if len(set([ 'duration', 'bitrate' ]) -
               set( media_elem.attrs ) ) != 0:
            return False
        part_elem = media_elem.find( 'part' )
        return 'size' in part_elem.attrs
    
    #
    ## for videlems in shows
    ## videlem.get('index') == episode # in season
    ## videlem.get('parentindex') == season # of show ( season 0 means Specials )
    ## videlem.get('originallyavailableat') == when first aired
    def _get_show_data( input_data ):
        times_requests_given = [ ]
        cont =    input_data[ 'cont' ]
        session = input_data[ 'session' ]
        slist =   input_data[ 'slist' ]
        t0 =      input_data[ 't0' ]
        timeout = input_data[ 'timeout' ]
        indices = input_data[ 'indices' ]
        #
        html = BeautifulSoup( cont, 'lxml' )
        direlems = html.find_all('directory')
        tvdata_tup = [ ]
        for idx in indices:
            direlem = direlems[ idx ]
            show = unescape( direlem['title'] )
            if 'summary' in direlem.attrs: summary = direlem['summary']
            else: summary = ''
            if 'art' in direlem.attrs: picurl = '%s%s' % ( fullURL, direlem.get('art') )
            else: picurl = None
            newURL = urljoin( fullURL, direlem['key'] )
            resp2 = session.get( newURL, params = params, verify = False, timeout = timeout )
            times_requests_given.append( time.time( ) - t0 )
            if resp2.status_code != 200: continue
            h2 = BeautifulSoup( resp2.content, 'lxml' )
            leafElems = list( filter(lambda le: 'allLeaves' not in le['key'], h2.find_all('directory') ) )
            if len(leafElems) == 0: continue
            seasons = { }
            showdata = {
                'title' : show,
                'summary' : summary,
                'picurl' : picurl
            }
            for idx, leafElem in enumerate(leafElems):
                newURL = urljoin( fullURL, leafElem[ 'key' ] )
                resp3 = session.get( newURL, params = params, verify = False, timeout = timeout )
                times_requests_given.append( time.time( ) - t0 )
                h3 = BeautifulSoup( resp3.content, 'lxml' )
                for videlem in h3.find_all( _valid_videlem ):
                    if datetime.datetime.fromtimestamp( float( videlem['addedat'] ) ).date() < sinceDate:
                        continue
                    seasno = int( videlem['parentindex'] )
                    epno = int( videlem[ 'index' ] )
                    pthumb = videlem.get( 'parentthumb' )
                    if pthumb is not None: seasonpicurl = '%s%s' % ( fullURL, videlem.get( 'parentthumb' ) )
                    else: seasonpicurl = fullURL
                    episodepicurl = '%s%s' % ( fullURL, videlem.get( 'thumb' ) )
                    episodesummary = videlem.get('summary')
                    try:
                        dateaired = datetime.datetime.strptime(
                            videlem['originallyavailableat'], '%Y-%m-%d' ).date( )
                    except:
                        dateaired = datetime.datetime.strptime( '1900-01-01', '%Y-%m-%d' ).date( )
                    title = videlem[ 'title' ]
                    duration = 1e-3 * int( videlem[ 'duration' ] )
                    media_elem = videlem.find('media')
                    bitrate = int( media_elem[ 'bitrate' ] ) * 1e3 / 8.0
                    part_elem = media_elem.find('part')
                    filename = part_elem[ 'file' ]
                    size = int( part_elem[ 'size' ] )
                    seasons.setdefault( seasno, { } )
                    if 'episodes' not in seasons[ seasno ]:
                        seasons[ seasno ].setdefault( 'episodes', { } )
                        seasons[ seasno ][ 'seasonpicurl' ] = seasonpicurl
                    seasons[ seasno ]['episodes'][ epno ] = {
                        'title' : title,
                        'episodepicurl' : episodepicurl,
                        'date aired' : dateaired,
                        'summary' : episodesummary,
                        'duration' : duration,
                        'size' : size,
                        'path' : filename }
                    #
                    ## look for directors and writers
                    director_elems = videlem.find_all( 'director' )
                    if len( director_elems ) != 0:
                        directors = list(
                            map(lambda elem: elem['tag'].strip( ),
                                filter(lambda elem: 'tag' in elem.attrs,
                                       director_elems ) ) )
                        seasons[ seasno ]['episodes'][ epno ][ 'director' ] = directors
                    writer_elems = videlem.find_all( 'writer' )
                    if len( writer_elems ) != 0:
                        writers = list(
                            map(lambda elem: elem['tag'].strip( ),
                                filter(lambda elem: 'tag' in elem.attrs,
                                       writer_elems ) ) )
                        seasons[ seasno ]['episodes'][ epno ][ 'writer' ] = writers
                                                                              
            showdata[ 'seasons' ] = seasons
            tvdata_tup.append( ( show, showdata ) )
        slist.append( times_requests_given )
        return tvdata_tup
    
    num_direlems = len( BeautifulSoup( response.content, 'lxml' ).find_all('directory' ) )
    max_of_num_vals = max( num_direlems, multiprocessing.cpu_count( ) )
    act_num_threads = min( num_threads, max_of_num_vals )
    with multiprocessing.Pool( processes = act_num_threads ) as pool:
        #
        ## manager with shared memory objects
        manager = Manager( )
        shared_list = manager.list( )
        #
        ## setting up a connection pool to minimize the number of connections we have
        sess = requests.Session( )
        sess.mount( 'https://', requests.adapters.HTTPAdapter(
            pool_connections = act_num_threads,
            pool_maxsize = act_num_threads ) )
        sess.mount( 'http://', requests.adapters.HTTPAdapter(
            pool_connections = act_num_threads,
            pool_maxsize = act_num_threads ) )
        #
        ## multiprocess chunking of input data among act_num_threads processes
        time0 = time.time( )
        input_tuples = list(
            map(lambda idx: {
                'cont'    : response.content,
                'session' : sess,
                'slist'   : shared_list,
                't0'      : time0,
                'timeout' : timeout,
                'indices' : list( range( idx, num_direlems, act_num_threads ) ) },
                range( act_num_threads ) ) )
        #
        ## final result reduced after a multiprocessing map
        tvdata = dict(
            chain.from_iterable(filter(
                None, pool.map( _get_show_data, input_tuples ) ) ) )
        total_times_requests_given = numpy.sort( numpy.array(
            list( chain.from_iterable( shared_list ) ) ) )
        dts = total_times_requests_given[1:] - total_times_requests_given[:-1]
        logging.debug( 'total number of requests given = %d.' % len( total_times_requests_given ) )
        logging.debug( 'minimum time between requests = %0.3e seconds.' % dts.min( ) )
        logging.debug( 'maximum time between requests = %0.3e seconds.' % dts.max( ) )
        logging.debug( 'average time between requests = %0.3e seconds.' % dts.mean( ) )            
        return key, tvdata

def _get_library_stats_show(
        key, token, fullURL = 'http://localhost:32400',
        sinceDate = None ):
    _, tvdata = _get_library_data_show( key, token, fullURL = fullURL,
                                        sinceDate = sinceDate )
    numTVshows = len( tvdata )
    numTVeps = sum(list(
        map(lambda show:
            sum(list(
                map(lambda seasno: len( tvdata[ show ]['seasons'][ seasno ]['episodes'] ),
                    tvdata[ show ]['seasons'] ) ) ),
            tvdata ) ) )
    totdur = sum(list(
        map(lambda show:
            sum(list(
                map(lambda seasno:
                    sum(list(
                        map(lambda epno: tvdata[ show ]['seasons'][ seasno ]['episodes'][epno]['duration'],
                            tvdata[ show ]['seasons'][ seasno ]['episodes'] ) ) ),
                    tvdata[ show ]['seasons'] ) ) ),
            tvdata ) ) )
    totsize = sum(list(
        map(lambda show:
            sum(list(
                map(lambda seasno:
                    sum(list(
                        map(lambda epno: tvdata[ show ]['seasons'][ seasno ]['episodes'][epno]['size'],
                            tvdata[ show ]['seasons'][ seasno ]['episodes'] ) ) ),
                    tvdata[ show ]['seasons'] ) ) ),
            tvdata ) ) )
    return key, numTVeps, numTVshows, totdur, totsize

def _get_library_stats_artist( key, token, fullURL = 'http://localhost:32400',
                               sinceDate = None ):
    _, music_data = _get_library_data_artist(
        key, token, fullURL = fullURL, sinceDate = sinceDate )
    num_artists = len( music_data )
    num_albums = sum(list(
        map(lambda artist: len( music_data[ artist ] ), music_data ) ) )
    num_songs = sum(list(
        map(lambda artist: sum(list(
            map(lambda album: len( music_data[ artist ][ album ][ 'tracks' ] ),
                music_data[ artist ] ) ) ),
            music_data ) ) )
    totdur = sum(list(
        map(lambda artist: sum(list(
            map(lambda album: sum(list(
                map(lambda track: track[ 'duration' ],
                    music_data[ artist ][ album ][ 'tracks' ] ) ) ),
                music_data[ artist ] ) ) ),
            music_data ) ) )
    totsize = sum(list(
        map(lambda artist: sum(list(
            map(lambda album: sum(list(
                map(lambda track: track[ 'size' ],
                    music_data[ artist ][ album ][ 'tracks' ] ) ) ),
                music_data[ artist ] ) ) ),
            music_data ) ) )                
    return key, num_songs, num_albums, num_artists, totdur, totsize

def _get_library_data_artist( key, token, fullURL = 'http://localhost:32400',
                              sinceDate = None, num_threads = 2 * multiprocessing.cpu_count( ),
                              timeout = None ):
    assert( num_threads >= 1 )
    params = { 'X-Plex-Token' : token }
    if sinceDate is None:
        sinceDate = datetime.datetime.strptime( '1900-01-01', '%Y-%m-%d' ).date( )
        
    response = requests.get( '%s/library/sections/%d/all' % ( fullURL, key ),
                             params = params, verify = False, timeout = timeout )
    if response.status_code != 200:
        logging.error('ERROR: COULD NOT REACH PLEX LIBRARIES AT %s/library/sections/%d/all' %
                      ( fullURL, key ) )
        return None
    
    def valid_track( track_elem ):
        if len(list(track_elem.find_all('media'))) != 1:
            return False
        media_elem = max( track_elem.find_all('media') )
        if len(set([ 'bitrate', 'duration' ]) -
               set(media_elem.attrs)) != 0:
            return False
        return True
    #
    def _get_artist_data( input_data ):
        cont =    input_data[ 'cont' ]
        session = input_data[ 'session' ]
        timeout = input_data[ 'timeout' ]
        indices = input_data[ 'indices' ]
        #
        html = BeautifulSoup( cont, 'lxml' )
        artist_elems = html.find_all('directory')
        song_data_sub = [ ]
        for idx in indices:
            artist_elem = artist_elems[ idx ]
            newURL = '%s%s' % ( fullURL, artist_elem.get('key') )
            resp2 = session.get( newURL, params = params, verify = False, timeout = timeout )        
            if resp2.status_code != 200: continue
            h2 = BeautifulSoup( resp2.content, 'lxml' )
            album_elems = list( h2.find_all('directory') )
            artist_name = artist_elem[ 'title' ]
            artist_data = { }
            for album_elem in album_elems:
                newURL = '%s%s' % ( fullURL, album_elem.get('key') )
                resp3 = session.get( newURL, params = params, verify = False, timeout = timeout )
                if resp3.status_code != 200: continue
                h3 = BeautifulSoup( resp3.content, 'lxml' )
                track_elems = filter(valid_track, h3.find_all( 'track' ) )
                album_name = album_elem[ 'title' ]
                artist_data.setdefault( album_name, [ ] )
                tracks = [ ]
                if 'thumb' in album_elem.attrs: picurl = '%s%s' % ( fullURL, album_elem.get('thumb') )
                else: picurl = None
                if 'year' in album_elem.attrs: year = int( album_elem.get('year'))
                else: year = 1900
                for track_elem in track_elems:
                    if datetime.datetime.fromtimestamp( float(
                            track_elem.get('addedat') ) ).date() < sinceDate:
                        continue
                    media_elem = max(track_elem.find_all('media'))
                    duration = 1e-3 * int( media_elem[ 'duration' ] )
                    bitrate = int( media_elem[ 'bitrate' ] ) * 1e3 / 8.0
                    curdate = datetime.datetime.fromtimestamp( float( track_elem[ 'addedat' ] ) ).date( )
                    track_name = track_elem[ 'title' ]
                    if 'index' in track_elem.attrs: track = int( track_elem.get('index'))
                    else: track = 0
                    tracks.append(
                        { 'track_name' : track_name,
                          'curdate' : curdate,
                          'duration' : duration,
                          'size' : bitrate * duration,
                          'track' : track } )
                if len( tracks ) == 0: continue
                artist_data[ album_name ] = {
                    'year' : year,
                    'picurl' : picurl,
                    'tracks' : sorted(tracks, key = lambda track: track[ 'track' ] ) }
            if len( artist_data ) == 0: continue
            song_data_sub.append( ( artist_name, artist_data ) )
        return song_data_sub

    act_num_threads = max( num_threads, multiprocessing.cpu_count( ) )
    len_artistelems = len( BeautifulSoup( response.content, 'lxml' ).find_all('directory') )
    
    s = requests.Session( )
    s.mount( 'https://', requests.adapters.HTTPAdapter(
        pool_connections = act_num_threads,
        pool_maxsize = act_num_threads ) )
    s.mount( 'http://', requests.adapters.HTTPAdapter(
        pool_connections = act_num_threads,
        pool_maxsize = act_num_threads ) )
    
    with multiprocessing.Pool( processes = act_num_threads ) as pool:
        input_tuples = list(
            map(lambda idx: {
                'cont'    : response.content,
                'session' : s,
                'timeout' : timeout,
                'indices' : list(range( idx, len_artistelems, act_num_threads ) ) },
                range( act_num_threads ) ) )
        song_data = dict(chain.from_iterable(pool.map(
            _get_artist_data, input_tuples ) ) )
        #
        ## now go through each artist + album. If nothing there, then pop.
        for artist in song_data:
            albums_to_pop = set(filter(lambda album: len( song_data[ artist ][ album ] ) == 0, song_data[ artist ] ) )
            for album in albums_to_pop: song_data[ artist ].pop( album )

        #
        ## now pop the artist that have no albums
        artists_to_pop = set(filter(lambda artist: len( song_data[ artist ] ) == 0, song_data ) )
        for artist in artists_to_pop: song_data.pop( artist )
        
        return key, song_data

def get_movies_libraries( token, fullURL = 'http://localhost:32400' ):
    """
    Returns a :py:class:`list` of the key numbers of all Plex movie libraries on the Plex_ server.

    :param str token: the Plex_ server access token.
    :param str fullURL: the Plex_ server address.

    :returns: a :py:class:`list` of the Plex_ movie library key numbers.
    :rtype: list.
    """
    params = { 'X-Plex-Token' : token }
    response = requests.get(
        '%s/library/sections' % fullURL, params = params,
        verify = False )
    if response.status_code != 200: return None
    html = BeautifulSoup( response.content, 'lxml' )
    library_dict = { int( direlem['key'] ) : ( direlem['title'], direlem['type'] ) for
                     direlem in html.find_all('directory') }
    return sorted(set(filter(lambda key: library_dict[ key ][1] == 'movie',
                             library_dict ) ) )

def get_library_data( title, token, fullURL = 'http://localhost:32400',
                      num_threads = 2 * multiprocessing.cpu_count( ), timeout = None ):
    """
    Returns the data on the specific Plex library, as a :py:class:`dict`. This lower level functionality lives in the same space as `PlexAPI <https://python-plexapi.readthedocs.io/en/latest>`_. Three types of library data can be returned: movies, TV shows, and music.
    
      * Movie data has this JSON like structure. ``moviedata`` is an example movie data dictionary.

        * ``moviedata`` is a :py:class:`dict` whose keys (of type :py:class:`str`) are the main movie genres in the Plex_ library, such as ``comedy``.

        * Each value in ``moviedata[<genre>]``  is a :py:class:`list` of movies of that (main) genre.
        
        * Each ``movie`` in ``moviedata[<genre>]`` is a :py:class:`dict` with the following ten keys and values.
        
          * ``title``: :py:class:`str` movie's name.
          * ``rating``: :py:class:`float` the movie's quality rating as a number between ``0.0`` and ``10.0``.
          * ``contentrating``: :py:class:`str` the `MPAA content rating <https://en.wikipedia.org/wiki/Motion_Picture_Association_of_America_film_rating_system>`_ for the movie (such as ``PG``, ``PG-13``, ``R``, or ``NR``).
          * ``picurl``: :py:class:`str` URL of the movie's poster on the Plex_ server.
          * ``releasedate``: :py:class:`date <datetime.date>` of when the movie was first released.
          * ``addedat``: :py:class:`date <datetime.date>` of when the movie was added to the Plex_ server.
          * ``summary``: :py:class:`str` plot summary of the movie.
          * ``duration``: :py:class:`float` movie's duration in seconds.
          * ``totsize``: :py:class:`int` size of the movie file in bytes.
          * ``localpic``: :py:class:`bool` currently unused variable, always ``True``.
          
        * An example ``moviedata`` :py:class:`dict` with one genre (``comedy``) and ten highly rated movies can be found in :download:`moviedata example </_static/moviedata_example.json>` in JSON format.

      * TV data has this JSON like structure.  ``tvdata`` is an example TV data dictionary.
      
        * ``tvdata`` is a :py:class:`dict` whose keys are the individual TV shows.
        
        * Each value in ``tvdata[<showname>]`` is a dictionary with four keys: ``title`` (:py:class:`str` name of the show, <showname>), ``summary`` (:py:class:`str` description of the show), ``picturl`` (:py:class:`str` URL of the poster for the show), and ``seasons`` (:py:class:`dict` whose keys are the seasons of the show).
        
        * ``tvdata[<showname>]['seasons']`` is a :py:class:`dict` whose keys are the seasons. If the show has specials, then those episodes are in season 0.
        
          * this :py:class:`dict` has two keys: ``seasonpicurl`` (:py:class:`str` URL of the poster for the season), and ``episodes`` (:py:class:`dict` of the episodes for that season).
          * ``tvdata[<showname>]['seasons']['episodes']`` is a :py:class:`dict` whose keys are the episode numbers, and whose value is a :py:class:`dict` with the following nine keys and values.
          
            * ``title``: :py:class:`str` title of the episode.
            * ``episodepicurl``: :py:class:`str` URL of the poster of the episode.
            * ``date aired``: :py:class:`date <datetime.date>` of when the episode first aired.
            * ``summary``: :py:class:`str` summary of the episode's plot.
            * ``duration:``: :py:class:`float` episode duration in seconds.
            * ``size``: :py:class:`int` size of the episode file in bytes.
            * ``path``: :py:class:`str` path, on the Plex_ server, of the episode file.
            * ``director``: :py:class:`list` of the episode's directors.
            * ``writer``: :py:class:`list` of the episode's writers.
            
        * An example ``tvdata`` :py:class:`dict` with one finished HBO show, `The Brink <https://en.wikipedia.org/wiki/The_Brink_(TV_series)>`_, can be found in :download:`tvdata example </_static/tvdata_example.json>` in JSON format.

      * Music data has this structure.
    
    :param str title: the name of the library.
    :param str token: the Plex_ server access token.
    :param str fullURL: the Plex_ server address.
    :param int num_threads: the number of concurrent threads used to access the Plex_ server and get the library data.
    :param int timeout: optional time, in seconds, to wait for an HTTP conection to the Plex_ server.
    
    :returns: a dictionary of library data on the Plex server.
    :rtype: dict
    
    """
    time0 = time.time( )
    params = { 'X-Plex-Token' : token }
    response = requests.get( '%s/library/sections' % fullURL, params = params,
                             verify = False, timeout = timeout )
    if response.status_code != 200:
        logging.error( "took %0.3f seconds to get here in get_library_data, library = %s." %
                      ( time.time( ) - time0, title ) )
        logging.error( "no data found. Exiting..." )
        return None
    html = BeautifulSoup( response.content, 'lxml' )
    library_dict = { direlem[ 'title' ] : ( int( direlem['key'] ), direlem['type'] ) for
                     direlem in html.find_all('directory') }
    assert( title in library_dict )
    key, mediatype = library_dict[ title ]
    if mediatype == 'movie':
        _, data = _get_library_data_movie( key, token, fullURL = fullURL,
                                           num_threads = num_threads, timeout = timeout )
    elif mediatype == 'show':
        _, data =  _get_library_data_show( key, token, fullURL = fullURL,
                                           num_threads = num_threads, timeout = timeout )
    elif mediatype == 'artist':
        _, data = _get_library_data_artist( key, token, fullURL = fullURL,
                                            num_threads = num_threads, timeout = timeout )
    else:
        logging.error( "took %0.3f seconds to get here in get_library_data, library = %s." %
                      ( time.time( ) - time0, title ) )
        logging.error( "could not find a library with name = %s. Exiting..." % title )
        return None
    logging.info( "took %0.3f seconds to gete here in get_library_data, library = %s." %
                  ( time.time( ) - time0, title ) )
    return data

def get_library_stats( key, token, fullURL = 'http://localhost:32400', sinceDate = None ):
    """
    Gets summary data on a specific library on the Plex_ server. returned as a :py:class:`dict`. The Plex_ library ``mediatype`` can be one of ``movie`` (Movies), ``show`` (TV shows), or ``artist`` (Music). The common part of the :py:class:`dict` looks like the following.

    .. code-block:: python

       {
         'fullURL'   : FULLURL,   # URL of the Plex server in the form of https://IP-ADDRESS:PORT
         'title'     : TITLE,     # name of the Plex library
         'mediatype' : MEDIATYPE, # one of "movie", "show", or "artist"
       }

    Here are what the extra parts of this dictionary look like.

    * If the library is a ``movie`` (Movies), then

      .. code-block:: python
         
         {
           'num_movies' : num_movies,     # total number of movies in this library.
           'totdur'     : totdur,         # total duration in seconds of all movies.
           'totsize'    : totsize,        # total size in bytes of all movies.
           'genres'     : sorted_by_genre # another dictionary subdivided by, showing # movies, size, and duration by genre.
         }
      
      ``sorted_by_genre`` is also a :py:class:`dict`, whose keys are the separate movie genres in this Plex_ library (such as ``action``, ``horror``, ``comedy``). Each value in this dictionary is another dictionary that looks like this.

      .. code-block:: python

         {
           'num_movies' : num_movies_gen, # total number of movies in this genre.
           'totdur'     : totdur_gen,     # total duration in seconds of movies in this genre.
           'totsize'    : totsize_gen,    # total size in bytes of movies in this genre.
         }

    * If the library is a ``show`` (TV Shows), then
    
      .. code-block:: python
         
         {
           'num_tveps'   : num_tveps,   # total number of TV episodes in this library.
           'num_tvshows' : num_tvshows, # total number of TV shows in this library.
           'totdur'      : totdur,      # total duration in seconds of all TV shows.
           'totsize'     : totsize      # otal size in bytes of all TV shows.
         }

    * If the library is an ``artist`` (Music), then

      .. code-block:: python

         {
           'num_songs'   : num_songs,   # total number of songs in this library.
           'num_albums'  : num_albums,  # total number of albums in this library.
           'num_artists' : num_artists, # total number of unique artists in this library.
           'totdur'      : totdur,      # total duration in seconds of all songs.
           'totsize'     : totsize      # total size in bytes of all songs.
         }

    :param int key: the key number of the library in the Plex_ server.
    :param str token: the Plex_ server access token.
    :param str fullURL: the Plex_ server address.
    :param sinceDate: If defined, only tally the library media that was added after this date. This is of type :py:class:`date <datetime.date>`.
    
    :returns: a dictionary of summary statistics on the Plex_ library.
    :rtype: dict

    .. seealso:: :py:meth:`get_library_data <plexcore.plexcore.get_library_data>`.
    """
    library_dict = get_libraries( token, fullURL = fullURL, do_full = True )
    if library_dict is None: return None
    assert( key in library_dict )
    title, mediatype = library_dict[ key ]
    common_data = {
        'fullURL'   : fullURL,
        'title'     : title,
        'mediatype' : mediatype
    }
    if mediatype == 'movie':
        data = _get_library_stats_movie( key, token, fullURL = fullURL, sinceDate = sinceDate )
        if data is None: return None
        actkey, num_movies, totdur, totsize, sorted_by_genre = data
        extra_vals = {
            'num_movies' : num_movies,
            'totdur'     : totdur,
            'totsize'    : totsize,
            'genres'     : sorted_by_genre
        }
    elif mediatype == 'show':
        data =  _get_library_stats_show( key, token, fullURL = fullURL, sinceDate = sinceDate )
        if data is None: return None
        actkey, num_tveps, num_tvshows, totdur, totsize = data
        extra_vals = {
            'num_tveps'   : num_tveps,
            'num_tvshows' : num_tvshows,
            'totdur'      : totdur,
            'totsize'     : totsize
        }
    elif mediatype == 'artist':
        data = _get_library_stats_artist( key, token, fullURL = fullURL, sinceDate = sinceDate )
        if data is None:
            return None
        actkey, num_songs, num_albums, num_artists, totdur, totsize = data
        extra_vals = {
            'num_songs'   : num_songs,
            'num_albums'  : num_albums,
            'num_artists' : num_artists,
            'totdur'      : totdur,
            'totsize'     : totsize
        }
    else: return common_data
    return dict( list( common_data.items( ) ) +
                 list( extra_vals.items( ) ) )
        
def get_libraries( token, fullURL = 'http://localhost:32400', do_full = False, timeout = None ):
    """
    Gets the :py:class:`dict` of libraries on the Plex_ server. The key is the library number, while the value can be either the name of the library or a :py:class:`tuple` of library name and library type

    :param str token: the Plex_ server access token.
    
    :param str fullURL: the Plex_ server address.

    :param bool do_full: if `False`, then the values are the names of the Plex_ libraries. If ``True``, then the values are :py:class:`tuple` of the library name and library type. The library type can be one of ``movie``, ``show``, or ``artist``.
    
    :returns: a dictionary of libraries on the Plex_ server.
    :rtype: :py:class:`dict`.

    .. seealso:
    
    * :py:meth:`fill_out_movies_stuff <plexcore.plexcore.fill_out_movies_stuff>`.
    * :py:meth:`get_movie_titles_by_year <plexcore.plexcore_attic.get_movie_titles_by_year>`.
    * :py:meth:`get_lastN_movies <plexcore.plexcore.get_lastN_movies>`.
    * :py:meth:`get_summary_data_music_remote <plexemail.plexemail.get_summary_data_music_remote>`.
    * :py:meth:`get_summary_data_television_remote <plexemail.plexemail.get_summary_data_television_remote>`.
    * :py:meth:`get_summary_data_movies_remote <plexemail.plexemail.get_summary_data_movies_remote>`.
    
    """
    params = { 'X-Plex-Token' : token }
    response = requests.get(
        '%s/library/sections' % fullURL,
        params = params, verify = False, timeout = timeout )
    if response.status_code != 200:
        logging.error( "error, got status code = %d." %
                       response.status_code )
        return None
    html = BeautifulSoup( response.content, 'lxml' )
    if not do_full:
        return dict( map( lambda direlem: ( int( direlem['key'] ), direlem['title'] ),
                          html.find_all('directory') ) )
    else:
        return dict( map( lambda direlem: ( int( direlem['key'] ), ( direlem['title'], direlem['type'] ) ),
                          html.find_all('directory') ) )

def fill_out_movies_stuff( token, fullURL = 'http://localhost:32400', verify = True ):
    """
    Creates a :py:class:`tuple`. The first element of the :py:class:`tuple` is a :py:class:`list` of movies from this Plex_ server. Each element in that list is a :py:class:`dict` with the following structure with 12 keys and values, as shown in this example

    .. code-block:: python

       { 'title': 'Blue Collar',
         'rating': 10.0,
         'contentrating': 'R',
         'picurl': 'https://24.5.231.186:32400/library/metadata/46001/art/1569656413',
         'releasedate': datetime.date(1978, 2, 10),
         'addedat': datetime.date(2019, 6, 6),
         'summary': "Fed up with mistreatment at the hands of both management and union brass, and coupled with financial hardships on each man's end, three auto assembly line workers hatch a plan to rob a safe at union headquarters.",
         'duration': 6820.394,
         'totsize': 935506414.0,
         'localpic': True,
         'imdb_id': 'tt0077248',
         'genre': 'drama'
       }

    The second element of the :py:class:`tuple` is a :py:class:`list` of movie genres on the Plex_ server.

    :param str token: the Plex_ server access token.
    :param str fullURL: the Plex_ server address.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: a :py:class:`tuple` of two lists. The first is a list of all the movies on the Plex_ server. The second is a list of all the movie genres found on the Plex server.
    :rtype: :py:class:`tuple`.
    """
    unified_movie_data = { }
    movie_data_rows = [ ]
    problem_rows = [ ]
    plex_libraries = get_libraries( token, fullURL, do_full = True )
    movie_keys = set(filter(lambda key: plex_libraries[ key ][ -1 ] == 'movie',
                            plex_libraries ) )
    library_names = list(map(lambda key: plex_libraries[ key ][ 0 ], movie_keys ) )
    for library_name in library_names:
        movie_data = get_library_data( library_name, token, fullURL )
        for genre in movie_data:
            unified_movie_data.setdefault( genre, [] )
            unified_movie_data[ genre ] += movie_data[ genre ]
    #
    ##
    genres = sorted( unified_movie_data )
    def _solve_problem_row( dat ):
        dat_copy = dat.copy( )
        #
        ## first look for the movie
        movies_here = plextmdb.get_movies_by_title(
            dat_copy[ 'title' ], verify = verify )
        movies_here = list(filter(
            lambda movie: 'release_date' in movie and
            'poster_path' in movie and
            'overview' in movie and
            'vote_average' in movie, movies_here ) )
        if len( movies_here ) != 0:
            movie_here = movies_here[ 0 ]
        else: movie_here = None
        if movie_here is not None:
            dat_copy[ 'rating' ] = movie_here[ 'vote_average' ]
            dat_copy[ 'picurl' ] = movie_here[ 'poster_path' ]
            dat_copy[ 'localpic' ] = False
            dat_copy[ 'summary' ] = movie_here[ 'overview' ]                        
            if dat_copy[ 'releasedate' ] is None:
                dat_copy[ 'releasedate' ] = movie_here['release_date'].date( )
            if 'imdb_id' in movie_here:
                dat_copy[ 'imdb_id' ] = movie_here[ 'imdb_id' ]
        else:
            if dat_copy[ 'releasedate' ] is None:
                dat_copy[ 'releasedate' ] = datetime.datetime.strptime(
                    '1900-01-01', '%Y-%m-%d' ).date( )
            if dat_copy[ 'rating' ] is None: dat_copy[ 'rating' ] = 0.0
        return dat_copy
        
    for genre in unified_movie_data:
        for dat in unified_movie_data[ genre ]:
            dat_copy = dat.copy( )
            dat_copy[ 'genre' ] = genre
            #
            ## possible cannot find the movie situation here
            len_summary = len( dat_copy[ 'summary' ].strip( ) )
            if dat_copy[ 'releasedate' ] is None or len_summary == 0 or dat_copy[ 'rating' ] is None:
                problem_rows.append( dat_copy )
                continue
            assert( 'localpic' in dat_copy )
            movie_data_rows.append( dat_copy )
            
    with multiprocessing.Pool( processes = multiprocessing.cpu_count( ) ) as pool:
        logging.info( 'number of problem rows: %d.' % len( problem_rows ) )
        movie_data_rows += list(
            pool.map( _solve_problem_row, problem_rows ) )
        return movie_data_rows, genres

def get_lastN_movies( lastN, token, fullURL = 'http://localhost:32400',
                      useLastNewsletterDate = True ):
    """
    Returns the last :math:`N` movies that were uploaded to the Plex_ server, either after the last date at which a newsletter was sent out or not.
    
    :param int lastN: the last :math:`N` movies to be sent out. Must be :math:`\ge 1`.
    
    :param str token: the Plex_ server access token.
    
    :param str fullURL: the Plex_ server address.
    
    :param bool useLastNewsletterDate: if ``True``, then find the last movies after the date of the previous newsletter. If ``False``. don't make that restriction.

    :returns: a :py:class:`list` of Plex_ movies. Each element in the list is  :py:class:`tuple` of the movie: title, year, :py:class:`datetime <datetime.datetime>`, and `The Movie Database <TMDB_>` URL of the movie.
    :rtype: :py:class:`dict`.

    .. seealso:
    
    * :py:meth:`get_summary_data_movies_remote <plexemail.plexemail.get_summary_data_movies_remote>`.
    * :py:meth:`get_summary_data_movies <plexemail.plexemail.get_summary_data_movies>`.
    
    .. _TMDB: https://www.themoviedb.org
    """
    assert( isinstance( lastN, int ) )
    assert( lastN > 0 )
    libraries_dict = get_libraries( fullURL = fullURL, token = token, do_full = True )
    if libraries_dict is None: return None
    keynums = set(filter(lambda keynum: libraries_dict[ keynum ][ 1 ] == 'movie', libraries_dict ) )
    if len( keynums ) == 0: return None
    #
    def _get_lastN( keynum ):
        params = { 'X-Plex-Token' : token }
        response = requests.get('%s/library/sections/%d/recentlyAdded' % ( fullURL, keynum ),
                                params = params, verify = False )
        if response.status_code != 200: return None
        html = BeautifulSoup( response.content, 'lxml' )
        valid_video_elems = sorted(filter(lambda elem: len( set([ 'addedat', 'title', 'year' ]) -
                                                            set( elem.attrs ) ) == 0,
                                          html.find_all('video') ),
                                   key = lambda elem: -int( elem[ 'addedat' ] ) )[:lastN]
        if useLastNewsletterDate:
            lastnewsletterdate = get_current_date_newsletter( )
            if lastnewsletterdate is not None:
                valid_video_elems = filter(lambda elem: datetime.datetime.fromtimestamp(
                    int( elem['addedat'] ) ).date( ) >=
                                           lastnewsletterdate, valid_video_elems )
        return list(map(lambda elem: (
            elem['title'], int( elem['year'] ),
            datetime.datetime.fromtimestamp( int( elem['addedat'] ) ).
            replace(tzinfo = pytz.timezone( 'US/Pacific' ) ),
            plextmdb.get_movie( elem['title'], verify = False ) ),
                        valid_video_elems ) )

    return sorted( chain.from_iterable(map(_get_lastN, keynums ) ),
                   key = lambda elem: elem[2] )[::-1][:lastN]

def refresh_library( key, library_dict, token, fullURL = 'http://localhost:32400' ):
    """
    Lower level front-end to ``plex_resynclibs.py`` that refreshes a Plex_ server library. Here I use instructions found in this `Plex forum article on URL commands <https://support.plex.tv/hc/en-us/articles/201638786-Plex-Media-Server-URL-Commands>`_.
    
    :param int key: the library number on the Plex_ server.
    
    :param :py:class:`dict` library_dict: the dictionary of libraries. The key is Plex_ server library number, and the value is the library name.
    
    """
    assert( key in library_dict )
    params = { 'X-Plex-Token' : token }
    response = requests.get(
        '%s/library/sections/%d/refresh' % ( fullURL, key ),
        params = params, verify = False )
    assert( response.status_code == 200 )
    logging.info( 'refreshing %s Library...' % library_dict[ key ] )

def oauthCheckGoogleCredentials( ):
    """
    Checks whether the `Google OAuth2`_ authentication settings exist in the SQLite3_ configuration database. The format of the authentication data in the configuration database is,

    .. code-block:: python
    
      { 'access_token': XXXX,
        'client_id': YYYY, 
        'client_secret': ZZZZ,
        'refresh_token': AAAA,
        'token_expiry': BBBB,
        'token_uri': 'https://accounts.google.com/o/oauth2/token',
        'user_agent': None,
        'revoke_uri': 'https://oauth2.googleapis.com/revoke',
        'id_token': None,
        'id_token_jwt': None,
        'token_response': { 'access_token': XXXX,
          'expires_in': 3600,
          'refresh_token': AAAA,
          'scope': 'https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/contacts.readonly https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/musicmanager https://www.googleapis.com/auth/spreadsheets',
          'token_type': 'Bearer' },
        'scopes': ['https://www.googleapis.com/auth/gmail.send',
          'https://spreadsheets.google.com/feeds',
          'https://www.googleapis.com/auth/youtube.readonly',
          'https://www.googleapis.com/auth/contacts.readonly',
          'https://www.googleapis.com/auth/musicmanager'],
        'token_info_uri': 'https://oauth2.googleapis.com/tokeninfo',
        'invalid': False,
        '_class': 'OAuth2Credentials',
        '_module': 'oauth2client.client' }

    If ``data`` is this dictionary, note the scopes defined in the ``data['scopes']`` and ``data['token_response']['scope']``.
    
    :returns: a :py:class:`tuple` of status and message. If the settings are in the database, returns ``( True, 'SUCCESS' )``. If they are not, returns ``( False, 'GOOGLE AUTHENTICATION CREDENTIALS DO NOT EXIST.' )``.
    :rtype: tuple.

    .. seealso::

      * :py:meth:`oauthCheckGoogleCredentials <plexcore.plexcore.oauthCheckGoogleCredentials>`
      * :py:meth:`oauthGetGoogleCredentials <plexcore.plexcore.oauthGetGoogleCredentials>`
      * :py:meth:`oauthGetOauth2ClientGoogleCredentials <plexcore.plexcore.oauthGetOauth2ClientGoogleCredentials>`
      * :py:meth:`oauth_generate_google_permission_url <plexcore.plexcore.oauth_generate_google_permission_url>`
      * :py:meth:`oauth_store_google_credentials <plexcore.plexcore.oauth_store_google_credentials>`

    .. _`Google OAuth2` : https://developers.google.com/identity/protocols/OAuth2
    
    """
    val = session.query( PlexConfig ).filter( PlexConfig.service == 'google' ).first( )
    if val is None:
        return False, 'GOOGLE AUTHENTICATION CREDENTIALS DO NOT EXIST.'
    return True, 'SUCCESS'

def oauthGetGoogleCredentials( verify = True ):
    """
    Gets the `Google Oauth2`_ credentials, stored in the SQLite3_ configuration database, in the form of a refreshed :py:class:`Credentials <google.oauth2.credentials.Credentials>` object. The OAuth2 authentication with this method has not been implemented for services yet.

    :returns: a :py:class:`Credentials <google.oauth2.credentials.Credentials>` form of the `Google Oauth2`_ credentials for various Oauth2 services.
    :rtype: :py:class:`Credentials <google.oauth2.credentials.Credentials>`

    .. seealso::

      * :py:meth:`oauthGetGoogleCredentials <plexcore.plexcore.oauthGetGoogleCredentials>`
      * :py:meth:`oauthGetOauth2ClientGoogleCredentials <plexcore.plexcore.oauthGetOauth2ClientGoogleCredentials>`
      * :py:meth:`oauth_generate_google_permission_url <plexcore.plexcore.oauth_generate_google_permission_url>`
      * :py:meth:`oauth_store_google_credentials <plexcore.plexcore.oauth_store_google_credentials>`
    """
    val = session.query( PlexConfig ).filter( PlexConfig.service == 'google' ).first( )
    if val is None: return None
    cred_data = val.data
    credentials = Credentials.from_authorized_user_info( cred_data )
    s = requests.Session( )
    s.verify = verify
    credentials.refresh( Request( session = s ) )
    return credentials

def oauthGetOauth2ClientGoogleCredentials( ):
    """
    Gets the `Google Oauth2`_ credentials, stored in the SQLite3_ configuration database, in the form of a refreshed :py:class:`AccessTokenCredentials <oauth2client.client.AccessTokenCredentials>` object. This OAuth2 authentication method IS used for all the services accessed by Plexstuff_.

    :returns: a :py:class:`AccessTokenCredentials <oauth2client.client.AccessTokenCredentials>` form of the `Google Oauth2`_ credentials for various Oauth2 services.
    :rtype: :py:class:`AccessTokenCredentials <oauth2client.client.AccessTokenCredentials>`
    
    .. seealso::

      * :py:meth:`oauthCheckGoogleCredentials <plexcore.plexcore.oauthCheckGoogleCredentials>`
      * :py:meth:`oauthGetGoogleCredentials <plexcore.plexcore.oauthGetGoogleCredentials>`
      * :py:meth:`oauth_generate_google_permission_url <plexcore.plexcore.oauth_generate_google_permission_url>`
      * :py:meth:`oauth_store_google_credentials <plexcore.plexcore.oauth_store_google_credentials>`

    .. _Plexstuff: https://plexstuff.readthedocs.io
    """
    val = session.query( PlexConfig ).filter( PlexConfig.service == 'google' ).first( )
    if val is None: return None
    cred_data = val.data
    credentials = oauth2client.client.OAuth2Credentials.from_json(
        json.dumps( cred_data ) )
    return credentials

def oauth_generate_google_permission_url( ):
    """
    Generates a `Google OAuth2`_ web-based flow for all the Google services used in Plexstuff_. Descriptions of OAuth2_ and different flows (web server app, client, etc.)  is almost impossible for me to follow (see `this page on OAuth2 authentication flows <https://auth0.com/docs/api-auth/which-oauth-flow-to-use>`_), I have given up, and I can only understand the specific authentication work flow implemented in Plexstuff_. The authentication process that uses this method is described in :ref:`this subsection <Summary of Setting Up Google Credentials>`. Here are the programmatic steps to finally generate an  :py:class:`AccessTokenCredentials <oauth2client.client.AccessTokenCredentials>` object.
    
      1. Get the  :py:class:`OAuth2WebServerFlow <oauth2client.client.OAuth2WebServerFlow>` and authentication URI.

      .. code-block:: python
      
        flow, auth_uri = oauth_generate_google_permission_url( )

      2. Go to the URL, ``auth_uri``, in a browser, grant permissions, and copy the authorization code in the browser window. This authorization code is referred to as ``authorization_code``.

      3. Create the  :py:class:`AccessTokenCredentials <oauth2client.client.AccessTokenCredentials>` using ``authorization_code``.
    
      .. code-block:: python

        credentials = flow.step2_exchange( authorization_code )

    :returns: a :py:class:`tuple` of two elements. The first element is an OAuth2_ web server flow object of type :py:class:`OAuth2WebServerFlow <oauth2client.client.OAuth2WebServerFlow>`. The second element is the redirection URI that redirects the user to begin the authorization flow.
    :rtype: tuple
    
    .. seealso::

      * :py:meth:`oauthCheckGoogleCredentials <plexcore.plexcore.oauthCheckGoogleCredentials>`
      * :py:meth:`oauthGetGoogleCredentials <plexcore.plexcore.oauthGetGoogleCredentials>`
      * :py:meth:`oauthGetOauth2ClientGoogleCredentials <plexcore.plexcore.oauthGetOauth2ClientGoogleCredentials>`
      * :py:meth:`oauth_store_google_credentials <plexcore.plexcore.oauth_store_google_credentials>`
    
    .. _Oauth2: https://oauth.net/2/
    """
    
    #flow = Flow.from_client_secrets_file(
    #    os.path.join( mainDir, 'resources', 'client_secrets.json' ),
    #    scopes = [ 'https://www.googleapis.com/auth/gmail.send',
    #               'https://www.googleapis.com/auth/contacts.readonly',
    #               'https://www.googleapis.com/auth/youtube.readonly',
    #               'https://spreadsheets.google.com/feeds', # google spreadsheet scope
    #               'https://www.googleapis.com/auth/musicmanager' ], # this is the gmusicapi one
    #    redirect_uri = "urn:ietf:wg:oauth:2.0:oob" )
    #auth_uri = flow.authorization_url( )
    flow = oauth2client.client.flow_from_clientsecrets(
        os.path.join( mainDir, 'resources', 'client_secrets.json' ),
        scope = [ 'https://www.googleapis.com/auth/gmail.send',
                  'https://www.googleapis.com/auth/contacts.readonly',
                  'https://www.googleapis.com/auth/youtube.readonly',
                  'https://www.googleapis.com/auth/spreadsheets', # google spreadsheet scope
                  'https://www.googleapis.com/auth/musicmanager',  # this is the gmusicapi one
                  'https://www.googleapis.com/auth/drive' ], # allow one to upload and download files to google drive
        redirect_uri = "urn:ietf:wg:oauth:2.0:oob" )
    auth_uri = flow.step1_get_authorize_url( )
    return flow, auth_uri

def oauth_store_google_credentials( credentials ):
    """
    Store the `Google OAuth2`_ credentials, in the form of a :py:class:`AccessTokenCredentials <oauth2client.client.AccessTokenCredentials>` object, into the SQLite3_ configuration database.
    
    :param credentials: the :py:class:`AccessTokenCredentials <oauth2client.client.AccessTokenCredentials>` object to store into the database.

    .. seealso::

      * :py:meth:`oauthCheckGoogleCredentials <plexcore.plexcore.oauthCheckGoogleCredentials>`
      * :py:meth:`oauthGetGoogleCredentials <plexcore.plexcore.oauthGetGoogleCredentials>`
      * :py:meth:`oauthGetOauth2ClientGoogleCredentials <plexcore.plexcore.oauthGetOauth2ClientGoogleCredentials>`
      * :py:meth:`oauth_generate_google_permission_url <plexcore.plexcore.oauth_generate_google_permission_url>`
    """
    val = session.query( PlexConfig ).filter( PlexConfig.service == 'google' ).first( )
    if val is not None:
        session.delete( val )
        session.commit( )
    newval = PlexConfig(
        service = 'google',
        data = json.loads( credentials.to_json( ) ) )
    session.add( newval )
    session.commit( )
    
#
## put in the jackett credentials into here
def store_jackett_credentials( url, apikey, verify = True ):
    """
    stores the Jackett_ server's API credentials into the SQLite3_ configuration database.

    :param str url: the Jackett_ server's URL.
    :param str apikey: the Jackett_ server's API key.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: the string ``"SUCCESS"`` if could store the new Jackett_ server credentials. Otherwise, some illuminating error message.
    
    :rtype: str

    .. seealso::

      * :py:meth:`get_jackett_credentials <plexcore.plexcore.get_jackett_credentials>`.
      * :py:meth:`check_jackett_credentials <plexcore.plexcore.check_jackett_credentials>`.
    """
    actURL, status = check_jackett_credentials(
        url, apikey, verify = verify )
    if status != 'SUCCESS': return status
    
    #
    ## now put the stuff inside
    query = session.query( PlexConfig ).filter( PlexConfig.service == 'jackett' )
    val = query.first( )
    if val is not None:
        session.delete( val )
        session.commit( )
    newval = PlexConfig(
        service = 'jackett',
        data = { 'url' : actURL.strip( ),
                 'apikey' : apikey.strip( ) } )
    session.add( newval )
    session.commit( )
    return 'SUCCESS'

def get_jackett_credentials( ):
    """
    retrieves the Jackett_ server's API credentials from the SQLite3_ configuration database.

    :returns: a :py:class:`tuple` of the Jackett_ server's API credentials. First element is the URL of the Jackett_ server. Second element is the API key.

    :rtype: tuple

    .. seealso::

      * :py:meth:`check_jackett_credentials <plexcore.plexcore.check_jackett_credentials>`.
      * :py:meth:`store_jackett_credentials <plexcore.plexcore.store_jackett_credentials>`.
    
    .. _Jackett: https://github.com/Jackett/Jackett
    """
    
    query = session.query( PlexConfig ).filter( PlexConfig.service == 'jackett' )
    val = query.first( )
    if val is None: return None
    data = val.data
    url = data['url'].strip( )
    apikey = data['apikey'].strip( )
    return url, apikey

def check_jackett_credentials( url, apikey, verify = True ):
    """
    validate the Jackett_ server credentials with the provided URL and API key.

    :param str url: the Jackett_ server's URL.
    :param str apikey: the Jackett_ server's API key.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: a :py:class:`tuple`. If successful, this is a tuple of the server's URL and the string ``"SUCCESS"``. If unsuccessful, this is a tuple of :py:class:`NoneType`  and error message string.
    
    :rtype: tuple

    .. seealso::
    
      * :py:meth:`get_jackett_credentials <plexcore.plexcore.get_jackett_credentials>`.
      * :py:meth:`store_jackett_credentials <plexcore.plexcore.store_jackett_credentials>`.
    """
    endpoint = 'api/v2.0/indexers/all/results/torznab/api'
    #
    ## now check that everything works
    ## first, is URL a valid URL?
    if not validators.url( url ):
        return None, "ERROR, %s is not a valid URL" % url

    #
    ## second, add a '/' to end of URL
    actURL = url
    if not actURL.endswith('/'): actURL += '/'
    try:
        #
        ## third, check that we have a valid URL
        response = requests.get(
            urljoin( actURL, endpoint ),
            params = { 'apikey' : apikey, 't' : 'caps' },
            verify = verify )
        if response.status_code != 200:
            return None, "ERROR, invalid jackett credentials"

        html = BeautifulSoup( response.content, 'lxml' )
        error_items = html.find_all('error')
        if len( error_items ) != 0:
            return "ERROR, invalid API key"
        return actURL, 'SUCCESS'
    except Exception as e:
        return None, "ERROR, exception emitted: %s." % str( e )

def get_imgurl_credentials( ):
    """
    retrieves the Imgur_ API credentials from the SQLite3_ configuration database.

    :returns: a :py:class:`dict` of the Imgur_ API credentials. Its structure is,

    .. code-block:: python
    
       { 'clientID': XXXX,
         'clientSECRET': XXXX,
         'clientREFRESHTOKEN': XXXX,
         'mainALBUMID': XXXX,
         'mainALBUMTITLE': XXXX }

    :rtype: dict

    .. seealso::

      * :py:meth:`check_imgurl_credentials <plexcore.plexcore.check_imgurl_credentials>`.
      * :py:meth:`store_imgurl_credentials <plexcore.plexcore.store_imgurl_credentials>`.
    
    .. _Imgur: https://imgur.com/
    """
    val = session.query( PlexConfig ).filter( PlexConfig.service == 'imgurl' ).first( )
    if val is None:
        raise ValueError( "ERROR, COULD NOT FIND IMGUR CREDENTIALS." )
    data_imgurl = val.data
    return data_imgurl

def check_imgurl_credentials(
        clientID, clientSECRET,
        clientREFRESHTOKEN, verify = True ):
    """
    validate the Imgur_ API credentials with the provided API client ID, secret, and refresh token.

    :param str clientID: the Imgur_ client ID.
    :param str clientSECRET: the Imgur_ client secret.
    :param str clientREFRESHTOKEN: the Imgur_ client refresh token.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: whether the new credentials are correct.
    
    :rtype: bool

    .. seealso::

      * :py:meth:`get_imgurl_credentials <plexcore.plexcore.get_imgurl_credentials>`.
      * :py:meth:`store_imgurl_credentials <plexcore.plexcore.store_imgurl_credentials>`.
    
    """
    response = requests.post(
         'https://api.imgur.com/oauth2/token',
        data = {'client_id': clientID,
                'client_secret': clientSECRET,
                'grant_type': 'refresh_token',
                'refresh_token': clientREFRESHTOKEN },
        verify = verify )
    if response.status_code != 200:
        return False
    return True

def store_imgurl_credentials( clientID, clientSECRET, clientREFRESHTOKEN, verify = True ):
    """
    stores the Imgur_ API credentials into the SQLite3_ configuration database.

    :param str clientID: the Imgur_ client ID.
    :param str clientSECRET: the Imgur_ client secret.
    :param str clientREFRESHTOKEN: the Imgur_ client refresh token.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: the string ``"SUCCESS"`` if could store the new Imgur_ credentials. Otherwise, the string ``'ERROR, COULD NOT STORE IMGURL CREDENTIALS.'``.
    
    :rtype: str

    .. seealso::

      * :py:meth:`check_imgurl_credentials <plexcore.plexcore.check_imgurl_credentials>`.
      * :py:meth:`get_imgurl_credentials <plexcore.plexcore.get_imgurl_credentials>`.
    """
    isValid =  check_imgurl_credentials(
        clientID, clientSECRET, clientREFRESHTOKEN, verify = verify )
    if not isValid: return 'ERROR, COULD NOT STORE IMGURL CREDENTIALS.'
    val = session.query( PlexConfig ).filter( PlexConfig.service == 'imgurl' ).first( )
    if val is not None:
        session.delete( val )
        session.commit( )
    newval = PlexConfig(
        service = 'imgurl',
        data = { 'clientID' : clientID,
                 'clientSECRET' : clientSECRET,
                 'clientREFRESHTOKEN' : clientREFRESHTOKEN } )
    session.add( newval )
    session.commit( )
    return 'SUCCESS'
    
def set_date_newsletter( ):
    """
    sets the date of the Plex_ newsletter to :py:meth:`now() <datetime.datetime.now>`.

    .. seealso:: :py:meth:`get_current_date_newsletter <plexcore.plexcore.get_current_date_newsletter>`.
    """
    query = session.query( LastNewsletterDate )
    backthen = datetime.datetime.strptime( '1900-01-01', '%Y-%m-%d' ).date( )
    val = query.filter( LastNewsletterDate.date >= backthen ).first( )
    if val:
        session.delete( val )
        session.commit( )
    datenow = datetime.datetime.now( ).date( )
    lastnewsletterdate = LastNewsletterDate( date = datenow )
    session.add( lastnewsletterdate )
    session.commit( )
