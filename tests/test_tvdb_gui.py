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
from plextvdb import plextvdb_gui
from plexcore import plexcore

def main( info = False, doLocal = True, verify = True ):
    app = QApplication([])
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
    if info: logging.basicConfig( level = logging.INFO )
    fullURL, token = plexcore.checkServerCredentials(
        doLocal = doLocal, verify = verify )
    if doLocal:
        tvdata = pickle.load( gzip.open(max(glob.glob('tvdata.pkl.gz')), 'rb' ))
        didend = pickle.load( gzip.open(max(glob.glob('didend.pkl.gz')), 'rb'))
    else:
        tvdata = pickle.load( gzip.open(max(glob.glob('tvdata_remote.pkl.gz')), 'rb' ))
        didend = pickle.load( gzip.open(max(glob.glob('didend.pkl.gz')), 'rb'))
    toGet = pickle.load( gzip.open(max(glob.glob('toGet.pkl.gz')), 'rb' ))
    tvdbg = plextvdb_gui.TVDBGUI(
        token, fullURL, tvdata_on_plex = tvdata,
        toGet = toGet, didend = didend, verify = verify )
    result = app.exec_( )

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('--local', dest='do_local', action='store_true',
                      default = False, help = 'Check for locally running plex server.')
    parser.add_option('--info', dest='do_info', action='store_true',
                      default = False, help = 'Run info mode if chosen.')
    parser.add_option('--noverify', dest='do_verify', action='store_false',
                      default = True, help = 'Do not verify SSL transactions if chosen.')
    opts, args = parser.parse_args( )
    main( info = opts.do_info, doLocal = opts.do_local, verify = opts.do_verify )
