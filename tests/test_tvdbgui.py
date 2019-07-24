import os, sys, glob, logging, pytest, warnings
import qdarkstyle, pickle, gzip, requests, time
from PyQt4.QtGui import QApplication
from plexcore import plexcore
from plextvdb import plextvdb_gui, plextvdb_season_gui, get_token, plextvdb
from .test_plexcore import get_token_fullURL, get_libraries_dict

@pytest.fixture( scope="module" )
def get_tvdata_toGet_didend( request, get_token_fullURL, get_libraries_dict ):
    testDir = os.path.expanduser( '~/.config/plexstuff/tests' )
    time0 = time.time( )
    rebuild = request.config.option.do_rebuild
    doLocal = request.config.option.do_local
    verify = request.config.option.do_verify
    fullURL, token = get_token_fullURL
    libraries_dict = get_libraries_dict
    if rebuild:
        #
        ## tv library
        key = list(filter(lambda k: libraries_dict[k][-1] == 'show',
                          libraries_dict))
        assert( len( key ) != 0 )
        key = max( key )
        library_name = libraries_dict[ key ][ 0 ]
        tvdata = plexcore.get_library_data( library_name, token = token, fullURL = fullURL )
        pickle.dump( tvdata, gzip.open(
            os.path.join( testDir, 'tvdata.pkl.gz' ), 'wb' ) )
        #
        ## toGet
        toGet = plextvdb.get_remaining_episodes(
            tvdata, showSpecials=False, showsToExclude = plextvdb.get_shows_to_exclude( ),
            verify = verify )
        pickle.dump( toGet, gzip.open(
            os.path.join( testDir, 'toGet.pkl.gz' ), 'wb' ) )
        #
        ## didend
        didend = plextvdb.get_all_series_didend( tvdata, verify = verify )
        pickle.dump( didend, gzip.open(
            os.path.jpin( testDir, 'didend.pkl.gz' ), 'wb' ) )
        print( 'processed and stored new TV data in %0.3f seconds.' % (
            time.time( ) - time0 ) )
    else:
        tvdata = pickle.load(
            gzip.open( os.path.join( testDir, 'tvdata.pkl.gz' ), 'rb' ) )
        toGet = pickle.load( gzip.open(
            gzip.open( os.path.join( testDir, 'toGet.pkl.gz' ), 'rb' ) )
        didend = pickle.load( gzip.open(
            os.path.join( testDir, 'didend.pkl.gz'), 'rb' ) )
    yield tvdata, toGet, didend

@pytest.fixture( scope="module" )
def get_app( ):
    app = QApplication([])
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
    yield app

def test_tvdbseason_gui( get_token_fullURL, get_tvdata_toGet_didend, get_app,
                         request ):
    verify = request.config.option.do_verify
    series = 'The Simpsons'
    season = 1
    fullURL, plex_token = get_token_fullURL
    app = get_app
    tvdata, toGet, _ = get_tvdata_toGet_didend
    assert( season > 0 )
    assert( series in tvdata )
    assert( season in tvdata[ series ][ 'seasons' ] )
    missing_eps = dict(map(
        lambda seriesName: ( seriesName, toGet[ seriesName ][ 'episodes' ] ),
        toGet ) )#
    tvdb_season_gui = plextvdb_season_gui.TVDBSeasonGUI(
        series, season, tvdata, missing_eps, get_token( verify = verify ),
        plex_token, verify = verify )

def test_tvdbshow_gui( get_token_fullURL, get_tvdata_toGet_didend, get_app,
                       request ):
    verify = request.config.option.do_verify
    series = 'The Simpsons'
    fullURL, plex_token = get_token_fullURL
    app = get_app
    tvdata, toGet, _ = get_tvdata_toGet_didend
    assert( series in tvdata )
    tvdb_token = get_token( verify = verify )
    tvdb_show_gui = plextvdb_gui.TVDBShowGUI(
        series, tvdata, toGet, tvdb_token, plex_token,
        verify = verify )

def test_tvdb_gui( get_token_fullURL, get_tvdata_toGet_didend, get_app,
                   request ):
    verify = request.config.option.do_verify
    fullURL, plex_token = get_token_fullURL
    app = get_app
    tvdata, toGet, didend = get_tvdata_toGet_didend
    tvdbg = plextvdb_gui.TVDBGUI(
        plex_token, fullURL, tvdata_on_plex = tvdata,
        toGet = toGet, didend = didend, verify = verify )
