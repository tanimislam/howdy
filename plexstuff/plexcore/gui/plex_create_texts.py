import os, sys, qdarkstyle
from PyQt5.QtWidgets import QApplication
#
from plexstuff.plexcore import plexcore_texts_gui, returnQAppWithFonts

def main( ):
    app = returnQAppWithFonts( )
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt5( ) )                       
    mg = plexcore_texts_gui.MainGUI( )
    result = app.exec_( )
