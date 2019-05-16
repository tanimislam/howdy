import os, sys, glob, logging, pytest, signal
from . import signal_handler
signal.signal( signal.SIGINT, signal_handler )
from plextmdb import plextmdb

_movie_name = 'Corner Gas: The Movie'
_actor_name = 'Brent Butt'
_genre = 'comedy'

@pytest.fixture( scope = "module" )
def get_tv_ids_by_series_name( request ):
    verify = request.config.option.do_verify
    tmdb_ids = plextmdb.get_tv_ids_by_series_name(
        'The Simpsons' )
    print( 'here are the TMDB IDs for the Simpsons: %s' %
           tmdb_ids )
    yield tmdb_ids

@pytest.fixture( scope = "module" )
def get_movie_tmdbids( request ):
    verify = request.config.option.do_verify
    tmdb_ids = plextmdb.get_movie_tmdbids(
        _movie_name, verify = verify, getAll = True )
    print( 'here are the TMDB IDs for %s: %s' % (
        _movie_name, tmdb_ids ) )
    yield tmdb_ids

@pytest.fixture( scope = "module")
def get_genre_movie( request ):
    verify = request.config.option.do_verify    
    genre = plextmdb.get_genre_movie( _movie_name, verify = verify )
    print( 'here is the main genre for %s: %s' % (
        _movie_name, genre ) )
    yield genre    

def test_get_tv_ids_by_series_name( get_tv_ids_by_series_name ):
    tmdb_ids = get_tv_ids_by_series_name
    assert( len( tmdb_ids ) != 0 )
    assert( all(map(lambda id: isinstance( id, int ), tmdb_ids ) ) )

def test_get_tv_info_for_series( get_tv_ids_by_series_name, request ):
    season = 1
    verify = request.config.option.do_verify
    tmdb_id = max( get_tv_ids_by_series_name )
    assert( plextmdb.get_tv_info_for_season(
        tmdb_id, season, verify = verify ) is not None )

def test_get_episodes_series_tmdb( get_tv_ids_by_series_name, request ):
    verify = request.config.option.do_verify
    tmdb_id = max( get_tv_ids_by_series_name )
    assert( len(
        plextmdb.get_episodes_series_tmdb(
        tmdb_id, verify = verify ) ) != 0 )

def test_get_movies_by_actors( request ):
    verify = request.config.option.do_verify
    actor_names = [ _actor_name ]
    actualMovieData = plextmdb.get_movies_by_actors(
        actor_names, verify = verify )
    assert( len( actualMovieData ) != 0 )
    assert( any( map(
        lambda row: row[ 'title' ] == _movie_name,
        actualMovieData ) ) )

def test_get_movies_by_title( request ):
    verify = request.config.option.do_verify
    actualMovieData = plextmdb.get_movies_by_title(
        'Corner Gas', verify = verify )
    assert( len( actualMovieData ) != 0 )
    assert( any( map(
        lambda row: row[ 'title' ] == _movie_name,
        actualMovieData ) ) )

#
## does not work right now
def test_get_imdbid_from_id( get_tv_ids_by_series_name, request ):
    verify = request.config.option.do_verify
    tmdb_id = max( get_tv_ids_by_series_name )
    imdb_id = plextmdb.get_imdbid_from_id( tmdb_id, verify = verify )
    assert( imdb_id is not None )
    assert( isinstance( imdb_id, int ) )

def test_get_movie( request ):
    verify = request.config.option.do_verify
    results = plextmdb.get_movie( _movie_name, verify = verify, getAll = True )
    assert( results is not None )
    assert( len( results ) != 0 )
    
def test_get_movie_tmdbids( get_movie_tmdbids ):
    tmdb_ids = get_movie_tmdbids
    assert( tmdb_ids is not None )
    assert( len( tmdb_ids ) != 0 )
    assert( all(map(lambda id: isinstance( id, int ), tmdb_ids ) ) )
    
def test_get_genre_movie( get_genre_movie ):
    verify = request.config.option.do_verify
    genre = get_genre_movie
    assert( genre is not None )

def test_getMovieData( request ):
    verify = request.config.option.do_verify
    year = 1991
    actualMovieData = plextmdb.getMovieData( year, _genre, verify = verify )
    assert( actualMovieData is not None )
    assert( len( actualMovieData ) != 0 )
