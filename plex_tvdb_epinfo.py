#!/usr/bin/env python3

import sys, signal 
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import os, json, time, logging
from io import BytesIO
from fabric import Connection
from plextvdb import plextvdb
from plexcore import plexcore_deluge
from optparse import OptionParser

def main( ):
    time0 = time.time( )
    parser = OptionParser( )
    parser.add_option('-s', '--show', type=str, action='store', dest='show',
                      help = 'Name of the TV Show to push into remote server.')
    parser.add_option('-j', '--jsonfile', type=str, action='store', dest='jsonfile', default = 'eps.json',
                      help = 'Name of the JSON file into which to store the episode information. Default is eps.json.' )
    parser.add_option('--debug', dest='do_debug', action='store_true', default = False,
                      help = 'If chosen, then run DEBUG logging.' )
    parser.add_option('--noverify', dest='do_verify', action='store_false', default = True,
                      help = 'If chosen, do not verify the SSL connection.')
    opts, args = parser.parse_args( )
    assert( opts.show is not None ), "error, show name not defined."
    assert( opts.jsonfile.endswith('.json' ) ), "error, JSON file does not end with json."
    if opts.do_debug: logging.basicConfig( level = logging.DEBUG )
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
        epdicts = plextvdb.get_tot_epdict_tvdb( opts.show.strip( ), verify = opts.do_verify )
        logging.debug( 'name of show: %s. Number of eps: %d.' % (
            opts.show.strip( ), sum(list(map(lambda seasno: len( epdicts[ seasno ] ), epdicts)))))
    except Exception as e:
        print( "error, could not get show %s." % opts.show.strip( ) )
        return
    epdicts_sub = { seasno : {
        epno : epdicts[seasno][epno][0] for epno in epdicts[seasno] } for seasno in epdicts }
    with Connection( server, user = username, connect_kwargs = { 'password' : password } ) as conn, BytesIO( ) as io_obj:
        if 'key_filename' in conn.connect_kwargs:
            conn.connect_kwargs.pop( 'key_filename' )
        io_obj.write( json.dumps( epdicts_sub, indent=1 ).encode( ) )
        r = conn.put( io_obj, os.path.basename( opts.jsonfile ) )
        print( 'put episode info for "%s" into %s in %0.3f seconds.' % (
            opts.show.strip( ), r.remote, time.time( ) - time0 ) )

if __name__=='__main__':
    main( )
    
