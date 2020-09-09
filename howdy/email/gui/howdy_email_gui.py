import sys, signal
from howdy import signal_handler
signal.signal( signal.SIGINT, signal_handler )
#
import os, logging, warnings, qtmodern.styles, qtmodern.windows
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from argparse import ArgumentParser
#
from howdy import resourceDir
from howdy.core.core_gui import returnToken, returnGoogleAuthentication
from howdy.email.email_gui import HowdyEmailGUI
from howdy.email.email_mygui import HowdyEmailMyGUI

warnings.simplefilter( 'ignore' )

def mainSub( info = False, doLocal = True, doLarge = False, verify = True, onlyEmail = False ):
    app = QApplication([])
    icn = QIcon( os.path.join( resourceDir, 'icons', 'howdy_email_gui_SQUARE_VECTA.svg' ) )
    app.setWindowIcon( icn )
    qtmodern.styles.dark( app )
    logger = logging.getLogger( )
    if info: logger.setLevel( logging.INFO )
    val = returnGoogleAuthentication( )
    if not onlyEmail:
        pegui = HowdyEmailGUI( doLocal = doLocal, doLarge = doLarge, verify = verify )
    else:
        pegui = HowdyEmailMyGUI( doLocal = doLocal, doLarge = doLarge, verify = verify )
    mw = qtmodern.windows.ModernWindow( pegui )
    mw.show( )
    result = app.exec_( )

def main( ):
    parser = ArgumentParser( )
    parser.add_argument('--info', dest='do_info', action='store_true',
                      default = False, help = 'Run info mode if chosen.')
    parser.add_argument('--local', dest='do_local', action = 'store_true', default = False,
                      help = 'Check for locally running plex server.' )
    parser.add_argument('--large', dest='do_large', action='store_true', default = False,
                      help = 'If chosen, make the GUI (widgets and fonts) LARGER to help with readability.')
    parser.add_argument('--noverify', dest='do_verify', action='store_false',
                      default = True, help = 'Do not verify SSL transactions if chosen.')
    # parser.add_argument('--extraemails', dest='extraemails', type=str, action='store',
    #                   help = 'If defined, the list of extra emails to send.' )
    # parser.add_argument('--extranames', dest = 'extranames', type=str, action='store',
    #                   help = 'If defined, the list of extra names to send.' )
    #
    ## subparser to do onlyemail or newsletter
    subparsers = parser.add_subparsers(
        help = ' '.join([
            'Choose one of two options:',
            '(o) do only the email.',
            '(n) do the newslettering functionality.' ]), dest = 'choose_option' )
    #
    ## newslettering one (n)
    parser_newsletter = subparsers.add_parser( 'n', help = 'Do the newsletter one.' )
    #
    ## only email one
    parser_onlyeemail = subparsers.add_parser( 'o', help = 'Only do a straightforward email.' )
    #
    ##
    args = parser.parse_args( )
    logger = logging.getLogger( )
    if args.do_info: logger.setLevel( logging.INFO )
    do_onlyemail = True
    if args.choose_option == 'n': do_onlyemail = False
    mainSub( info = args.do_info, doLocal = args.do_local, verify = args.do_verify,
            onlyEmail = do_onlyemail )
