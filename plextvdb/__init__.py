# resource file
import os, requests, json, sys
mainDir = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
sys.path.append( mainDir )

_apiKey = '0B3F6D72213D71C8'
_usrKey = 'AEE839E62568BA63'
_usname = '***REMOVED***islam1978'

# change this later
_apiKey_jackett = '0cstpcrrdx7wrihtij3jbe461t0uk3l6'
_url_jackett = 'https://dark.seedhost.eu/***REMOVED***islam/jackett'

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
