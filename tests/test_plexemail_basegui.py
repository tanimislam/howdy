#!/usr/bin/env python3

import signal, logging, sys, os, pickle, gzip, qdarkstyle
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
from functools import reduce
_mainDir = reduce(lambda x,y: os.path.dirname( x ), range(2),
                  os.path.abspath( __file__ ) )
sys.path.append( _mainDir )
from optparse import OptionParser
from PyQt4.QtGui import QApplication

from plexcore import plexcore
from plexemail import plexemail_basegui

if __name__=='__main__':
    app = QApplication([])
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
    qw = plexemail_basegui.PNGWidget( None )
    qw.show( )
    result = app.exec_( )

