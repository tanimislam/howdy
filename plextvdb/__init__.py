import os, requests, json, sys
from sqlalchemy import Column, String
mainDir = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
sys.path.append( mainDir )
from plexcore import session, create_all, PlexConfig, Base
from sqlalchemy import String, Column

class ShowsToExclude( Base ): # these are shows you want to exclude
    #
    ## create the table using Base.metadata.create_all( _engine )
    __tablename__ = 'showstoexclude'
    __table_args__ = { 'extend_existing': True }
    show = Column( String( 65536 ), index = True, primary_key = True )

#
## commit all tables
create_all( )
    
def save_tvdb_api( username, apikey, userkey ):
    query = session.query( PlexConfig ).filter( PlexConfig.service == 'tvdb' )
    val = query.first( )
    if val is not None:
        session.delete( val )
        session.commit( )
    newval = PlexConfig( service = 'tvdb',
                         data = {
                             'apikey' : apikey,
                             'username' : username,
                             'userkey' : userkey } )
    session.add( newval )
    session.commit( )

def get_tvdb_api( ):
    query = session.query( PlexConfig ).filter( PlexConfig.service == 'tvdb' )
    val = query.first( )
    if val is None:
        raise ValueError("ERROR, NO TVDB API CREDENTIALS FOUND")
    data = val.data
    return { 'username' : data['username'],
             'apikey' : data['apikey'],
             'userkey' : data['userkey'] }

def get_token( verify = True ):
    data = json.dumps( get_tvdb_api( ) )
    headers = { 'Content-Type' : 'application/json' }
    response = requests.post( 'https://api.thetvdb.com/login',
                              data = json.dumps( get_tvdb_api( ) ),
                              verify = verify, headers = headers )
    if response.status_code != 200: return None
    return response.json( )[ 'token' ]

def refresh_token( token, verify = True ):
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % token }
    response = requests.get( 'https://api.thetvdb.com/refresh_token',
                             headers = headers, verify = verify )
    if response.status_code != 200: return None
    return response.json( )['token']
