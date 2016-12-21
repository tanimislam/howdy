import os, sys, glob, numpy
from . import mainDir, pygn
try:
    from ConfigParser import RawConfigParser
except:
    from configparser import RawConfigParser

def push_gracenote_credentials( client_ID ):
    try:
        userID = pygn.register( client_ID )
        cParser = RawConfigParser( )
        cParser.add_section( 'GRACENOTE' )
        cParser.set( 'GRACENOTE', 'clientID', client_ID )
        cParser.set( 'GRACENOTE', 'userID', userID )
        absPath = os.path.join( mainDir, 'resources', 'gracenote_api.conf' )
        with open( absPath, 'w') as openfile:
            cParser.write( openfile )
        os.chmod( absPath, 0o600 )
    except:
        raise ValueError("Error, %s is invalid." % client_ID )

def get_gracenote_credentials( ):
    cParser = RawConfigParser( )
    absPath = os.path.join( mainDir, 'resources', 'gracenote_api.conf' )
    if not os.path.isfile( absPath ):
        raise ValueError("ERROR, GRACENOTE CREDENTIALS NOT FOUND" )
    cParser.read( absPath )
    if not cParser.has_section( 'GRACENOTE' ):
        raise ValueError("Error, gracenote_api.conf does not have a GRACENOTE section.")
    if not cParser.has_option( 'GRACENOTE', 'clientID' ):
        raise ValueError("Error, conf file does not have clientID.")
    if not cParser.has_option( 'GRACENOTE', 'userID' ):
        raise ValueError("Error, conf file does not have userID.")
    return cParser.get( "GRACENOTE", "clientID" ), cParser.get( "GRACENOTE", "userID" )

def get_all_stuff( ):
    pass
