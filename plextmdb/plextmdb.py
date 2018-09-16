import logging, glob, os, requests, datetime, fuzzywuzzy.fuzz
from . import mainDir, tmdb_apiKey

def get_movies_by_actors( actor_names ):
    actor_name_dict = { }
    for actor_name in set(actor_names):
        actor_ids = [ ]
        params = { 'api_key' : tmdb_apiKey,
                   'query' : '+'.join( actor_name.split( ) ), }
        response = requests.get( 'https://api.themoviedb.org/3/search/person',
                                 params = params )
        if response.status_code != 200:
            continue
        data = response.json()
        total_pages = data['total_pages']
        actor_ids = list( map(lambda result: result['id'], data['results'] ) )
        if total_pages >= 2:
            for pageno in xrange(2, total_pages + 1 ):
                params =  { 'api_key' : tmdb_apiKey,
                            'query' : '+'.join( actor_name.split( ) ),
                            'page' : pageno }
            response = requests.get( 'https://api.themoviedb.org/3/search/person',
                                     params = params )
            if response.status_code != 200:
                continue
            data = response.json( )
            actor_ids += list( map(lambda result: result['id'], data['results'] ) )
        actor_name_dict[ actor_name ] = min(set( actor_ids ) )
    #
    response = requests.get( 'https://api.themoviedb.org/3/discover/movie',
                             params = { 'api_key' : tmdb_apiKey,
                                        'append_to_response': 'images',
                                        'include_image_language': 'en',
                                        'language': 'en',
                                        'page': 1,
                                        'sort_by': 'popularity.desc',
                                        'with_cast' : ','.join(map(lambda num: '%d' % num,
                                                                   actor_name_dict.values( ) ) ) } )
    if response.status_code != 200:
        return [ ]
    data = response.json( )
    total_pages = data['total_pages']
    results = data['results']
    if total_pages >= 2:
        for pageno in xrange( 2, total_pages + 1 ):
            response = requests.get( 'https://api.themoviedb.org/3/discover/movie',
                                     params = { 'api_key' : tmdb_apiKey,
                                                'append_to_response': 'images',
                                                'include_image_language': 'en',
                                                'language': 'en',
                                                'sort_by': 'popularity.desc',
                                                'with_cast' : ','.join(map(lambda num: '%d' % num,
                                                                           actor_name_dict.values( ) ) ),
                                                'page' : pageno } )
            if response.status_code != 200:
                continue
            data = response.json( )
            results += data[ 'results' ]
    # return results
    actualMovieData = [ ]
    moviePosterMainURL = 'http://image.tmdb.org/t/p/w396'
    movieListMainURL = 'http://api.themoviedb.org/3/discover/movie'
    for datum in results:
        if 'poster_path' not in datum or datum['poster_path'] is None:
            poster_path = None
        else:
            poster_path = moviePosterMainURL + datum['poster_path']
        if 'vote_average' not in datum:
            vote_average = 0.0
        else:
            if 'vote_count' not in datum or int( datum[ 'vote_count' ] ) <= 10:
                vote_average = 0.0
            else:
                vote_average = float( datum[ 'vote_average' ] )
        try:
            datetime.datetime.strptime( datum['release_date'], '%Y-%m-%d' ),
            row = [ datum['title'],
                    datetime.datetime.strptime( datum['release_date'], '%Y-%m-%d' ),
                    datum['popularity'],
                    vote_average,
                    datum['overview'],                    
                    poster_path,
                    False ]
        except Exception:
            pass
        actualMovieData.append( row )
    return actualMovieData

def get_movies_by_title( title ):
    response = requests.get( 'https://api.themoviedb.org/3/search/movie',
                             params = { 'api_key' : tmdb_apiKey,
                                        'append_to_response': 'images',
                                        'include_image_language': 'en',
                                        'language': 'en',
                                        'sort_by': 'popularity.desc',
                                        'query' : '+'.join( title.split( ) ),
                                        'page' : 1 } )
    if response.status_code != 200:
        return [ ]
    data = response.json( )
    total_pages = data['total_pages']
    results = list( filter(lambda result: fuzzywuzzy.fuzz.ratio( result['title'], title ) >= 10.0,
                           data['results'] ) )
    results = sorted( results, key = lambda result: -fuzzywuzzy.fuzz.ratio( result['title'], title ) )
    if total_pages >= 2:
        for pageno in xrange( 2, max( 5, total_pages + 1 ) ):
            response = requests.get( 'https://api.themoviedb.org/3/search/movie',
                                     params = { 'api_key' : tmdb_apiKey,
                                                'append_to_response': 'images',
                                                'include_image_language': 'en',
                                                'language': 'en',
                                                'sort_by': 'popularity.desc',
                                                'query' : '+'.join( title.split( ) ),
                                                'page' : pageno } )
            if response.status_code != 200:
                continue
            data = response.json( )
            newresults = list( filter(lambda result: fuzzywuzzy.fuzz.ratio( result['title'], title ) >= 10.0,
                                      data['results'] ) )
            if len( newresults ) > 0:
                results += sorted( newresults, key = lambda result: -fuzzywuzzy.fuzz.ratio( result['title'], title ) )
    #return results
    actualMovieData = [ ]
    moviePosterMainURL = 'http://image.tmdb.org/t/p/w396'
    movieListMainURL = 'http://api.themoviedb.org/3/discover/movie'
    for datum in results:
        if 'poster_path' not in datum or datum['poster_path'] is None:
            poster_path = None
        else:
            poster_path = moviePosterMainURL + datum['poster_path']
        if 'vote_average' not in datum:
            vote_average = 0.0
        else:
            if 'vote_count' not in datum or int( datum[ 'vote_count' ] ) <= 10:
                vote_average = 0.0
            else:
                vote_average = float( datum[ 'vote_average' ] )
        try:
            datetime.datetime.strptime( datum['release_date'], '%Y-%m-%d' ),
            row = [ datum['title'],
                    datetime.datetime.strptime( datum['release_date'], '%Y-%m-%d' ),
                    datum['popularity'],
                    vote_average,
                    datum['overview'],                    
                    poster_path,
                    False ]
        except Exception:
            pass
        actualMovieData.append( row )
    return actualMovieData

# Followed advice from https://www.themoviedb.org/talk/5493b2b59251416e18000826?language=en
def get_imdbid_from_id( id ):
    response = requests.get( 'https://api.themoviedb.org/3/movie/%d' % id,
                             params = { 'api_key' : tmdb_apiKey } )
    if response.status_code != 200:
        return None
    data = response.json( )
    if 'imdb_id' not in data:
        return None
    return data['imdb_id']

def get_movie( title, year = None, checkMultiple = True, getAll = False ):
    movieSearchMainURL = 'https://api.themoviedb.org/3/search/movie'
    params = { 'api_key' : tmdb_apiKey,
               'append_to_response': 'images',
               'include_image_language': 'en',
               'language': 'en',
               'sort_by': 'popularity.desc',
               'query' : '+'.join( title.split( ) ),
               'page' : 1 }
    if year is not None:
        params[ 'primary_release_year' ] = int( year )
    response = requests.get( movieSearchMainURL, params = params )
    data = response.json( )
    if 'total_pages' in data:
        total_pages = data['total_pages']
        results = list( filter(lambda result: fuzzywuzzy.fuzz.ratio( result['title'], title ) >= 90.0,
                         data['results'] ) )
        results = sorted( results, key = lambda result: -fuzzywuzzy.fuzz.ratio( result['title'], title ) )
    else:
        return None
    if len(results) == 0:
        if checkMultiple:
            indices = range(len(title.split()))
            for idx in indices:
                split_titles = title.split()
                split_titles[idx] = split_titles[idx].upper( )
                newtitle = ' '.join( split_titles )
                val = get_movie( newtitle, year = year, checkMultiple = False )
                if val is not None:
                    return val
        return None
    if not getAll:
        first_movie = results[0]
        return 'https://www.themoviedb.org/movie/%d' % first_movie['id']
    else:
        return results

def get_movie_tmdbids( title, year = None, getAll = False ):
    results = get_movie( title, year = year, checkMultiple = True, getAll = True )
    if results is None: return None
    ids = list(map(lambda result: result['id'], results ) )
    if not getAll: return ids[0]
    else: return ids                   

#
## funky logic needed here...
def get_genre_movie( title, year = None, checkMultiple = True ):
    movieSearchMainURL = 'http://api.themoviedb.org/3/search/movie'
    params = { 'api_key' : tmdb_apiKey,
               'query' : '+'.join( title.split( ) ),
               'page' : 1 }
    if year is not None:
        params[ 'primary_release_year' ] = int( year )
    response = requests.get( movieSearchMainURL, params = params )
    data = response.json( )
    if 'total_pages' in data:
        total_pages = data['total_pages']
        results = list( filter(lambda result: fuzzywuzzy.fuzz.ratio( result['title'], title ) >= 90.0,
                               data['results'] ) )
        results = sorted( results, key = lambda result: -fuzzywuzzy.fuzz.ratio( result['title'], title ) )
    else: results = [ ]
    if len(results) == 0:
        if checkMultiple:
            indices = range(len(title.split()))
            for idx in indices:
                split_titles = title.split()
                split_titles[idx] = split_titles[idx].upper( )
                newtitle = ' '.join( split_titles )
                val = get_genre_movie( newtitle, year = year, checkMultiple = False )
                if val is not None:
                    return val
        return None
    first_movie = results[0]
    genre_ids = first_movie['genre_ids']
    for genre_id in genre_ids:
        val = TMDBEngineSimple( ).getGenreFromGenreId( genre_id ).lower( )
        if val in ( 'horror', 'comedy', 'animation', 'documentary', 'drama',
                    'action', 'hindi', 'horror', 'science fiction' ):
            return val
        if val == 'fantasy':
            return 'science fiction'
        if val == 'family':
            return 'drama'

def get_main_genre_movie( movie_elem ):
    def postprocess_genre( genre ):
        if 'sci-fi' in genre:
            return 'science fiction'
        if genre == 'adventure':
            return 'action'
        if genre == 'thriller':
            return 'action'
        if genre == 'crime':
            return 'drama'
        if genre == 'romance':
            return 'drama'
        if genre == 'factual':
            return 'documentary'
        if genre == 'war':
            return 'drama'
        if genre == 'mystery':
            return 'horror'
        return genre
    
    if len(movie_elem.find_all('genre') ) == 0:
        val = get_genre_movie( movie_elem[ 'title' ] )
        if val is None:
            return 'unclassified'
        return val
    classic_genres = [ 'horror', 'comedy', 'animation', 'documentary', 'drama',
                       'action', 'hindi', 'horror', 'science fiction' ]
    genres = list( map(lambda elem: elem['tag'].lower( ).strip( ), movie_elem.find_all( 'genre' ) ) )
    for genre in genres:
        if genre in classic_genres:
            return genre
    val = get_genre_movie( movie_elem[ 'title' ] )
    if val is not None:
        return val
    return postprocess_genre( genres[ 0 ] )
                             
def getMovieData( year, genre_id ):
    moviePosterMainURL = 'http://image.tmdb.org/t/p/w396'
    movieListMainURL = 'http://api.themoviedb.org/3/discover/movie'
    params = { 'api_key' : tmdb_apiKey,
               'append_to_response': 'images',
               'include_image_language': 'en',
               'language': 'en',
               'page': 1,
               'primary_release_year': year,
               'sort_by': 'popularity.desc',
               'with_genres': genre_id }
    if genre_id == -1: params.pop( 'with_genres' )
    response = requests.get( movieListMainURL, params = params )
    logging.debug('RESPONSE STATUS FOR %s = %s.' % ( str(params), str(response) ) )
    total_pages = response.json()['total_pages']
    data = list( filter(lambda datum: datum['title'] is not None and
                        datum['release_date'] is not None and
                        datum['popularity'] is not None, response.json( )['results'] ) )
    for pageno in range( 2, total_pages + 1 ):
        params['page'] = pageno
        response = requests.get( movieListMainURL, params = params )
        if response.status_code != 200: continue
        logging.debug('RESPONSE STATUS FOR %s = %s.' % ( str(params), str(response) ) )
        data += list( filter(lambda datum: datum['title'] is not None and
                             datum['release_date'] is not None and
                             datum['popularity'] is not None, response.json( )['results'] ) )
    actualMovieData = [ ]
    for datum in data:
        if 'poster_path' not in datum or datum['poster_path'] is None:
            poster_path = None
        else:
            poster_path = moviePosterMainURL + datum['poster_path']
        if 'vote_average' not in datum:
            vote_average = 0.0
        else:
            if 'vote_count' not in datum or int( datum[ 'vote_count' ] ) <= 10:
                vote_average = 0.0
            else:
                vote_average = float( datum[ 'vote_average' ] )
        row = [ datum['title'],
                datetime.datetime.strptime( datum['release_date'], '%Y-%m-%d' ),
                datum['popularity'],
                vote_average,
                datum['overview'],                    
                poster_path,
                False ]
        actualMovieData.append( row )
    return actualMovieData

class TMDBEngine( object ):
    class __TMDBEngine( object ):
        def __init__( self ):
            from PyQt4.QtGui import QFontDatabase
            mainURL = 'http://api.themoviedb.org/3/genre/movie/list'
            params = { 'api_key' : tmdb_apiKey }
            response = requests.get( mainURL, params = params )
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

    _instance = None

    def __new__( cls ):
        if not TMDBEngine._instance:
            TMDBEngine._instance = TMDBEngine.__TMDBEngine( )
        return TMDBEngine._instance

class TMDBEngineSimple( object ):
    class __TMDBEngine( object ):
        def __init__( self ):
            mainURL = 'http://api.themoviedb.org/3/genre/movie/list'
            params = { 'api_key' : tmdb_apiKey }
            response = requests.get( mainURL, params = params )
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

    _instance = None

    def __new__( cls ):
        if not TMDBEngineSimple._instance:
            TMDBEngineSimple._instance = TMDBEngineSimple.__TMDBEngine( )
        return TMDBEngineSimple._instance
