#!/usr/bin/env python2

import re, codecs, requests
from optparse import OptionParser
from plextmdb import plextmdb_torrents

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
    its, status = plextmdb_torrents.get_movie_torrent_rarbg( name, maxnum = maxnum )
    if status != 'SUCCESS' : return None
    items = map(lambda item: { 'title' : item['filename'], 'seeders' : 10, 'leechers' : 10,
                               'link' : item['download'] }, its )
    return items

def get_movie_torrent_items( items, filename = None):    
    if len( items ) != 1:
        sortdict = { idx + 1 : item for ( idx, item ) in enumerate(items) }
        bs = codecs.encode( 'Choose movie:\n%s\n' %
                            '\n'.join(map(lambda idx: '%d: %s (%d SE, %d LE)' % ( idx, sortdict[ idx ][ 'title' ],
                                                                                  sortdict[ idx ][ 'seeders' ],
                                                                                  sortdict[ idx ][ 'leechers' ]),
                                          sorted( sortdict ) ) ), 'utf-8' )
        iidx = raw_input( bs )
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
        iidx = raw_input( 'choose movie: %s\n' % '\n'.join([
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
    parser.add_option('--name', dest='name', type=str, action='store',
                      help = 'Name of the movie file to get.')
    parser.add_option('--maxnum', dest='maxnum', type=int, action='store', default = 10,
                      help = 'Maximum number of torrents to look through. Default is 10.')
    parser.add_option('--any', dest='do_any', action='store_true', default = False,
                      help = 'If chosen, make no filter on movie format.')
    parser.add_option('--filename', dest='filename', action='store', type=str,
                      help = 'If defined, put option into filename.')
    parser.add_option('--bypass', dest='do_bypass', action='store_true', default=False,
                      help = 'If chosen, bypass YTS.AG.')    
    opts, args = parser.parse_args( )
    assert( opts.name is not None )
    if not opts.do_bypass:
        try:
            get_movie_yts( opts.name, verify = True, raiseError = True )
            return
        except ValueError:
            pass

    items = get_items_tpb( opts.name, doAny = opts.do_any, maxnum = opts.maxnum )
    if items is None:
        items = get_items_rarbg( opts.name, maxnum = opts.maxnum )
    if items is not None:
        get_movie_torrent_items( items, filename = opts.filename )

if __name__=='__main__':
    main( )
