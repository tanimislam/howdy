import sys, signal
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import logging, os, re, time
from itertools import chain
from multiprocessing import Pool
from argparse import ArgumentParser
#
from plexstuff.plexcore import plexcore_deluge, plexcore
from plexstuff.plextvdb import plextvdb_torrents, plextvdb

def get_items_eztv_io( name, maxnum = 10, verify = True ):
    assert( maxnum >= 5 )
    items, status = plextvdb_torrents.get_tv_torrent_eztv_io(
        name, maxnum = maxnum, verify = verify )
    if status != 'SUCCESS':
        logging.info( 'ERROR, EZTV.IO COULD NOT FIND %s.' % name )
        return None
    return items

def get_items_jackett( name, maxnum = 1000, raw = False, verify = True ):
    assert( maxnum >= 5 )
    logging.info( 'started jackett %s.' % name )
    items, status = plextvdb_torrents.get_tv_torrent_jackett(
        name, maxnum = maxnum, raw = raw, verify = verify )
    if status != 'SUCCESS':
        logging.info( 'ERROR, JACKETT COULD NOT FIND %s.' % name )
        return None
    return items
    
def get_items_zooqle( name, maxnum = 10, verify = True ):
    assert( maxnum >= 5 )
    items, status = plextvdb_torrents.get_tv_torrent_zooqle(
        name, maxnum = maxnum, verify = verify )
    if status != 'SUCCESS':
        logging.info( 'ERROR, ZOOQLE COULD NOT FIND %s.' % name )
        return None
    return items

def get_items_tpb(name, maxnum = 10, doAny = False, raiseError = False, verify = True ):
    assert( maxnum >= 5 )
    items, status = plextvdb_torrents.get_tv_torrent_tpb(
        name, maxnum = maxnum, doAny = doAny, verify = verify )
    if status != 'SUCCESS':
        if raiseError:
            raise ValueError('ERROR, TPB COULD NOT FIND %s.' % name)
        logging.info( 'ERROR, TPB COULD NOT FIND %s.' % name )
        return None
    return items

def get_items_torrentz( name, maxnum = 10, verify = True ):
    assert( maxnum >= 5 )
    items, status = plextvdb_torrents.get_tv_torrent_torrentz(
        name, maxnum = maxnum, verify = verify )
    if status != 'SUCCESS':
        logging.info( 'ERROR, TORRENTZ COULD NOT FIND %s.' % name )
        return None
    return items

def get_items_rarbg( name, maxnum = 10, verify = True ):
    assert( maxnum >= 10 )
    items, status = plextvdb_torrents.get_tv_torrent_rarbg(
        name, maxnum = maxnum, verify = verify )
    if status != 'SUCCESS':
        logging.info( 'ERROR, RARBG COULD NOT FIND %s.' % name )
        return None
    return items

def get_items_kickass( name, maxnum = 10, verify = True ):
    assert( maxnum >= 10 )
    items, status = plextvdb_torrents.get_tv_torrent_kickass(
        name, maxnum = maxnu, verify = verify )
    if status != 'SUCCESS':
        logging.info( 'ERROR, KICKASS COULD NOT FIND %s.' % name )
        return None
    return items

def get_tv_torrent_items(
        items, filename = None, to_torrent_server = False ):
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
    if to_torrent_server: # upload to deluge server
        client, status = plexcore_deluge.get_deluge_client( )
        if status != 'SUCCESS':
            print( status )
            return
        plexcore_deluge.deluge_add_magnet_file(
            client, magnet_link )
    elif filename is None:
        print('magnet link: %s' % magnet_link )
    else:
        with open(filename, 'w') as openfile:
            openfile.write('%s\n' % magnet_link )

def process_magnet_items( name, raw = False, verify = True, maxnum = 10 ):
    time0 = time.time( )
    #
    ## check for jackett
    if plexcore.get_jackett_credentials( ) is None:
        pool = Pool( processes = 5 )
        jobs = list(map(
            lambda func: pool.apply_async( func, args = ( name, maxnum ) ),
            ( get_items_zooqle, get_items_rarbg, #get_items_kickass,
              get_items_torrentz, get_items_eztv_io ) ) )
        jobs.append( pool.apply_async( get_items_tpb, args = (
            name, maxnum, False, False ) ) ) # args.do_any = False
    else:
        pool = Pool( processes = 3 )
        jobs = list(map(
            lambda func: pool.apply_async( func, args = ( name, maxnum, verify ) ),
            ( get_items_zooqle, get_items_eztv_io ) ) )
        jobs.append( pool.apply_async( get_items_jackett, args = ( name, maxnum, raw, verify ) ) )
    items_all = list( chain.from_iterable( filter( None, map(lambda job: job.get( ), jobs ) ) ) )
    logging.info( 'search for torrents took %0.3f seconds.' % ( time.time( ) - time0 ) )
    pool.close( )
    pool.join( )
    if len( items_all ) != 0: return items_all
    return None
            
def main( ):
    parser = ArgumentParser( )
    parser.add_argument('-n', '--name', dest='name', type=str, action='store', required = True,
                      help = 'Name of the TV show to get.')
    parser.add_argument('--maxnum', dest='maxnum', type=int, action='store', default = 10,
                      help = 'Maximum number of torrents to look through. Default is 10.')
    parser.add_argument('--raw', dest='do_raw', action='store_true', default = False,
                      help = 'If chosen, then use the raw string (for jackett) to download the torrent.' )
    parser.add_argument('-f', '--filename', dest='filename', action='store', type=str,
                      help = 'If defined, put torrent or magnet link into filename.')
    parser.add_argument('--add', dest='do_add', action='store_true', default = False,
                      help = 'If chosen, push the magnet link into the deluge server.' )
    parser.add_argument('--info', dest='do_info', action='store_true', default = False,
                      help = 'If chosen, run in info mode.' )
    parser.add_argument('--noverify', dest='do_verify', action='store_false', default = True,
                      help = 'If chosen, do not verify SSL connections.' )
    parser.add_argument('--timing', dest='do_timing', action='store_true', default = False,
                      help = 'If chosen, show timing information (how long to get TV torrents).')
    args = parser.parse_args( )
    logger = logging.getLogger( )
    if args.do_info: logger.setLevel( logging.INFO )
    #
    time0 = time.time( )
    items = process_magnet_items(
        args.name, maxnum = args.maxnum,
        raw = args.do_raw, verify = args.do_verify )
    if args.do_timing:
        print( 'took %0.3f seconds to get TV torrents for %s.' % (
            time.time( ) - time0, args.name ) )
    if items is not None:
        #
        ## sort from most seeders + leecher to least
        items_sorted = sorted( items, key = lambda tup: (
            -tup['seeders'] - tup['leechers'], tup['title'] ) )[:args.maxnum]
        get_tv_torrent_items( items_sorted, filename = args.filename, to_torrent_server = args.do_add )
