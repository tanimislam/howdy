import sys, signal
from howdy import signal_handler
signal.signal( signal.SIGINT, signal_handler )
#
import re, codecs, requests, time, logging, warnings
from itertools import chain
from pathos.multiprocessing import Pool
from argparse import ArgumentParser
#
from howdy.core import core_deluge, core_torrents, core_transmission
from howdy.movie import movie_torrents, movie
from howdy.tv import tv_torrents
from howdy.core.core import get_jackett_credentials
#
## now remove the XMLParsedAsHTMLWarning warning. GUARD CODE UNTIL SINGLETON-IZED SOLUTION!
from bs4 import XMLParsedAsHTMLWarning
warnings.filterwarnings('ignore', category = XMLParsedAsHTMLWarning )

def get_items_jackett( name, tmdb_id = None, maxnum = 1000, verify = True, doRaw = False ):
    assert( maxnum >= 5 )
    items, status = movie_torrents.get_movie_torrent_jackett(
        name, maxnum = maxnum, doRaw = doRaw, verify = verify,
        tmdb_id = tmdb_id )
    if status != 'SUCCESS':
        logging.info( 'ERROR, JACKETT COULD NOT FIND %s.' % name )
        return None
    return items

def get_items_eztv_io( name, tmdb_id = None, year = None, maxnum = 1000, verify = True ):
    assert( maxnum >= 5 )
    items, status = movie_torrents.get_movie_torrent_eztv_io(
        name, maxnum = maxnum, verify = verify, tmdb_id = tmdb_id )
    if status != 'SUCCESS':
        logging.info( 'ERROR, EZTV.IO COULD NOT FIND %s.' % name )
        return None
    return items
    
def get_items_zooqle( name, maxnum = 100, verify = True ):
    assert( maxnum >= 5)
    items, status = movie_torrents.get_movie_torrent_zooqle(
        name, maxnum = maxnum, verify = verify )
    if status != 'SUCCESS':
        return None
    return items

def get_items_tpb( name, maxnum = 10, doAny = False, verify = True ):
    assert( maxnum >= 5)
    its, status = movie_torrents.get_movie_torrent_tpb(
        name, maxnum = maxnum, doAny = doAny, verify = verify )
    if status != 'SUCCESS':
        return None
    items = [ { 'title' : item[0], 'seeders' : item[1], 'leechers' : item[2], 'link' : item[3] } for
              item in its ]
    return items

def get_items_kickass( name, maxnum = 10, doAny = False, verify = True ):
    assert( maxnum >= 5)
    its, status = movie_torrents.get_movie_torrent_kickass(
        name, maxnum = maxnum, doAny = doAny, verify = verify )
    if status != 'SUCCESS': return None
    items = [ { 'title' : item[0], 'seeders' : item[1], 'leechers' : item[2], 'link' : item[3] } for
              item in its ]
    return items

def get_items_rarbg( name, maxnum = 100, verify = True ):
    assert( maxnum >= 5 )
    items, status = movie_torrents.get_movie_torrent_rarbg(
        name, maxnum = maxnum, verify = verify )
    if status != 'SUCCESS' : return None
    return items

def get_items_torrentz( name, maxnum = 100, verify = True ):
    assert( maxnum >= 5 )
    items, status = tv_torrents.get_tv_torrent_torrentz(
        name, maxnum = maxnum, verify = verify )
    if status != 'SUCCESS':
        logging.info( 'ERROR, TORRENTZ COULD NOT FIND %s.' % name )
        return None
    return items

def get_movie_torrent_items( items, filename = None, to_torrent = False ):
    excluded_tracker_stubs = core_torrents.get_trackers_to_exclude( )
    if len( items ) != 1:
        sortdict = { idx + 1 : item for ( idx, item ) in enumerate(items) }
        bs = 'Choose movie:\n%s\n' % '\n'.join(
            map(lambda idx: '%d: %s (%d SE, %d LE)' % (
                idx, sortdict[ idx ][ 'title' ],
                sortdict[ idx ][ 'seeders' ],
                sortdict[ idx ][ 'leechers' ]),
                sorted( sortdict ) ) )
        iidx = input( bs )
        try:
            iidx = int( iidx.strip( ) )
            if iidx not in sortdict:
                print('Error, need to choose one of the movie names. Exiting...')
                return
            magnet_link = core_torrents.deconfuse_magnet_link(
                sortdict[ iidx ][ 'link' ], excluded_tracker_stubs = excluded_tracker_stubs )
            actmov = sortdict[ iidx ][ 'title' ]
        except Exception:
            print('Error, did not give a valid integer value. Exiting...')
            return
    else:
        actmov = max( items )[ 'title' ]
        magnet_link = core_torrents.deconfuse_magnet_link(
            max( items )[ 'link' ],
            excluded_tracker_stubs = excluded_tracker_stubs )

    print('Chosen movie %s' % actmov )
    if to_torrent: # upload to deluge server
        client, status = core_deluge.get_deluge_client( )
        if status != 'SUCCESS':
            print( status )
            return
        core_deluge.deluge_add_magnet_file( client, magnet_link )
    elif filename is None:
        print('magnet link: %s' % magnet_link )
        return
    else:
        with open(filename, mode='w', encoding='utf-8') as openfile:
            openfile.write('%s\n' % magnet_link )
            
def get_movie_yts( name, verify = True, raiseError = False, to_torrent = False ):
    movies, status = movie_torrents.get_movie_torrent(
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
        except Exception as e:
            logging.debug( "ERROR MESSAGE = %s." % str( e ) )
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
        #client, status = core_deluge.get_deluge_client( )
        client, status = core_transmission.get_transmission_client( )
        if status != 'SUCCESS':
            print( status )
            return
        core_transmission.transmission_add_torrent_file_as_data(
            client, resp.content )

def main( ):
    parser = ArgumentParser( )
    parser.add_argument('-n', '--name', dest='name', type=str, action='store',
                        help = 'Name of the movie to get.', required = True )
    parser.add_argument('-y', '--year', dest='year', type=int, action='store',
                        help = 'Year to look for the movie to get.')
    parser.add_argument('-M', '--maxnum', dest='maxnum', type=int, action='store', default = 10,
                        help = 'Maximum number of torrents to look through. Default is 10.')
    parser.add_argument('-f', '--filename', dest='filename', action='store', type=str,
                        help = 'If defined, put torrent or magnet file into filename.')
    parser.add_argument('--bypass', dest='do_bypass', action='store_true', default=False,
                        help = 'If chosen, bypass YTS.')
    parser.add_argument('-L', '--level', dest='level', action='store', default = 'NONE', choices = ['DEBUG','INFO','ERROR','NONE'],
                        help = 'Choose logging level. By default it is NONE. Choices are: [ DEBUG, INFO, ERROR, NONE ].' )
    parser.add_argument('-a', '--add', dest='do_add', action='store_true', default = False,
                        help = 'If chosen, push the magnet link or torrent file into the deluge server.' )  
    parser.add_argument('--noverify', dest='do_verify', action='store_false', default = True,
                        help = 'If chosen, do not verify SSL connections.' )
    parser.add_argument('-r', '--raw', dest='do_raw', action='store_true', default = False,
                        help = 'If chosen, do not use IMDB matching for Jackett torrents.')
    args = parser.parse_args( )
    # assert( args.timeout >= 10 )
    logging_dict = {
        'DEBUG' : logging.DEBUG,
        'INFO'  : logging.INFO,
        'ERROR' : logging.ERROR }
    if args.level != 'NONE':
        logging.basicConfig( level = logging_dict[ args.level ] )
    #
    num_both = 0
    if args.filename is not None: num_both += 1
    if args.do_add: num_both += 1
    assert( num_both != 2 ), "error, at most either one of --f or --add must be set, NOT both."
    #
    time0 = time.time( )
    tmdb_id = None
    if args.year is not None and not args.do_raw:
        tmdb_id = movie.get_movie_tmdbids( args.name, year = args.year )
    if not args.do_bypass:
        try:
            get_movie_yts( args.name, verify = args.do_verify,
                           raiseError = True, to_torrent = args.do_add )
            logging.info( 'search for YTS torrents took %0.3f seconds.' %
                          ( time.time( ) - time0 ) )
            return
        except ValueError: pass

    if not get_jackett_credentials( ):
        print( "ERROR, NEED JACKETT SERVER TO SEARCH FOR MAGNET LINKS. EXITING..." )
        return
    items = get_items_jackett( args.name, tmdb_id, args.maxnum, args.do_verify, args.do_raw )
    if items is None: items = [ ]
    logging.info( 'search for %d torrents took %0.3f seconds.' % (
        len( items ), time.time( ) - time0 ) )    
    if len( items ) == 0: return
    #
    ## sort from most seeders + leecher to least
    items_sorted = sorted( items, key = lambda tup: -tup['seeders'] - tup['leechers'] )[:args.maxnum]
    get_movie_torrent_items( items_sorted, filename = args.filename, to_torrent = args.do_add )
