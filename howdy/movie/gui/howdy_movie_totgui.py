import sys, signal
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import logging, os, time, numpy, qtmodern.styles, qtmodern.windows
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from argparse import ArgumentParser
#
from howdy import resourceDir
from howdy.core import core, returnQAppWithFonts
from howdy.movie import movie_totgui

def mainSub(info = False, doLocal = True, doLarge = False, verify = True):
    app = returnQAppWithFonts( )
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    icn = QIcon( os.path.join(
        resourceDir, 'icons', 'howdy_movie_gui.svg' ) )
    app.setWindowIcon( icn )
    qtmodern.styles.dark( app )
    logger = logging.getLogger( )
    if info: logger.setLevel( logging.INFO )
    fullurl, token = core.checkServerCredentials(
        doLocal = doLocal, verify = verify )
    howdy_mygui = movie_totgui.HowdyMovieTotGUI(
        fullurl, token, doLarge = doLarge, verify = verify )
    mw = qtmodern.windows.ModernWindow( howdy_mygui )
    mw.show( )
    result = app.exec_( )
    return howdy_mygui

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
