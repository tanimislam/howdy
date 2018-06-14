#!/usr/bin/env python3

from plexcore import plexcore
from optparse import OptionParser

def main( ):
    parser = OptionParser( )
    parser.add_option('--youtube', dest='do_youtube', action='store_true', default = False,
                      help = 'If chosen, store the YOUTUBE credentials into the config directory.' )
    parser.add_option('--contacts', dest='do_contacts', action='store_true', default = False,
                      help = 'If chosen, store the Google CONTACTS credentials into the config directory.' )
    opts, args = parser.parse_args( )
    if len(list(filter(lambda tok: tok is True, ( opts.do_youtube, opts.do_contacts ) ) ) ) != 1:
        print( 'Error, only one of --youtube or --contacts must be chosen. Not neither, and not both.' )
        return
    if opts.do_youtube:
        flow, url = plexcore.oauth_generate_youtube_permission_url( )
        print( 'Please go to this URL in a browser window: %s' % url )
        bs = '\n'.join([ 'After giving permission for the app to go to YOUTUBE on your behalf,',
                         'type in the access code:' ] )
        access_code = input( bs )
        try:
            credentials = flow.step2_exchange( access_code )
            plexcore.oauth_store_youtube_credentials( credentials )
            print( 'Success. Stored YOUTUBE credentials.' )
        except:
            print( 'Error: invalid authorization code.' )
            return
    elif opts.do_contacts:
        flow, url = plexcore.oauth_generate_contacts_permission_url( )
        print( 'Please go to this URL in a browser window: %s' % url )
        bs = '\n'.join([ 'After giving permission for the app to go to Google CONTACTS on your behalf,',
                         'type in the access code:' ] )
        access_code = input( bs )
        try:
            credentials = flow.step2_exchange( access_code )
            plexcore.oauth_store_contacts_credentials( credentials )
            print( 'Success. Stored Google CONTACTS credentials.' )
        except:
            print( 'Error: invalid authorization code.' )
            return

if __name__=='__main__':
    main( )
