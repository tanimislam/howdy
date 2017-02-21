#!/usr/bin/env python2

import re, codecs, requests
from optparse import OptionParser

def get_movie_torrent_items( name, email, filename = None):
    url = 'https://***REMOVED***islam.ddns.net/flask/plex/sendmovietorrent'
    response = requests.post( url, json = { 'mode' : 'MAGNET', 'name' : name },
                              auth = ( email, 'initialplexserver' ) )
    if response.status_code == 400:
        print( response.json( )['message'] )
        return
    items = response.json( )['items']
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
            
def get_movie_yts( name, email ):
    url = 'https://***REMOVED***islam.ddns.net/flask//plex/sendmovietorrent'
    response = requests.post( url, json = { 'mode' : 'TORRENT', 'name' : name },
                              auth = ( email, 'initialplexserver' ) )
    if response.status_code == 200:
        movies = response.json( )['movies']
        if len(movies) != 1:
            movdict = map(lambda mov: mov['title'], movies)
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
            actmov = max( movies )
        print('Chosen movie %s' % actmov['title'])
        url = list(filter(lambda tor: 'quality' in tor and '3D' not in tor['quality'],
                          actmov['torrents']))[0]['url']
        resp = requests.get( url )
        with open( '%s.torrent' % '_'.join( actmov['title'].split() ), 'wb') as openfile:
            openfile.write( resp.content )
    elif response.status_code == 400:
        message = response.json( )['message']
        raise ValueError('PROBLEM WITH TORRENT SEARCH: %s' % message)
    else:
        print 'ERROR, server https://***REMOVED***islam.ddns.net/flask may be down.'
        return
    
def main( ):
    parser = OptionParser( )
    parser.add_option('--name', dest='name', type=str, action='store',
                      help = 'Name of the movie file to get.')
    parser.add_option( '--email', dest='email', type=str, action='store',
                       help = 'Email of person who has access to the Plex server.' )
    parser.add_option('--filename', dest='filename', action='store', type=str,
                      help = 'If defined, put option into filename.')
    parser.add_option('--bypass', dest='do_bypass', action='store_true', default=False,
                      help = 'If chosen, bypass YTS.AG.')    
    opts, args = parser.parse_args( )
    assert( opts.name is not None and opts.email is not None )
    if not opts.do_bypass:
        try:
            get_movie_yts( opts.name, opts.email )
            return
        except ValueError:
            pass

    get_movie_torrent_items( opts.name, opts.email, filename = opts.filename )

if __name__=='__main__':
    main( )
