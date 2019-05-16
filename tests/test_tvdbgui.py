import os, sys, glob, logging, pytest, warnings
import qdarkstyle, pickle, gzip, requests
from PyQt4.QtGui import QApplication
from plextvdb import plextvdb_gui, plextvdb_season_gui, get_token
from .test_plexcore import get_token_fullURL

def get_tvdata_toGet_didend_standalone( ):
    tvdata = pickle.load( gzip.open(max(glob.glob('tvdata*pkl.gz')), 'rb' ))
    toGet  = pickle.load( gzip.open(max(glob.glob('toGet*pkl.gz')), 'rb' ))
    didend = pickle.load( gzip.open(max(glob.glob('didend*pkl.gz')), 'rb'))
    return tvdata, toGet, didend

def get_app_standalone( ):
    app = QApplication([])
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
    return app

@pytest.fixture( scope="module" )
def get_tvdata_toGet_didend( ):
    tvdata = pickle.load( gzip.open(max(glob.glob('tvdata*pkl.gz')), 'rb' ))
    toGet  = pickle.load( gzip.open(max(glob.glob('toGet*pkl.gz')), 'rb' ))
    didend = pickle.load( gzip.open(max(glob.glob('didend*pkl.gz')), 'rb'))
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
