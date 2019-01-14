#!/usr/bin/env python3

import re, codecs, requests, sys, signal, time, logging
from functools import reduce
from plexcore import signal_handler
signal.signal( signal.SIGINT, signal_handler )
from optparse import OptionParser
from plextmdb import plextmdb_torrents

def get_items_zooqle( name, maxnum = 10 ):
    assert( maxnum >= 5)
    items, status = plextmdb_torrents.get_movie_torrent_zooqle( name, maxnum = maxnum )
    if status != 'SUCCESS': return None
    return items

def get_items_tpb( name, maxnum = 10, doAny = False ):
    assert( maxnum >= 5)
    its, status = plextmdb_torrents.get_movie_torrent_tpb( name, maxnum = maxnum, doAny = doAny )
    if status != 'SUCCESS': return None    
    items = [ { 'title' : item[0], 'seeders' : item[1], 'leechers' : item[2], 'link' : item[3] } for
              item in its ]
    return items

def get_items_kickass( name, maxnum = 10, doAny = False ):
    assert( maxnum >= 5)
    its, status = plextmdb_torrents.get_movie_torrent_kickass( name, maxnum = maxnum, doAny = doAny )
    if status != 'SUCCESS':
        return None    
    items = [ { 'title' : item[0], 'seeders' : item[1], 'leechers' : item[2], 'link' : item[3] } for
              item in its ]
    return items

def get_items_rarbg( name, maxnum = 10 ):
    assert( maxnum >= 5 )
    items, status = plextmdb_torrents.get_movie_torrent_rarbg( name, maxnum = maxnum )
    if status != 'SUCCESS' : return None
    return items

def get_movie_torrent_items( items, filename = None):    
    if len( items ) != 1:
        sortdict = { idx + 1 : item for ( idx, item ) in enumerate(items) }
        bs = 'Choose movie:\n%s\n' % '\n'.join(
            map(lambda idx: '%d: %s (%d SE, %d LE)' % ( idx, sortdict[ idx ][ 'title' ],
                                                        sortdict[ idx ][ 'seeders' ],
                                                        sortdict[ idx ][ 'leechers' ]),
                sorted( sortdict ) ) )
        iidx = input( bs )
        try:
            iidx = int( iidx.strip( ) )
            if iidx not in sortdict:
                print('Error, need to choose one of the movie names. Exiting...')
                return
            magnet_link = sortdict[ iidx ][ 'link' ]
            actmov = sortdict[ iidx ][ 'title' ]
        except Exception:
            print('Error, did not give a valid integer value. Exiting...')
            return
    else:
        actmov = max( items )[ 'title' ]
        magnet_link = max( items )[ 'link' ]

    print('Chosen movie %s' % actmov )
    if filename is None:
        print('magnet link: %s' % magnet_link )
    else:
        with open(filename, 'w') as openfile:
            openfile.write('%s\n' % magnet_link )
            
def get_movie_yts( name, verify = True, raiseError = False ):
    movies, status = plextmdb_torrents.get_movie_torrent( name, verify = verify )
    if status != 'SUCCESS':
        if raiseError:
            raise ValueError("Could not find %s, exiting..." % name )
        print('Could not find %s, exiting...' % name)
        return
    if len(movies) != 1:
        movdict = { mov['title'] : mov for mov in movies }
        sortdict = { idx + 1 : title for (idx, title) in
                     enumerate( sorted( movdict.keys( ) ) ) }
        if sys.version_info.major == 2:
            iidx = raw_input( 'choose movie: %s\n' % '\n'.join([
                '%d: %s' % ( idx, sortdict[idx] ) for idx in
                sorted( sortdict.keys( ) ) ]) )
        else:
            iidx = input( 'choose movie: %s\n' % '\n'.join([
                '%d: %s' % ( idx, sortdict[idx] ) for idx in
                sorted( sortdict.keys( ) ) ]) )
        try:
            iidx = int( iidx.strip( ) )
            if iidx not in sortdict:
                print('Error, need to choose one of the movie names. Exiting...')
                return
            actmov = movdict[ sortdict[ iidx ] ]
        except Exception:
            print('Error, did not give an integer value. Exiting...')
            return
    else:
        def valid_movie( mov ):
            if 'quality' not in mov:
                return True
            if '3D' in mov['quality']:
                return False
            return True
        actmov = max( movies )
    print('Chosen movie %s' % actmov['title'])
    url = list(filter(lambda tor: 'quality' in tor and '3D' not in tor['quality'],
                      actmov['torrents']))[0]['url']
    resp = requests.get( url, verify = verify )
    with open( '%s.torrent' % '_'.join( actmov['title'].split() ), 'wb') as openfile:
        openfile.write( resp.content )

def main( ):
    parser = OptionParser( )
    parser.add_option('-n', '--name', dest='name', type=str, action='store',
                      help = 'Name of the movie file to get.')
    parser.add_option('--maxnum', dest='maxnum', type=int, action='store', default = 10,
                      help = 'Maximum number of torrents to look through. Default is 10.')
    parser.add_option('--any', dest='do_any', action='store_true', default = False,
                      help = 'If chosen, make no filter on movie format.')
    parser.add_option('-f', '--filename', dest='filename', action='store', type=str,
                      help = 'If defined, put option into filename.')
    parser.add_option('--bypass', dest='do_bypass', action='store_true', default=False,
                      help = 'If chosen, bypass YTS.AG.')
    parser.add_option('--nozooq', dest='do_nozooq', action='store_true', default=False,
                      help = 'If chosen, bypass ZOOQLE.')
    parser.add_option('--debug', dest='do_debug', action='store_true', default = False,
                      help = 'If chosen, run in debug mode.' )
    opts, args = parser.parse_args( )
    assert( opts.name is not None )
    if opts.do_debug: logging.basicConfig( level = logging.INFO )
    #
    time0 = time.time( )
    if not opts.do_bypass:
        try:
            get_movie_yts( opts.name, verify = True, raiseError = True )
            logging.info( 'search for torrents took %0.3f seconds.' % ( time.time( ) - time0 ) )
            return
        except ValueError:
            pass

    if not opts.do_nozooq:
        items = get_items_zooqle( opts.name, maxnum = opts.maxnum )
    else:
        items = None
    items = reduce(lambda x,y: x+y, list( filter(
        None,
        [ items,
          get_items_rarbg( opts.name, maxnum = opts.maxnum ),
          get_items_tpb( opts.name, doAny = opts.do_any, maxnum = opts.maxnum ) ] ) ) )
    
    logging.info( 'search for torrents took %0.3f seconds.' % ( time.time( ) - time0 ) )    
    if items is not None:
        #
        ## sort from most seeders + leecher to least
        items_sorted = sorted( items, key = lambda tup: tup['seeders'] + tup['leechers'] )[::-1][:opts.maxnum]
        get_movie_torrent_items( items, filename = opts.filename )

if __name__=='__main__':
    main( )
