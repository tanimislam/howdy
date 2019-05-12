import os, sys, sqlite3, tempfile, shutil
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
