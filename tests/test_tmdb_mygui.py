#!/usr/bin/env python3

import signal, sys
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
#
from functools import reduce
import logging, os, pickle, gzip, qdarkstyle
mainDir = reduce(lambda x,y: os.path.dirname( x ), range(2),
                 os.path.abspath( __file__ ) )
sys.path.append( mainDir )
#
from plexcore import plexcore, returnQAppWithFonts
from plextmdb import plextmdb_mygui
from optparse import OptionParser

def main(debug = False, doLocal = True, verify = True ):
    testDir = os.path.expanduser( '~/.config/howdy/tests' )
    app = returnQAppWithFonts( )
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt5( ) )
    if debug: logging.basicConfig( level = logging.DEBUG )
    fullurl, token = plexcore.checkServerCredentials(
        doLocal = doLocal, verify = verify )
    movie_data_rows = pickle.load( gzip.open(
        os.path.join( testDir, 'movie_data_rows.pkl.gz' ), 'rb' ) )
    tmdb_mygui = plextmdb_mygui.TMDBMyGUI(
        token, movie_data_rows, verify = verify )
    result = app.exec_( )

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('--local', dest='do_local', action='store_true',
                      default = False, help = 'Check for locally running plex server.')
    parser.add_option('--debug', dest='do_debug', action='store_true',
                      default = False, help = 'Run debug mode if chosen.')
    parser.add_option('--noverify', dest='do_verify', action='store_false',
                      default = True, help = 'Do not verify SSL transactions if chosen.')
    opts, args = parser.parse_args( )
    main( debug = opts.do_debug, doLocal = opts.do_local, verify = opts.do_verify  )
