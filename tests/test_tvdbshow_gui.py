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
from plextvdb import plextvdb_gui
from plexcore import plexcore

#
## start the application here
app = QApplication([])
app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
tvdata = pickle.load( gzip.open('tvdata_20190504.pkl.gz', 'rb' ) )
tvshow_dict = pickle.load( gzip.open( 'tvshow_dict_20190507.pkl.gz', 'rb' ) )
tvdb_show_gui = plextvdb_gui.TVDBShowGUI(
    "Bob's Burgers", tvdata, tvshow_dict, verify = False)
result = app.exec_( )
