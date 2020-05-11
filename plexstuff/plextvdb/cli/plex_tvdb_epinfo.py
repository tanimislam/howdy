import sys, signal 
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import os, json, time, logging
from io import BytesIO
from fabric import Connection
from argparse import ArgumentParser
#
from plexstuff.plextvdb import plextvdb
from plexstuff.plexcore import plexcore_deluge

def main( ):
    time0 = time.time( )
    parser = ArgumentParser( )
    parser.add_argument('-s', '--show', type=str, action='store', dest='show',
                        help = 'Name of the TV Show to push into remote server.')
    parser.add_argument('-j', '--jsonfile', type=str, action='store', dest='jsonfile', default = 'eps.json',
                        help = 'Name of the JSON file into which to store the episode information. Default is eps.json.' )
    parser.add_argument('--showspecials', dest='do_showspecials', action='store_true', default = False,
                        help = 'If chosen, then also find all the specials.' )
    parser.add_argument('--debug', dest='do_debug', action='store_true', default = False,
                        help = 'If chosen, then run DEBUG logging.' )
    parser.add_argument('--noverify', dest='do_verify', action='store_false', default = True,
                        help = 'If chosen, do not verify the SSL connection.')
    args = parser.parse_args( )
    assert( args.show is not None ), "error, show name not defined."
    assert( args.jsonfile.endswith('.json' ) ), "error, JSON file does not end with json."
    if args.do_debug: logging.basicConfig( level = logging.DEBUG )
    #
    client, status = plexcore_deluge.get_deluge_client( )
    if status != 'SUCCESS':
        print( "error, could not find remote server to push series info.")
        return
    username = client.username
    password = client.password
    server = client.host
    #
    ## now get episode information
    try:
        epdicts = plextvdb.get_tot_epdict_tvdb(
            args.show.strip( ), showSpecials = args.do_showspecials, verify = args.do_verify )
        logging.debug( 'name of show: %s. Number of eps: %d.' % (
            args.show.strip( ), sum(list(map(lambda seasno: len( epdicts[ seasno ] ), epdicts)))))
    except Exception as e:
        print( "error, could not get show %s." % args.show.strip( ) )
        return
    epdicts_sub = { seasno : {
        epno : epdicts[seasno][epno][0] for epno in epdicts[seasno] } for seasno in epdicts }
    with Connection( server, user = username, connect_kwargs = { 'password' : password } ) as conn, BytesIO( ) as io_obj:
        if 'key_filename' in conn.connect_kwargs:
            conn.connect_kwargs.pop( 'key_filename' )
        io_obj.write( json.dumps( epdicts_sub, indent=1 ).encode( ) )
        r = conn.put( io_obj, os.path.basename( args.jsonfile ) )
        print( 'put episode info for "%s" into %s in %0.3f seconds.' % (
            args.show.strip( ), r.remote, time.time( ) - time0 ) )
