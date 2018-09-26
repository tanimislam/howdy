#!/usr/bin/env python3

import re, codecs, logging, sys, signal
from plexcore import signal_handler
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

def get_tv_torrent_items( items, filename = None ):
    if len( items ) != 1:
        sortdict = { idx + 1 : item for ( idx, item ) in enumerate(items) }
        if sys.version_info.major == 2:
            bs = codecs.encode( 'Choose TV episode or series:\n%s\n' %
                                '\n'.join(map(lambda idx: '%d: %s (%d SE, %d LE)' % ( idx, sortdict[ idx ][ 'title' ],
                                                                                      sortdict[ idx ][ 'seeders' ],
                                                                                      sortdict[ idx ][ 'leechers' ]),
                                              sorted( sortdict ) ) ), 'utf-8' )
            iidx = raw_input( bs )
        else:
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
    if filename is None:
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
    opts, args = parser.parse_args( )
    assert( opts.name is not None )
    #
    items = get_items_zooqle( opts.name, maxnum = opts.maxnum )
    if items is None:
        items = get_items_kickass( opts.name, maxnum = opts.maxnum )
    if items is None:
        items = get_items_tpb( opts.name, doAny = opts.do_any, maxnum = opts.maxnum, raiseError = False )    
    if items is None:
        items = get_items_torrentz( opts.name, maxnum = opts.maxnum )
    if items is None:
        items = get_items_rarbg( opts.name, maxnum = opts.maxnum )
    if items is not None:
        get_tv_torrent_items( items, filename = opts.filename )
