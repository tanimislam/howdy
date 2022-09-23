import os, sys, tabulate, signal
from howdy import signal_handler
signal.signal( signal.SIGINT, signal_handler )
#
from howdy.core import core, core_torrents, return_error_raw
from itertools import chain
from argparse import ArgumentParser

def try_continue( ):
    val = str(input( 'PERFORM OPERATION (must choose one) [y/n]:')).lower( )
    val_map = { 'y' : True, 'n' : False }
    if val not in ( 'y', 'n' ):
        print( "chosen value not one of 'y' or 'n'. Default chosen is 'n'." )
        return False
    return val_map[ val ]

def show_excluded_trackers( ):
    return core_torrents.get_trackers_to_exclude( )

def set_excluded_shows( tvdata, shows_to_exclude ):
    shows_act = set( shows_to_exclude ) & set( tvdata )
    if len( shows_act ) == 0:
        return return_error_raw( "Error, the set of TV shows, %s, is not in any of %d TV shows in Plex library." % ( sorted( shows_act ), len( set( tvdata ) ) ) )
    #
    ##
    tv.push_shows_to_exclude( tvdata, shows_act )

def process_excluded_shows( tvdata,
    original_excluded_shows, excluded_shows ):
    print( 'Originally %d shows to exclude. Now %d shows to exclude.\n' % (
        len( original_excluded_shows ), len( excluded_shows ) ) )
    maxlen = max( len( excluded_shows ), len( original_excluded_shows ) )
    print_exclude_shows = list( chain.from_iterable([
        sorted( excluded_shows ), [''] * ( maxlen - len( excluded_shows ) ) ] ) )
    print_orig_excluded = list( chain.from_iterable([
        sorted( original_excluded_shows ), [''] * ( maxlen - len( original_excluded_shows ) ) ]) )
    print( '%s\n' % tabulate.tabulate(
        list(zip( print_orig_excluded, print_exclude_shows ) ), headers = [ 'ORIGINAL', 'NEW' ] ) )
    status = try_continue( )
    if status:
        set_excluded_shows( tvdata, excluded_shows )
        print( 'EXCLUDED SHOWS CHANGED' )

def main( ):
    parser = ArgumentParser( )
    #
    ##
    subparser = parser.add_subparsers( help = 'Either show, exclude, add, or remove torrent trackers.', dest = 'choose_option' )
    #
    ##
    parser_show = subparser.add_parser( 'show', help = 'Show those torrent trackers that have been excluded.' )
    #
    ##
    parser_add = subparser.add_parser( 'add', help = 'Add a new set of torrent trackers to the current exclude set.' )
    parser_add.add_argument( 'add_tracker', metavar = 'tracker', type=str, action='store', nargs = '*',
                            help = 'Set of torrent trackers to add, to excluded set.' )
    #
    ##
    parser_remove = subparser.add_parser( 'remove', help = 'Remove a set of torrent trackers from the current exclude set.' )
    parser_remove.add_argument( 'remove_tracker', metavar = 'tracker', type=str, action='store', nargs = '*',
                               help = 'Set of torrent trackers to remove, from excluded set.' )
    #
    ##
    args = parser.parse_args( )
    #
    ## if showing excluded shows
    excluded_trackers = set( show_excluded_trackers( ) )
    if args.choose_option == 'show':
        print( 'found %d excluded torrent trackers.\n' % (
            len( excluded_trackers ) ) )
        print( '%s\n' % tabulate.tabulate( map(lambda tok: [ tok ], sorted( excluded_trackers ) ), headers = [ 'TRACKER STUB' ] ) )
        return
    if args.choose_option == 'add':
        tracker_stubs = set(map(lambda tok: tok.strip( ).lower( ), args.add_tracker ) ) - excluded_trackers
        if len( tracker_stubs ) == 0:
            print( 'All torrent trackers are already in the exclude set.' )
            return
        if '*' in tracker_stubs:
            print( "Error, cannot exclude ALL torrent trackers." )
            return
        core_torrents.push_trackers_to_exclude( tracker_stubs )
        return
    if args.choose_option == 'remove':
        original_excluded_shows = set( show_excluded_shows( tvdata ) )
        removed_tvshows = set(map(lambda tok: tok.strip( ), args.remove_tvshow ) )
        if '*' in removed_tvshows:
            removed_tvshows = original_excluded_shows
        removed_tvshows = removed_tvshows & original_excluded_shows
        if len( removed_tvshows ) == 0:
            print( "Found NO shows to remove from exclusion list that are in the Plex TV library." )
            return
        excluded_shows = original_excluded_shows - removed_tvshows
        process_excluded_shows( tvdata, original_excluded_shows, excluded_shows )
        return
        
        
