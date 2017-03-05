#!/usr/bin/env python2

import re, codecs, requests, zipfile, os
from io import BytesIO
from optparse import OptionParser
from plextmdb import plextmdb_subtitles

def get_items_yts( name, maxnum = 10 ):
    assert( maxnum >= 5 )
    items = plextmdb_subtitles.get_subtitles_yts( name )
    if items is None: return None
    return map(lambda item: { 'title' : item['name'],
                              'zipurl' : item['url'] }, items[:maxnum] ), False

def get_items_subscene( name, maxnum = 10 ):
    assert( maxnum >= 5 )
    items = plextmdb_subtitles.get_subtitles_subscene( name )
    if items is None: return None
    return map(lambda item: { 'title' : item['name'],
                              'srtdata' : item['srtdata'] },
               items[ 'subtitles' ][:maxnum] ), True

def get_movie_subtitle_items( items, hasSubs = False, filename = 'eng.srt' ):
    if len( items ) != 1:
        sortdict = { idx + 1 : item for ( idx, item ) in enumerate( items ) }
        bs = codecs.encode( 'Choose movie subtitle:\n%s\n' %
                            '\n'.join(map(lambda idx: '%d: %s' % ( idx, sortdict[ idx ][ 'title' ] ),
                                          sorted( sortdict ) ) ), 'utf-8' )
        iidx = raw_input( bs )
        try:
            iidx = int( iidx.strip( ) )
            if iidx not in sortdict:
                print('Error, need to choose one of the movie names. Exiting...')
                return
            if hasSubs:
                with open( filename, 'wb' ) as openfile:
                    openfile.write('%s\n' % sortdict[ iidx ][ 'srtdata' ] )
            else:
                zipurl = sortdict[ iidx ][ 'zipurl' ]
                with zipfile.ZipFile( BytesIO( requests.get( zipurl ).content ), 'r') as zf:
                    with open( filename, 'wb' ) as openfile:
                        name = max( zf.namelist( ) )
                        openfile.write( zf.read( name ) )
        except Exception:
            print('Error, did not give a valid integer value. Exiting...')
            return

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('--name', dest='name', type=str, action='store',
                      help = 'Name of the movie file to get.')
    parser.add_option('--maxnum', dest='maxnum', type=int, action='store', default = 10,
                      help = 'Maximum number of torrents to look through. Default is 10.')
    parser.add_option('--filename', dest='filename', action='store', type=str, default = 'eng.srt',
                      help = 'Name of the subtitle file. Default is eng.srt.')
    opts, args = parser.parse_args( )
    assert( opts.name is not None )
    assert( os.path.basename( opts.filename ).endswith('.srt' ) )
    data = get_items_yts( opts.name, maxnum = opts.maxnum )
    if data is None:
        data = get_items_subscene( opts.name, maxnum = opts.maxnum )
    if data is not None:
        items, hasSubs = data
        get_movie_subtitle_items( items, hasSubs = False, filename = opts.filename )
