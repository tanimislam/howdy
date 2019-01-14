#!/usr/bin/env python3

import re, codecs, logging, sys, signal, time
from functools import reduce
from plexcore import signal_handler, plexcore_deluge
signal.signal( signal.SIGINT, signal_handler )
from optparse import OptionParser
from plextvdb import plextvdb_torrents

def get_items_zooqle( name, maxnum = 10 ):
    assert( maxnum >= 5 )
    items, status = plextvdb_torrents.get_tv_torrent_zooqle( name, maxnum = maxnum )
    if status != 'SUCCESS':
        logging.debug( 'ERROR, ZOOQLE COULD NOT FIND %s.' % name )
        return None
    return items

def get_items_tpb(name, maxnum = 10, doAny = False, raiseError = False):
    assert( maxnum >= 5 )
    items, status = plextvdb_torrents.get_tv_torrent_tpb( name, maxnum = maxnum, doAny = doAny )
    if status != 'SUCCESS':
        if raiseError:
            raise ValueError('ERROR, TPB COULD NOT FIND %s.' % name)
        logging.debug( 'ERROR, TPB COULD NOT FIND %s.' % name )
        return None
    return items

def get_items_torrentz( name, maxnum = 10 ):
    assert( maxnum >= 5 )
    items, status = plextvdb_torrents.get_tv_torrent_torrentz( name, maxnum = maxnum )
    if status != 'SUCCESS':
        logging.debug( 'ERROR, TORRENTZ COULD NOT FIND %s.' % name )
        return None
    return items

def get_items_rarbg( name, maxnum = 10 ):
    assert( maxnum >= 10 )
    items, status = plextvdb_torrents.get_tv_torrent_rarbg( name, maxnum = maxnum )
    if status != 'SUCCESS':
        logging.debug( 'ERROR, RARBG COULD NOT FIND %s.' % name )
        return None
    return items

def get_items_kickass( name, maxnum = 10 ):
    assert( maxnum >= 10 )
    items, status = plextvdb_torrents.get_tv_torrent_kickass( name, maxnum = maxnum )
    if status != 'SUCCESS':
        logging.debug( 'ERROR, KICKASS COULD NOT FIND %s.' % name )
        return None
    return items

def get_tv_torrent_items( items, filename = None, to_torrent = False ):
    if len( items ) != 1:
        sortdict = { idx + 1 : item for ( idx, item ) in enumerate(items) }
        bs = 'Choose TV episode or series:\n%s\n' % '\n'.join(
            map(lambda idx: '%d: %s (%d SE, %d LE)' % ( idx, sortdict[ idx ][ 'title' ],
                                                        sortdict[ idx ][ 'seeders' ],
                                                        sortdict[ idx ][ 'leechers' ]),
                sorted( sortdict ) ) )
        iidx = input( bs )
        try:
            iidx = int( iidx.strip( ) )
            if iidx not in sortdict:
                print('Error, need to choose one of the TV files. Exiting...')
                return
            magnet_link = sortdict[ iidx ][ 'link' ]
            actmov = sortdict[ iidx ][ 'title' ]
        except Exception:
            print('Error, did not give a valid integer value. Exiting...')
            return
    else:
        actmov = max( items )[ 'title' ]
        magnet_link = max( items )[ 'link' ]

    print('Chosen TV show: %s' % actmov )
    if to_torrent: # upload to deluge server
        client, status = plexcore_deluge.get_deluge_client( )
        if status != 'SUCCESS':
            print( status )
            return
        plexcore_deluge.deluge_add_magnet_file( client, magnet_link )
    elif filename is None:
        print('magnet link: %s' % magnet_link )
    else:
        with open(filename, 'w') as openfile:
            openfile.write('%s\n' % magnet_link )

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('-n', '--name', dest='name', type=str, action='store',
                      help = 'Name of the movie file to get.')
    parser.add_option('--maxnum', dest='maxnum', type=int, action='store', default = 10,
                      help = 'Maximum number of torrents to look through. Default is 10.')
    parser.add_option('--any', dest='do_any', action='store_true', default = False,
                      help = 'If chosen, make no filter on movie format.')
    parser.add_option('-f', '--filename', dest='filename', action='store', type=str,
                      help = 'If defined, put option into filename.')
    parser.add_option('--add', dest='do_add', action='store_true', default = False,
                      help = 'If chosen, push the magnet link into the deluge server.' )
    parser.add_option('--debug', dest='do_debug', action='store_true', default = False,
                      help = 'If chosen, run in debug mode.' )
    opts, args = parser.parse_args( )
    assert( opts.name is not None )
    if opts.do_debug: logging.basicConfig( level = logging.INFO )
    #
    time0 = time.time( )
    items = reduce(lambda x,y: x+y, list( filter(
        None,
        [ get_items_zooqle( opts.name, maxnum = opts.maxnum ),
          get_items_tpb( opts.name, doAny = opts.do_any, maxnum = opts.maxnum, raiseError = False ),
          get_items_torrentz( opts.name, maxnum = opts.maxnum ),
          get_items_rarbg( opts.name, maxnum = opts.maxnum ),
          get_items_kickass( opts.name, maxnum = opts.maxnum ) ] ) ) )
    logging.info( 'search for torrents took %0.3f seconds.' % ( time.time( ) - time0 ) )
    if items is not None:
        #
        ## sort from most seeders + leecher to least
        items_sorted = sorted( items, key = lambda tup: tup['seeders'] + tup['leechers'] )[::-1][:opts.maxnum]
        get_tv_torrent_items( items_sorted, filename = opts.filename, to_torrent = opts.do_add )
