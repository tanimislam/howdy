#!/usr/bin/env python3

import os, sys, glob, logging, signal
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import qdarkstyle, pickle, gzip
from functools import reduce
mainDir = reduce(lambda x,y: os.path.dirname( x ), range(2),
                 os.path.abspath( __file__ ) )
sys.path.append( mainDir )
from PyQt4.QtGui import QApplication
from plextvdb import plextvdb_gui, plextvdb_season_gui, get_token
from plexcore import plexcore
from test_plexcore import get_token_fullURL
from optparse import OptionParser

#
## start the application here
logging.basicConfig( level = logging.INFO )
parser = OptionParser( )
parser.add_option('-s', '--series', type=str, dest='series', action='store',
                  default='The Simpsons',
                  help = 'Name of the series to choose. Default is "The Simpsons".' )
opts, args = parser.parse_args( )
app = QApplication([])
app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
tvdata = pickle.load(
    gzip.open( os.path.join( testDir, 'tvdata.pkl.gz' ), 'rb' ) )
toGet = pickle.load( gzip.open(
    gzip.open( os.path.join( testDir, 'toGet.pkl.gz' ), 'rb' ) )
didend = pickle.load( gzip.open(
    os.path.join( testDir, 'didend.pkl.gz'), 'rb' ) )
assert( opts.series in tvdata )
_, plex_token = plexcore.checkServerCredentials(
    doLocal = False, verify = False )
tvdb_token = get_token( verify = False )
tvdb_show_gui = plextvdb_gui.TVDBShowGUI(
    opts.series, tvdata, toGet, tvdb_token, plex_token,
    verify = False )
tvdb_show_gui.setStyleSheet("""
QWidget {
font-family: Consolas;
font-size: 11;
}""" )
result = tvdb_show_gui.exec_( )
