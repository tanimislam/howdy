# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )

from . import plexinitialization
pi = plexinitialization.PlexInitialization( )

import os, sys, xdg.BaseDirectory, signal
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

def splitall( path_init ):
    allparts = [ ]
    path = path_init
    while True:
        parts = os.path.split( path )
        if parts[0] == path:
            allparts.insert( 0, parts[ 0 ] )
            break
        elif parts[1] == path:
            allparts.insert( 0, parts[ 1 ] )
            break
        else:
            path = parts[0]
            allparts.insert( 0, parts[ 1 ] )
    return allparts

# resource file
mainDir = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
baseConfDir = xdg.BaseDirectory.save_config_path( 'plexstuff' )
sys.path.append( mainDir )

# follow directions in http://pythoncentral.io/introductory-tutorial-python-sqlalchemy/
_engine = create_engine( 'sqlite:///%s' % os.path.join( baseConfDir, 'app.db') )
Base = declarative_base( )
Base.metadata.bind = _engine
session = sessionmaker( bind = _engine )( )
