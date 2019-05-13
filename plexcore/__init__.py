# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )

from . import plexinitialization
pi = plexinitialization.PlexInitialization( )

import os, sys, xdg.BaseDirectory, signal, datetime
import geoip2.database, _geoip_geolite2
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, Column, String, JSON, Date, Boolean

#
## geoip stuff, exposes a single geop_reader from plexcore
_geoip_database = os.path.join(
    os.path.dirname( _geoip_geolite2.__file__ ),
    _geoip_geolite2.database_name )
assert( os.path.isfile( _geoip_database ) )
geoip_reader = geoip2.database.Reader( _geoip_database )

# split paths 
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

# resource file and stuff
mainDir = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
baseConfDir = xdg.BaseDirectory.save_config_path( 'plexstuff' )
sys.path.append( mainDir )

# follow directions in http://pythoncentral.io/introductory-tutorial-python-sqlalchemy/
_engine = create_engine( 'sqlite:///%s' % os.path.join( baseConfDir, 'app.db') )
Base = declarative_base( )
Base.metadata.bind = _engine
session = sessionmaker( bind = _engine )( )

#
## this will be used to replace all the existing credentials stored in separate tables
class PlexConfig( Base ):
    #
    ## create the table using Base.metadata.create_all( _engine )
    __tablename__ = 'plexconfig'
    __table_args__ = { 'extend_existing' : True }
    service = Column( String( 65536 ), index = True, unique = True, primary_key = True )
    data = Column( JSON )

class LastNewsletterDate( Base ):
    #
    ## create the table using Base.metadata.create_all( _engine )
    __tablename__ = 'lastnewsletterdate'
    __table_args__ = {'extend_existing': True}
    date = Column( Date, onupdate = datetime.datetime.now, index = True, primary_key = True )
    
class PlexGuestEmailMapping( Base ):
    #
    ## create the table using Base.metadata.create_all( _engine )
    __tablename__ = 'plexguestemailmapping'
    __table_args__ = { 'extend_existing' : True }
    plexemail = Column( String( 256 ), index = True, unique = True, primary_key = True )
    plexmapping = Column( String( 65536 ) )
    plexreplaceexisting = Column( Boolean )

    
def create_all( ):
    Base.metadata.create_all( _engine )
    session.commit( )

create_all( )
