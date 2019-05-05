#!/usr/bin/env python3

import os, sys, glob, logging, signal, pickle, gzip
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
mainDir = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
sys.path.append( mainDir )
from PyQt4.QtGui import QApplication
from optparse import OptionParser
from plextvdb import plextvdb_gui
from plexcore import plexcore

#parser = OptionParser( )
# parser.add_option('--movie', dest='movie', type=str, action='store',
#                   default = 'Big Hero 6', help =
#                   ' '.join([ 'Name of movie to do torrent for.',
#                              'Default is Big Hero 6.' ]) )
# parser.add_option('--bypass', dest='do_bypass', action='store_true',
#                   default = False, help = 'If chosen, then bypass using YTS Movies.' )
# parser.add_option('--debug', dest='do_debug', action='store_true', default = False,
#                   help = 'If chosen, then run with debug mode.' )
# opts, args = parser.parse_args( )
#
app = QApplication([])
app.setStyleSheet(
    open( os.path.join( mainDir, 'resources', 'ubuntu.qss' ), 'r' ).read( ) )
#if opts.do_debug: logging.basicConfig( level = logging.DEBUG )
fullURL, token = plexcore.checkServerCredentials( doLocal = True )
tvdbg = plextvdb_gui.TVDBGUI(
    token, fullURL, tvdata_on_plex = pickle.load(
        gzip.open('tvdata_20190504.pkl.gz', 'rb' ) ),
    missing_eps = { },
    did_end = pickle.load( gzip.open( 'didend_20190504.pkl.gz', 'rb' ) ) )
result = app.exec_( )
