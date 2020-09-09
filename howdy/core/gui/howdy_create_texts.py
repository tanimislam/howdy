import os, sys, qtmodern.styles, qtmodern.windows, warnings, logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from argparse import ArgumentParser
#
from howdy import resourceDir
from howdy.core import core_texts_gui, returnQAppWithFonts
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
        resourceDir, 'icons', 'howdy_create_texts_SQUARE.png' ) )
    app.setWindowIcon( icn )
    qtmodern.styles.dark( app )
    cw = core_texts_gui.ConvertWidget( verify = args.do_verify )
    mw = qtmodern.windows.ModernWindow( cw )
    mw.show( )
    result = app.exec_( )
