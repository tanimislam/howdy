import os, sys, qtmodern.styles, qtmodern.windows, warnings
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
#
from howdy import resourceDir
from howdy.core import core_texts_gui, returnQAppWithFonts
#
warnings.simplefilter( 'ignore' )

def main( ):
    app = returnQAppWithFonts( )
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    icn = QIcon( os.path.join(
        resourceDir, 'icons', 'howdy_create_texts_SQUARE.png' ) )
    app.setWindowIcon( icn )
    qtmodern.styles.dark( app )
    cw = core_texts_gui.ConvertWidget( )
    mw = qtmodern.windows.ModernWindow( cw )
    mw.show( )
    result = app.exec_( )
