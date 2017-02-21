#!/usr/bin/env python2

import re, codecs, logging, requests
from optparse import OptionParser

def get_tv_torrent_items( email, name, filename = None ):
    url = 'https://tanimislam.ddns.net/flask/plex/sendtvtorrent'
    response = requests.post( url, json = { 'name' : name },
                              auth = ( email, 'initialplexserver' ) )
    if response.status_code == 400:
        print( response.json( )['message'] )
        return
    elif response.status_code > 400:
        print 'ERROR, server https://tanimislam.ddns.net/flask may be down.'
        return

    items = response.json( )[ 'items' ]
    if len( items ) != 1:
        sortdict = { idx + 1 : item for ( idx, item ) in enumerate(items) }
        bs = codecs.encode( 'Choose TV episode or series:\n%s\n' %
                            '\n'.join(map(lambda idx: '%d: %s (%d SE, %d LE)' % ( idx, sortdict[ idx ][ 'title' ],
                                                                                  sortdict[ idx ][ 'seeders' ],
                                                                                  sortdict[ idx ][ 'leechers' ]),
                                          sorted( sortdict ) ) ), 'utf-8' )
        iidx = raw_input( bs )
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
    parser.add_option('--name', dest='name', type=str, action='store',
                      help = 'Name of the movie file to get.')
    parser.add_option( '--email', dest='email', type=str, action='store',
                       help = 'Email of person who has access to the Plex server.' )
    parser.add_option('--filename', dest='filename', action='store', type=str,
                      help = 'If defined, put option into filename.')
    opts, args = parser.parse_args( )
    assert( opts.name is not None and opts.email is not None )
    get_tv_torrent_items( opts.email, opts.name, filename = opts.filename )

