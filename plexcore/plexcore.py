import os, glob, datetime, gspread, logging, sys, numpy, urllib3
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
from urllib.parse import urlencode, urljoin
from itertools import chain
from multiprocessing import Manager
from . import mainDir, session
from . import PlexConfig, LastNewsletterDate, PlexGuestEmailMapping
from plextmdb import plextmdb

# disable insecure request warnings, because do not recall how to get the name of the certificate for a 
# given plex server
requests.packages.urllib3.disable_warnings( )
urllib3.disable_warnings( )

def add_mapping( plex_email, plex_emails, new_emails, replace_existing ):
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
    
    :param dstring: the initial date string.
    
    :returns: its :py:class:`date <datetime.date>` object representation.
    
    :rtype: :py:class:`date <datetime.date>`

    """
    try: return datetime.datetime.strptime( dstring, '%B %d, %Y' ).date( )
    except Exception: return None

def latexToHTML( latexString ):
    """Converts a LaTeX_ string into HTML using Pandoc_, then prettifies the
    intermediate HTML using BeautifulSoup_.

    :param latexString: the initial LaTeX_ string.
    
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
    htmlData = BeautifulSoup( html, 'lxml' )
    pngNames = set(filter(lambda name: name.endswith('.png'),
                          map(lambda img: img['src'], htmlData.find_all('img'))))
    if len( pngNames ) == 0: return htmlData.prettify( )
    if len( pngNames - set( pngDataDict ) ) != 0:
        logging.debug( 'error, some defined figures in latex do not have images.' )
        return htmldata.prettify( )
    for img in htmlData.find_all('img'):
        name = img['src']
        b64data, widthInCM, url = pngDataDict[ name ]
        if doEmbed: img['src'] = "data:image/png;base64," + b64data
        else: img['src'] = url
        img['width'] = "%d" % ( widthInCM / 2.54 * 300 )
    return htmlData.prettify( )

def getTokenForUsernamePassword( username, password, verify = True ):
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
    
def checkServerCredentials( doLocal = False, verify = True ):
    """Returns get a local or remote URL and Plex_ access token to allow for API access to the server.

    :param bool doLocal: optional argument, whether to get a local (``http://localhost:32400``) or remote URL. Default is ``False`` (look for the remote URL).
    
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: a tuple of server URL and Plex_ access token.
    
    :rtype: tuple

    .. _Plex: https://plex.tv

    """
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
        _, fullurl = max( get_owned_servers( token, verify = verify ).items( ) )
        fullurl = 'https://%s' % fullurl
    else: fullurl = 'http://localhost:32400'
    return fullurl, token

def getCredentials( verify = True ):
    """Returns the Plex_ user account information stored in ``~/.config/plexstuff/app.db``.

    :param verify: optional ``bool`` argument, whether to use SSL verification. Default is ``True``.
    :returns: the Plex_ account tuple of ``(username, password)``.
    :rtype: tuple

    .. seealso:: :py:meth:`pushCredentials <plexstuff.plexcore.plexcore.pushCredentials>`

    """
    val = session.query( PlexConfig ).filter(
        PlexConfig.service == 'login' ).first( )
    if val is None: return None
    data = val.data
    username = data['username'].strip( )
    password = data['password'].strip( )
    token = getTokenForUsernamePassword(
        username, password, verify = verify )
    if token is None: return None
    return username, password

def pushCredentials( username, password ):
    """replace the Plex_ server credentials, located in ``~/.config/plexstuff/app.db``, with a new ``username`` and ``password``.

    :param username: the Plex_ account username.
    :param password: the Plex_ account password.
    :returns: if successful, return a string, ``SUCCESS``. If unsuccessful, returns a string reason of why it failed.
    :rtype: str

    .. seealso:: :py:meth:`getCredentials <plexstuff.plexcore.plexcore.getCredentials>`

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

    :param token: the Plex str access token, returned by :py:meth:`checkServerCredentials <plexstuff.plexcore.checkServerCredentials>`.
    :param verify: optional bool argument, whether to verify SSL connections. Default is ``True``.
    :returns: a dictionary of servers owned by you. Each key is the Plex_ server's name, and the value is the URL with port.
    :rtype: dict

    .. seealso::
       * :py:meth:`checkServerCredentials <plexstuff.plexcore.plexcore.checkServerCredentials>`
       * :py:meth:`get_owned_servers <plexstuff.plexcore.plexcore.get_owned_servers>`

    .. _Plex: https://plex.tv

    """
    response = requests.get( 'https://plex.tv/api/resources',
                             params = { 'X-Plex-Token' : token },
                             verify = verify )
    if response.status_code != 200:
        return None
    myxml = BeautifulSoup( response.content, 'lxml' )
    server_dict = { }
    for server_elem in filter(lambda se: len(set([ 'product', 'publicaddress', 'owned' ]) - set( se.attrs ) ) == 0 and
                              se['product'] == 'Plex Media Server', myxml.find_all('device') ):
        connections = list( filter(lambda elem: elem['local'] == '0', server_elem.find_all('connection') ) )
        if len( connections ) != 1:
            continue
        connection = max( connections )
        name = server_elem[ 'name' ]
        host = connection[ 'address' ]
        port = int( connection[ 'port' ] )
        server_dict[ name ] = '%s:%d' % ( host, port )
    return server_dict
    
def get_owned_servers( token, verify = True ):
    """Find the Plex_ servers that you own own.

    :param token: the Plex str access token, returned by :py:meth:`checkServerCredentials`.
    :param verify: optional ``bool`` argument, whether to verify SSL connections. Default is ``True``.
    :returns: a dictionary of servers owned by you. Each key is the Plex_ server's name, and the value is the URL with port.
    :rtype: dict

    .. seealso:: 
       * :py:meth:`checkServerCredentials <plexstuff.plexcore.plexcore.checkServerCredentials>`
       * :py:meth:`get_all_servers <plexstuff.plexcore.plexcore.get_all_servers>`

    .. _Plex: https://plex.tv

    """
    response = requests.get( 'https://plex.tv/api/resources',
                             params = { 'X-Plex-Token' : token },
                             verify = verify )
    if response.status_code != 200:
        return None
    myxml = BeautifulSoup( response.content, 'lxml' )
    server_dict = { }
    for server_elem in filter(
            lambda se: len(set([ 'product', 'publicaddress', 'owned' ]) - set( se.attrs ) ) == 0 and
            se['product'] == 'Plex Media Server', myxml.find_all('device') ):
        owned = int( server_elem['owned'] )
        if owned != 1: continue
        connections = list( filter(lambda elem: elem['local'] == '0', server_elem.find_all('connection') ) )
        if len( connections ) != 1: continue
        connection = max( connections )
        name = server_elem[ 'name' ]
        host = connection[ 'address' ]
        port = int( connection[ 'port' ] )
        server_dict[ name ] = '%s:%d' % ( host, port )
    return server_dict

def get_pic_data( plexPICURL, token = None ):
    if token is None: params = { }
    else: params = { 'X-Plex-Token' : token }
    response = requests.get( plexPICURL, params = params, verify = False )
    logging.debug( 'FULLMOVIEPATH: %s, size = %d' %
                   ( plexPICURL, len( response.content ) ) )
    return response.content

def get_updated_at( token, fullURLWithPort = 'http://localhost:32400' ):
    params = { 'X-Plex-Token' : token }
    response = requests.get( fullURLWithPort, params = params, verify = False )
    if response.status_code != 200:
        return None
    myxml = BeautifulSoup( response.content, 'lxml' )
    media_elem = max( myxml.find_all( 'mediacontainer' ) )
    assert( 'updatedat' in media_elem.attrs )
    return datetime.datetime.fromtimestamp( int( media_elem['updatedat'] ) )

def get_email_contacts( token, verify = True ):
    response = requests.get( 'https://plex.tv/pms/friends/all',
                             headers = { 'X-Plex-Token' : token },
                             verify = verify )
    if response.status_code != 200: return None
    myxml = BeautifulSoup( response.content, 'lxml' )
    return sorted(set(map(lambda elem: elem['email'],
                          filter(lambda elem: 'email' in elem.attrs,
                                 myxml.find_all( 'user' ) ) ) ) )

def get_mapped_email_contacts( token, verify = True ):
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
    query = session.query( LastNewsletterDate )
    backthen = datetime.datetime.strptime( '1900-01-01', '%Y-%m-%d' ).date( )
    val = query.filter( LastNewsletterDate.date >= backthen ).first( )
    if val is None:
        return None
    return val.date

def _get_library_data_movie( key, token, fullURL = 'http://localhost:32400', sinceDate = None,
                             num_threads = 16 ):
    assert( num_threads >= 1 )
    params = { 'X-Plex-Token' : token }
    if sinceDate is None:
        sinceDate = datetime.datetime.strptime( '1900-01-01', '%Y-%m-%d' ).date( )
        
    response = requests.get( '%s/library/sections/%d/all' % ( fullURL, key ),
                             params = params, verify = False )
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
                'localpic' : True }
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
            map( _get_movie_data, input_tuples ) ) )
        for first_genre, data in movie_data_list:
            movie_data.setdefault( first_genre, [ ] ).append( data )
        return key, movie_data
        
def _get_library_stats_movie( key, token, fullURL ='http://localhost:32400', sinceDate = None ):
    tup = _get_library_data_movie( key, token, fullURL = fullURL, sinceDate = sinceDate )
    if tup is None: return None
    _, movie_data = tup
    sorted_by_genres = {
        genre : ( len( movie_data[ genre ] ),
                  sum( map(lambda tup: tup[-2], movie_data[ genre ] ) ),
                  sum( map(lambda tup: tup[-1], movie_data[ genre ] ) ) ) for
        genre in movie_data }
    totnum = sum(map(lambda genre: sorted_by_genres[ genre ][ 0 ], sorted_by_genres ) )
    totdur = sum(map(lambda genre: sorted_by_genres[ genre ][ -1 ], sorted_by_genres ) )
    totsize = sum(map(lambda genre: sorted_by_genres[ genre ][ -2 ], sorted_by_genres ) )
    return key, totnum, totdur, totsize, sorted_by_genres

def _get_library_data_show( key, token, fullURL = 'http://localhost:32400',
                            sinceDate = None, num_threads = 16 ):
    assert( num_threads >= 1 )
    params = { 'X-Plex-Token' : token }
    if sinceDate is None:
        sinceDate = datetime.datetime.strptime( '1900-01-01', '%Y-%m-%d' ).date()
    response = requests.get( '%s/library/sections/%d/all' % ( fullURL, key ),
                             params = params, verify = False )
    if response.status_code != 200: return None
    
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
    def _get_show_data( input_tuple ):
        times_requests_given = [ ]
        cont, session, slist, t0, indices = input_tuple
        html = BeautifulSoup( cont, 'lxml' )
        direlems = html.find_all('directory')
        tvdata_tup = [ ]
        idx_number = min( indices )
        for idx in indices:
            direlem = direlems[ idx ]
            show = unescape( direlem['title'] )
            if 'summary' in direlem.attrs: summary = direlem['summary']
            else: summary = ''
            if 'art' in direlem.attrs: picurl = '%s%s' % ( fullURL, direlem.get('art') )
            else: picurl = None
            newURL = urljoin( fullURL, direlem['key'] )
            resp2 = session.get( newURL, params = params, verify = False )
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
                resp3 = session.get( newURL, params = params, verify = False )
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
            map(lambda idx: (
                response.content, sess, shared_list, time0,
                list( range( idx, num_direlems, act_num_threads ) ) ),
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

def _get_library_stats_show( key, token, fullURL = 'http://localhost:32400',
                             sinceDate = None ):
    _, tvdata = _get_library_data_show( key, token, fullURL = fullURL,
                                        sinceDate = sinceDate )
    numTVshows = len( tvdata )
    numTVeps = 0
    totdur = 0.0
    totsize = 0.0
    for show in tvdata:
        numTVeps += sum(map(lambda seasno: len( tvdata[ show ][ seasno ] ),
                            tvdata[ show ] ) )
        for seasno in tvdata[ show ]:
            totdur += sum(map(lambda epno: tvdata[ show ][ seasno ][ epno ][ -2 ],
                              tvdata[ show ][ seasno ] ) )
            totsize+= sum(map(lambda epno: tvdata[ show ][ seasno ][ epno ][ -1 ],
                              tvdata[ show ][ seasno ] ) )
    return key, numTVeps, numTVshows, totdur, totsize

def _get_library_stats_artist( key, token, fullURL = 'http://localhost:32400',
                               sinceDate = None ):
    params = { 'X-Plex-Token' : token }
    if sinceDate is None:
        sinceDate = datetime.datetime.strptime( '1900-01-01', '%Y-%m-%d' ).date( )
        
    response = requests.get( '%s/library/sections/%d/all' % ( fullURL, key ),
                             params = params, verify = False )
    if response.status_code != 200:
        return None
    html = BeautifulSoup( response.content, 'lxml' )
    artistelems = list(html.find_all('directory'))
    num_artists = 0
    num_albums = 0
    num_songs = 0
    totdur = 0.0
    totsize = 0.0
    def valid_track( track_elem ):
        if len(list(track_elem.find_all('media'))) != 1:
            return False
        media_elem = max( track_elem.find_all('media') )
        if len(set([ 'bitrate', 'duration' ]) -
               set(media_elem.attrs) ) != 0:
            return False
        return True    
    for artist_elem in artistelems:
        newURL = '%s%s' % ( fullURL, artist_elem.get('key') )
        resp2 = requests.get( newURL, params = params, verify = False )        
        if resp2.status_code != 200:
            continue
        h2 = BeautifulSoup( resp2.content, 'lxml' )
        album_elems = list( h2.find_all('directory') )
        albums_here = 0
        for album_elem in album_elems:
            newURL = '%s%s' % ( fullURL, album_elem.get('key') )
            resp3 = requests.get( newURL, params = params, verify = False )
            if resp3.status_code != 200:
                continue
            h3 = BeautifulSoup( resp3.content, 'lxml' )
            track_elems = filter(valid_track, h3.find_all( 'track' ) )
            num_songs_here = 0
            for track_elem in track_elems:
                if datetime.datetime.fromtimestamp( float( track_elem['addedat'] ) ).date() < sinceDate:
                    continue
                num_songs_here += 1
                media_elem = max(track_elem.find_all('media'))
                duration = 1e-3 * int( media_elem['duration'] )
                bitrate = int( media_elem['bitrate'] ) * 1e3 / 8.0
                totsize += duration * bitrate
                totdur += duration
            if num_songs_here > 0:
                num_songs += num_songs_here
                albums_here += 1
        if albums_here > 0:
            num_albums += albums_here
            num_artists += 1                
    return key, num_songs, num_albums, num_artists, totdur, totsize

def _get_library_data_artist( key, token, fullURL = 'http://localhost:32400',
                              sinceDate = None, num_threads = 16 ):
    assert( num_threads >= 1 )
    params = { 'X-Plex-Token' : token }
    if sinceDate is None:
        sinceDate = datetime.datetime.strptime( '1900-01-01', '%Y-%m-%d' ).date( )
        
    response = requests.get( '%s/library/sections/%d/all' % ( fullURL, key ),
                             params = params, verify = False )
    if response.status_code != 200: return None
    
    s = requests.Session( )
    s.mount( 'https://', requests.adapters.HTTPAdapter(
        pool_connections = num_threads,
        pool_maxsize = num_threads ) )
    s.mount( 'http://', requests.adapters.HTTPAdapter(
        pool_connections = num_threads,
        pool_maxsize = num_threads ) )
    
    def valid_track( track_elem ):
        if len(list(track_elem.find_all('media'))) != 1:
            return False
        media_elem = max( track_elem.find_all('media') )
        if len(set([ 'bitrate', 'duration' ]) -
               set(media_elem.attrs)) != 0:
            return False
        return True
    #
    def _get_artist_data( input_tuple ):
        cont, indices = input_tuple
        html = BeautifulSoup( cont, 'lxml' )
        artist_elems = html.find_all('directory')
        song_data_sub = [ ]
        for idx in indices:
            artist_elem = artist_elems[ idx ]
            newURL = '%s%s' % ( fullURL, artist_elem.get('key') )
            resp2 = s.get( newURL, params = params, verify = False )        
            if resp2.status_code != 200: continue
            h2 = BeautifulSoup( resp2.content, 'lxml' )
            album_elems = list( h2.find_all('directory') )
            artist_name = artist_elem[ 'title' ]
            artist_data = { }
            for album_elem in album_elems:
                newURL = '%s%s' % ( fullURL, album_elem.get('key') )
                resp3 = s.get( newURL, params = params, verify = False )
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
    with multiprocessing.Pool( processes=act_num_threads ) as pool:
        input_tuples = list(
            map(lambda idx: ( response.content, list(range(
                idx, len_artistelems, act_num_threads ) ) ),
                range(act_num_threads)))
        song_data = dict(chain.from_iterable(pool.map(
            _get_artist_data, input_tuples ) ) )
        return key, song_data

def get_movies_libraries( token, fullURL = 'http://localhost:32400' ):
    params = { 'X-Plex-Token' : token }
    response = requests.get( '%s/library/sections' % fullURL, params = params,
                             verify = False )
    if response.status_code != 200: return None
    html = BeautifulSoup( response.content, 'lxml' )
    library_dict = { int( direlem['key'] ) : ( direlem['title'], direlem['type'] ) for
                     direlem in html.find_all('directory') }
    return sorted(set(filter(lambda key: library_dict[ key ][1] == 'movie',
                             library_dict ) ) )

def get_library_data( title, token, fullURL = 'http://localhost:32400', num_threads = 16 ):
    time0 = time.time( )
    params = { 'X-Plex-Token' : token }
    response = requests.get( '%s/library/sections' % fullURL, params = params,
                             verify = False )
    if response.status_code != 200:
        logging.info( "took %0.3f seconds to get here in get_library_data, library = %s." %
                      ( time.time( ) - time0, title ) )
        logging.info( "no data found. Exiting..." )
        return None
    html = BeautifulSoup( response.content, 'lxml' )
    library_dict = { direlem[ 'title' ] : ( int( direlem['key'] ), direlem['type'] ) for
                     direlem in html.find_all('directory') }
    assert( title in library_dict )
    key, mediatype = library_dict[ title ]
    if mediatype == 'movie':
        _, data = _get_library_data_movie( key, token, fullURL = fullURL,
                                           num_threads = num_threads )
    elif mediatype == 'show':
        _, data =  _get_library_data_show( key, token, fullURL = fullURL,
                                           num_threads = num_threads )
    elif mediatype == 'artist':
        _, data = _get_library_data_artist( key, token, fullURL = fullURL,
                                            num_threads = num_threads )
    else:
        logging.info( "took %0.3f seconds to gete here in get_library_data, library = %s." %
                      ( time.time( ) - time0, title ) )
        logging.info( "could not find a library with name = %s. Exiting..." % title )
        return None
    logging.info( "took %0.3f seconds to gete here in get_library_data, library = %s." %
                  ( time.time( ) - time0, title ) )
    return data

def get_library_stats( key, token, fullURL = 'http://localhost:32400' ):
    params = { 'X-Plex-Token' : token }
    response = requests.get( '%s/library/sections' % fullURL, params = params,
                             verify = False )
    if response.status_code != 200:
        return None
    html = BeautifulSoup( response.content, 'lxml' )
    library_dict = { int( direlem['key'] ) : ( direlem[ 'title' ], direlem[ 'type' ] ) for
                     direlem in html.find_all('directory') }
    assert( key in library_dict )
    title, mediatype = library_dict[ key ]
    if mediatype == 'movie':
        data = _get_library_stats_movie( key, token, fullURL = fullURL )
        if data is None:
            return None
        actkey, num_movies, totdur, totsize, _ = data
        return fullURL, title, mediatype, num_movies, totdur, totsize
    elif mediatype == 'show':
        data =  _get_library_stats_show( key, token, fullURL = fullURL )
        if data is None:
            return None
        actkey, num_tveps, num_tvshows, totdur, totsize = data
        return fullURL, title, mediatype, num_tveps, num_tvshows, totdur, totsize
    elif mediatype == 'artist':
        data = _get_library_stats_artist( key, token, fullURL = fullURL )
        if data is None:
            return None
        actkey, num_songs, num_albums, num_artists, totdur, totsize = data
        return fullURL, title, mediatype, num_songs, num_albums, num_artists, totdur, totsize
    else:
        return fullURL, title, mediatype
        
def get_libraries( fullURL = 'http://localhost:32400', token = None, do_full = False ):
    if token is None:
        if fullURL == 'http://localhost:32400':
            data = checkServerCredentials( doLocal = True )
        else:
            data = checkServerCredentials( doLocal = False )
        if data is None:
            return None
        _, token = data
    params = { 'X-Plex-Token' : token }
    response = requests.get(
        '%s/library/sections' % fullURL,
        params = params, verify = False )
    if response.status_code != 200: return None
    html = BeautifulSoup( response.content, 'lxml' )
    if not do_full:
        return dict( map( lambda direlem: ( int( direlem['key'] ), direlem['title'] ),
                          html.find_all('directory') ) )
    else:
        return dict( map( lambda direlem: ( int( direlem['key'] ), ( direlem['title'], direlem['type'] ) ),
                          html.find_all('directory') ) )

def fill_out_movies_stuff( fullURL = 'http://localhost:32400', token = None,
                           debug = False, verify = True ):
    if token is None:
        if fullURL == 'http://localhost:32400':
            data = checkServerCredentials( doLocal = True )
        else:
            data = checkServerCredentials( doLocal = False )
        if data is None:
            return None
        _, token = data        
    unified_movie_data = { }
    movie_data_rows = [ ]
    problem_rows = [ ]
    plex_libraries = get_libraries(
        fullURL, token, do_full = True )
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
        movie_data_rows += list(
            pool.map(_solve_problem_row, problem_rows ) )
        return movie_data_rows, genres
    
def get_movie_titles_by_year( year, fullURLWithPort = 'http://localhost:32400',
                              token = None ):
    if token is None:
        params = {}
    else:
        params = { 'X-Plex-Token' : token }
    params['year'] = year
    libraries_dict = get_libraries( token = token, fullURL = fullURLWithPort )
    if libraries_dict is None:
        return None
    keynum = max([ key for key in libraries_dict if libraries_dict[key] == 'Movies' ])
    response = requests.get( '%s/library/sections/%d/all' % ( fullURLWithPort, keynum ),
                             params = params, verify = False )                             
    if response.status_code != 200: return None
    movie_elems = filter( lambda elem: 'title' in elem.attrs,
                          BeautifulSoup( response.content, 'lxml' ).find_all('video') )
    return sorted(set(map( lambda movie_elem: movie_elem['title'], movie_elems ) ) )

def get_lastN_movies( lastN, token, fullURLWithPort = 'http://localhost:32400',
                      useLastNewsletterDate = True ):    
    assert( isinstance( lastN, int ) )
    assert( lastN > 0 )
    params = { 'X-Plex-Token' : token }
    libraries_dict = get_libraries( fullURL = fullURLWithPort, token = token )
    if libraries_dict is None: return None
    keynum = max(filter(lambda key: libraries_dict[key] == 'Movies', libraries_dict))
    response = requests.get('%s/library/sections/%d/recentlyAdded' % ( fullURLWithPort, keynum ),
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
        plextmdb.get_movie( elem['title'] ) ),
                    valid_video_elems ) )

"""
All this stuff I found at https://support.plex.tv/hc/en-us/articles/201638786-Plex-Media-Server-URL-Commands
"""
def refresh_library( library_key, library_dict, fullURL = 'http://localhost:32400', token = None ):    
    assert( library_key in library_dict )
    if token is None: params = { }
    else: params = { 'X-Plex-Token' : token }
    response = requests.get( '%s/library/sections/%d/refresh' % ( fullURL, library_key ),
                             params = params, verify = False )
    assert( response.status_code == 200 )
    print('refreshing %s Library...' % library_dict[ library_key ])

def _get_failing_artistalbum( filename ):
    if os.path.basename( filename ).endswith( '.m4a' ):
        mp4tag = mutagen.mp4.MP4( filename )
        if not all([ key in mp4tag for key in ( '\xa9alb', '\xa9ART' ) ]):
            return filename
    return None

def get_lastupdated_string( dt = datetime.datetime.now( ) ):
    return dt.strftime('%A, %d %B %Y, at %-I:%M %p')

def get_tvshownames_gspread( ):
    import oauth2client.file, httplib2
    credPath = os.path.join( mainDir, 'resources', 'credentials_gspread.json' )
    storage = oauth2client.file.Storage( credPath )
    credentials = storage.get( )
    credentials.refresh( httplib2.Http( ) )
    gclient = gspread.authorize( credentials )
    sURL = 'https://docs.google.com/spreadsheets/d/10MR-mXd3sJlZWKOG8W-LhYp_6FAt0wq1daqPZ7is9KE/edit#gid=0'
    sheet = gclient.open_by_url( sURL )
    wksht = sheet.get_worksheet( 0 )
    tvshowshere = set(filter(lambda val: len(val.strip()) != 0, wksht.col_values(1)))
    return tvshowshere

def oauthCheckGoogleCredentials( ):
    val = session.query( PlexConfig ).filter( PlexConfig.service == 'google' ).first( )
    if val is None:
        return False, 'GOOGLE AUTHENTICATION CREDENTIALS DO NOT EXIST.'
    return True, 'SUCCESS'

def oauthGetGoogleCredentials( verify = True ):
    val = session.query( PlexConfig ).filter( PlexConfig.service == 'google' ).first( )
    if val is None: return None
    cred_data = val.data
    credentials = Credentials.from_authorized_user_info( cred_data )
    s = requests.Session( )
    s.verify = verify
    credentials.refresh( Request( session = s ) )
    return credentials

def oauthGetOauth2ClientGoogleCredentials( ):
    val = session.query( PlexConfig ).filter( PlexConfig.service == 'google' ).first( )
    if val is None: return None
    cred_data = val.data
    credentials = oauth2client.client.OAuth2Credentials.from_json(
        json.dumps( cred_data ) )
    return credentials

def oauth_generate_google_permission_url( ):
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

#
## read in JACKETT credentials here
def get_jackett_credentials( ):
    query = session.query( PlexConfig ).filter( PlexConfig.service == 'jackett' )
    val = query.first( )
    if val is None: return None
    data = val.data
    url = data['url'].strip( )
    apikey = data['apikey'].strip( )
    return url, apikey

#
## now check that Jackett credentials work
def check_jackett_credentials( url, apikey, verify = True ):
    endpoint = 'api/v2.0/indexers/all/results/torznab/api'
    #
    ## now check that everything works
    ## first, is URL a valid URL?
    if not validators.url( url ):
        return "ERROR, %s is not a valid URL" % url

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
            return "ERROR, invalid jackett credentials"

        html = BeautifulSoup( response.content, 'lxml' )
        error_items = html.find_all('error')
        if len( error_items ) != 0:
            return "ERROR, invalid API key"
        return actURL, 'SUCCESS'
    except Exception as e:
        return None, "ERROR, exception emitted: %s." % str( e )

#
## now get imgurl credentials
def get_imgurl_credentials( ):
    val = session.query( PlexConfig ).filter( PlexConfig.service == 'imgurl' ).first( )
    if val is None:
        raise ValueError( "ERROR, COULD NOT GET ACCESS TOKEN." )
    data_imgurl = val.data
    return data_imgurl

def check_imgurl_credentials( clientID, clientSECRET,
                              clientREFRESHTOKEN, verify = True ):
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
    isValid =  check_imgurl_credentials( clientID, clientSECRET, clientREFRESHTOKEN,
                                         verify = verify )
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
