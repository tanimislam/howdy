import os, sys, qtmodern.styles, qtmodern.windows, warnings, logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from argparse import ArgumentParser
#
from howdy import resourceDir
from howdy.core import returnQAppWithFonts
from howdy.email import email_demo_gui
#
warnings.simplefilter( 'ignore' )

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
    app = returnQAppWithFonts( )
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    icn = QIcon( os.path.join(
        resourceDir, 'icons', 'howdy_email_demo_gui_SQUARE_VECTA.svg' ) )
    app.setWindowIcon( icn )
    qtmodern.styles.dark( app )
    hedg = email_demo_gui.HowdyEmailDemoGUI( verify = args.do_verify )
    mw = qtmodern.windows.ModernWindow( hedg )
    mw.show( )
    result = app.exec_( )
