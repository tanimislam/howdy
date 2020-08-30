from httplib2 import Http
from argparse import ArgumentParser
#
from howdy.core import core

def main( ):
    parser = ArgumentParser( )
    parser.add_argument( '--noverify', dest='do_verify', action='store_false', default = True,
                       help = 'If chosen, do not verify SSL connections.' )
    args = parser.parse_args( )
    flow, url = core.oauth_generate_google_permission_url( )
    print( 'Please go to this URL in a browser window: %s' % url )
    bs = '\n'.join([ 'After giving permission for Google services on your behalf,',
                     'type in the access code:' ] )
    access_code = input( bs )
    try:
        http = Http( disable_ssl_certificate_validation = not args.do_verify )
        credentials = flow.step2_exchange( access_code, http = http )
        core.oauth_store_google_credentials( credentials )
        print( 'Success. Stored GOOGLE credentials.' )
    except:
        print( 'Error: invalid authorization code.' )
        return
