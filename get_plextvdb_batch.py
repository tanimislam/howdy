#!/usr/bin/env python3

import sys, signal
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import os, numpy, glob, time, datetime
import multiprocessing, logging
from plexcore import plexcore
from plextvdb import plextvdb
from optparse import OptionParser

def main( ):
    time0 = time.time( )
    default_time = 1000
    default_iters = 2
    
    parser = OptionParser( )
    parser.add_option('--maxtime', dest='maxtime_in_secs', type=int, action='store', default = default_time,
                      help = ' '.join([
                          'The maximum amount of time to spend (in seconds),',
                          'per candidate magnet link,',
                          'trying to download a TV show.',
                          'Default is %d seconds.' % default_time ] ) )
    parser.add_option('--num', dest='num_iters', type=int, action='store', default = default_iters,
                      help = ' '.join([ 
                          'The maximum number of different magnet links to try',
                          'before giving up. Default is %d.' % default_iters ]) )
    parser.add_option('--info', dest='do_info', action='store_true', default=False,
                      help = 'If chosen, then run in info mode.' )
    parser.add_option('--numthreads', dest='numthreads', type=int, action='store', default = multiprocessing.cpu_count( ) * 2,
                      help = 'Number of threads over which to search for TV shows in my library. Default is %d.' % (
                          2 * multiprocessing.cpu_count( ) ) )
    opts, args = parser.parse_args( )
    if opts.do_info: logging.basicConfig( level = logging.INFO )
    assert( opts.maxtime_in_secs >= 60 ), 'error, max time must be >= 60 seconds.'
    assert( opts.num_iters >= 1 ), 'error, must have a positive number of iterations.'
    step = 0
    print( '%d, started on %s' % ( step, datetime.datetime.now( ).strftime( '%B %d, %Y @ %I:%M:%S %p' ) ) )
    step += 1
    #
    ## get plex server token
    dat = plexcore.checkServerCredentials( doLocal = True )
    if dat is None:
        print('\n'.join([
            '%d, error, could not access local Plex server in %0.3f seconds. Exiting...' % (
                step, time.time( ) - time0 ),
            '%d, finished on %s.' % ( step + 1, datetime.datetime.now( ).strftime(
                '%B %d, %Y @ %I:%M:%S %p' ) ) ] ) )
        return
    fullURL, token = dat
    #
    ## first find out which libraries are the TV show ones
    library_dict = plexcore.get_libraries( fullURL = fullURL, token = token, do_full = True )
    if library_dict is None:
        print('\n'.join([
            '%d, error, could not access libraries in plex server in %0.3f seconds. Exiting...' % (
                step, time.time( ) - time0 ),
            '%d, finished on %s.' % ( step + 1, datetime.datetime.now( ).strftime(
                '%B %d, %Y @ %I:%M:%S %p' ) ) ] ) )
        return
    #
    valid_keys = list(filter(lambda key: library_dict[ key ][ -1 ] ==
                             'show', library_dict ) )
    if len( valid_keys ) == 0:
        print('\n'.join([
            '%d, Error, could not find a TV show library in %0.3f seconds. Exiting...' %
            ( time.time( ) - time0, step ),
            '%d, finished on %s.' % ( step + 1, datetime.datetime.now( ).strftime(
                '%B %d, %Y @ %I:%M:%S %p' ) ) ] ) )
        return
    tvlib_title = library_dict[ max( valid_keys ) ][ 0 ]
    print( '%d, found TV library: %s.' % ( step, tvlib_title ) )
    step += 1
    #
    ## now get the TV shows
    time0 = time.time( )
    tvdata = plexcore.get_library_data(
        tvlib_title, token = token, num_threads = opts.numthreads )
    showsToExclude = plextvdb.get_shows_to_exclude( tvdata )
    if len( showsToExclude ) != 0:
        print( '%d, excluding these TV shows: %s.' % (
            step, '; '.join( showsToExclude ) ) )
        step += 1
    toGet = plextvdb.get_remaining_episodes(
        tvdata, showSpecials = False,
        showsToExclude = showsToExclude,
        num_threads = opts.numthreads )
    if len( toGet ) == 0:
        print('\n'.join([
            '%d, no episodes to download in %0.3f seconds. Exiting...' % (
                step, time.time( ) - time0 ),
            '%d, finished on %s.' % ( step + 1, datetime.datetime.now( ).strftime(
                '%B %d, %Y @ %I:%M:%S %p' ) ) ] ) )        
        return
    print( '%d, took %0.3f seconds to get list of %d episodes to download.' % (
        step, time.time( ) - time0, sum(
            map(lambda tvshow: len(toGet[tvshow]['episodes']), toGet ) ) ) )
    step += 1
    #
    ## now download these episodes
    tvTorUnits, tv_torrent_gets = plextvdb.create_tvTorUnits( toGet )
    print('%d, here are the %d episodes to get: %s.' % ( step,
        len( tvTorUnits ), ', '.join(map(lambda tvTorUnit: tvTorUnit[ 'torFname' ], tvTorUnits))))
    step += 1
    plextvdb.download_batched_tvtorrent_shows(
        tv_torrent_gets, tvTorUnits, maxtime_in_secs = opts.maxtime_in_secs,
        num_iters = opts.num_iters )
    print( '\n'.join([ '%d, everything done in %0.3f seconds.' % ( step, time.time( ) - time0 ),
                       '%d, finished on %s.' % ( step + 1, datetime.datetime.now( ).strftime(
                           '%B %d, %Y @ %I:%M:%S %p' ) ) ] ) )
    
if __name__=='__main__':
    main( )
