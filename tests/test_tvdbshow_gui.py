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
from plextvdb import plextvdb_gui, get_token
from plexcore import plexcore
from optparse import OptionParser

#
## start the application here
logging.basicConfig( level = logging.INFO )
parser = OptionParser( )
parser.add_option('-s', '--series', type=str, dest='series', action='store', default='The Simpsons',
                  help = 'Name of the series to choose. Default is "The Simpsons".' )
opts, args = parser.parse_args( )
app = QApplication([])
app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
tvdata = pickle.load( gzip.open(max(glob.glob('tvdata_*pkl.gz')), 'rb' ))
toGet = pickle.load( gzip.open(max(glob.glob('toGet_*pkl.gz')), 'rb' ))
didend= pickle.load( gzip.open(max(glob.glob('didend_*pkl.gz')), 'rb'))
assert( opts.series in tvdata )
_, plex_token = plexcore.checkServerCredentials( doLocal = False, verify = False )
tvdb_token = get_token( verify = False )
tvdb_show_gui = plextvdb_gui.TVDBShowGUI(
    opts.series, tvdata, toGet, tvdb_token, plex_token,
    verify = False )
result = tvdb_show_gui.exec_( )
