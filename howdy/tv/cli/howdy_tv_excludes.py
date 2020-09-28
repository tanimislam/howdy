import os, sys, tabulate, signal
from howdy import signal_handler
signal.signal( signal.SIGINT, signal_handler )
#
from howdy.tv import tv
from howdy.core import core, return_error_raw
from itertools import chain
from argparse import ArgumentParser

def try_continue( ):
    val = str(input( 'PERFORM OPERATION (must choose one) [y/n]:')).lower( )
    val_map = { 'y' : True, 'n' : False }
    if val not in ( 'y', 'n' ):
        print( "chosen value not one of 'y' or 'n'. Default chosen is 'n'." )
        return False
    return val_map[ val ]

def get_tvdata( tvlibraryname, fullURL, token, doCheck = True ):
    if doCheck:
        try:
            all_libraries = core.get_libraries( token = token, fullURL = fullURL, do_full = True )
        except: return return_error_raw( "Error, bad token or URL may have been given." )
        key_found = list(filter(lambda key: all_libraries[ key ][ 0 ] == tvlibraryname, all_libraries))
        if key_found is None: return return_error_raw("Error, %s library does not exist." % tvlibraryname )
        key_found = min( key_found )
        if all_libraries[ key_found ][ 1 ] != 'show':
            return return_error_raw( "Error, %s library is not a TV library." % tvlibraryname )
    #
    ## now get data
    tvdata = core.get_library_data( tvlibraryname, token = token, fullURL = fullURL )
    return tvdata, 'SUCCESS'

def show_excluded_shows( tvdata ):
    return tv.get_shows_to_exclude( tvdata = tvdata )

def set_excluded_shows( tvdata, shows_to_exclude ):
    shows_act = set( shows_to_exclude ) & set( tvdata )
    if len( shows_act ) == 0:
        return return_error_raw( "Error, the set of TV shows, %s, is not in any of %d TV shows in Plex library." % ( sorted( shows_act ), len( set( tvdata ) ) ) )
    #
    ##
    tv.push_shows_to_exclude( tvdata, shows_act )

def get_default_tvlibrary( fullURL, token ):
    try:
        all_libraries = core.get_libraries( token = token, fullURL = fullURL, do_full = True )
    except: return return_error_raw( "Error, bad token or URL may have been given." )
    key_found = list(filter(lambda key: all_libraries[ key ][ 1 ] == 'show', all_libraries ) )
    if key_found is None: return_error_raw( "Error, could not find any TV libraries." )
    key_found = min( key_found )
    return all_libraries[ key_found ][ 0 ], 'SUCCESS'

def process_excluded_shows(
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
        print( 'NEW EXCLUDED SHOWS ADDED' )

def main( ):
    parser = ArgumentParser( )
    parser.add_argument( '--remote', dest='do_local', action = 'store_false', default = True,
                        help = 'If chosen, do not check localhost for running plex server.')
    parser.add_argument( '--noverify', dest='do_verify', action='store_false', default = True,
                        help = 'If chosen, do not verify SSL connections.' )
    parser.add_argument( '-L', '--library', dest='library', type=str, action='store',
                        help = 'If named, then choose this as the TV library through which to look. Otherwise, look for first TV library found on Plex server.' )
    #
    ##
    subparser = parser.add_subparsers( help = 'Either show, exclude, add, or remove shows.', dest = 'choose_option' )
    #
    ##
    parser_show = subparser.add_parser( 'show', help = 'Show those TV shows that have been excluded.' )
    #
    ##
    parser_exclude = subparser.add_parser( 'exclude', help = 'Exclude a new list of TV shows.' )
    parser_exclude.add_argument( 'exclude_tvshow', metavar='tvshow', type=str, action='store', nargs='*',
                                help = 'Set of TV shows to exclude from update.' )
    #
    ##
    parser_add = subparser.add_parser( 'add', help = 'Add a new list of TV shows to the current exclude list.' )
    parser.add.add_argument( 'add_tvshow', metavar = 'tvshow', type=str, action='store', nargs = '*',
                            help = 'Set of TV shows to add, to excluded list.' )
    #
    ##
    parser_remove = subparser.add_parser( 'remove', help = 'Remove a list of TV shows from the current exclude list.' )
    parser_remove.add_argument( 'remove_tvshow', metavar = 'tvshow', type=str, action='store', nargs = '*',
                               help = 'Set of TV shows to remove, to excluded list.' )
    #
    ##
    args = parser.parse_args( )
    #
    ## first get token and URL for Plex server
    dat = core.checkServerCredentials( doLocal = args.do_local, verify = args.do_verify )
    if dat is None:
        print( 'Error, could not find Plex server.' )
        return
    fullURL, token = dat
    #
    ## now use library
    if args.library is not None: tvlibrary = args.library
    else:
        tvlibrary, status = get_default_tvlibrary( fullURL, token )
        if status != 'SUCCESS':
            print( status )
            return
    #
    ## now get tvdata
    tvdata, status = get_tvdata( tvlibrary, fullURL, token, doCheck = False )
    if status != 'SUCCESS':
        print( status )
        return
    print( 'found %d TV shows in Plex server.' % ( len( set( tvdata ) ) ) )
    #
    ## if showing excluded shows
    if args.choose_option == 'show':
        excluded_shows = show_excluded_shows( tvdata )
        print( 'found %d / %d TV shows that are excluded from update.\n' % (
            len( excluded_shows ), len( set( tvdata ) ) ) )
        print( '%s\n' % tabulate.tabulate( map(lambda tok: [ tok ], sorted( set( excluded_shows ) ) ), headers = [ 'SHOW' ] ) )
        return
    if args.choose_option == 'exclude':
        exclude_tvshows = set(map(lambda tok: tok.strip( ), args.exclude_tvshow ) )
        if '*' in exclude_tvshows:
            print( "Error, cannot exclude ALL shows." )
            return                  
        excluded_shows = exclude_tvshows & set( tvdata )
        if len( excluded_shows ) == 0:
            print( "Found NO shows to exclude that are in the Plex TV library." )
            return
        original_excluded_shows = show_excluded_shows( tvdata )
        if set( original_excluded_shows ) == excluded_shows:
            print( "No change in collection of excluded shows." )
            return
        process_excluded_shows( original_excluded_shows, excluded_shows )
        return
    if args.choose_option == 'add':
        original_excluded_shows = set( show_excluded_shows( tvdata ) )
        added_tvshows = set(map(lambda tok: tok.strip( ), args.add_tvshow ) ) - original_excluded_shows
        if '*' in added_tvshows:
            print( "Error, cannot add ALL shows." )
            return
        added_shows = added_tvshows & set( tvdata )
        if len( added_shows ) == 0:
            print( "Found NO shows to add to exclusion list that are in the Plex TV library." )
            return
        excluded_shows = added_shows | original_excluded_shows
        process_excluded_shows( original_excluded_shows, excluded_shows )
        return
    if args.choose_option == 'remove':
        original_excluded_shows = set( show_excluded_shows( tvdata ) )
        removed_tvshows = set(map(lambda tok: tok.strip( ), args.add_tvshow ) )
        if '*' in removed_tvshows:
            removed_tvshows = original_excluded_shows
        removed_tvshows = removed_tvshows & original_excluded_shows
        if len( removed_tvshows ) == 0:
            print( "Found NO shows to remove from exclusion list that are in the Plex TV library." )
            return
        excluded_shows = original_excluded_shows - removed_tvshows
        process_excluded_shows( original_excluded_shows, excluded_shows )
        return
        
        
