import sqlite3, shutil, os, glob, datetime, gspread, logging, sys
import multiprocessing, tempfile, uuid, requests, pytz, pypandoc
import xdg.BaseDirectory, urllib, json, oauth2client.file, httplib2
from ConfigParser import RawConfigParser
from contextlib import contextmanager
from bs4 import BeautifulSoup
from . import mainDir, Base, session, baseConfDir
from sqlalchemy import Column, Date, Boolean, String
from oauth2client.client import flow_from_clientsecrets
sys.path.append( mainDir )
from plextmdb import plextmdb

# disable insecure request warnings, because do not recall how to get the name of the certificate for a 
# given plex server
requests.packages.urllib3.disable_warnings( )

dbloc = os.path.join( '/var/lib/plexmediaserver/Library/',
                      'Application Support/Plex Media Server/',
                      'Plug-in Support/Databases/com.plexapp.plugins.library.db' )
# assert( os.path.isfile( dbloc ) )

class LastNewsletterDate( Base ):
    #
    ## create the table using Base.metadata.create_all( _engine )
    __tablename__ = 'lastnewsletterdate'
    __table_args__ = {'extend_existing': True}
    date = Column( Date, onupdate = datetime.datetime.now, index = True, primary_key = True )

class PlexGuestEmailMapping( Base ):
    #
    ## create the table using Base.metadata.create_all( _engine )
    __tablename__ = 'plexguestemailmapping'
    __table_args__ = { 'extend_existing' : True }
    plexemail = Column( String( 256 ), index = True, unique = True, primary_key = True )
    plexmapping = Column( String( 65536 ) )
    plexreplaceexisting = Column( Boolean )

def add_mapping( plex_email, plex_emails, new_emails, replace_existing ):
    assert( plex_email in plex_emails )
    assert( len( set( new_emails ) & set( plex_emails ) ) == 0 )
    query = session.query( PlexGuestEmailMapping )
    val = query.filter( PlexGuestEmailMapping.plexemail == plex_email ).first( )
    if val is not None:
        session.delete( val )
        session.commit( )
    newval = PlexGuestEmailMapping( plexemail = plex_email,
                                    plexmapping = ','.join( sorted( set( new_emails ) ) ),
                                    plexreplaceexisting = replace_existing )
    session.add( newval )
    session.commit( )

@contextmanager
def plexconnection( ):
    _, tmpsub = tempfile.mkstemp( suffix = '.db' )
    shutil.copy( dbloc, tmpsub )
    conn = sqlite3.connect( tmpsub )
    cursor = conn.cursor( )
    try:
        yield cursor
    finally:
        conn.close( )
        os.remove( tmpsub )

def get_date_from_datestring( dstring ):
    try:
        date = datetime.datetime.strptime( dstring, '%B %d, %Y' ).date( )
        return date
    except Exception:
        return None
        
#
## now convert this into HTML using pandoc, then BeautifulSoup :)
def latexToHTML( latexString ):
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
        print( 'ERROR, SOME DEFINED FIGURES IN LATEX DO NOT HAVE IMAGES.' )
        return htmlData.prettify( )
    for img in htmlData.find_all('img'):
        name = img['src']
        b64data, widthInCM, url = pngDataDict[ name ]
        if doEmbed:
            img['src'] = "data:image/png;base64," + b64data
        else:
            img['src'] = url
        img['width'] = "%d" % ( widthInCM / 2.54 * 300 )
    return htmlData.prettify( )

def getTokenForUsernamePassword( username, password, verify = True ):
    with requests.Session( ) as session:
        response = session.post( 'https://plex.tv/users/sign_in.json',
                                 auth = ( username, password ),
                                 headers = { 'X-Plex-Client-Identifier' : str( uuid.uuid4( ) ),
                                             'X-Plex-Platform' : 'Linux',
                                             'X-Plex-Provides' : 'server' },
                                 verify = verify )
        if response.status_code != 201:
            logging.debug( 'STATUS CODE = %d' % response.status_code )
            logging.debug( 'CONTENT = %s' %  response.content )
            return None
        token = response.json()['user']['authentication_token']
        return token

def checkClientCredentials( ):
    filename = 'plex_creds.conf'
    secname = 'PLEX_CLIENT_CREDENTIALS'
    absPath = os.path.join( baseConfDir, filename )
    if not os.path.isfile( absPath ):
        return None
    cparser = RawConfigParser( )
    cparser.read( absPath )
    if not cparser.has_section( secname ):
        return None
    if any(map(lambda opt: not cparser.has_option( secname, opt ),
               ( 'username', 'password' ) ) ):
        return None
    username = cparser.get( secname, 'username' )
    password = cparser.get( secname, 'password' )
    response = requests.get( 'https://tanimislam.ddns.net/flask/plex/tokenurl',
                             auth = ( username, password ) )
    if response.status_code != 200:
        return None
    token = response.json( )[ 'token' ]
    fullurl = response.json( )[ 'url' ]
    return fullurl, token
    
def checkServerCredentials( doLocal = False ):
    filename = 'plex_creds.conf'
    absPath = os.path.join( baseConfDir, filename )
    if not os.path.isfile( absPath ):
        return None
    cparser = RawConfigParser( )
    cparser.read( absPath )
    if not cparser.has_section( 'PLEX_SERVER_CREDENTIALS' ):
        return None
    if any([ not cparser.has_option( 'PLEX_SERVER_CREDENTIALS', opt ) for opt in
             ('username', 'password' ) ]):
        return None
    username = cparser.get( 'PLEX_SERVER_CREDENTIALS', 'username' )
    password = cparser.get( 'PLEX_SERVER_CREDENTIALS', 'password' )
    token = getTokenForUsernamePassword( username, password )
    if token is None:
        return None
    if not doLocal:
        _, fullurl = max( get_owned_servers( token ).items( ) )
        fullurl = 'https://%s' % fullurl
    else:
        fullurl = 'http://localhost:32400'
    return fullurl, token

def pushCredentials( username, password, name = 'CLIENT' ):
    assert(name in ( 'CLIENT', 'SERVER' ) )
    filename = 'plex_creds.conf'
    secname = 'PLEX_%s_CREDENTIALS' % name
    absPath = os.path.join( baseConfDir, filename )
    cparser = RawConfigParser( )
    if os.path.isfile( absPath ):
        cparser.read( absPath )
    cparser.remove_section( secname )
    cparser.add_section( secname )
    cparser.set( secname, 'username', username )
    cparser.set( secname, 'password', password )
    with open( absPath, 'wb') as openfile:
        cparser.write( openfile )
    os.chmod( absPath, 0o600 )

"""
get_all_servers and get_owned_servers don't work. Something wrong with servers.xml endpoint
"""
def get_all_servers( token ):
    response = requests.get( 'https://plex.tv/api/resources',
                             params = { 'X-Plex-Token' : token } )
    if response.status_code != 200:
        return None
    myxml = BeautifulSoup( response.content, 'lxml' )
    server_dict = { }
    for server_elem in filter(lambda se: len(set([ 'product', 'publicaddress', 'owned' ]) - set( se.attrs ) ) == 0 and
                              se['product'] == 'Plex Media Server', myxml.find_all('device') ):
        connections = filter(lambda elem: elem['local'] == '0', server_elem.find_all('connection') )
        if len( connections ) != 1:
            continue
        connection = max( connections )
        name = server_elem[ 'name' ]
        host = connection[ 'address' ]
        port = int( connection[ 'port' ] )
        server_dict[ name ] = '%s:%d' % ( host, port )
    return server_dict
    
def get_owned_servers( token ):
    response = requests.get( 'https://plex.tv/api/resources',
                             params = { 'X-Plex-Token' : token } )
    if response.status_code != 200:
        return None
    myxml = BeautifulSoup( response.content, 'lxml' )
    server_dict = { }
    for server_elem in filter(lambda se: len(set([ 'product', 'publicaddress', 'owned' ]) - set( se.attrs ) ) == 0 and
                              se['product'] == 'Plex Media Server', myxml.find_all('device') ):
        owned = int( server_elem['owned'] )
        if owned != 1: continue
        connections = filter(lambda elem: elem['local'] == '0', server_elem.find_all('connection') )
        if len( connections ) != 1:
            continue
        connection = max( connections )
        name = server_elem[ 'name' ]
        host = connection[ 'address' ]
        port = int( connection[ 'port' ] )
        server_dict[ name ] = '%s:%d' % ( host, port )
    return server_dict

def get_pic_data( plexPICURL, token = None ):
    if token is None:
        params = { }
    else:
        params = { 'X-Plex-Token' : token }
    response = requests.get( plexPICURL, params = params, verify = False )
    logging.debug( 'FULLMOVIEPATH: %s, size = %d' %
                   ( plexPICURL, len( response.content ) ) )
    return response.content

def get_updated_at( token, fullURLWithPort = 'https://localhost:32400' ):
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
    if response.status_code != 200:
        return None
    myxml = BeautifulSoup( response.content, 'lxml' )
    emails = sorted(set(map(lambda elem: elem['email'],
                            filter(lambda elem: 'email' in elem.attrs,
                                   myxml.find_all( 'user' ) ) ) ) )
    return emails

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

def _get_library_data_movie( key, token, fullURL = 'https://localhost:32400', sinceDate = None ):
    params = { 'X-Plex-Token' : token }
    if sinceDate is None:
        sinceDate = datetime.datetime.strptime( '1900-01-01', '%Y-%m-%d' ).date( )

    response = requests.get( '%s/library/sections/%d/all' % ( fullURL, key ),
                             params = params, verify = False )
    if response.status_code != 200:
        return None
    html = BeautifulSoup( response.content, 'lxml' )
    movie_data = { }
    for movie_elem in html.find_all( 'video' ):
        if datetime.datetime.fromtimestamp( float( movie_elem.get('addedat') ) ).date() < sinceDate:
            continue
        first_genre = plextmdb.get_main_genre_movie( movie_elem )
        title = movie_elem['title']
        if 'rating' in movie_elem.attrs:
            rating = float( movie_elem.get('rating') )
        else:
            rating = None
        summary = movie_elem.get('summary')
        #
        ## to get the Image, use the following code from Stackoverflow
        ## http://stackoverflow.com/questions/13137817/how-to-download-image-using-requests
        ##
        ## from cStringIO import StringIO
        ## from PIL import Image
        ## response = requests.get( picurl, params = params )
        ## img = Image.open( StringIO( response.content ) )
        ##
        ## maybe need to do something to convert to QImage from Image
        if 'art' in movie_elem.attrs:
            picurl = '%s%s' % ( fullURL, movie_elem.get('art') )
        else:
            picurl = None
        if 'originallyavailableat' in movie_elem.attrs:
            releasedate = datetime.datetime.strptime( movie_elem.get( 'originallyavailableat' ), '%Y-%m-%d' ).date( )
        else:
            releasedate = None
        addedat = datetime.datetime.fromtimestamp( float( movie_elem.get( 'addedat' ) ) ).date( )
        if 'contentrating' in movie_elem.attrs:
            contentrating = movie_elem.get('contentrating')
        else:
            contentrating = 'NR'
        duration = 1e-3 * int( movie_elem[ 'duration' ] )
        bitrate = int( min( movie_elem.find_all('media'))[ 'bitrate' ] ) * 1e3 / 8.0
        totsize = duration * bitrate
        data = ( title, rating, contentrating, picurl, releasedate, addedat, summary,
                 duration, totsize )
        movie_data.setdefault( first_genre, [] ).append( data )
    return key, movie_data
        
def _get_library_stats_movie( key, token, fullURL ='https://localhost:32400', sinceDate = None ):
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
                            sinceDate = None ):
    from requests.compat import urljoin
    params = { 'X-Plex-Token' : token }
    if sinceDate is None:
        sinceDate = datetime.datetime.strptime( '1900-01-01', '%Y-%m-%d' ).date()
    response = requests.get( '%s/library/sections/%d/all' % ( fullURL, key ),
                             params = params, verify = False )
    if response.status_code != 200:
        return None
    html = BeautifulSoup( response.content, 'lxml' )
    def valid_videlem( elem ):
        if elem.name != 'video':
            return False
        if len( elem.find_all('media')) != 1:
            return False
        media_elem = elem.find( 'media' )
        if len(set([ 'duration', 'bitrate']) -
               set( media_elem.attrs ) ) != 0:
            return False
        return True

    #
    ## for videlems in shows
    ## videlem.get('index') == episode # in season
    ## videlem.get('parentindex') == season # of show ( season 0 means Specials )
    ## videlem.get('originallyavailableat') == when first aired
    tvdata = { }
    for direlem in html.find_all( 'directory' ):
        show = direlem['title']
        tvdata.setdefault( show, { } )
        newURL = urljoin( fullURL, direlem['key'] )
        resp2 = requests.get( newURL, params = params, verify = False )
        if resp2.status_code != 200:
            continue
        h2 = BeautifulSoup( resp2.content, 'lxml' )
        leafElems = list( filter(lambda le: 'allLeaves' not in le['key'], h2.find_all('directory') ) )
        if len(leafElems) == 0:
            continue
        for leafElem in leafElems:
            newURL = urljoin( fullURL, leafElem[ 'key' ] )
            resp3 = requests.get( newURL, params = params, verify = False )
            h3 = BeautifulSoup( resp3.content, 'lxml' )
            for videlem in h3.find_all( valid_videlem ):
                if datetime.datetime.fromtimestamp( float( videlem['addedat'] ) ).date() < sinceDate:
                    continue
                seasno = int( videlem['parentindex'] )
                epno = int( videlem[ 'index' ] )
                try:
                    dateaired = datetime.datetime.strptime(
                        videlem['originallyavailableat'], '%Y-%m-%d' ).date( )
                except:
                    dateaired = datetime.datetime.strptime( '1900-01-01', '%Y-%m-%d' ).date( )
                title = videlem[ 'title' ]
                duration = 1e-3 * int( videlem[ 'duration' ] )
                media_elem = videlem.find('media')
                bitrate = int( media_elem[ 'bitrate' ] ) * 1e3 / 8.0
                size = duration * bitrate
                tvdata[ show ].setdefault( seasno, { } )
                tvdata[ show ][ seasno ][ epno ] = ( title, dateaired, duration, size )
    return tvdata

def _get_library_stats_show( key, token, fullURL = 'http://localhost:32400',
                             sinceDate = None ):
    tvdata = _get_library_data_show( key, token, fullURL = fullURL,
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
    song_data = { }
    def valid_track( track_elem ):
        if len(list(track_elem.find_all('media'))) != 1:
            return False
        media_elem = max( track_elem.find_all('media') )
        if len(set([ 'bitrate', 'duration' ]) -
               set(media_elem.attrs)) != 0:
            return False
        return True
    for artist_elem in artistelems:
        newURL = '%s%s' % ( fullURL, artist_elem.get('key') )
        resp2 = requests.get( newURL, params = params, verify = False )        
        if resp2.status_code != 200:
            continue
        h2 = BeautifulSoup( resp2.content, 'lxml' )
        album_elems = list( h2.find_all('directory') )
        artist_name = artist_elem[ 'title' ]
        song_data.setdefault( artist_name, { } )
        for album_elem in album_elems:
            newURL = '%s%s' % ( fullURL, album_elem.get('key') )
            resp3 = requests.get( newURL, params = params, verify = False )
            if resp3.status_code != 200:
                continue
            h3 = BeautifulSoup( resp3.content, 'lxml' )
            track_elems = filter(valid_track, h3.find_all( 'track' ) )
            album_name = album_elem[ 'title' ]
            song_data[ artist_name ].setdefault( album_name, [ ] )
            for track_elem in track_elems:
                if datetime.datetime.fromtimestamp( float( track_elem.get('addedat') ) ).date() < sinceDate:
                    continue
                media_elem = max(track_elem.find_all('media'))
                duration = 1e-3 * int( media_elem[ 'duration' ] )
                bitrate = int( media_elem[ 'bitrate' ] ) * 1e3 / 8.0
                curdate = datetime.datetime.fromtimestamp( float( track_elem[ 'addedat' ] ) ).date( )
                track_name = track_elem[ 'title' ]
                song_data[ artist_name ][ album_name ].append( ( track_name, curdate, duration, bitrate * duration ) )
            if len( song_data[ artist_name ][ album_name ] ) == 0:
                song_data[ artist_name ].pop( album_name )
        if len( song_data[ artist_name ] ) == 0:
            song_data.pop( artist_name )
    return key, song_data

def get_movie_data( key, token, fullURL = 'http://localhost:32400' ):
    params = { 'X-Plex-Token' : token }
    response = requests.get( '%s/library/sections' % fullURL, params = params,
                             verify = False )
    html = BeautifulSoup( response.content, 'lxml' )
    library_dict = { int( direlem['key'] ) : ( direlem[ 'title' ], direlem[ 'type' ] ) for
                     direlem in html.find_all('directory') }
    assert( key in library_dict )
    _, mediatype = library_dict[ key ]
    assert( mediatype == 'movie' )
    _, movie_data = _get_library_data_movie( key, token, fullURL = fullURL )
    return movie_data

def get_movies_libraries( token, fullURL = 'http://localhost:32400' ):
    params = { 'X-Plex-Token' : token }
    response = requests.get( '%s/library/sections' % fullURL, params = params,
                             verify = False )
    if response.status_code != 200:
        return None
    if response.status_code != 200:
        return None
    html = BeautifulSoup( response.content, 'lxml' )
    library_dict = { int( direlem['key'] ) : ( direlem['title'], direlem['type'] ) for
                     direlem in html.find_all('directory') }
    keys = sorted(set(filter(lambda key: library_dict[ key ][1] == 'movie', library_dict.keys( ) ) ) )
    return keys

def get_library_data( title, token, fullURL = 'http://localhost:32400' ):
    params = { 'X-Plex-Token' : token }
    response = requests.get( '%s/library/sections' % fullURL, params = params,
                             verify = False )
    if response.status_code != 200:
        return None
    html = BeautifulSoup( response.content, 'lxml' )
    library_dict = { direlem[ 'title' ] : ( int( direlem['key'] ), direlem['type'] ) for
                     direlem in html.find_all('directory') }
    assert( title in library_dict )
    key, mediatype = library_dict[ title ]
    if mediatype == 'movie':
        data = _get_library_data_movie( key, token, fullURL = fullURL )
    elif mediatype == 'show':
        data =  _get_library_data_show( key, token, fullURL = fullURL )
    elif mediatype == 'artist':
        data = _get_library_data_artist( key, token, fullURL = fullURL )
    else:
        return None
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
        
def get_libraries( fullURL = 'http://localhost:32400', token = None ):
    if token is None:
        if fullURL == 'http://localhost:32400':
            data = checkServerCredentials( doLocal = True )
        else:
            data = checkServerCredentials( doLocal = False )
        if data is None:
            return None
        _, token = data
    params = { 'X-Plex-Token' : token }
    response = requests.get('%s/library/sections' % fullURL,
                            params = params, verify = False )
    if response.status_code != 200:
        return None
    html = BeautifulSoup( response.content, 'lxml' )
    return dict( map( lambda direlem: ( int( direlem['key'] ), direlem['title'] ),
                      html.find_all('directory') ) )

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
    if response.status_code != 200:
        return None
    movie_elems = filter( lambda elem: 'title' in elem.attrs,
                          BeautifulSoup( response.content, 'lxml' ).find_all('video') )
    return sorted(set(map( lambda movie_elem: movie_elem['title'], movie_elems ) ) )

def get_lastN_movies( lastN, token, fullURLWithPort = 'http://localhost:32400',
                      useLastNewsletterDate = True ):    
    assert( isinstance( lastN, int ) )
    assert( lastN > 0 )
    params = { 'X-Plex-Token' : token }
    libraries_dict = get_libraries( fullURL = fullURLWithPort, token = token )
    if libraries_dict is None:
        return None
    keynum = max([ key for key in libraries_dict if libraries_dict[key] == 'Movies' ])
    response = requests.get('%s/library/sections/%d/recentlyAdded' % ( fullURLWithPort, keynum ),
                            params = params, verify = False )
    if response.status_code != 200:
        return None
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
    return map(lambda elem: ( elem['title'], int( elem['year'] ),
                              datetime.datetime.fromtimestamp( int( elem['addedat'] ) ).
                              replace(tzinfo = pytz.timezone( 'US/Pacific' ) ),
                              plextmdb.get_movie( elem['title'] ) ),
               valid_video_elems )

"""
All this stuff I found at https://support.plex.tv/hc/en-us/articles/201638786-Plex-Media-Server-URL-Commands
"""
def refresh_library( library_key, library_dict, fullURL = 'http://localhost:32400', token = None ):    
    assert( library_key in library_dict )
    if token is None:
        params = { }
    else:
        params = { 'X-Plex-Token' : token }
    response = requests.get( '%s/library/sections/%d/refresh' % ( fullURL, library_key ),
                             params = params, verify = False )
    assert( response.status_code == 200 )
    print('Refreshing %s Library...' % library_dict[ library_key ])

def _get_failing_artistalbum( filename ):
    if os.path.basename( filename ).endswith( '.m4a' ):
        mp4tag = mutagen.mp4.MP4( filename )
        if not all([ key in mp4tag for key in ( '\xa9alb', '\xa9ART' ) ]):
            return filename
    return None        

def get_lastupdated_string( dt = datetime.datetime.now( ) ):
    # dt = dt = datetime.datetime.fromtimestamp( os.stat( dbloc ).st_mtime ) ):
    return dt.strftime('%A, %d %B %Y, at %-I:%M %p')
        
def get_allrows( ):
    with plexconnection( ) as c:
        rows = list( c.execute( 'SELECT * from media_parts;' ) )    
        return rows

def get_tvshownames_gspread( ):
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

def fill_out_movies_stuff( token, fullurl = 'http://localhost:32400' ):
    keys = get_movies_libraries( token, fullURL = fullurl )
    unified_movie_data = { }
    for key in keys:
        movie_data = get_movie_data( key, fullURL = fullurl, token = token )
        for genre in movie_data:
            unified_movie_data.setdefault( genre, [] ).append( movie_data[ genre ] )
    for genre in unified_movie_data:
        rows = reduce(lambda x,y: x + y, unified_movie_data[ genre ] )
        unified_movie_data[ genre ] = rows
    #
    ##
    movie_data_rows = [ ]
    num_err = 0
    genres = sorted( unified_movie_data.keys( ) )
    for genre in unified_movie_data:
        movie_data = [ ]
        for row in unified_movie_data[ genre ]:
            try:
                title, popularity, rating, imageURL, date_released, date_added, overview, _, _ = row
                if popularity is None:
                    popularity = 0.0
                if date_released is None:
                    date_released = datetime.datetime.strptime('1900-01-01', '%Y-%m-%d' ).date( )
                movie_data.append(( title, popularity, rating, date_released, date_added, genre,
                                    overview, imageURL ))
            except ValueError:
                num_err += 1
        movie_data_rows += movie_data
    #pickle.dump( movie_data_rows, gzip.open( os.path.expanduser('~/temp/movie_data_rows.pkl.gz' ), 'wb' ) )
    return movie_data_rows, genres


# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
     # http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Performs client tasks for testing IMAP OAuth2 authentication.

To use this script, you'll need to have registered with Google as an OAuth
application and obtained an OAuth client ID and client secret.
See https://developers.google.com/identity/protocols/OAuth2 for instructions on
registering and for documentation of the APIs invoked by this code.

Taken from oauth2.py, found at https://github.com/google/gmail-oauth2-tools, under python directory

Instructions on usage found here: https://github.com/google/gmail-oauth2-tools/wiki/OAuth2DotPyRunThrough
"""

def _url_escape(text):
    # See OAUTH 5.1 for a definition of which characters need to be escaped.
    return urllib.quote(text, safe='~-._')

def _accounts_url(command):
  """Generates the Google Accounts URL.

  Args:
    command: The command to execute.

  Returns:
    A URL for the given command.
  """
  return '%s/%s' % ( 'https://accounts.google.com', command )

def _format_url_params(params):
  """Formats parameters into a URL query string.

  Args:
    params: A key-value map.

  Returns:
    A URL query string version of the given parameters.
  """
  param_fragments = map(lambda param: '%s=%s' % ( param[0], _url_escape( param[1] ) ),
                        sorted( params.iteritems( ), key = lambda x: x[0] ) )
  return '&'.join( param_fragments )

def oauth_generate_permission_url(client_id = '1062550112138-03t22u9sr35ph67c7v7db3tsgcujhekf.apps.googleusercontent.com',
                                  scope='https://mail.google.com/'):
    """Generates the URL for authorizing access.
    
    This uses the "OAuth2 for Installed Applications" flow described at
    https://developers.google.com/accounts/docs/OAuth2InstalledApp
    
    Args:
    client_id: Client ID obtained by registering your app.
    scope: scope for access token, e.g. 'https://mail.google.com'
    Returns:
    A URL that the user should visit in their browser.
    """
    REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
    
    params = {}
    params['client_id'] = client_id
    params['redirect_uri'] = REDIRECT_URI
    params['scope'] = scope
    params['response_type'] = 'code'
    return '%s?%s' % (_accounts_url('o/oauth2/auth'),
                      _format_url_params(params))

def oauth_authorize_tokens(authorization_code,
                           client_id = '1062550112138-03t22u9sr35ph67c7v7db3tsgcujhekf.apps.googleusercontent.com',
                           client_secret = 'Sp3nrqJcryaym820zEJ9Mu4j' ):
  """Obtains OAuth access token and refresh token.

  This uses the application portion of the "OAuth2 for Installed Applications"
  flow at https://developers.google.com/accounts/docs/OAuth2InstalledApp#handlingtheresponse

  Args:
    client_id: Client ID obtained by registering your app.
    client_secret: Client secret obtained by registering your app.
    authorization_code: code generated by Google Accounts after user grants
        permission.
  Returns:
    The decoded response from the Google Accounts server, as a dict. Expected
    fields include 'access_token', 'expires_in', and 'refresh_token'.
  """
  REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
  params = {}
  params['client_id'] = client_id
  params['client_secret'] = client_secret
  params['code'] = authorization_code
  params['redirect_uri'] = REDIRECT_URI
  params['grant_type'] = 'authorization_code'
  request_url = _accounts_url('o/oauth2/token')

  response = urllib.urlopen(request_url, urllib.urlencode(params)).read()
  return json.loads(response)

def oauth_push_new_gmailauthentication( valid_token ):
    client_id = '1062550112138-03t22u9sr35ph67c7v7db3tsgcujhekf.apps.googleusercontent.com'
    client_secret = 'Sp3nrqJcryaym820zEJ9Mu4j'    
    filename = 'email_authentication.json'
    absPath = os.path.join( baseConfDir, filename )
    mydict = { 'Client ID' : client_id,
               'Client Secret' : client_secret,
               'Refresh Token' : valid_token }
    json.dump( mydict, open( absPath, 'w' ) )
    os.chmod( absPath, 0o600 )

def oauth_get_access_token( ):    
    filename = 'email_authentication.json'
    absPath = os.path.join( baseConfDir, filename )
    if not os.path.isfile( absPath ):
        return None
    creds_email = json.load( open( absPath, 'r' ) )
    refreshURL = 'https://accounts.google.com/o/oauth2/token'
    params = {
        'client_id' : creds_email['Client ID'],
        'client_secret' : creds_email['Client Secret'],
        'refresh_token' : creds_email['Refresh Token'],
        'grant_type' : 'refresh_token',
    }
    refreshData = json.loads( urllib.urlopen( refreshURL, urllib.urlencode( params ) ).read( ) )
    if 'access_token' not in refreshData:
       return None
    access_token = refreshData[ 'access_token' ]
    return access_token

def oauthCheckEmailCredentials( ):
    filename = 'email_authentication.json'
    absPath = os.path.join( baseConfDir, filename )
    if not os.path.isfile( absPath ):
        return False, 'EMAIL AUTHENTICATION FILE DOES NOT EXIST.'
    data = json.load( open( absPath, 'r' ) )
    if len( set([ 'Client ID', 'Client Secret', 'Refresh Token' ]) - set( data.keys( ) ) ) != 0:
        return False, 'HAVE NOT DEFINED ONE OF CLIENT ID, CLIENT SECRET, REFRESH TOKEN'
    val = oauth_get_access_token( )
    if val is None:
        return False, 'INVALID AUTHORIZATION CREDENTIALS'
    return True, 'SUCCESS'

def oauth_generate_contacts_permission_url( ):
    flow = flow_from_clientsecrets( os.path.join( mainDir, 'resources', 'client_secrets.json' ),
                                    scope = 'https://www.googleapis.com/auth/contacts.readonly',
                                    redirect_uri = "urn:ietf:wg:oauth:2.0:oob" )
    auth_uri = flow.step1_get_authorize_url( )
    return flow, auth_uri

def oauth_store_contacts_credentials( credentials ):    
    filename = 'contacts_authentication.json'
    absPath = os.path.join( baseConfDir, filename )
    oauth2client.file.Storage( absPath ).put( credentials )

def oauth_get_contact_access_token( ):
    import gdata.gauth
    filename = 'contacts_authentication.json'
    absPath = os.path.join( baseConfDir, filename )
    if not os.path.isfile( absPath ):
        return None
    try:
        credentials = oauth2client.file.Storage( absPath ).get( )
        credentials.refresh( httplib2.Http( ) )
        return gdata.gauth.OAuth2TokenFromCredentials( credentials )
    except:
        return None

def oauthCheckContactCredentials( ):
    filename = 'contacts_authentication.json'
    absPath = os.path.join( baseConfDir, filename )
    if not os.path.isfile( absPath ):
        return False, 'CONTACTS AUTHENTICATION FILE DOES NOT EXIST.'
    val = oauth_get_contact_access_token( )
    if val is None:
        return False, 'INVALID AUTHORIZATION CREDENTIALS'
    return True, 'SUCCESS'
    #
    ## now get the flow from mainDir
    flow = flow_from_clientsecrets( os.path.join( mainDir, 'resources', 'client_secrets.json'),
                                    client_secrets.json,
                                    redirect_uri = "urn:ietf:wg:oauth:2.0:oob" )
    auth_uri = flow.step1_get_authorize_url( )

def oauth_generate_youtube_permission_url( ):
    flow = flow_from_clientsecrets( os.path.join( mainDir, 'resources', 'client_secrets.json' ),
                                    scope = 'https://www.googleapis.com/auth/youtube.readonly',
                                    redirect_uri = "urn:ietf:wg:oauth:2.0:oob" )
    auth_uri = flow.step1_get_authorize_url( )
    return flow, auth_uri

def oauth_store_youtube_credentials( credentials ):
    filename = 'youtube_authentication.json'
    absPath = os.path.join( baseConfDir, filename )
    oauth2client.file.Storage( absPath ).put( credentials )

def oauth_get_youtube_access_token( ):
    import gdata.gauth
    filename = 'youtube_authentication.json'
    absPath = os.path.join( baseConfDir, filename )
    if not os.path.isfile( absPath ):
        return None
    try:
        credentials = oauth2client.file.Storage( absPath ).get( )
        credentials.refresh( httplib2.Http( ) )
        return gdata.gauth.OAuth2TokenFromCredentials( credentials )
    except:
        return None

def getOauthYoutubeCredentials( ):
    filename = 'youtube_authentication.json'
    absPath = os.path.join( baseConfDir, filename )
    if not os.path.isfile( absPath ):
        return None
    credentials = oauth2client.file.Storage( absPath ).get( )
    credentials.refresh( httplib2.Http( ) )
    return credentials
