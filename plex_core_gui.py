#!/usr/bin/env python3

import sys, signal, os
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import qdarkstyle, logging
from PyQt4.QtGui import QApplication
from urllib.parse import urlparse
from optparse import OptionParser

from plexcore import geoip_reader
from plexcore.plexcore_gui import returnToken, returnGoogleAuthentication

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option( '--info', dest='do_info', action = 'store_true', default = False,
                       help = 'If chosen, run in INFO logging mode.')
    parser.add_option( '--remote', dest='do_local', action = 'store_false', default = True,
                       help = 'If chosen, do not check localhost for running plex server.')
    parser.add_option( '--googleauth', dest='do_googleauth', action='store_true', default = False,
                       help = 'If chosen, set up google oauth2 authentication.' )
    opts, args = parser.parse_args( )
    if opts.do_info: logging.basicConfig( level = logging.INFO )
    app = QApplication([])
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
    if not opts.do_googleauth:
        fullurl, token = returnToken(
            shouldCheckLocal = opts.do_local )
        print( 'token = %s' % token )
        print( 'url = %s' % fullurl )
        ipaddr = urlparse( fullurl ).netloc.split(':')[0]
        myloc = geoip_reader.city( ipaddr )
        print( 'location is in %s, %s, %s.' % (
            myloc.city.name, myloc.subdivisions.most_specific.iso_code, myloc.country.name ) )
        
    else: val = returnGoogleAuthentication( )
