import os, sys, glob, logging, pytest
import qdarkstyle, pickle, gzip
from PyQt4.QtGui import QApplication
from plextmdb import plextmdb_gui, plextmdb_mygui, plextmdb_totgui
from .test_plexcore import get_token_fullURL

def get_app_standalone( ):
    app = QApplication([])
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
    return app

def get_movie_data_rows_standalone( ):
    movie_data_rows = pickle.load( gzip.open( 'movie_data_rows.pkl.gz', 'rb' ) )
    return movie_data_rows

@pytest.fixture( scope="module" )
def get_app( ):
    app = QApplication([])
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
    yield app

@pytest.fixture( scope="module" )
def get_movie_data_rows( ):
    movie_data_rows = pickle.load( gzip.open( 'movie_data_rows.pkl.gz', 'rb' ) )
    yield movie_data_rows

def test_tmdb_mygui( get_token_fullURL, get_movie_data_rows,
                     get_app, request ):
    verify = request.config.option.do_verify
    fullurl, token = get_token_fullURL
    app = get_app
    movie_data_rows = get_movie_data_rows
    tmdb_mygui = plextmdb_mygui.TMDBMyGUI(
        token, movie_data_rows, verify = verify )

def test_tmdb_gui( get_token_fullURL, get_movie_data_rows,
                   get_app, request ):
    verify = request.config.option.do_verify
    fullurl, token = get_token_fullURL
    app = get_app
    movie_data_rows = get_movie_data_rows
    tmdbgui = plextmdb_gui.TMDBGUI(
        token, fullurl, movie_data_rows, verify = verify )

def test_tmdb_totgui( get_token_fullURL, get_movie_data_rows,
                      get_app, request ):
    verify = request.config.option.do_verify
    fullurl, token = get_token_fullURL
    app = get_app
    movie_data_rows = get_movie_data_rows
    tmdb_totgui = plextmdb_totgui.TMDBTotGUI(
        fullurl, token, movie_data_rows = movie_data_rows,
        doLarge = True, verify = verify )

def test_tmdb_torrents( get_token_fullURL, get_app, request ):
    movie = 'Big Hero 6'
    bypass = request.config.option.do_bypass
    fullurl, token = get_token_fullURL
    app = get_app
    tmdbt = plextmdb_gui.TMDBTorrents(
        None, token, movie, bypass = bypass )
    
                        
