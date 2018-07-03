#!/usr/bin/env python3

from plexcore import plexcore
from optparse import OptionParser

def main( ):
    parser = OptionParser( )
    opts, args = parser.parse_args( )
    flow, url = plexcore.oauth_generate_google_permission_url( )
    print( 'Please go to this URL in a browser window: %s' % url )
    bs = '\n'.join([ 'After giving permission for Google services on your behalf,',
                     'type in the access code:' ] )
    access_code = input( bs )
    try:
        credentials = flow.step2_exchange( access_code )
        plexcore.oauth_store_youtube_credentials( credentials )
        print( 'Success. Stored GOOGLE credentials.' )
    except:
        print( 'Error: invalid authorization code.' )
        return
    
if __name__=='__main__':
    main( )
