#!/usr/bin/env python3

import sys, signal
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
from plexcore import plexcore, returnQAppWithFonts, mainDir
from plextmdb import plextmdb_totgui
from optparse import OptionParser
import logging, os, qdarkstyle, time, numpy
from PyQt4.QtCore import *
from PyQt4.QtGui import *

def main(info = False, doLocal = True, doLarge = False, verify = True):
    app = returnQAppWithFonts( )
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
    icn = QIcon( os.path.join( mainDir, 'resources', 'icons', 'plex_tmdb_totgui.png' ) )
    app.setWindowIcon( icn )
    logger = logging.getLogger( )
    if info: logger.setLevel( logging.INFO )
    fullurl, token = plexcore.checkServerCredentials(
        doLocal = doLocal, verify = verify )
    tmdb_mygui = plextmdb_totgui.TMDBTotGUI( fullurl, token, doLarge = doLarge,
                                             verify = verify )
    result = app.exec_( )
    return tmdb_mygui

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('--large', dest='do_large', action='store_true',
                      default = False, help = 'Run with large fonts to help with readability.' )
    parser.add_option('--local', dest='do_local', action='store_true',
                      default = False, help = 'Check for locally running plex server.')
    parser.add_option('--info', dest='do_info', action='store_true',
                      default = False, help = 'Run info mode if chosen.')
    parser.add_option('--noverify', dest='do_verify', action='store_false',
                      default = True, help = 'Do not verify SSL transactions if chosen.')    
    opts, args = parser.parse_args( )
    main( info = opts.do_info, doLocal = opts.do_local, doLarge = opts.do_large, verify = opts.do_verify )
