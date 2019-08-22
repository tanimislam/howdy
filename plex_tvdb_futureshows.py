#!/usr/bin/env python3

import signal, sys
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import datetime, time, logging, os, tabulate
from plexcore import plexcore
from plextvdb import plextvdb
from optparse import OptionParser

def main( ):
    time0 = time.time( )
    parser = OptionParser( )
    parser.add_option('--noverify', dest='do_verify', action='store_false', default = True,
                      help = 'If chosen, do not verify the SSL connection.')
    parser.add_option('--local', dest='do_local', action='store_true',
                      default = False, help = 'Check for locally running plex server.')
    parser.add_option('--info', dest='do_info', action='store_true',
                      default = False, help = 'If chosen, run with INFO logging mode.' )
    opts, args = parser.parse_args( )
    logger = logging.getLogger( )
    if opts.do_info: logger.setLevel( logging.INFO )

    #
    ## function to do the processing

    step = 0
    print( '%d, started on %s' % ( step, datetime.datetime.now( ).strftime(
        '%B %d, %Y @ %I:%M:%S %p' ) ) )

    #
    ## get plex server token
    dat = plexcore.checkServerCredentials( doLocal = True )
    if dat is None:
        step += 1
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
        step += 1
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
        step += 1
        print('\n'.join([
            '%d, Error, could not find a TV show library in %0.3f seconds. Exiting...' %
            ( time.time( ) - time0, step ),
            '%d, finished on %s.' % ( step + 1, datetime.datetime.now( ).strftime(
                '%B %d, %Y @ %I:%M:%S %p' ) ) ] ) )
        return
    tvlib_title = library_dict[ max( valid_keys ) ][ 0 ]
    step += 1
    nowdate = datetime.datetime.now( ).date( )
    print( '%d, found TV library: %s.' % (
        step, tvlib_title ) )
    #
    ## now get the future TV shows
    tvdata = plexcore.get_library_data(
        tvlib_title, token = token, fullURL = fullURL )
    showsToExclude = plextvdb.get_shows_to_exclude( tvdata )
    if len( showsToExclude ) != 0:
        step += 1
        print( '%d, excluding these TV shows: %s.' % (
            step, '; '.join( showsToExclude ) ) )

    future_shows_dict = plextvdb.get_future_info_shows(
        tvdata, verify = opts.do_verify, showsToExclude = showsToExclude,
        fromDate = nowdate )
    for show in future_shows_dict:
        tdelta = future_shows_dict[ show ][ 'start_date' ] - nowdate
        future_shows_dict[ show ][ 'days_to_new_season' ] = tdelta.days

    if len( future_shows_dict ) == 0:
        step += 1
        print( '%d, found no TV shows with new seasons.' % step )
        print( '%d,  finished on %s.' % ( step + 1, datetime.datetime.now( ).strftime(
                '%B %d, %Y @ %I:%M:%S %p' ) ) )
        return
    step += 1
    print( '%d, Found %d TV shows with new seasons after %s, in %0.3f seconds.' % (
        step, len( future_shows_dict ), nowdate.strftime( '%B %d, %Y' ), time.time( ) - time0 ) )
    print( '\n' )
    all_new_show_data = list(
        map(lambda show: ( show, future_shows_dict[ show ][ 'max_last_season' ], future_shows_dict[ show ][ 'min_next_season' ],
                           future_shows_dict[ show ][ 'start_date' ].strftime( '%B %d, %Y' ),
                           future_shows_dict[ show ][ 'days_to_new_season' ] ),
            sorted(future_shows_dict, key = lambda shw: ( future_shows_dict[ shw ][ 'start_date' ], shw ) ) ) )
    print( '%s\n' % tabulate.tabulate( all_new_show_data, headers = [
        'SHOW', 'LAST SEASON', 'NEXT SEASON', 'AIR DATE', 'DAYS TO NEW SEASON' ] ) )

    step += 1
    print( '\n'.join([
        '%d, processed everything in %0.3f seconds.' % (
            step, time.time( ) - time0 ),
        '%d, finished everything on %s.' % (
            step + 1, datetime.datetime.now( ).strftime(
                '%B %d, %Y @ %I:%M:%S %p' ) ) ] ) )

if __name__=='__main__':
    main( )
