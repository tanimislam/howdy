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
    Saves the provided TMDB_ API key into the ``plexconfig`` table, under the ``tmdb`` service, in the SQLite3_ configuration database.

    :param str apikey: the TMDB_ API key.

    .. _TMDB: https://www.themoviedb.org/documentation/api?language=en-US
    .. _SQLite3: https://www.themoviedb.org/documentation/api?language=en-US
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
    Returns the TMDB_ API key found in the SQLite3_ configuration database (specifically the ``tmdb`` service column in the ``plexconfig`` table). Otherwise returns ``None`` if not found.
    
    :returns: the TMDB_ API key.
    :rtype: str
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
    """
    The singleton class that, once called, initializes movie genre information from the TMDB_ database. This object can then be accessed to find TMDB_ database genre IDs from genres or vice-versa. This also loads in all TTF fonts located in the ``resources`` directory.

    .. seealso:: :py:class:`TMDBEngineSimple <plextmdb.TMDBEngineSimple>`
    """
    
    class __TMDBEngine( object ):
        """
        This object is only instantiated once. It implements mappings between TMDB_ API genre IDs and genre names (horror, comedy, etc.)  and loads all TTF fonts from the ``resources`` subdirectory.

        :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
        """
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
            """
            :param str genre: the movie genre.
            :returns: the TMDB_ genre ID from the genre.
            :rtype: int
            """
            return self._genres[ genre ]

        def getGenreFromGenreId( self, genre_id ):
            """
            :param int genre_id: the TMDB_ genre ID.
            :returns: the movie genre.
            :rtype: str
            """
            return self._genres_rev[ genre_id ]

        def getGenreIds( self ):
            """
            :returns: a :py:class:`list` of all the TMDB_ genre IDs.
            :rtype: list
            """
            return self._genres.values( )
        
        def getGenres( self ):
            """
            :returns: a :py:class:`list` of all the movie genres.
            :rtype: list
            """
            return self._genres.keys( )
        
        def get_tmdb_apiKey( self ):
            """
            :returns: a TMDB_ api key.
            :rtype: str
            """
            return self._tmdb_apiKey
        
    _instances = { }

    def __new__( cls, verify = True ):
        """
        Instantiates a single object of type :py:class:`TMDBEngine.__TMDBEngine <plextmdb.TMDBEngine.__TMDBEngine>` that contains TMDB_ API genre ID mappings, and that updates the GUI database to load all TTF fonts in the ``resources`` subdirectory.

        :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
        :returns: a single instance of :py:class:`TMDBEngine.__TMDBEngine <plextmdb.TMDBEngine.__TMDBEngine>`.
        :rtype: :py:class:`TMDBEngine.__TMDBEngine <plextmdb.TMDBEngine.__TMDBEngine>`
        """
        if verify not in TMDBEngine._instances:
            TMDBEngine._instances[ verify ] = TMDBEngine.__TMDBEngine( verify = verify )
        return TMDBEngine._instances[ verify ]

class TMDBEngineSimple( object ):
    """
    The singleton class that, once called, initializes movie genre information from the TMDB_ database. This object can then be accessed to find TMDB_ database genre IDs from genres or vice-versa. Unlike :py:class:`TMDBEngine <plextmdb.TMDBEngine>`, this also does not contain the TMDB_ API key.

    .. seealso:: :py:class:`TMDBEngine <plextmdb.TMDBEngine>`
    """
    
    class __TMDBEngine( object ):
        """
        This object is only instantiated once. It implements mappings between TMDB_ API genre IDs and genre names (horror, comedy, etc.).

        :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
        """
        def __init__( self, verify = True ):
            mainURL = 'http://api.themoviedb.org/3/genre/movie/list'
            params = { 'api_key' : tmdb_apiKey }
            response = requests.get( mainURL, params = params, verify = verify )
            data = response.json( )
            genres_tup = data['genres']
            self._genres = { genre_row['name'] : genre_row['id'] for genre_row in genres_tup }
            self._genres_rev = { genre_row['id'] : genre_row['name'] for genre_row in genres_tup }
            
        def getGenreIdFromGenre( self, genre ):
            """
            :param str genre: the movie genre.
            :returns: the TMDB_ genre ID from the genre.
            :rtype: int
            """
            return self._genres[ genre ]

        def getGenreFromGenreId( self, genre_id ):
            """
            :param int genre_id: the TMDB_ genre ID.
            :returns: the movie genre.
            :rtype: str
            """
            return self._genres_rev[ genre_id ]

        def getGenreIds( self ):
            """
            :returns: a :py:class:`list` of all the TMDB_ genre IDs.
            :rtype: list
            """
            return self._genres.values( )
        
        def getGenres( self ):
            """
            :returns: a :py:class:`list` of all the movie genres.
            :rtype: list
            """
            return self._genres.keys( )

    _instances = { }

    def __new__( cls, verify = True ):
        """
        Instantiates a single object of type :py:class:`TMDBEngineSimple.__TMDBEngine <plextmdb.TMDBEngineSimple.__TMDBEngine>` that contains TMDB_ API genre ID mappings.

        :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
        :returns: a single instance of :py:class:`TMDBEngineSimple.__TMDBEngine <plextmdb.TMDBEngineSimple.__TMDBEngine>`.
        :rtype: :py:class:`TMDBEngineSimple.__TMDBEngine <plextmdb.TMDBEngineSimple.__TMDBEngine>`
        """
        if verify not in TMDBEngineSimple._instances:
            TMDBEngineSimple._instances[ verify ] = TMDBEngineSimple.__TMDBEngine( verify )
        return TMDBEngineSimple._instances[ verify ]
