__author__ = 'Tanim Islam'
__email__ = 'tanim.islam@gmail.com'

import sys, os

_mainDir = os.path.dirname( os.path.abspath( __file__ ) )
resourceDir = os.path.join( _mainDir, 'resources' )
"""
the directory in which the Plexstuff resources are stored.
"""

assert( os.path.isdir( resourceDir ) )
#
# from plexstuff import plexinitialization
# _ = plexinitialization.PlexInitialization( )
# resource file and stuff
baseConfDir = os.path.abspath( os.path.expanduser( '~/.config/plexstuff' ) )
"""
the directory where Plexstuff user data is stored -- ``~/.config/plexstuff``.
"""

if not os.path.isdir( baseConfDir ):
    os.mkdir( baseConfDir )

# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    """
    This is a convenience method that ``kills`` a Python execution when ``Ctrl+C`` is pressed. Its usage is fairly straightforward, shown in the code block below.

    .. code-block:: python

       import signal
       signal.signal( signal.SIGINT, plexstuff.signal_handler )

    This block of code at the top of the executable will capture ``Ctrl+C`` and then hard kill the executable by invoking ``sys.exit( 0 )``.

    :param dict signal: the POSIX signal to capture. See `the Python 3 signal high level overview <signal_high_level_overview_>`_ to begin to understand what POSIX signals are, and how Python can expose functionality to interact with them.
    :param frame: the stack frame. I don't know what it is, or why it's necessary in this context, when trying to capture a ``Ctrl+C`` and cleanly exit. It is of type :py:class:`frame`.
    
    .. _signal_high_level_overview: https://docs.python.org/3/library/signal.html
    """
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
