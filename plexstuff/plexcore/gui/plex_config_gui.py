import sys, signal
 # code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import qdarkstyle, logging, glob, os
from argparse import ArgumentParser
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
#
from plexstuff import resourceDir
from plexstuff.plexcore import plexcore_gui

def main( ):
    parser = ArgumentParser( )
    parser.add_argument('--info', dest='do_info', action='store_true',
                      default = False, help = 'Run info mode if chosen.')
    parser.add_argument('--noverify', dest='do_verify', action='store_false',
                      default = True, help = 'Do not verify SSL transactions if chosen.')
    args = parser.parse_args( )
    logger = logging.getLogger( )
    if args.do_info: logger.setLevel( logging.INFO )
    #
    app = QApplication([])
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt5( ) )
    icn = QIcon( os.path.join(
        resourceDir, 'icons', 'plex_config_gui.png' ) )
    app.setWindowIcon( icn )
    pcgui = plexcore_gui.PlexConfigGUI( verify = args.do_verify )
    pcgui.setStyleSheet("""
    QWidget {
    font-family: Consolas;
    font-size: 11;
    }""" )
    pcgui.show( )
    result = pcgui.exec_( )
