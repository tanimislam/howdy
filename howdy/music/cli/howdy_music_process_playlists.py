import os, sys, numpy, json, time, logging
import datetime, tempfile, shutil, pandas, tabulate
from itertools import chain
from pathos.multiprocessing import Pool, cpu_count
from pathos.threading import ThreadPool
from ffmpeg_normalize import FFmpegNormalize
from howdy.core import core
from plexapi.server import PlexServer
#
from argparse import ArgumentParser

def _process_media_file( media_file, outputfile ):
    time0 = time.perf_counter( )
    input_file = media_file.input_file
    media_file.ffmpeg_normalize.print_stats = True # allow to print stats
    media_file._first_pass( )
    stats_data = media_file.streams["audio"][0].get_stats( )
    if stats_data['ebu'] is None: return None # error state
    outputfile.write('took %0.3f seconds to process %s. EBU = %0.3f.\n' % (
        time.perf_counter( ) - time0, input_file, stats_data['ebu']['input_tp'] ) )
    return { 'input_file' : input_file,
            'input_tp' : stats_data['ebu']['input_tp'] }

def _add_media_file( norm, filename ):
    try:
        norm.add_media_file( filename, 'foo.wav' )
    except: pass

def _process_normalization_files( input_tup ):
    prefix_playlist_name, procno, input_files = input_tup
    if len( input_files ) == 0: return None
    dstring = datetime.datetime.now( ).date( ).strftime('%d%m%Y' )
    input_filename = '%s_playlist_%s.%d.txt' % (
        prefix_playlist_name, dstring, procno )
    time0 = time.perf_counter( )
    norm = FFmpegNormalize( dry_run = True )
    _ = list(map(lambda filename: _add_media_file( norm, filename ), input_files))
    #
    ## now go through each
    with open( input_filename, 'w' ) as outputfile:
        stats_data = list(filter(None, map(
            lambda media_file: _process_media_file( media_file, outputfile ),
            norm.media_files)))                                
        logging.warning('took %0.3f seconds to process %d / %d files in PROC %d.' % (
            time.perf_counter( ) - time0, len( stats_data ), len( input_files ), procno ) )
    try: os.remove( input_filename )
    except: pass
    return stats_data

def _get_playlists( ):
    #
    ## first get the playlist
    fullURL, token = core.checkServerCredentials( doLocal=True )
    plex = PlexServer( fullURL, token )
    playlists = plex.playlists( )
    if len( playlists ) == 0: return []
    def _get_playlist_info( playlist ):
        name = playlist.title
        num_items = len( playlist.items( ) )
        playlist_type = playlist.playlistType
        added_at = playlist.addedAt.date( )
        updated_at = playlist.updatedAt.date( )
        return {
            'name' : name,
            'number of items' : num_items,
            'type' : playlist_type,
            'added at' : added_at,
            'updated at' : updated_at }
    time0 = time.perf_counter( )    
    with Pool( processes = min( len( playlists ), cpu_count( ) ) ) as pool:
        list_of_playlists = sorted(pool.map( _get_playlist_info, playlists ),
                                   key = lambda entry: -entry[ 'number of items' ] )
        df_playlists = pandas.DataFrame({
            'name' : list(map(lambda entry: entry['name'], list_of_playlists ) ),
            'type' : list(map(lambda entry: entry['type'], list_of_playlists ) ),
            'number of items' : numpy.array( list(map(lambda entry: entry['number of items'], list_of_playlists ) ), dtype=int ),
            'created' : list(map(lambda entry: entry['added at'], list_of_playlists ) ),
            'updated' : list(map(lambda entry: entry['updated at'], list_of_playlists ) ) } )
        logging.warning( 'took %0.3f seconds to get info for %d playlists.' % (
            time.perf_counter( ) - time0, len( playlists ) ) )
        return df_playlists

def _print_playlists( df_playlists ):
    assert( df_playlists.shape[0] != 0 )
    headers = [ 'name', 'type', 'number of items', 'created', 'updated' ]
    def _get_data( rowno ):
        df_sub = df_playlists[ df_playlists.index == rowno ]
        return (
            max( df_sub.name ),
            max( df_sub.type ),
            max( df_sub['number of items' ] ),
            max( df_sub['created'] ).strftime( '%d %B %Y' ),
            max( df_sub['updated'] ).strftime( '%d %B %Y' ) )
    print( 'summary info for %d playlists.\n' % df_playlists.shape[ 0 ] )
    print( '%s\n' % tabulate.tabulate(
        list(map(_get_data, range( df_playlists.shape[ 0 ] ) ) ),
        headers = headers ) )


def _get_playlist_files( playlist_name ):
    #
    ## first get the playlist
    fullURL, token = core.checkServerCredentials( doLocal=True )
    plex = PlexServer( fullURL, token )
    playlist = max(filter(lambda playlist: playlist.title == playlist_name,
                          plex.playlists() ) )
    assert( playlist.playlistType == 'audio' )
    all_items = playlist.items( )
    #
    ## only those entries that are valid files
    playlist_files = list(filter( 
        os.path.isfile,
        map(lambda item: max(item._data.iter('Part')).attrib['file'], all_items)))
    return playlist_files

def _get_files_belowmin( json_file, min_peak_val = -1 ):
    try:
        data = json.load( open( json_file, 'r' ) )
        filenames_to_process = set(map(
            lambda entry: entry['input_file'],
            filter(lambda entry: entry['input_tp'] <= min_peak_val and
                   os.path.isfile( entry['input_file']), data ) ) )
        return sorted(filenames_to_process)
    except:
        return []

def _normalize_media_file( media_file, openfile ):
    time0 = time.perf_counter( )
    input_file = media_file.input_file
    output_file= media_file.output_file
    assert( os.path.isfile( input_file ) )
    #assert( os.path.basename( input_file ).endswith( '.m4a' ) )
    #assert( os.path.basename( output_file ).endswith( '.m4a' ) )
    try:
        media_file.run_normalization( )
        os.chmod( output_file, 0o644 )
        shutil.move( output_file, input_file )
        openfile.write('took %0.3f seconds to normalize %s.\n' % (
            time.perf_counter( ) - time0, input_file ) )
        return input_file
    except Exception as e:
        openfile.write('exception = %s, processing %s.\n' % ( e, input_file ) )
        return None

def _add_media_file_norm( norm, filename ):
    try:
        act_suffix = os.path.basename( filename ).split('.')[-1].strip( ).lower( )
        _, tmpfile = tempfile.mkstemp( suffix = '.%s' % act_suffix )
        try: os.remove( tmpfile )
        except: pass
        norm.add_media_file( filename, tmpfile )
        return ( filename, tmpfile )
    except Exception as e:
        print( e )
        return None
        
def _normalize_files( input_tuple ):
    prefix_playlist_name, procno, input_files = input_tuple
    if len( input_files ) == 0: return None
    dstring = datetime.datetime.now( ).date( ).strftime('%d%m%Y' )
    input_filename = '%s_normalize_%s.%d.txt' % (
        prefix_playlist_name, dstring, procno )
    time0 = time.perf_counter( )
    norm_aac = FFmpegNormalize( normalization_type="peak", target_level = 0.0,
                               extra_input_options = [ '-c:a', 'aac' ], video_disable = True,
                               audio_codec = 'aac' )
    
    norm_mp3 = FFmpegNormalize( normalization_type="peak", target_level = 0.0,
                               extra_input_options = [ '-c:a', 'mp3' ], video_disable = True,
                               audio_codec = 'mp3' )
    input_files_aac = list(filter(lambda fname: os.path.basename( fname ).endswith('.m4a'), input_files ) )
    input_files_mp3 = list(filter(lambda fname: os.path.basename( fname ).endswith('.mp3'), input_files ) )
    input_output_files = list(chain.from_iterable([
        list(filter(
            None, map(lambda filename: _add_media_file_norm(
                norm_aac, filename ), input_files_aac))),
        list(filter(
            None, map(lambda filename: _add_media_file_norm(
                norm_mp3, filename ), input_files_mp3))) ]))
    #
    ## now go through each
    with open( input_filename, 'w' ) as openfile:
        norm_data = list(chain.from_iterable([
            list(filter(None, map(
                lambda media_file: _normalize_media_file( media_file, openfile ),
                norm_aac.media_files))),
            list(filter(None, map(
                lambda media_file: _normalize_media_file( media_file, openfile ),
                norm_mp3.media_files))) ]) )
        logging.warning('took %0.3f seconds to normalize %d / %d files.' % (
            time.perf_counter( ) - time0, len( norm_data ), len( input_output_files ) ) )
    try: os.remove( input_filename )
    except: pass
    return norm_data

def main_actual( ):
    parser = ArgumentParser( )
    parser.add_argument( '-d', '--debug', dest='do_debug', action='store_true', default = False,
                        help = 'If chosen, then print out debug info.' )
    parser.add_argument( '-P', '--playlists', dest='do_playlists', action='store_true', default = False,
                        help = 'If chosen, then print out summary of all the playlists.' )
    parser.add_argument( '-D', '--dryrun', dest='do_dryrun', action='store_true', default = False,
                        help = 'If chosen, then just do dry run and no heavy processing.' )
    subparsers = parser.add_subparsers(
        help = ' '.join([
            'Choose one of two options: (json) or (norm)' ]), dest = 'choose_option' )
    #
    ## dump out as JSON a chosen playlist
    parser_json = subparsers.add_parser( 'json', help = 'If chosen, dumps out info for the chosen AUDIO playlist into a JSON file. MAY TAKE A LONG TIME!' )
    parser_json.add_argument( '-p', '--playlist', dest='json_playlist', metavar = 'playlist', action='store', type=str, required = True,
                        help = 'Name of the playlist to summarize or normalize. Must be of type AUDIO.' )
    #
    ## normalizes files in the JSON playlist
    parser_norm = subparsers.add_parser( 'norm', help = 'If chosen, normalizes the audio in the chosen AUDIO playlist JSON file whose peak loudness is below some threshold. MAY TAKE A LONG TIME!' )
    parser_norm.add_argument('-j', '--json', dest='norm_jsonfile', action='store', metavar = 'jsonfile', type=str, required = True,
                             help = 'Name of the input JSON file that contains the song filenames, and the input peak loudness (in dB).' )
    parser_norm.add_argument('-p', '--peak', dest='norm_peakloud', action='store', metavar = 'peak', type=float, default = -1,
                             help = 'Peak loudness value of song for processing. If peak loudness is less than this value, perform normalization.' )
    #
    ##
    args = parser.parse_args( )
    logger = logging.getLogger( )
    logger.setLevel( logging.ERROR )
    if args.do_debug: logger.setLevel( logging.WARNING )
    #
    ## if just get the playlists
    if args.do_playlists:
        _print_playlists( _get_playlists( ) )
        return
    #
    ## choose_option must be one of "json" or "norm", and playlist must NOT be none
    assert( args.choose_option.lower( ) in ( 'json', 'norm' ) )
    if args.choose_option.lower( ) == 'json':
        main_json( args.json_playlist, do_dryrun = args.do_dryrun )
        return
    if args.choose_option.lower( ) == 'norm':
        main_norm( args.norm_jsonfile, args.norm_peakloud, do_dryrun = args.do_dryrun )
        return
    
def main_json( playlist_name, do_dryrun = False ):
    #
    ## only those entries that are valid files
    time0 = time.perf_counter( )
    playlist_files = _get_playlist_files( playlist_name )
    logging.warning("We process %d files from AUDIO playlist %s." % (
        len( playlist_files ), playlist_name ) )
    if do_dryrun: return
    #
    ## now run ffmpeg-normalize in parallel
    prefix_playlist_name = '_'.join( playlist_name.split( ) ).strip( )
    prefix_playlist_name = prefix_playlist_name.lower( )
    num_procs = cpu_count( )
    chunked_files = list(filter(lambda tup: len(tup[2]) != 0,
                                map(lambda idx: (prefix_playlist_name, idx, playlist_files[idx::num_procs]),
                                    range(num_procs))))
    with ThreadPool( processes = len( chunked_files )) as pool:
        all_stats_data = list(filter(
            None, chain.from_iterable( pool.map( _process_normalization_files, chunked_files))))
        all_stats_data_dict = dict(map(lambda entry: ( entry['input_file'], entry ), all_stats_data))
        all_stats_data_ordered = list(map(lambda filename: all_stats_data_dict[ filename ],
                                          filter(lambda filename: filename in all_stats_data_dict, playlist_files)))
        logging.warning('took %0.3f seconds to process %d files.' % (
            time.perf_counter( ) - time0, len( all_stats_data_dict ) ) )
        dstring = datetime.datetime.now( ).date( ).strftime('%d%m%Y' )
        json.dump(
            all_stats_data_ordered,
            open( '%s_playlist_%s.json' % ( prefix_playlist_name, dstring ), 'w' ), indent = 1 )

def main_norm( jsonfile, peakloud, do_dryrun = False ):
    assert( peakloud <= 0 )
    assert( os.path.isfile( jsonfile ) )
    assert( os.path.basename( jsonfile ).endswith('.json'))
    #
    ## now get files
    time0 = time.perf_counter( )
    allfiles = json.load( open( jsonfile, 'r' ) )
    filenames_belowmin = _get_files_belowmin( jsonfile, peakloud )
    logging.warning( 'found %d / %d files with peak loudness at or below %0.1f dB.' % (
        len( filenames_belowmin ), len( allfiles ), peakloud ) )
    if do_dryrun: return
    #
    ## now run ffmpeg-normalize in parallel
    prefix_playlist_name = '_'.join( os.path.basename( jsonfile ).split( '_' )[:-1] )
    prefix_playlist_name = prefix_playlist_name.lower( )
    num_procs = cpu_count( )
    chunked_files = list(filter(lambda tup: len(tup[2]) != 0,
                                map(lambda idx: (prefix_playlist_name, idx, filenames_belowmin[idx::num_procs]),
                                    range(num_procs))))
    with ThreadPool( processes = len( chunked_files )) as pool:
        all_norm_data = list(filter(
            None, chain.from_iterable( pool.map( _normalize_files, chunked_files))))
        all_norm_data_set = set( all_norm_data )
        logging.warning('took %0.3f seconds to normalize %d / %d files.' % (
            time.perf_counter( ) - time0, len( all_norm_data_set ), len( filenames_belowmin ) ) )
