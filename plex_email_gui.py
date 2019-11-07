#!/usr/bin/env python3

import sys, signal
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )

import os, logging, warnings, qdarkstyle
from PyQt4.QtGui import QApplication, QStyleFactory, QIcon
from optparse import OptionParser
warnings.simplefilter( 'ignore' )

from plexcore import mainDir
from plexemail.plexemail_gui import PlexEmailGUI
from plexemail.plexemail_mygui import PlexEmailMyGUI
from plexcore.plexcore_gui import returnToken, returnGoogleAuthentication

def main( info = False, doLocal = True, doLarge = False, verify = True, onlyEmail = False ):
    app = QApplication([])
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
    icn = QIcon( os.path.join(
        mainDir, 'resources', 'icons', 'plex_email_gui.png' ) )
    app.setWindowIcon( icn )
    logger = logging.getLogger( )
    if info: logger.setLevel( logging.INFO )
    val = returnGoogleAuthentication( )
    if not opts.do_onlyemail:
        pegui = PlexEmailGUI( doLocal = doLocal, doLarge = doLarge, verify = verify )
    else:
        pegui = PlexEmailMyGUI( doLocal = doLocal, doLarge = doLarge, verify = verify )
    result = app.exec_( )

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('--info', dest='do_info', action='store_true',
                      default = False, help = 'Run info mode if chosen.')
    parser.add_option('--onlyemail', dest = 'do_onlyemail', action = 'store_true',
                      default = False, help = 'If chosen, only send bare email.')
    parser.add_option('--local', dest='do_local', action = 'store_true', default = False,
                      help = 'Check for locally running plex server.' )
    parser.add_option('--large', dest='do_large', action='store_true', default = False,
                      help = 'If chosen, make the GUI (widgets and fonts) LARGER to help with readability.')
    parser.add_option('--noverify', dest='do_verify', action='store_false',
                      default = True, help = 'Do not verify SSL transactions if chosen.') 
    opts, args = parser.parse_args( )
    main( info = opts.do_info, doLocal = opts.do_local, verify = opts.do_verify,
          onlyEmail = opts.do_onlyemail )
