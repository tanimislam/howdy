import sys, signal
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import qdarkstyle, logging, os, warnings
import qtmodern.styles
import qtmodern.windows
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from argparse import ArgumentParser
#
from plexstuff import resourceDir
from plexstuff.plextvdb.plextvdb_gui import TVDBGUI
from plexstuff.plexcore import plexcore

warnings.simplefilter("ignore")

def mainSub( info = False, doLocal = True, doLarge = False, verify = True ):
    app = QApplication([])
    # app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt5( ) )
    icn = QIcon( os.path.join( resourceDir, 'icons', 'plex_tvdb_gui.png' ) )
    app.setWindowIcon( icn )
    qtmodern.styles.dark( app )
    logger = logging.getLogger( )
    if info: logger.setLevel( level = logging.INFO )
    logging.info( 'TRYING TO GET CREDENTIALS. LOCAL? %s. VERIFY? %s.'
                 % ( doLocal, verify ) )
    fullURL, token = plexcore.checkServerCredentials(
        doLocal = doLocal, verify = verify )
    tvdb_gui = TVDBGUI( token, fullURL, verify = verify, doLarge = doLarge )
    mw = qtmodern.windows.ModernWindow( tvdb_gui )
    mw.show( )
    result = app.exec_( )
    return tvdb_gui

#
## start the application here
def main( ):
    parser = ArgumentParser( )
    parser.add_argument('--large', dest='do_large', action='store_true',
                        default = False, help = 'Run with large fonts to help with readability.' )
    parser.add_argument('--local', dest='do_local', action='store_true',
                        default = False, help = 'Check for locally running plex server.')
    parser.add_argument('--info', dest='do_info', action='store_true',
                        default = False, help = 'Run logging at INFO level if chosen.')
    parser.add_argument('--noverify', dest='do_verify', action='store_false',
                        default = True, help = 'Do not verify SSL transactions if chosen.')
    args = parser.parse_args( )
    mainSub( info = args.do_info, doLocal = args.do_local,
            doLarge = args.do_large, verify = args.do_verify )
    
