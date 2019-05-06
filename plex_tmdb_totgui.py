#!/usr/bin/env python3

import sys, signal
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import logging, PyQt4.QtGui, os, qdarkstyle
from plexcore import plexcore_gui, mainDir
from plextmdb import plextmdb_totgui
from optparse import OptionParser

def main(debug = False, checkLocal = True, doLarge = False):
    app = PyQt4.QtGui.QApplication([])
    #app.setStyleSheet(
    #    open( os.path.join( mainDir, 'resources', 'ubuntu.qss' ), 'r' ).read( ) )
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
    if debug:
        logging.basicConfig( level = logging.DEBUG )
    if checkLocal: fullurl, token = plexcore_gui.returnClientToken( )
    else: fullurl, token = plexcore_gui.returnServerToken( )
    tmdb_mygui = plextmdb_totgui.TMDBTotGUI( fullurl, token, doLarge = doLarge )
    result = app.exec_( )
    return tmdb_mygui

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('--local', dest='do_local', action='store_true',
                      default = False, help = 'Check for locally running plex server.')
    parser.add_option('--debug', dest='do_debug', action='store_true',
                      default = False, help = 'Run debug mode if chosen.')
    opts, args = parser.parse_args( )
    main( debug = opts.do_debug, checkLocal = opts.do_local )
