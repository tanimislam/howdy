#!/usr/bin/env python3

import sys, signal
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import re, codecs, requests, time, logging
from plexcore import plexcore_deluge
from itertools import chain
from pathos.multiprocessing import Pool
from optparse import OptionParser
from plextmdb import plextmdb_torrents
from plextvdb import plextvdb_torrents
from plexcore.plexcore import get_jackett_credentials

def get_items_jackett( name, maxnum = 1000, verify = True ):
    assert( maxnum >= 5 )
    items, status = plextmdb_torrents.get_movie_torrent_jackett(
        name, maxnum = maxnum, doRaw = False, verify = verify )
    if status != 'SUCCESS':
        logging.info( 'ERROR, JACKETT COULD NOT FIND %s.' % name )
        return None
    return items

def get_items_eztv_io( name, maxnum = 1000, verify = True ):
    assert( maxnum >= 5 )
    items, status = plextmdb_torrents.get_movie_torrent_eztv_io(
        name, maxnum = maxnum, verify = verify )
    if status != 'SUCCESS':
        logging.info( 'ERROR, EZTV.IO COULD NOT FIND %s.' % name )
        return None
    return items
    
def get_items_zooqle( name, maxnum = 100, verify = True ):
    assert( maxnum >= 5)
    items, status = plextmdb_torrents.get_movie_torrent_zooqle(
        name, maxnum = maxnum, verify = verify )
    if status != 'SUCCESS':
        return None
    return items

def get_items_tpb( name, maxnum = 10, doAny = False, verify = True ):
    assert( maxnum >= 5)
    its, status = plextmdb_torrents.get_movie_torrent_tpb(
        name, maxnum = maxnum, doAny = doAny, verify = verify )
    if status != 'SUCCESS':
        return None
    items = [ { 'title' : item[0], 'seeders' : item[1], 'leechers' : item[2], 'link' : item[3] } for
              item in its ]
    return items

def get_items_kickass( name, maxnum = 10, doAny = False, verify = True ):
    assert( maxnum >= 5)
    its, status = plextmdb_torrents.get_movie_torrent_kickass(
        name, maxnum = maxnum, doAny = doAny, verify = verify )
    if status != 'SUCCESS': return None
    items = [ { 'title' : item[0], 'seeders' : item[1], 'leechers' : item[2], 'link' : item[3] } for
              item in its ]
    return items

def get_items_rarbg( name, maxnum = 100, verify = True ):
    assert( maxnum >= 5 )
    items, status = plextmdb_torrents.get_movie_torrent_rarbg(
        name, maxnum = maxnum, verify = verify )
    if status != 'SUCCESS' : return None
    return items

def get_items_torrentz( name, maxnum = 100, verify = True ):
    assert( maxnum >= 5 )
    items, status = plextvdb_torrents.get_tv_torrent_torrentz(
        name, maxnum = maxnum, verify = verify )
    if status != 'SUCCESS':
        logging.info( 'ERROR, TORRENTZ COULD NOT FIND %s.' % name )
        return None
    return items

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
        with open(filename, mode='w', encoding='utf-8') as openfile:
            openfile.write('%s\n' % magnet_link )
            
def get_movie_yts( name, verify = True, raiseError = False, to_torrent = False ):
    movies, status = plextmdb_torrents.get_movie_torrent(
        name, verify = verify )
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
    parser.add_option('--timeout', dest='timeout', type=int, action='store', default = 60,
                      help = 'Timeout on when to quit getting torrents (in seconds). Default is 60 seconds..' )
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
    parser.add_option('--info', dest='do_info', action='store_true', default = False,
                      help = 'If chosen, run in info mode.' )
    parser.add_option('--add', dest='do_add', action='store_true', default = False,
                      help = 'If chosen, push the magnet link into the deluge server.' )  
    parser.add_option('--noverify', dest='do_verify', action='store_false', default = True,
                      help = 'If chosen, do not verify SSL connections.' )
    parser.add_option('--timing', dest='do_timing', action='store_true', default = False,
                      help = 'If chosen, show timing information (how long to get TV torrents.')
    opts, args = parser.parse_args( )
    assert( opts.timeout >= 10 )
    assert( opts.name is not None )
    if opts.do_info: logging.basicConfig( level = logging.INFO )
    #
    time0 = time.time( )
    if not opts.do_bypass:
        try:
            get_movie_yts( opts.name, verify = opts.do_verify,
                           raiseError = True, to_torrent = opts.do_add )
            logging.info( 'search for YTS torrents took %0.3f seconds.' %
                          ( time.time( ) - time0 ) )
            return
        except ValueError: pass

    pool = Pool( processes = 4 )
    if not opts.do_nozooq: jobs = [
            pool.apply_async( get_items_zooqle, args = ( opts.name, opts.maxnum ) ) ]
    else: jobs = [ ]
    #
    ## check for jackett
    if get_jackett_credentials( ) is None:
        jobs += list(map(lambda func: pool.apply_async( func, args = ( opts.name, opts.maxnum ) ),
                         ( get_items_rarbg, get_items_tpb ) ) )
        if opts.do_torrentz:
            jobs.append( pool.apply_async( get_items_torrentz, args = ( opts.name, opts.maxnum ) ) )
    else:        
        jobs += list(map(lambda func: pool.apply_async(
            func, args = ( opts.name, opts.maxnum, opts.do_verify ) ),
                         ( get_items_jackett, get_items_eztv_io ) ) )
    items_lists = [ ]
    for job in jobs:
        try:
            items = job.get( opts.timeout )   # 60 second timeout on process
            if items is None: continue
            items_lists.append( items )
        except: pass
    items = list( chain.from_iterable( items_lists ) )
    if opts.do_timing:
        print( 'search for %d torrents took %0.3f seconds.' % (
            len( items ), time.time( ) - time0 ) )    
    if len( items ) != 0:
        #
        ## sort from most seeders + leecher to least
        items_sorted = sorted( items, key = lambda tup: -tup['seeders'] - tup['leechers'] )[:opts.maxnum]
        get_movie_torrent_items( items_sorted, filename = opts.filename, to_torrent = opts.do_add )

if __name__=='__main__':
    main( )
