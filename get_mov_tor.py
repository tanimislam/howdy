#!/usr/bin/env python3

import re, codecs, requests, sys, signal, time, logging
from plexcore import signal_handler, plexcore_deluge
signal.signal( signal.SIGINT, signal_handler )
from functools import reduce
from multiprocessing import Process, Manager, cpu_count
from optparse import OptionParser
from plextmdb import plextmdb_torrents
from plextvdb import plextvdb_torrents

def _process_items_list( items, shared_list ):
    if shared_list is None: return items
    else:
        shared_list.append( items )
        return

def get_items_zooqle( name, maxnum = 10, shared_list = None ):
    assert( maxnum >= 5)
    items, status = plextmdb_torrents.get_movie_torrent_zooqle( name, maxnum = maxnum )
    if status != 'SUCCESS':
        return _process_items_list( None, shared_list )
    return _process_items_list( items, shared_list )

def get_items_tpb( name, maxnum = 10, doAny = False, shared_list = None ):
    assert( maxnum >= 5)
    its, status = plextmdb_torrents.get_movie_torrent_tpb( name, maxnum = maxnum, doAny = doAny )
    if status != 'SUCCESS':
        return _process_items_list( None, shared_list )
    items = [ { 'title' : item[0], 'seeders' : item[1], 'leechers' : item[2], 'link' : item[3] } for
              item in its ]
    return _process_items_list( items, shared_list )

def get_items_kickass( name, maxnum = 10, doAny = False, shared_list = None ):
    assert( maxnum >= 5)
    its, status = plextmdb_torrents.get_movie_torrent_kickass( name, maxnum = maxnum, doAny = doAny )
    if status != 'SUCCESS':
        return _process_items_list( None, shared_list )
    items = [ { 'title' : item[0], 'seeders' : item[1], 'leechers' : item[2], 'link' : item[3] } for
              item in its ]
    return _process_items_list( items, shared_list )

def get_items_rarbg( name, maxnum = 10, shared_list = None ):
    assert( maxnum >= 5 )
    items, status = plextmdb_torrents.get_movie_torrent_rarbg( name, maxnum = maxnum )
    if status != 'SUCCESS' :
        return _process_items_list(None, shared_list )
    return _process_items_list( items, shared_list )

def get_items_torrentz( name, maxnum = 10, shared_list = None ):
    assert( maxnum >= 5 )
    items, status = plextvdb_torrents.get_tv_torrent_torrentz( name, maxnum = maxnum )
    if status != 'SUCCESS':
        logging.debug( 'ERROR, TORRENTZ COULD NOT FIND %s.' % name )
        return _process_items_list( None, shared_list )
    return _process_items_list( items, shared_list )

def get_movie_torrent_items( items, filename = None, to_torrent = False ):    
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
            
def get_movie_yts( name, verify = True, raiseError = False, to_torrent = False ):
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
    filename =  '%s.torrent' % '_'.join( actmov['title'].split() )
    if not to_torrent:
        with open( filename, 'wb') as openfile:
            openfile.write( resp.content )
    else:
        import base64
        client, status = plexcore_deluge.get_deluge_client( )
        if status != 'SUCCESS':
            print( status )
            return
        plexcore_deluge.deluge_add_torrent_file_as_data(
            client, filename, resp.content )

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
    parser.add_option('--torrentz', dest='do_torrentz', action='store_true', default=False,
                      help = 'If chosen, also look through TORRENTZ to get magnet link.')
    parser.add_option('--debug', dest='do_debug', action='store_true', default = False,
                      help = 'If chosen, run in debug mode.' )
    parser.add_option('--add', dest='do_add', action='store_true', default = False,
                      help = 'If chosen, push the magnet link into the deluge server.' )
    opts, args = parser.parse_args( )
    assert( opts.name is not None )
    if opts.do_debug: logging.basicConfig( level = logging.INFO )
    #
    time0 = time.time( )
    if not opts.do_bypass:
        try:
            get_movie_yts( opts.name, verify = True, raiseError = True,
                           to_torrent = opts.do_add )
            logging.info( 'search for torrents took %0.3f seconds.' %
                          ( time.time( ) - time0 ) )
            return
        except ValueError: pass

    manager = Manager( )  # multiprocessing may be a bit faster than single-process code
    num_processes = cpu_count( )
    shared_list = manager.list( )
    if not opts.do_nozooq: jobs = [
            Process(target=get_items_zooqle, args=(opts.name, opts.maxnum, shared_list ) ) ]
    else: jobs = [ ]
    jobs += [
        Process( target=get_items_rarbg, args=(opts.name, opts.maxnum, shared_list ) ),
        Process( target=get_items_tpb, args=(opts.name, opts.maxnum, opts.do_any, shared_list ) ) ]
    if opts.do_torrentz:
        jobs.append( Process( target=get_items_torrentz, args=(opts.name, opts.maxnum, shared_list ) ) )
    for process in jobs: process.start( )
    for process in jobs: process.join( )
    items = reduce(lambda x,y: x+y, list( filter( None, shared_list ) ) )
    
    logging.info( 'search for torrents took %0.3f seconds.' % ( time.time( ) - time0 ) )    
    if items is not None:
        #
        ## sort from most seeders + leecher to least
        items_sorted = sorted( items, key = lambda tup: tup['seeders'] + tup['leechers'] )[::-1][:opts.maxnum]
        get_movie_torrent_items( items, filename = opts.filename, to_torrent = opts.do_add )

if __name__=='__main__':
    main( )
