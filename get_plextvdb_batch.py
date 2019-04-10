#!/usr/bin/env python3

import sys, signal
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import os, numpy, glob, time, datetime
from functools import reduce
from plexcore import plexcore
from plextvdb import plextvdb
from optparse import OptionParser

def main( ):
    time0 = time.time( )
    parser = OptionParser( )
    parser.add_option('--maxtime', dest='maxtime_in_secs', type=int, action='store', default=120,
                      help = ' '.join([
                          'The maximum amount of time to spend (in seconds),',
                          'per candidate magnet link,',
                          'trying to download a TV show.',
                          'Default is 120 seconds.' ] ) )
    parser.add_option('--num', dest='num_iters', type=int, action='store', default=5,
                      help = ' '.join([ 
                          'The maximum number of different magnet links to try',
                          'before giving up. Default is 5.' ]) )
    opts, args = parser.parse_args( )
    assert( opts.maxtime_in_secs >= 60 ), 'error, max time must be >= 60 seconds.'
    assert( opts.num_iters >= 1 ), 'error, must have a positive number of iterations.'
    print( '0, started on %s' % datetime.datetime.now( ).strftime( '%B %d, %Y @ %I:%M:%S %p' ) ) 
    #
    ## get plex server token
    dat = plexcore.checkServerCredentials( doLocal = True )
    if dat is None:
        print('1, error, could not access local Plex server. Exiting...')
        return
    fullURL, token = dat
    #
    ## first find out which libraries are the TV show ones
    library_dict = plexcore.get_libraries( token = token, do_full = True )
    valid_keys = list(filter(lambda key: library_dict[ key ][ -1 ] ==
                             'show', library_dict ) )
    if len( valid_keys ) == 0:
        print('1, Error, could not find a TV show library. Exiting...')
        return
    tvlib_title = library_dict[ max( valid_keys ) ][ 0 ]
    print( '1, found TV library: %s' % tvlib_title )
    #
    ## now get the TV shows
    time0 = time.time( )
    toGet = plextvdb.get_remaining_episodes(
        plexcore.get_library_data( tvlib_title, token = token ),
        showSpecials = False,
        showsToExclude = [ 'The Great British Bake Off' ] )
    if len( toGet ) == 0:
        print('2, no episodes to download. Exiting...')
        return
    print( '2, took %0.3f seconds to get list of %d episodes to download.' % (
        time.time( ) - time0, sum(map(lambda tvshow: len(toGet[tvshow]['episodes']),
                                      toGet))))
    #
    ## now download these episodes
    tv_torrent_gets = plextvdb.get_tvtorrent_candidate_downloads( toGet )
    tvTorUnits = reduce(lambda x,y: x+y, [ tv_torrent_gets[ 'nonewdirs' ] ] +
                        list(map(lambda newdir: tv_torrent_gets[ 'newdirs' ][ newdir ],
                                tv_torrent_gets[ 'newdirs' ] ) ) )
    print('3, here are the %d episodes to get: %s' % (
        len( tvTorUnits ), ', '.join(map(lambda tvTorUnit: tvTorUnit[ 'torFname' ], tvTorUnits))))
    plextvdb.download_batched_tvtorrent_shows(
        tv_torrent_gets, maxtime_in_secs = opts.maxtime_in_secs,
        num_iters = opts.num_iters )
    print( '\n'.join([ '4, everything done in %0.3f seconds.' % ( time.time( ) - time0 ),
                       'finished on %s.' % datetime.datetime.now( ).strftime( '%B %d, %Y @ %I:%M:%S %p' ) ] ) )

if __name__=='__main__':
    main( )
