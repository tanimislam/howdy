#!/usr/bin/env python3

import sys, signal, os
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import logging, warnings, qtmodern.styles, qtmodern.windows
from PyQt5.QtWidgets import QApplication
from urllib.parse import urlparse
from argparse import ArgumentParser

from howdy.core import geoip_reader
from howdy.core.core_gui import returnToken, returnGoogleAuthentication

def main( ):
    parser = ArgumentParser( )
    parser.add_argument( '--info', dest='do_info', action = 'store_true', default = False,
                        help = 'If chosen, run in INFO logging mode.')
    parser.add_argument( '--remote', dest='do_local', action = 'store_false', default = True,
                        help = 'If chosen, do not check localhost for running plex server.')
    parser.add_argument( '--googleauth', dest='do_googleauth', action='store_true', default = False,
                        help = 'If chosen, set up google oauth2 authentication.' )
    args = parser.parse_args( )
    logger = logging.getLogger( )
    if args.do_info: logger.setConfig( level = logging.INFO )
    app = QApplication([])
    qtmodern.styles.dark( app )
    if not args.do_googleauth:
        fullurl, token = returnToken(
            doLocal = args.do_local, verify = False )
        print( 'token = %s' % token )
        print( 'url = %s' % fullurl )
        ipaddr = urlparse( fullurl ).netloc.split(':')[0]
        if ipaddr != 'localhost':
            myloc = geoip_reader.city( ipaddr )
            print( 'location is in %s, %s, %s.' % (
                myloc.city.name, myloc.subdivisions.most_specific.iso_code, myloc.country.name ) )
        
    else: val = returnGoogleAuthentication( )
