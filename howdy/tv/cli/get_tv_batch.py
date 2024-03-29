import sys, signal
from howdy import signal_handler
signal.signal( signal.SIGINT, signal_handler )
import os, numpy, glob, time, datetime, warnings
import multiprocessing, logging
from argparse import ArgumentParser
#
from howdy.core import core
from howdy.tv import tv, get_token
#
## now remove the XMLParsedAsHTMLWarning warning. GUARD CODE UNTIL SINGLETON-IZED SOLUTION!
from bs4 import XMLParsedAsHTMLWarning
warnings.filterwarnings('ignore', category = XMLParsedAsHTMLWarning )

def finish_statement( step ):
    return '%d, finished on %s.' % ( step + 1, datetime.datetime.now( ).strftime(
        '%B %d, %Y @ %I:%M:%S %p' ) )

_debug_level_dict = {
    'info'  : logging.INFO,
    'debug' : logging.DEBUG, }

def main( ):
    time0 = time.perf_counter( )
    default_time = 1000
    default_iters = 2
    default_num_threads = 2 * multiprocessing.cpu_count( )
    #
    parser = ArgumentParser( )
    parser.add_argument(
        '--maxtime', dest='maxtime_in_secs', type=int, action='store', default = default_time,
        help = ' '.join([
            'The maximum amount of time to spend (in seconds),',
            'per candidate magnet link,',
            'trying to download a TV show.',
            'Default is %d seconds.' % default_time ] ) )
    parser.add_argument(
        '--num', dest='num_iters', type=int, action='store', default = default_iters,
        help = ' '.join([ 
            'The maximum number of different magnet links to try',
            'before giving up. Default is %d.' % default_iters ]) )
    parser.add_argument(
        '--token', dest='token', type=str, action='store',
        help = 'Optional argument. If chosen, user provided Plex access token.')
    parser.add_argument(
        '-D', '--debuglevel', dest='debug_level', action='store', type=str, default = 'None',
        choices = [ 'None', 'info', 'debug' ], help = 'Choose the debug level for the system logger. Default is None (no logging). Can be one of None (no logging), info, or debug.' )
    parser.add_argument(
        '--numthreads', dest='numthreads', type=int, action='store', default = default_num_threads,
        help = 'Number of threads over which to search for TV shows in my library. Default is %d.' %
        default_num_threads )
    parser.add_argument(
        '--nomax', dest='do_restrict_maxsize', action='store_false', default=True,
        help = 'If chosen, do not restrict maximum size of downloaded file.' )
    parser.add_argument(
        '--nomin', dest='do_restrict_minsize', action='store_false', default=True,
        help = 'If chosen, do not restrict minimum size of downloaded file.' )
    parser.add_argument(
        '-r', '--raw', dest='do_raw', action='store_true', default = False,
        help = 'If chosen, then use the raw string to specify TV show torrents.' )
    #
    ##
    parser.add_argument(
        '-R', '--remote', dest = 'do_local', action = 'store_false', default = True,
        help = 'If chosen, then use a REMOTE Plex server location.' )
    parser.add_argument(
        '-M', '--mainPath', dest = 'mainPath', type = str, action = 'store', default = None,
        help = 'Optional argument fix, sometimes needed to add proper prefix path to files in Plex_ tv libraries. Otherwise do not add.' )
    parser.add_argument(
        '-L', '--localRSYNC', dest = 'do_local_rsync', action = 'store_true', default = False,
        help = 'Optional argument. If chosen, then do move command from local server where episodes downloaded instead of rsync ssh from remote server.' )
    #
    ## now filter on these items
    parser.add_argument('-F', '--filter', dest = 'filter', action = 'store', nargs = '*',
                        help = 'List of strings on which to filter for the magnet link name.' )
    args = parser.parse_args( )
    #
    logger = logging.getLogger( )
    if args.debug_level.lower( ) in _debug_level_dict:
        logger.setLevel( _debug_level_dict[ args.debug_level.lower( ) ] )
    assert( args.maxtime_in_secs >= 60 ), 'error, max time must be >= 60 seconds.'
    assert( args.num_iters >= 1 ), 'error, must have a positive number of maximum iterations.'
    step = 0
    print( '%d, started on %s' % ( step, datetime.datetime.now( ).strftime( '%B %d, %Y @ %I:%M:%S %p' ) ) )
    step += 1
    #
    ## get plex server token
    dat = core.checkServerCredentials( doLocal = args.do_local )
    if dat is None:
        print('\n'.join([
            '%d, error, could not access local Plex server in %0.3f seconds. Exiting...' % (
                step, time.perf_counter( ) - time0 ),
            finish_statement( step )  ] ) )
        return
    fullURL, token = dat
    if args.token is not None: token = args.token
    #
    ## first find out which libraries are the TV show ones
    library_dict = core.get_libraries( token,
        fullURL = fullURL, do_full = True )
    if library_dict is None:
        print('\n'.join([
            '%d, error, could not access libraries in plex server in %0.3f seconds. Exiting...' % (
                step, time.perf_counter( ) - time0 ), finish_statement( step ) ]))
        return
    #
    valid_keys = list(filter(lambda key: library_dict[ key ][ -1 ] ==
                             'show', library_dict ) )
    if len( valid_keys ) == 0:
        print('\n'.join([
            '%d, Error, could not find a TV show library in %0.3f seconds. Exiting...' %
            ( time.perf_counter( ) - time0, step ), finish_statement( step ) ]))
        return
    tvlib_title = library_dict[ max( valid_keys ) ][ 0 ]
    print( '%d, found TV library: %s.' % ( step, tvlib_title ) )
    step += 1
    #
    ## now get the TV shows
    time0 = time.perf_counter( )
    tvdata = core.get_library_data(
        tvlib_title, token = token, fullURL = fullURL, num_threads = args.numthreads,
        mainPath = args.mainPath )
    print( '%d, found %d shows in the TV library, in %0.3f seconds.' % (
        step, len( tvdata ), time.perf_counter( ) - time0 ) )
    step += 1
    showsToExclude = tv.get_shows_to_exclude( tvdata )
    if len( showsToExclude ) != 0:
        print( '%d, excluding these TV shows: %s.' % (
            step, '; '.join( showsToExclude ) ) )
        step += 1
    tvdb_token = get_token( )
    if tvdb_token is None:
        print( '\n'.join([
            '%d, error, could not access the TVDB API server in %0.3f seconds. Exiting...' % (
                step, time.perf_counter( ) - time0 ) ] ) )
        return
    toGet = tv.get_remaining_episodes(
        tvdata, showSpecials = False,
        showsToExclude = showsToExclude,
        num_threads = args.numthreads )
    if len( toGet ) == 0:
        print('\n'.join([
            '%d, no episodes to download in %0.3f seconds. Exiting...' % (
                step, time.perf_counter( ) - time0 ), finish_statement( step ) ]))
        return
    print( '%d, took %0.3f seconds to get list of %d episodes to download.' % (
        step, time.perf_counter( ) - time0, sum(
            map(lambda tvshow: len(toGet[tvshow]['episodes']), toGet ) ) ) )
    step += 1
    #
    ## now download these episodes
    must_have = set([])
    if args.filter is not None:
        must_have = set(
            filter(lambda tok: len( tok ) > 0, map(lambda tok: tok.strip( ).lower( ), args.filter ) ) )
    logging.info( 'must_have = %s.' % must_have )
    tvTorUnits, newdirs = tv.create_tvTorUnits(
        toGet, restrictMaxSize = args.do_restrict_maxsize,
        restrictMinSize = args.do_restrict_minsize, do_raw = args.do_raw, must_have = must_have )
    print('%d, here are the %d episodes to get: %s.' % ( step,
        len( tvTorUnits ), ', '.join(map(lambda tvTorUnit: tvTorUnit[ 'torFname_disp' ], tvTorUnits))))
    step += 1
    tv.download_batched_tvtorrent_shows(
        tvTorUnits, newdirs = newdirs, maxtime_in_secs = args.maxtime_in_secs,
        num_iters = args.num_iters, do_local_rsync = args.do_local_rsync )
    print( '\n'.join([ '%d, everything done in %0.3f seconds.' % ( step, time.perf_counter( ) - time0 ),
                       finish_statement( step ) ]))
