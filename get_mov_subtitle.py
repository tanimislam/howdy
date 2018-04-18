#!/usr/bin/env python3

import re, codecs, requests, zipfile, os, sys
from io import BytesIO
from optparse import OptionParser
from plextmdb import plextmdb_subtitles

def get_items_yts( name, maxnum = 10 ):
    assert( maxnum >= 5 )
    items = plextmdb_subtitles.get_subtitles_yts( name )
    if items is None: return None
    return map(lambda item: { 'title' : item['name'],
                              'zipurl' : item['url'] }, items[:maxnum] ), -1

def get_items_subscene( name, maxnum = 10 ):
    assert( maxnum >= 5 )
    items = plextmdb_subtitles.get_subtitles_subscene( name )
    if items is None: return None
    return list( map(lambda item: { 'title' : item['name'],
                                    'srtdata' : item['srtdata'] },
                     items[ 'subtitles' ][:maxnum] ) ), 0

def get_items_subscene2( name, maxnum = 20, extra_strings = [ ] ):
    assert( maxnum >= 5 )
    subtitles_map = plextmdb_subtitles.get_subtitles_subscene2( name, extra_strings = extra_strings )
    if subtitles_map is None: return None
    return list( map(lambda title: { 'title' : title,
                                     'srtdata' : subtitles_map[ title ] },
                     sorted( subtitles_map )[:maxnum] ) ), 1

def get_items_opensubtitles( name, maxnum = 20, extra_strings = [ ] ):
    assert( maxnum >= 5 )
    subtitles_map = plextmdb_subtitles.get_subtitles_opensubtitles( name, extra_strings = extra_strings )
    if subtitles_map is None: return None
    return list( map(lambda title: { 'title' : title,
                                     'srtdata' : subtitles_map[ title ] },
                     sorted( subtitles_map )[:maxnum] ) ), 2

def get_movie_subtitle_items( items, status, filename = 'eng.srt' ):
    if len( items ) != 0:
        sortdict = { idx + 1 : item for ( idx, item ) in enumerate( items ) }
        bs = 'Choose movie subtitle:\n%s\n' % '\n'.join(
            map(lambda idx: '%d: %s' % ( idx, sortdict[ idx ][ 'title' ] ),
                sorted( sortdict ) ) )
        iidx = input( bs )
        try:
            iidx = int( iidx.strip( ) )
            if iidx not in sortdict:
                print('Error, need to choose one of the movie names. Exiting...')
                return
            if status == 0: # yts
                 zipurl = sortdict[ iidx ][ 'zipurl' ]
                 with zipfile.ZipFile( BytesIO( requests.get( zipurl ).content ), 'r') as zf:
                     with open( filename, 'wb' ) as openfile:
                         name = max( zf.namelist( ) )
                         openfile.write( zf.read( name ) )
            elif status == 1: # subscene2
                zipurl = sortdict[ iidx ][ 'srtdata' ].zipped_url
                with zipfile.ZipFile( BytesIO( requests.get( zipurl ).content ), 'r') as zf:
                    with open( filename, 'wb' ) as openfile:
                        name = max( zf.namelist( ) )
                        openfile.write( zf.read( name ) )
            elif status == 2: # opensubtitles
                zipurl = sortdict[ iidx ][ 'srtdata' ]
                with zipfile.ZipFile( BytesIO( requests.get( zipurl ).content ), 'r') as zf:
                    with open( filename, 'wb' ) as openfile:
                        name = max( filter(lambda nm: nm.endswith('.srt'), zf.namelist( ) ) )
                        openfile.write( zf.read( name ) )
        except Exception as e:
            print('Error, did not give a valid integer value. Exiting...')
            print(e)
            return

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('--name', dest='name', type=str, action='store',
                      help = 'Name of the movie file to get.')
    parser.add_option('--maxnum', dest='maxnum', type=int, action='store', default = 10,
                      help = 'Maximum number of torrents to look through. Default is 10.')
    parser.add_option('--filename', dest='filename', action='store', type=str, default = 'eng.srt',
                      help = 'Name of the subtitle file. Default is eng.srt.')
    parser.add_option('--bypass', dest='do_bypass', action='store_true', default = True,
                      help = 'If chosen, then bypass yts subtitles.')
    parser.add_option('--keywords', dest='keywords', action='store', type=str,
                      help = 'Optional definition of a list of keywords to look for, in the subscene search for movie subtitles.')
    opts, args = parser.parse_args( )
    assert( opts.name is not None )
    assert( os.path.basename( opts.filename ).endswith('.srt' ) )
    keywords_set = { }
    if opts.keywords is not None:
        keywords_set = set(map(lambda tok: tok.lower( ), filter(lambda tok: len( tok.strip( ) ) != 0,
                                                                opts.keywords.strip().split(','))))
    data = None
    if not opts.do_bypass:
        data = get_items_yts( opts.name, maxnum = opts.maxnum )
    if data is None:
        data = get_items_subscene2( opts.name, maxnum = opts.maxnum, extra_strings = keywords_set )
    if data is None:
        data = get_items_opensubtitles( opts.name, maxnum = opts.maxnum, extra_strings = keywords_set )        
    if data is not None:
        items, status = data
        get_movie_subtitle_items( items, status, filename = opts.filename )
