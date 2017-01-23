# resource file
import os
mainDir = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )

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
