#!/usr/bin/env python3

import signal, sys
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import datetime, time, logging, os
from multiprocessing import Manager
from pathos.multiprocessing import Pool, cpu_count
from plexcore import plexcore
from plextvdb import plextvdb
from optparse import OptionParser

def _print_years( len_years ):
    if len_years == 1:
        return '1 year'
    else: return '%d years' % len_years

def main( ):
    time0 = time.time( )
    parser = OptionParser( )
    parser.add_option( '--years', dest='s_years', action='store', type=str,
                       help = 'Give a list of years as a string, such as "1980,1981". Optional.' )
    parser.add_option('--noverify', dest='do_noverify', action='store_true', default = False,
                      help = 'If chosen, do not verify the SSL connection.')
    parser.add_option('--local', dest='do_local', action='store_true',
                      default = False, help = 'Check for locally running plex server.')
    parser.add_option('--dirname', dest='dirname', action='store', type=str, default = os.getcwd( ),
                      help = 'Directory into which to store those plots. Default is %s.' %
                      os.getcwd( ) )
    opts, args = parser.parse_args( )

    #
    ## function to do the processing
    
    step = 0
    print( '%d, started on %s' % ( step, datetime.datetime.now( ).strftime(
        '%B %d, %Y @ %I:%M:%S %p' ) ) )
    if opts.s_years is not None:
        try:
            years = sorted(set(map(lambda tok: int( tok ), opts.s_years.split(','))))
        except:
            step += 1
            print( '%d, did not give a valid set of years.' % step )
            years = [ ]
    else: years = [ ]
            
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
    print( '%d, found TV library: %s.' % ( step, tvlib_title ) )    
    #
    ## now get the TV shows
    tvdata = plexcore.get_library_data(
        tvlib_title, token = token,
        fullURL = fullURL, num_threads = 16 )
    showsToExclude = plextvdb.get_shows_to_exclude( tvdata )
    if len( showsToExclude ) != 0:
        step += 1
        print( '%d, excluding these TV shows: %s.' % (
            step, '; '.join( showsToExclude ) ) )
    
    #
    ## now actual meat of the computation
    tvdata_date_dict = plextvdb.get_tvdata_ordered_by_date( tvdata )
    min_year = min( tvdata_date_dict.keys( ) ).year
    max_year = max( tvdata_date_dict.keys( ) ).year
    possible_years_set = set(
        map(lambda date: date.year, tvdata_date_dict ) )
    step += 1
    if len( years ) == 0:
        years = sorted( possible_years_set )
        print( '%d, no years specified. We will use %s total: %s.' % (
            step, _print_years( len( years ) ),
            ', '.join(map(lambda year: '%d' % year, years ) ) ) )          
    else:
        cand_years = sorted( set( years ) & possible_years_set )
        if len( cand_years ) == 0:
            print( '\n'.join([
                '%d, no intersection between the %s chosen (%s) and the %d years in the library.' % (
                    step, _print_years( len( years ) ),
                    ', '.join(lambda yr: '%d' % year, years ),
                    len( possible_years_set ) ),
                'Instead, we will use %s total: %s.' % (
                    _print_years( len( possible_years_set ) ),
                    ', '.join(map(lambda year: '%d' % year,
                                  sorted( possible_years_set ) ) ) ) ] ) )
            years = sorted( possible_years_set )
        else:
            print( '%d, we found %s to use: %s.' % (
                step, _print_years( len( cand_years ) ),
                ', '.join(map(lambda year: '%d' % year, cand_years ) ) ) )
            years = cand_years

    step += 1
    print( '%d, started processing %s of TV shows after %0.3f seconds.' % (
        step, _print_years( len( years ) ), time.time( ) - time0 ) )
    manager = Manager( )
    shared_step = manager.Value( 'step', step )
    num_procced = manager.Value( 'nump', 0 )
    lock = manager.RLock( )
    pool = Pool( processes = cpu_count( ) )
    def _process_year( year ):
        plextvdb.create_plot_year_tvdata(
            tvdata_date_dict, year, shouldPlot = True,
            dirname = opts.dirname )
        lock.acquire( )
        shared_step.value += 1
        num_procced.value += 1
        print( '%d, finished processing year = %d (%02d / %02d) in %0.3f seconds.' % (
            shared_step.value, year, num_procced.value, len( years ),
            time.time( ) - time0 ) )
        lock.release( )

    _ = list( pool.map( _process_year, years ) )
    step = shared_step.value + 1
    print( '\n'.join([
        '%d, processed all %s in %0.3f seconds.' % (
            step, _print_years( len( years ) ),
            time.time( ) - time0 ),
        '%d, finished everything on %s.' % (
            step + 1, datetime.datetime.now( ).strftime(
                '%B %d, %Y @ %I:%M:%S %p' ) ) ] ) )

if __name__=='__main__':
    main( )
