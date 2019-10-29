#!/usr/bin/env python3

import signal, sys
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import os, glob, gmusicapi, httplib2
from oauth2client.client import OAuth2WebServerFlow
from optparse import OptionParser

from plexmusic import plexmusic

def _files_from_commas(fnames_string):
    return set(filter(lambda fname: os.path.isfile(fname),
                      map(lambda tok: tok.strip( ), fnames_string.split(',') ) ) )

def _files_from_glob(fnames_string):
    return set(filter(lambda fname: os.path.isfile(fname), glob.glob(fnames_string)))

def _get_oauth_credentials( ):
    oauth_creds = dict( gmusicapi.session.Mobileclient.oauth._asdict( ) )
    flow = OAuth2WebServerFlow(
        client_id = oauth_creds[ 'client_id' ],
        client_secret = oauth_creds[ 'client_secret' ],
        scope = oauth_creds[ 'scope' ],
        redirect_uri = oauth_creds[ 'redirect_uri' ] )
    auth_uri = flow.step1_get_authorize_url( )
    return flow, auth_uri
    

def main( ):
    parser = OptionParser()
    parser.add_option('-f', '--filenames', dest='filenames', action='store', type=str,
                      help = 'Give the list of filenames to put into the Google Music Player.')
    parser.add_option('-P', dest='do_push', action='store_true', default = False,
                      help = 'If chosen, then push Google Music API Mobileclient credentials into the configuration database.' )
    parser.add_option( '--noverify', dest='do_verify', action='store_false', default = True,
                       help = 'If chosen, do not verify SSL connections.' )
    opts, args = parser.parse_args()
    if not opts.do_push:
        if opts.filenames is None:
            raise ValueError("Error, must give a list of file names.")
        if '*' in opts.filenames:
            fnames = _files_from_glob(opts.filenames)
        else:
            fnames = _files_from_commas(opts.filenames)
        plexmusic.upload_to_gmusic( fnames, verify = opts.do_verify )
    else:
        flow, url = _get_oauth_credentials( )
        print( 'Please go to this URL in a browser window: %s' % url )
        bs = '\n'.join([ 'After giving permission for Google services on your behalf,',
                         'type in the access code:' ] )
        access_code = input( bs )
        try:
            if opts.do_verify: http = httplib2.Http( )
            else: http = httplib2.Http( disable_ssl_certificate_validation = True )
            credentials = flow.step2_exchange( access_code, http = http )
            credentials.refresh( http )
            plexmusic.oauth_store_google_credentials( credentials )
            print( 'Success. Stored GMusicAPI Mobileclient credentials.' )
        except Exception as e:
            print( "What is error: %s." % str( e ) )
            print( "Error: invallid authorization  code." )
            return
        #if any( map(lambda tok: tok is not None, ( opts.email, opts.password ) ) ):
        #    raise ValueError( "Error, must define both Google Music email and password." )
        #plexmusic.save_gmusic_creds( opts.email.strip( ), opts.password.strip( ) )

if __name__=='__main__':
    main( )
