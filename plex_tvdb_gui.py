#!/usr/bin/env python3

import sys, signal
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import qdarkstyle, logging, os
from PyQt4.QtGui import QApplication
from optparse import OptionParser
from plextvdb import plextvdb_gui
from plexcore import plexcore

def main( debug = False, doLocal = True, verify = True ):
    app = QApplication([])
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
    if debug: logging.basicConfig( level = logging.DEBUG )
    fullURL, token = plexcore.checkServerCredentials(
        doLocal = doLocal, verify = verify )
    tvdb_gui = plextvdb_gui.TVDBGUI(
        token, fullURL, verify = verify )
    result = app.exec_( )
    return tvdb_gui

#
## start the application here
if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('--local', dest='do_local', action='store_true',
                      default = False, help = 'Check for locally running plex server.')
    parser.add_option('--debug', dest='do_debug', action='store_true',
                      default = False, help = 'Run debug mode if chosen.')
    parser.add_option('--noverify', dest='do_verify', action='store_false',
                      default = True, help = 'Do not verify SSL transactions if chosen.')    
    opts, args = parser.parse_args( )
    main( debug = opts.do_debug, doLocal = opts.do_local, verify = opts.do_verify )
