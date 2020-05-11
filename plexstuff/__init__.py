__author__ = 'Tanim Islam'
__email__ = 'tanim.islam@gmail.com'

import sys, os

_mainDir = os.path.dirname( os.path.abspath( __file__ ) )
resourceDir = os.path.join( _mainDir, 'resources' )
assert( os.path.isdir( resourceDir ) )
#
# from plexstuff import plexinitialization
# _ = plexinitialization.PlexInitialization( )
# resource file and stuff
baseConfDir = os.path.abspath( os.path.expanduser( '~/.config/plexstuff' ) )
"""
the directory where Plexstuff configuration data is stored -- ``~/.config/plexstuff``.
"""

# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
