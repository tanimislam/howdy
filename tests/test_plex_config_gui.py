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
import qdarkstyle, pickle, gzip
from optparse import OptionParser
from PyQt4.QtGui import QApplication
from plexcore import plexcore, plexcore_gui

scenarios = [ 'CRED', 'LOGIN', 'MUSIC', 'TOTAL' ]

def main( info = False, doLocal = True, verify = True,
          thingToShow = 'CRED' ):
    app = QApplication([])
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
    if info: logging.basicConfig( level = logging.INFO )
    if thingToShow == 'CRED':
        widg = plexcore_gui.PlexConfigCredWidget( None, verify = verify )
    elif thingToShow == 'LOGIN':
        widg = plexcore_gui.PlexConfigLoginWidget( None, verify = verify )
    elif thingToShow == 'MUSIC':
        widg = plexcore_gui.PlexConfigMusicWidget( None, verify = verify )
    elif thingToShow == 'TOTAL':
        widg = plexcore_gui.PlexConfigGUI( verify = verify )
    else: raise ValueError("Error: %s needs to be one of %s." % (
            thingToShow, scenarios ) )
    widg.setStyleSheet("""
    QWidget {
    font-family: Consolas;
    font-size: 11;
    }""" )
    widg.show( )
    result = widg.exec_( )

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('--local', dest='do_local', action='store_true',
                      default = False, help = 'Check for locally running plex server.')
    parser.add_option('--info', dest='do_info', action='store_true',
                      default = False, help = 'Run info mode if chosen.')
    parser.add_option('--noverify', dest='do_verify', action='store_false',
                      default = True, help = 'Do not verify SSL transactions if chosen.')
    parser.add_option('--widget', dest='widget', type=str, action='store', default = 'LOGIN',
                      help = ' '.join([
                          'Name of the widget to test.',
                          'Must be one of %s.' % scenarios,
                          'Default is LOGIN widget.']))
    opts, args = parser.parse_args( )
    assert( opts.widget in scenarios )
    main( info = opts.do_info, doLocal = opts.do_local,
          verify = opts.do_verify, thingToShow = opts.widget )
