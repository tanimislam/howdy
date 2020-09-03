import sys, signal, os
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import logging, warnings, qtmodern.styles, qtmodern.windows
from urllib.parse import urlparse
from argparse import ArgumentParser
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
#
from howdy import resourceDir
from howdy.core import geoip_reader
from howdy.core.core_gui import returnToken, returnGoogleAuthentication

def main( ):
    parser = ArgumentParser( )
    parser.add_argument( '--info', dest='do_info', action = 'store_true', default = False,
                        help = 'If chosen, run in INFO logging mode.')
    parser.add_argument( '--remote', dest='do_local', action = 'store_false', default = True,
                        help = 'If chosen, do not check localhost for running plex server.')
    subparsers = parser.add_subparsers( help = 'Can optionally choose to set up google oauth2 authentication.', dest = 'choose_option' )
    #
    parser_googleauth = subparsers.add_parser( 'googleauth', help = 'Set up google oauth2 authentication.' )
    parser_googleauth.add_argument('--bypass', dest='do_bypass', action = 'store_true',
                                   default = False, help = 'If chosen, then ignore any existing google oauth2 authentication credentials.' )
    #
    args = parser.parse_args( )
    logger = logging.getLogger( )
    if args.do_info: logger.setLevel( level = logging.INFO )
    app = QApplication([])
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    icn = QIcon( os.path.join(
        resourceDir, 'icons', 'howdy_core_gui_SQUARE.png' ) )
    app.setWindowIcon( icn )
    qtmodern.styles.dark( app )
    #
    ## googleauth
    if args.choose_option == 'googleauth':
        val = returnGoogleAuthentication( bypass = args.do_bypass )
        return
    #
    fullurl, token = returnToken(
        doLocal = args.do_local, verify = False )
    print( 'token = %s' % token )
    print( 'url = %s' % fullurl )
    ipaddr = urlparse( fullurl ).netloc.split(':')[0]
    if ipaddr != 'localhost':
        myloc = geoip_reader.city( ipaddr )
        print( 'location is in %s, %s, %s.' % (
            myloc.city.name, myloc.subdivisions.most_specific.iso_code, myloc.country.name ) )
