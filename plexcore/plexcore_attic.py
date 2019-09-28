import os, sys, sqlite3, tempfile, shutil, numpy, hashlib
from functools import reduce
__mainDir = reduce(lambda x,y: os.path.dirname( x ), range( 2 ),
                   os.path.abspath( __file__ ) )
sys.path.append( _mainDir )

from contextlib import contextmanager

dbloc = os.path.join( '/var/lib/plexmediaserver/Library/',
                      'Application Support/Plex Media Server/',
                      'Plug-in Support/Databases/com.plexapp.plugins.library.db' )
# assert( os.path.isfile( dbloc )

@contextmanager
def plexconnection( ):
    _, tmpsub = tempfile.mkstemp( suffix = '.db' )
    shutil.copy( dbloc, tmpsub )
    conn = sqlite3.connect( tmpsub )
    cursor = conn.cursor( )
    try: yield cursor
    finally:
        conn.close( )
        os.remove( tmpsub )

def get_allrows( ):
    with plexconnection( ) as c:
        rows = list( c.execute( 'SELECT * FROM media_parts;' ) )    
        return rows

def get_hash(filename):
    """
    Uses the SubDB API to get subtitles

    :param str filename: the subtitle filename.
    :returns: the MD5 hash of the subtitle filename.
    :rtype: str
    """    
    assert( os.path.isfile( filename ) )
    readsize = 64 * 1024
    with open( filename, 'rb') as openfile:
        size = os.path.getsize( name )
        data = openfile.read( readsize )
        openfile.seek( -readsize, os.SEEK_END )
        data += openfile.read( readsize )
    return hashlib.md5(data).hexdigest( )

def get_tvshownames_gspread( ):
    import oauth2client.file, httplib2
    credPath = os.path.join(
        mainDir, 'resources', 'credentials_gspread.json' )
    storage = oauth2client.file.Storage( credPath )
    credentials = storage.get( )
    credentials.refresh( httplib2.Http( ) )
    gclient = gspread.authorize( credentials )
    sURL = 'https://docs.google.com/spreadsheets/d/10MR-mXd3sJlZWKOG8W-LhYp_6FAt0wq1daqPZ7is9KE/edit#gid=0'
    sheet = gclient.open_by_url( sURL )
    wksht = sheet.get_worksheet( 0 )
    tvshowshere = set(filter(lambda val: len(val.strip()) != 0, wksht.col_values(1)))
    return tvshowshere

def get_movie_titles_by_year(
        year, fullURL = 'http://localhost:32400', token = None ):
    if token is None: params = {}
    else: params = { 'X-Plex-Token' : token }
    params['year'] = year
    libraries_dict = get_libraries( token, fullURL = fullURL )
    if libraries_dict is None:
        return None
    keynum = max([ key for key in libraries_dict if libraries_dict[key] == 'Movies' ])
    response = requests.get( '%s/library/sections/%d/all' % ( fullURL, keynum ),
                             params = params, verify = False )                             
    if response.status_code != 200: return None
    movie_elems = filter( lambda elem: 'title' in elem.attrs,
                          BeautifulSoup( response.content, 'lxml' ).find_all('video') )
    return sorted(set(map( lambda movie_elem: movie_elem['title'], movie_elems ) ) )
