# resource file
import os, sys
mainDir = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
sys.path.append( mainDir )
from plexcore import session, PlexConfig

def save_tmdb_api( apikey ):
    query = session.query( PlexConfig ).filter( PlexConfig.service == 'tmdb' )
    val = query.first( )
    if val is not None:
        session.delete( val )
        session.commit( )
    newval = PlexConfig( service = 'tmdb',
                         data = { 'apikey' : apikey.strip( ) } )
    session.add( newval )
    session.commit( )

def get_tmdb_api( ):
    query = session.query( PlexConfig ).filter( PlexConfig.service == 'tmdb' )
    val = query.first( )
    if val is None:
        raise ValueError("ERROR, NO TMDB API CREDENTIALS FOUND")
    return val.data['apikey']
    


