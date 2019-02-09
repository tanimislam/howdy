#!/usr/bin/env python3

import re, codecs, requests, zipfile, os, sys, signal, logging, time
from plexcore import signal_handler, subscene
signal.signal( signal.SIGINT, signal_handler )
from io import BytesIO
from functools import reduce
from multiprocessing import Process, Manager, cpu_count
from optparse import OptionParser
from plextmdb import plextmdb_subtitles

def _process_items_list( items, shared_list ):
    if shared_list is None: return items
    shared_list.append( items )

def get_items_yts( name, maxnum = 10, shared_list = None ):
    assert( maxnum >= 5 )
    items = plextmdb_subtitles.get_subtitles_yts( name )
    if items is None:
        return _process_items_list( None, shared_list )
    return _process_items_list(
        list( map(lambda item: { 'title' : item['name'], 'zipurl' : item['url'],
                                 'content' : 'yts' }, items[:maxnum] ) ),
        shared_list )

def get_items_subscene( name, maxnum = 20, extra_strings = [ ], shared_list = None ):
    assert( maxnum >= 5 )
    subtitles_map = plextmdb_subtitles.get_subtitles_subscene( name, extra_strings = extra_strings )
    if subtitles_map is None:
        return _process_items_list( None, shared_list )
    return _process_items_list(
         list( map(lambda title: { 'title' : title, 'srtdata' : subtitles_map[ title ],
                                   'content' : 'subscene' },
                   sorted( subtitles_map )[:maxnum] ) ),
        shared_list )

def get_items_opensubtitles( name, maxnum = 20, extra_strings = [ ], shared_list = None ):
    assert( maxnum >= 5 )
    subtitles_map = plextmdb_subtitles.get_subtitles_opensubtitles( name, extra_strings = extra_strings )
    if subtitles_map is None:
        return _process_items_list( None, shared_list )
    return _process_items_list(
        list( map(lambda title: { 'title' : title,
                                  'srtdata' : subtitles_map[ title ],
                                  'content' : 'opensubtitles' },
                     sorted( subtitles_map )[:maxnum] ) ),
        shared_list )

def get_movie_subtitle_items( items, filename = 'eng.srt' ):
    if len( items ) == 0: return
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
        content = sortdict[ iidx ][ 'content' ]
        if content == 'yts': # yts
            zipurl = sortdict[ iidx ][ 'zipurl' ]
            with zipfile.ZipFile( BytesIO( requests.get( zipurl ).content ), 'r') as zf:
                with open( filename, 'wb' ) as openfile:
                    name = max( zf.namelist( ) )
                    openfile.write( zf.read( name ) )
        elif content == 'subscene': # subscene
            suburl = sortdict[ iidx ][ 'srtdata' ]
            zipcontent = subscene.get_subscene_zipped_content( suburl )
            with zipfile.ZipFile( BytesIO( zipcontent ), 'r') as zf:
                with open( filename, 'wb' ) as openfile:
                    name = max( zf.namelist( ) )
                    openfile.write( zf.read( name ) )
        elif content == 'opensubtitles': # opensubtitles
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
    parser.add_option('--debug', dest='do_debug', action='store_true', default = False,
                      help = 'If chosen, run in debug mode.' )
    opts, args = parser.parse_args( )
    assert( opts.name is not None )
    assert( os.path.basename( opts.filename ).endswith('.srt' ) )
    if opts.do_debug: logging.basicConfig( level = logging.INFO )
    keywords_set = { }
    if opts.keywords is not None:
        keywords_set = set(map(lambda tok: tok.lower( ), filter(lambda tok: len( tok.strip( ) ) != 0,
                                                                opts.keywords.strip().split(','))))
    #
    ## now calculation with multiprocessing
    time0 = time.time( )
    manager = Manager( )
    num_processes = cpu_count( )
    shared_list = manager.list( )
    if not opts.do_bypass: jobs = [
            Process( target=get_items_yts, args=(opts.name, opts.maxnum, shared_list ) ) ]
    else: jobs = [ ]
    jobs += [
        Process( target=get_items_subscene, args = ( opts.name, opts.maxnum, keywords_set, shared_list ) ),
        Process( target=get_items_opensubtitles, args = ( opts.name, opts.maxnum, keywords_set, shared_list ) ) ]
    for process in jobs: process.start( )
    for process in jobs: process.join( )
    try: items = reduce(lambda x,y: x+y, list( filter( None, shared_list ) ) )
    except: items = None
    logging.info( 'search for movie subtitles took %0.3f seconds.' % ( time.time( ) - time0 ) )    
    if items is not None: get_movie_subtitle_items( items, filename = opts.filename )
