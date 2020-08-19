import signal
from plexstuff import signal_handler
signal.signal( signal.SIGINT, signal_handler )
import logging, os, re, time
from itertools import chain
from multiprocessing import Pool
from argparse import ArgumentParser
#
from plexstuff.plexcore import plexcore_deluge, plexcore, plexcore_torrents

def get_items_jackett( name, maxnum = 1000, verify = True ):
    assert( maxnum >= 5 )
    logging.info( 'started getting book torrents with jackett %s.' % name )
    items, status = plexcore_torrents.get_book_torrent_jackett(
        name, maxnum = maxnum, verify = verify )
    if status != 'SUCCESS':
        logging.info( 'ERROR, JACKETT COULD NOT FIND %s.' % name )
        return None
    return items

def get_book_torrent_items(
    items, filename = None, to_torrent_server = False ):
    if len( items ) != 1:
        sortdict = { idx + 1 : item for ( idx, item ) in enumerate( items ) }
        bs = 'Choose candidate book item:\n%s\n' % '\n'.join(
            map(lambda idx: '%d: %s (%d SE, %d LE)' % (
                idx, sortdict[ idx ][ 'title'], sortdict[ idx ][ 'seeders' ],
                sortdict[ idx ][ 'leechers' ] ),
                sorted( sortdict ) ) )
        iidx = input( bs )
        try:
            iidx = int( iidx.strip( ) )
            if iidx not in sortdict:
                print('Error, need to choose one of the candidate books. Exiting...')
                return
            magnet_link = sortdict[ iidx ][ 'link' ]
            actbook = sortdict[ iidx ][ 'title' ]
        except Exception as e:
            print( 'Error, did not give a valid integer value. Exiting...' )
            return
    else:
        actbook = max( items )[ 'title' ]
        magnet_link = max( items )[ 'link' ]

    print( 'Chosen book: %s' % actbook )
    if to_torrent_server: # upload to deluge server
        client, status = plexcore_deluge.get_deluge_client( )
        if status != 'SUCCESS':
            print( status )
            return
        plexcore_deluge.deluge_add_magnet_file(
            client, magnet_link )
    elif filename is None:
        print( 'magnet link: %s' % magnet_link )
    else:
        with open( filename, 'w' ) as openfile:
            openfile.write( '%s\n' % magnet_link )

def main( ):
    parser = ArgumentParser( )
    parser.add_argument('-n', '--name', dest='name', type=str, action='store', required = True,
                        help = 'Name of the book to get.')
    parser.add_argument('--maxnum', dest='maxnum', type=int, action='store', default = 10,
                      help = 'Maximum number of torrents to look through. Default is 10.')
    parser.add_argument('-f', '--filename', dest='filename', action='store', type=str,
                      help = 'If defined, put magnet link into filename.')
    parser.add_argument('--add', dest='do_add', action='store_true', default = False,
                      help = 'If chosen, push the magnet link into the deluge server.' )
    parser.add_argument('--info', dest='do_info', action='store_true', default = False,
                      help = 'If chosen, run in info mode.' )
    parser.add_argument('--noverify', dest='do_verify', action='store_false', default = True,
                      help = 'If chosen, do not verify SSL connections.' )
    args = parser.parse_args( )
    logger = logging.getLogger( )
    if args.do_info: logger.setLevel( logging.INFO )
    #
    time0 = time.time( )
    if plexcore.get_jackett_credentials( ) is None:
        print( 'Error, Jackett server does not work. Exiting...' )
        retur
    items = get_items_jackett( args.name, maxnum = args.maxnum, verify = args.do_verify )
    logging.info( 'search for %s took %0.3f seconds.' % ( args.name, time.time( ) - time0 ) )
    if items is None: return
    #
    ## sort from most seeders + leecher to least
    items_sorted = sorted( items, key = lambda tup: (
        -tup['seeders'] - tup['leechers'], tup['title'] ) )[:args.maxnum]
    get_book_torrent_items( items_sorted, filename = args.filename, to_torrent_server = args.do_add )
