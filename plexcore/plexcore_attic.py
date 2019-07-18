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
    import shutil, tempfile, sqlite3
    _, tmpsub = tempfile.mkstemp( suffix = '.db' )
    shutil.copy( dbloc, tmpsub )
    conn = sqlite3.connect( tmpsub )
    cursor = conn.cursor( )
    try:
        yield cursor
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
    """    
    assert( os.path.isfile( filename ) )
    readsize = 64 * 1024
    with open( filename, 'rb') as openfile:
        size = os.path.getsize( name )
        data = openfile.read( readsize )
        openfile.seek( -readsize, os.SEEK_END )
        data += openfile.read( readsize )
    return hashlib.md5(data).hexdigest( )
