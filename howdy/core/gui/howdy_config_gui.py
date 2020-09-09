import sys, signal
 # code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import logging, glob, os, warnings, qtmodern.styles, qtmodern.windows
from argparse import ArgumentParser
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
#
from howdy import resourceDir
from howdy.core import core_gui

warnings.simplefilter("ignore")

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
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    icn = QIcon( os.path.join(
        resourceDir, 'icons', 'howdy_config_gui_SQUARE_VECTA.svg' ) )
    app.setWindowIcon( icn )
    qtmodern.styles.dark( app )
    hcgui = core_gui.HowdyConfigGUI( verify = args.do_verify )
    mw = qtmodern.windows.ModernWindow( hcgui )
    mw.show( )
    result = app.exec_( )
