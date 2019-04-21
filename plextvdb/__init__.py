# resource file
import os, requests, json, sys
from sqlalchemy import Column, String
mainDir = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
sys.path.append( mainDir )
from plexcore import Base, session

_apiKey = '0B3F6D72213D71C8'
_usrKey = 'AEE839E62568BA63'
_usname = 'tanimislam1978'

def get_token( verify = True ):
    data = { 'apikey' : _apiKey,
             'username' : _usname,
             'userkey' : _usrKey }
    headers = { 'Content-Type' : 'application/json' }
    response = requests.post( 'https://api.thetvdb.com/login',
                              data = json.dumps( data ),
                              verify = verify, headers = headers )
    if response.status_code != 200:
        return None
    return response.json( )[ 'token' ]

def refresh_token( token, verify = True ):
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % token }
    response = requests.get( 'https://api.thetvdb.com/refresh_token',
                             headers = headers, verify = verify )
    if response.status_code != 200:
        return None
    return response.json( )['token']

class ShowsToExclude( Base ): # these are shows you want to exclude
    #
    ## create the table using Base.metadata.create_all( _engine )
    __tablename__ = 'showstoexclude'
    __table_args__ = { 'extend_existing': True }
    show = Column( String( 65536 ), index = True, primary_key = True )
