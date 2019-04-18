#!/usr/bin/env python3

import os, logging, sys, signal, qdarkstyle
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
from plexcore import mainDir
from plexemail.plexemail_gui import PlexEmailGUI
from plexemail.plexemail_mygui import PlexEmailMyGUI
from plexcore.plexcore_gui import returnServerToken, returnGoogleAuthentication
from optparse import OptionParser
from PyQt4.QtGui import QApplication, QStyleFactory

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('--debug', dest='do_debug', action='store_true',
                      default = False, help = 'Run debug mode if chosen.')
    parser.add_option('--onlyemail', dest = 'do_onlyemail', action = 'store_true',
                      default = False, help = 'If chosen, only send bare email.')
    parser.add_option('--remote', dest='do_remote', action = 'store_true', default = False,
                      help = 'If chosen, then do everything remotely.')
    parser.add_option('--large', dest='do_large', action='store_true', default = False,
                      help = 'If chosen, make the GUI (widgets and fonts) LARGER to help with readability.')
    opts, args = parser.parse_args( )
    if opts.do_debug:
        logging.basicConfig( level = logging.DEBUG )
    app = QApplication( [] )
    app.setStyleSheet(
        open( os.path.join( mainDir, 'resources', 'ubuntu.qss' ), 'r' ).read( ) )
    _, token = returnServerToken( )
    val = returnGoogleAuthentication( )
    if not opts.do_onlyemail:
        pegui = PlexEmailGUI( token, doLocal = not opts.do_remote, doLarge = opts.do_large )
    else:
        pegui = PlexEmailMyGUI( token, doLarge = opts.do_large )
    result = app.exec_( )
