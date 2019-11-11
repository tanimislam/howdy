#!/usr/bin/env python3

import os, sys, qdarkstyle
from PyQt5.QtWidgets import QApplication
from plexcore import plexcore_texts_gui, returnQAppWithFonts

if __name__=='__main__':
    app = returnQAppWithFonts( )
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt5( ) )                       
    mg = plexcore_texts_gui.MainGUI( )
    result = app.exec_( )
