#!/usr/bin/env python3

import os, sys, glob, logging, signal
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
from functools import reduce
mainDir = reduce(lambda x,y: os.path.dirname( x ), range(2),
                 os.path.abspath( __file__ ) )
sys.path.append( mainDir )
import qdarkstyle, pickle, gzip
from PyQt4.QtGui import QApplication
from plextvdb import plextvdb_gui
from plexcore import plexcore

#
## start the application here
app = QApplication([])
app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
fullURL, token = plexcore.checkServerCredentials(
    doLocal = False, verify = False )
tvdata = pickle.load( gzip.open(max(glob.glob('tvdata_*pkl.gz')), 'rb' ))
toGet = pickle.load( gzip.open(max(glob.glob('toGet_*pkl.gz')), 'rb' ))
didend= pickle.load( gzip.open(max(glob.glob('didend_*pkl.gz')), 'rb'))
tvdbg = plextvdb_gui.TVDBGUI(
    token, fullURL, tvdata_on_plex = tvdata,
    toGet = toGet, didend = didend, verify = True )
result = app.exec_( )
