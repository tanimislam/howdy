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

def _cleanup_excluded_tracker( excl_tracker ):
    return excl_tracker.strip( ).lower( )

def show_excluded_trackers( ):
    return core_torrents.get_trackers_to_exclude( )

def add_excluded_trackers( trackers_to_exclude ):
    trackers_excl = set(map(_cleanup_excluded_tracker, trackers_to_exclude ) ) - set( show_excluded_trackers( ) )
    if len( trackers_excl ) == 0:
        print( "All torrent trackers are already in the exclude set." )
        return
    #
    ##
    print( 'adding these %d tracker stubs to exclude: %s.' % (
        len( trackers_excl ), ', '.join(sorted(trackers_excl))))
    status = try_continue( )
    if status:
        core_torrents.push_trackers_to_exclude( trackers_to_exclude )
        print( 'EXCLUDED TRACKER STUBS ADDED' )

def remove_excluded_trackers( trackers_to_remove ):
    trackers_remove = set(map(_cleanup_excluded_tracker, trackers_to_remove ) ) & set( show_excluded_trackers( ) )
    if len( trackers_remove ) == 0:
        print(  "No selected torrent trackers for removal." )
        return
    print( 'Removing these %d torrent tracker stubs to remove: %s' % (
        len( trackers_remove ), ', '.join( sorted( trackers_remove ) ) ) )
    status = try_continue( )
    if status:
        core_torrents.remove_trackers_to_exclude( trackers_remove )
        print( 'EXCLUDED TRACKER STUBS REMOVED' )

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
    parser_add.add_argument( 'add_tracker', metavar = 'tracker', type=str, action='store', nargs = '+',
                            help = 'Set of torrent trackers to add, to excluded set.' )
    #
    ##
    parser_remove = subparser.add_parser( 'remove', help = 'Remove a set of torrent trackers from the current exclude set.' )
    parser_remove.add_argument( 'remove_tracker', metavar = 'tracker', type=str, action='store', nargs = '+',
                               help = 'Set of torrent trackers to remove, from excluded set.' )
    #
    ##
    args = parser.parse_args( )
    #
    ## if showing excluded shows
    if args.choose_option == 'show':
        excluded_trackers = set( show_excluded_trackers( ) )
        print( 'found %d excluded torrent trackers.\n' % len( excluded_trackers ) )
        print( '%s\n' % tabulate.tabulate( map(lambda tok: [ tok ], sorted( excluded_trackers ) ), headers = [ 'TRACKER STUB' ] ) )
        return
    if args.choose_option == 'add':
        add_excluded_trackers( args.add_tracker )
        excluded_trackers = set( show_excluded_trackers( ) )
        print( 'found %d excluded torrent trackers.\n' % len( excluded_trackers ) )
        print( '%s\n' % tabulate.tabulate( map(lambda tok: [ tok ], sorted( excluded_trackers ) ), headers = [ 'TRACKER STUB' ] ) )
        return
    if args.choose_option == 'remove':
        remove_excluded_trackers( args.remove_tracker )
        excluded_trackers = set( show_excluded_trackers( ) )
        print( 'found %d excluded torrent trackers.\n' % len( excluded_trackers ) )
        print( '%s\n' % tabulate.tabulate( map(lambda tok: [ tok ], sorted( excluded_trackers ) ), headers = [ 'TRACKER STUB' ] ) )
        return
        
        
