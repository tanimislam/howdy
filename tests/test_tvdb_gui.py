#!/usr/bin/env python3

import os, sys, glob, logging, signal
from . import signal_handler
signal.signal( signal.SIGINT, signal_handler )
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
tvdata = pickle.load( gzip.open(max(glob.glob('tvdata*pkl.gz')), 'rb' ))
toGet = pickle.load( gzip.open(max(glob.glob('toGet*pkl.gz')), 'rb' ))
didend= pickle.load( gzip.open(max(glob.glob('didend*pkl.gz')), 'rb'))
tvdbg = plextvdb_gui.TVDBGUI(
    token, fullURL, tvdata_on_plex = tvdata,
    toGet = toGet, didend = didend, verify = True )
result = app.exec_( )
