#!/usr/bin/env python3

import os, sys, glob, logging, signal
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
mainDir = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
sys.path.append( mainDir )
from PyQt4.QtGui import QApplication
from optparse import OptionParser
from plextmdb import plextmdb_gui
from plexcore import plexcore

parser = OptionParser( )
parser.add_option('--movie', dest='movie', type=str, action='store',
                  default = 'Big Hero 6', help =
                  ' '.join([ 'Name of movie to do torrent for.',
                             'Default is Big Hero 6.' ]) )
parser.add_option('--bypass', dest='do_bypass', action='store_true',
                  default = False, help = 'If chosen, then bypass using YTS Movies.' )
parser.add_option('--debug', dest='do_debug', action='store_true', default = False,
                  help = 'If chosen, then run with debug mode.' )
opts, args = parser.parse_args( )
#
app = QApplication([])
app.setStyleSheet(
    open( os.path.join( mainDir, 'resources', 'ubuntu.qss' ), 'r' ).read( ) )
if opts.do_debug: logging.basicConfig( level = logging.DEBUG )
_, token = plexcore.checkServerCredentials( doLocal = True )
tmdbt = plextmdb_gui.TMDBTorrents( None, token, opts.movie,
                                   bypass = opts.do_bypass,
                                   do_debug = opts.do_debug )
result = tmdbt.exec_( )
