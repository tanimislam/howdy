#!/usr/bin/env python3

import sys, signal
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
from optparse import OptionParser
from plextvdb.plextvdb_gui import TVDBGUI
from plexcore import plexcore
from PyQt4.QtGui import QApplication
import qdarkstyle, logging, os, warnings

warnings.simplefilter("ignore")

def main( info = False, doLocal = True, verify = True ):
    app = QApplication([])
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
    if info: logging.basicConfig( level = logging.INFO )
    fullURL, token = plexcore.checkServerCredentials(
        doLocal = doLocal, verify = verify )
    print('verify = %s.' % verify )
    tvdb_gui = TVDBGUI( token, fullURL, verify = verify )
    result = app.exec_( )
    return tvdb_gui

#
## start the application here
if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('--local', dest='do_local', action='store_true',
                      default = False, help = 'Check for locally running plex server.')
    parser.add_option('--info', dest='do_info', action='store_true',
                      default = False, help = 'Run logging at INFO level if chosen.')
    parser.add_option('--noverify', dest='do_verify', action='store_false',
                      default = True, help = 'Do not verify SSL transactions if chosen.')    
    opts, args = parser.parse_args( )
    main( info = opts.do_info, doLocal = opts.do_local, verify = opts.do_verify )
