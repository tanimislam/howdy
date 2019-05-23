#!/usr/bin/env python3

import os, sys, glob, logging, signal, qdarkstyle
 # code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
from functools import reduce
mainDir = reduce(lambda x,y: os.path.dirname( x ), range(2),
                 os.path.abspath( __file__ ) )
sys.path.append( mainDir )
from PyQt4.QtGui import QApplication
from plextmdb import plextmdb_gui
from plexcore import plexcore
from optparse import OptionParser

parser = OptionParser( )
parser.add_option('--movie', dest='movie', type=str, action='store',
                  default = 'Big Hero 6', help =
                  ' '.join([ 'Name of movie to do torrent for.',
                             'Default is Big Hero 6.' ]) )
parser.add_option('--bypass', dest='do_bypass', action='store_true',
                  default = False, help = 'If chosen, then bypass using YTS Movies.' )
parser.add_option('--debug', dest='do_debug', action='store_true', default = False,
                  help = 'If chosen, dump the JSON representation of the data.' )
opts, args = parser.parse_args( )
#
logging.basicConfig( level = logging.INFO )
app = QApplication([])
app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
fullURL, token = plexcore.checkServerCredentials(
    doLocal = False, verify = False )
tmdbt = plextmdb_gui.TMDBTorrents( None, token, opts.movie,
                                   bypass = opts.do_bypass,
                                   do_debug = opts.do_debug )
tmdbt.setStyleSheet("""
QWidget {
font-family: Consolas;
font-size: 11;
}""" )
result = tmdbt.exec_( )
