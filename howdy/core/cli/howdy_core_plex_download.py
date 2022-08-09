import signal
from howdy import signal_handler
signal.signal( signal.SIGINT, signal_handler )
import os, sys, logging, time
from argparse import ArgumentParser
#
from howdy.core import core, core_admin

def print_update_status( release ):
    print('here are the details for Plex update %s.' % release.version )
    print('added: %s\n' % release.added )
    print('fixed: %s\n' % release.fixed )

def main( ):
    parser = ArgumentParser( )
    parser.add_argument('-d', '--dest', dest='destination_dir', type=str, action='store', default = os.getcwd( ),
                        help = 'The directory into which to store the updated Plex server.' )
    parser.add_argument('-s', '--status', dest='do_status', action='store_true', default = False,
                        help = 'If chosen, just print out details of the Plex release but do not download.' )
    parser.add_argument('-p', '--progress', dest='do_progress', action='store_true', default = False,
                        help = 'If chosen, then show download progress.' )
    parser.add_argument('-i', '--info', dest='do_info', action='store_true', default = False,
                        help = 'If chosen, then show INFO logging.' )
    args = parser.parse_args( )
    #
    logger = logging.getLogger( )
    if args.do_info: logger.setLevel( logging.INFO )
    #
    assert( os.path.isdir( os.path.expanduser( args.destination_dir ) ) )
    destination_dir = os.path.expanduser( args.destination_dir )
    #
    ## get release
    dat = core.checkServerCredentials( doLocal = True )
    if dat is None:
        print( "ERROR, COULD NOT ACCESS LOCAL PLEX SERVER.")
        return
    fullURL, token = dat
    release, status = core_admin.plex_check_for_update( token, fullURL)
    if release is None:
        print( 'NO PLEX UPDATES NOW.' )
        return        
        
    #
    ## check on status
    if args.do_status:
        print_update_status( release )
        return
    #
    ## otherwise download!
    time0 = time.time( )
    full_path = core_admin.plex_download_release( release, token, args.destination_dir, do_progress = args.do_progress )
    print( 'Downloaded to %s in %0.3f seconds.' % ( os.path.basename( full_path ), time.time( ) - time0 ) )
