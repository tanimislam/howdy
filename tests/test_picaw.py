#!/usr/bin/env python3

import os, sys, glob, logging, signal
 # code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )

from functools import reduce
mainDir = reduce(lambda x,y: os.path.dirname( x ), range(2),
                 os.path.abspath( __file__ ) )
sys.path.append( mainDir )

import qdarkstyle
from optparse import OptionParser
from PyQt5.QtWidgets import QApplication
from plexcore import plexcore_gui, plexcore

def main( verify = True ):
    app = QApplication( [ ] )
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt5( ) )
    data_imgurl = plexcore.get_imgurl_credentials( )
    picaw = plexcore_gui.PlexImgurChooseAlbumWidget(
        parent = None, data_imgurl = data_imgurl, verify = False )
    picaw.setStyleSheet("""
    QWidget {
    font-family: Consolas;
    font-size: 11;
    }""" )
    picaw.show( )
    result = app.exec_( )

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option( '--noverify', dest='do_verify', action='store_false',
                      default = True, help = 'Do not verify SSL transactions if chosen.')
    opts, args = parser.parse_args( )
    main( verify = opts.do_verify )
