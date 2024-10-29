#!/usr/bin/env python3

import os, sys, signal
 # code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
from functools import reduce
mainDir = reduce(lambda x,y: os.path.dirname( x ), range(2),
                 os.path.abspath( __file__ ) )
sys.path.append( mainDir )
import qdarkstyle, logging
from optparse import OptionParser
from PyQt4.QtGui import QApplication

from plexcore import plexcore_gui, plexcore

def main( info = False ):
    imgur_credentials = plexcore.get_imgurl_credentials( )
    clientID = imgur_credentials[ 'clientID' ]
    clientSECRET = imgur_credentials[ 'clientSECRET' ]

    app = QApplication([])
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
    logger = logging.getLogger( )
    if info: logger.setLevel( logging.INFO )
    ioauth2dlg = plexcore_gui.ImgurOauth2Dialog(
        None, clientID, clientSECRET )
    ioauth2dlg.show( )
    app.exec_( )

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option( '--info', dest='do_info', action='store_true', default = False,
                      help = 'Run info mode if chosen.' )
    opts, args = parser.parse_args( )
    main( info = opts.do_info )
