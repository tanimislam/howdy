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
from PyQt4.QtGui import QApplication
from plextvdb import plextvdb_gui
from plexcore import plexcore

#
## start the application here
app = QApplication([])
#app.setStyleSheet(
#    open( os.path.join( mainDir, 'resources', 'ubuntu.qss' ), 'r' ).read( ) )
app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
#if opts.do_debug: logging.basicConfig( level = logging.DEBUG )
fullURL, token = plexcore.checkServerCredentials(
    doLocal = False, verify = False )
tvdbg = plextvdb_gui.TVDBGUI(
    token, fullURL, tvdata_on_plex = pickle.load(
        gzip.open('tvdata_20190504.pkl.gz', 'rb' ) ),
    missing_eps = { },
    did_end = pickle.load( gzip.open( 'didend_20190504.pkl.gz', 'rb' ) ) )
result = app.exec_( )
