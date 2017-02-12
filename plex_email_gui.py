#!/usr/bin/env python2

import os, logging, sys
from plexemail.plexemail_gui import PlexEmailGUI
from plexemail.plexemail_mygui import PlexEmailMyGUI
from plexcore.plexcore_gui import returnServerToken, returnEmailAuthentication, returnContactAuthentication
from optparse import OptionParser
from PyQt4.QtGui import QApplication

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
    app = QApplication([])
    _, token = returnServerToken( )
    val = returnEmailAuthentication( )
    val = returnContactAuthentication( )
    if not opts.do_onlyemail:
        pegui = PlexEmailGUI( token, doLocal = not opts.do_remote, doLarge = opts.do_large )
    else:
        pegui = PlexEmailMyGUI( token, doLarge = opts.do_large )
    result = app.exec_( )
