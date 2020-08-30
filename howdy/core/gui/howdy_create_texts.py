import os, sys, qtmodern.styles, qtmodern.windows
from PyQt5.QtWidgets import QApplication
#
from howdy.core import core_texts_gui, returnQAppWithFonts

def main( ):
    app = returnQAppWithFonts( )
    qtmodern.styles.dark( app )
    mg = core_texts_gui.MainGUI( )
    mw = qtmodern.windows.ModernWindow( mw )
    mw.show( )
    result = app.exec_( )
