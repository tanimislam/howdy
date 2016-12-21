from . import plexinitialization
pi = plexinitialization.PlexInitialization( )

import os, sys, xdg
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# resource file
mainDir = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )

# follow directions in http://pythoncentral.io/introductory-tutorial-python-sqlalchemy/
_engine = create_engine( 'sqlite:///%s' % os.path.join( mainDir, 'resources', 'app.db') )
Base = declarative_base( )
Base.metadata.bind = _engine
session = sessionmaker( bind = _engine )( )
