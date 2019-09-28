import os, sys, requests, glob
from functools import reduce
_mainDir = reduce(lambda x,y: os.path.dirname( x ), range( 2 ),
                  os.path.abspath( __file__ ) )
sys.path.append( _mainDir )

#from requests_respectful import RespectfulRequester
#tmdbrequests = RespectfulRequester( )
#tmdbrequests.register_realm( 'TheMovieDB', max_requests = 40, timespan = 10 )

from plexcore import session, PlexConfig, mainDir

def save_tmdb_api( apikey ):
    """
    Saves the provided TMDB API key into the database, stored on disk at ~/.config/plexstuff/app.db.

    Args:
        apikey (str): The TMDB API string, whose format is described in `The TMDB API`_.

    .._The TMDB API: https://developers.themoviedb.org/3/getting-started/introduction
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

def get_tmdb_api( ) -> str:
    """
    Returns the TMDB API key found in the database, stored on disk at
    ``~/.config/plexstuff/app.db``.

    Returns
        str: the TMDB API access key stored in the database.
    """
    query = session.query( PlexConfig ).filter(
        PlexConfig.service == 'tmdb' )
    val = query.first( )
    if val is None:
        raise ValueError("ERROR, NO TMDB API CREDENTIALS FOUND")
    return val.data['apikey']

if not os.environ.get( 'READTHEDOCS' ): tmdb_apiKey = get_tmdb_api( )
else: tmdb_apiKey = ''

#
## singleton objects
class TMDBEngine( object ):
    class __TMDBEngine( object ):
        def __init__( self, verify = True ):
            from PyQt4.QtGui import QFontDatabase
            mainURL = 'https://api.themoviedb.org/3/genre/movie/list'
            params = { 'api_key' : tmdb_apiKey }
            response = requests.get( mainURL, params = params, verify = verify )
            data = response.json( )
            genres_tup = data['genres']
            self._genres = { genre_row['name'] : genre_row['id'] for genre_row in genres_tup }
            self._genres_rev = { genre_row['id'] : genre_row['name'] for genre_row in genres_tup }
            self._genres[ 'ALL' ] = -1
            self._genres_rev[ -1 ] = 'ALL'
            #
            ## now load in the fonts
            for fontFile in glob.glob( os.path.join( mainDir, 'resources', '*.ttf' ) ):
                QFontDatabase.addApplicationFont( fontFile )
            
        def getGenreIdFromGenre( self, genre ):
            return self._genres[ genre ]

        def getGenreFromGenreId( self, genre_id ):
            return self._genres_rev[ genre_id ]

        def getGenreIds( self ):
            return self._genres.values( )
        
        def getGenres( self ):
            return self._genres.keys( )
        
        def get_tmdb_apiKey( self ):
            return self._tmdb_apiKey
        
    _instances = { }

    def __new__( cls, verify = True ):
        if verify not in TMDBEngine._instances:
            TMDBEngine._instances[ verify ] = TMDBEngine.__TMDBEngine( verify = verify )
        return TMDBEngine._instances[ verify ]

class TMDBEngineSimple( object ):
    class __TMDBEngine( object ):
        def __init__( self, verify = True ):
            mainURL = 'http://api.themoviedb.org/3/genre/movie/list'
            params = { 'api_key' : tmdb_apiKey }
            response = requests.get( mainURL, params = params, verify = verify )
            data = response.json( )
            genres_tup = data['genres']
            self._genres = { genre_row['name'] : genre_row['id'] for genre_row in genres_tup }
            self._genres_rev = { genre_row['id'] : genre_row['name'] for genre_row in genres_tup }
            
        def getGenreIdFromGenre( self, genre ):
            return self._genres[ genre ]

        def getGenreFromGenreId( self, genre_id ):
            return self._genres_rev[ genre_id ]

        def getGenreIds( self ):
            return self._genres.values( )
        
        def getGenres( self ):
            return self._genres.keys( )

    _instances = { }

    def __new__( cls, verify = True ):
        if verify not in TMDBEngineSimple._instances:
            TMDBEngineSimple._instances[ verify ] = TMDBEngineSimple.__TMDBEngine( verify )
        return TMDBEngineSimple._instances[ verify ]
