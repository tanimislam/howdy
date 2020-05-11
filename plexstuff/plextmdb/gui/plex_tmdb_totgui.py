import sys, signal
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import logging, os, qdarkstyle, time, numpy
from PyQt5.QtGui import QIcon
from argparse import ArgumentParser
#
from plexstuff import resourceDir
from plexstuff.plexcore import plexcore, returnQAppWithFonts
from plexstuff.plextmdb import plextmdb_totgui

def mainSub(info = False, doLocal = True, doLarge = False, verify = True):
    app = returnQAppWithFonts( )
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt5( ) )
    icn = QIcon( os.path.join(
        resourceDir, 'icons', 'plex_tmdb_totgui.png' ) )
    app.setWindowIcon( icn )
    logger = logging.getLogger( )
    if info: logger.setLevel( logging.INFO )
    fullurl, token = plexcore.checkServerCredentials(
        doLocal = doLocal, verify = verify )
    tmdb_mygui = plextmdb_totgui.TMDBTotGUI(
        fullurl, token, doLarge = doLarge, verify = verify )
    result = app.exec_( )
    return tmdb_mygui

def main( ):
    parser = ArgumentParser( )
    parser.add_argument('--large', dest='do_large', action='store_true',
                        default = False, help = 'Run with large fonts to help with readability.' )
    parser.add_argument('--local', dest='do_local', action='store_true',
                        default = False, help = 'Check for locally running plex server.')
    parser.add_argument('--info', dest='do_info', action='store_true',
                        default = False, help = 'Run info mode if chosen.')
    parser.add_argument('--noverify', dest='do_verify', action='store_false',
                        default = True, help = 'Do not verify SSL transactions if chosen.')    
    args = parser.parse_args( )
    mainSub( info = args.do_info, doLocal = args.do_local, doLarge = args.do_large, verify = args.do_verify )
    
