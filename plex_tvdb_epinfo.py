#!/usr/bin/env python3

import os, sys, json, signal, time

from io import BytesIO
from fabric import Connection
from plextvdb import plextvdb
from plexcore import plexcore_deluge
from optparse import OptionParser

def main( ):
    time0 = time.time( )
    parser = OptionParser( )
    parser.add_option('-S', '--show', type=str, action='store', dest='show',
                      help = 'Namer of the TV Show to push into remote server.')
    parser.add_option('-j', '--jsonfile', type=str, action='store', dest='jsonfile', default = 'eps.json',
                      help = 'Name of the JSON file into which to store the episode information. Default is eps.json.' )
    opts, args = parser.parse_args( )
    assert( opts.show is not None ), "ERROR, SHOW NAME NOT DEFINED."
    assert( opts.jsonfile.endswith('.json' ) ), "ERROR, JSON FILE DOES NOT END WITH JSON."
    #
    client, status = plexcore_deluge.get_deluge_client( )
    if status != 'SUCCESS':
        print( "ERROR, COULD NOT FIND REMOTE SERVER TO PUSH SERIES INFO.")
        return
    username = client.username
    server = client.host
    #
    ## now get episode information
    try: epdicts = plextvdb.get_tot_epdict_tvdb( opts.show.strip( ) )
    except Exception as e:
        print( "ERROR, COULD NOT GET SHOW %s." % opts.show.strip( ) )
        return
    epdicts_sub = { seasno : {
        epno : epdicts[seasno][epno][0] for epno in epdicts[seasno] } for seasno in epdicts }
    with Connection( server, user = username ) as conn, BytesIO( ) as io_obj:
        io_obj.write( json.dumps( epdicts_sub, indent=1 ).encode( ) )
        r = conn.put( io_obj, os.path.basename( opts.jsonfile ) )
        print( 'put episode info for "%s" into %s in %0.3f seconds.' % (
            opts.show.strip( ), r.remote, time.time( ) - time0 ) )

if __name__=='__main__':
    main( )
    
