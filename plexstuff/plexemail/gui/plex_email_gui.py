import sys, signal
from plexstuff import signal_handler
signal.signal( signal.SIGINT, signal_handler )
#
import os, logging, warnings, qtmodern.styles, qtmodern.windows
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from argparse import ArgumentParser
#
from plexstuff import resourceDir
from plexstuff.plexcore.plexcore_gui import returnToken, returnGoogleAuthentication
try:
    from plexstuff.plexemail.plexemail_gui import PlexEmailGUI
    from plexstuff.plexemail.plexemail_mygui import PlexEmailMyGUI
except ValueError as e:
    print( e.args[0] )
    sys.exit( 0 )

warnings.simplefilter( 'ignore' )

def mainSub( info = False, doLocal = True, doLarge = False, verify = True, onlyEmail = False ):
    app = QApplication([])
    icn = QIcon( os.path.join( resourceDir, 'icons', 'plex_email_gui.png' ) )
    app.setWindowIcon( icn )
    qtmodern.styles.dark( app )
    logger = logging.getLogger( )
    if info: logger.setLevel( logging.INFO )
    val = returnGoogleAuthentication( )
    if not onlyEmail:
        pegui = PlexEmailGUI( doLocal = doLocal, doLarge = doLarge, verify = verify )
    else:
        pegui = PlexEmailMyGUI( doLocal = doLocal, doLarge = doLarge, verify = verify )
    mw = qtmodern.windows.ModernWindow( pegui )
    mw.show( )
    result = app.exec_( )

def main( ):
    parser = ArgumentParser( )
    parser.add_argument('--info', dest='do_info', action='store_true',
                      default = False, help = 'Run info mode if chosen.')
    parser.add_argument('--onlyemail', dest = 'do_onlyemail', action = 'store_true',
                      default = False, help = 'If chosen, only send bare email.')
    parser.add_argument('--local', dest='do_local', action = 'store_true', default = False,
                      help = 'Check for locally running plex server.' )
    parser.add_argument('--large', dest='do_large', action='store_true', default = False,
                      help = 'If chosen, make the GUI (widgets and fonts) LARGER to help with readability.')
    parser.add_argument('--noverify', dest='do_verify', action='store_false',
                      default = True, help = 'Do not verify SSL transactions if chosen.')
    parser.add_argument('--extraemails', dest='extraemails', type=str, action='store',
                      help = 'If defined, the list of extra emails to send.' )
    parser.add_argument('--extranames', dest = 'extranames', type=str, action='store',
                      help = 'If defined, the list of extra names to send.' )
    args = parser.parse_args( )
    mainSub( info = args.do_info, doLocal = args.do_local, verify = args.do_verify,
            onlyEmail = args.do_onlyemail )
