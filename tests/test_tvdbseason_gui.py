#!/usr/bin/env python3

import signal, sys, os, logging, glob
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
from functools import reduce
mainDir = reduce(lambda x,y: os.path.dirname( x ), range(2),
                 os.path.abspath( __file__ ) )
sys.path.append( mainDir )
from PyQt4.QtGui import QApplication
import qdarkstyle, pickle, gzip
from plextvdb import plextvdb_season_gui, get_token
from plexcore import plexcore
from optparse import OptionParser

testDir = os.path.expanduser( '~/.config/plexstuff/tests' )

#
## start the application here
logging.basicConfig( level = logging.INFO )
parser = OptionParser( )
parser.add_option('-s', '--series', type=str, dest='series', action='store', default='The Simpsons',
                  help = 'Name of the series to choose. Default is "The Simpsons".' )
parser.add_option('-S', '--season', type=int, dest='season', action='store', default=1,
                  help = 'Season number to examine. Default is 1.' )
opts, args = parser.parse_args( )
app = QApplication([])
app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
tvdata = pickle.load(
    gzip.open( os.path.join( testDir, 'tvdata.pkl.gz' ), 'rb' ) )
toGet = pickle.load(
    gzip.open( os.path.join( testDir, 'toGet.pkl.gz' ), 'rb' ) )
fullURL, plex_token = plexcore.checkServerCredentials(
    doLocal = False, verify = False )
assert( opts.season > 0 )
assert( opts.series in tvdata )
assert( opts.season in tvdata[ opts.series ][ 'seasons' ] )
missing_eps = dict(map(
    lambda seriesName: ( seriesName, toGet[ seriesName ][ 'episodes' ] ),
    toGet ) )#
tvdb_season_gui = plextvdb_season_gui.TVDBSeasonGUI(
    opts.series, opts.season, tvdata, missing_eps, get_token( False ),
    plex_token, verify = False )
result = app.exec_( )
