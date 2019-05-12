#!/usr/bin/env python3

import os, sys, glob, logging, signal
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import qdarkstyle, pickle, gzip
mainDir = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
sys.path.append( mainDir )
sys.path.append( os.path.dirname( mainDir ) )
from PyQt4.QtGui import QApplication
from plextvdb import plextvdb_season_gui, get_token
from plexcore import plexcore
from optparse import OptionParser

#
## start the application here
parser = OptionParser( )
parser.add_option('-s', '--series', type=str, dest='series', action='store', default='The Simpsons',
                  help = 'Name of the series to choose. Default is "The Simpsons".' )
parser.add_option('-S', '--season', type=int, dest='season', action='store', default=1,
                  help = 'Season number to examine. Default is 1.' )
opts, args = parser.parse_args( )
assert( opts.season > 0 )
app = QApplication([])
app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
tvdata = pickle.load( gzip.open('tvdata_20190511.pkl.gz', 'rb' ) )
assert( opts.series in tvdata )

fullURL, token = plexcore.checkServerCredentials( doLocal = False )
tvdb_season_gui = plextvdb_season_gui.TVDBSeasonGUI(
    opts.series, opts.season, tvdata, { }, get_token( ), token, verify = True )
result = app.exec_( )
