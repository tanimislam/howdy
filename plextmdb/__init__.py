# resource file
import os, sys
mainDir = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
sys.path.append( mainDir )
from plexcore import session, PlexConfig

def save_tmdb_api( apikey ):
    """
    Saves the provided TMDB API key into the database, stored on disk at ~/.config/plexstuff/app.db.

    Parameters
    ----------
    apikey (string): The TMDB API string, whose format is described in `The TMDB API`_.

    Returns
    -------
    None

    .._The TMDB API:
       https://developers.themoviedb.org/3/getting-started/introduction
    """
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
    """
    Returns the TMDB API key found in the database, stored on disk at ~/.config/plexstuff/app.dbself.

    Returns
        string: the TMDB API key stored in the database.
    -------
    """
    query = session.query( PlexConfig ).filter( PlexConfig.service == 'tmdb' )
    val = query.first( )
    if val is None:
        raise ValueError("ERROR, NO TMDB API CREDENTIALS FOUND")
    return val.data['apikey']
