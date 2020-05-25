import os, sys, tabulate, signal
from plexstuff import signal_handler
signal.signal( signal.SIGINT, signal_handler )
#
from plexstuff.plextvdb import plextvdb
from plexstuff.plexcore import plexcore, return_error_raw
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
            all_libraries = plexcore.get_libraries( token = token, fullURL = fullURL, do_full = True )
        except: return return_error_raw( "Error, bad token or URL may have been given." )
        key_found = list(filter(lambda key: all_libraries[ key ][ 0 ] == tvlibraryname, all_libraries))
        if key_found is None: return return_error_raw("Error, %s library does not exist." % tvlibraryname )
        key_found = min( key_found )
        if all_libraries[ key_found ][ 1 ] != 'show':
            return return_error_raw( "Error, %s library is not a TV library." % tvlibraryname )
    #
    ## now get data
    tvdata = plexcore.get_library_data( tvlibraryname, token = token, fullURL = fullURL )
    return tvdata, 'SUCCESS'

def show_excluded_shows( tvdata ):
    return plextvdb.get_shows_to_exclude( tvdata = tvdata )

def set_excluded_shows( tvdata, shows_to_exclude ):
    shows_act = set( shows_to_exclude ) & set( tvdata )
    if len( shows_act ) == 0:
        return return_error_raw( "Error, the set of TV shows, %s, is not in any of %d TV shows in Plex library." % ( sorted( shows_act ), len( set( tvdata ) ) ) )
    #
    ##
    plextvdb.push_shows_to_exclude( tvdata, shows_act )

def get_default_tvlibrary( fullURL, token ):
    try:
        all_libraries = plexcore.get_libraries( token = token, fullURL = fullURL, do_full = True )
    except: return return_error_raw( "Error, bad token or URL may have been given." )
    key_found = list(filter(lambda key: all_libraries[ key ][ 1 ] == 'show', all_libraries ) )
    if key_found is None: return_error_raw( "Error, could not find any TV libraries." )
    key_found = min( key_found )
    return all_libraries[ key_found ][ 0 ], 'SUCCESS'

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
    subparser = parser.add_subparsers( help = 'Either show or exclude shows.', dest = 'choose_option' )
    #
    ##
    parser_show = subparser.add_parser( 'show', help = 'Show those TV shows that have been excluded.' )
    #
    ##
    parser_exclude = subparser.add_parser( 'exclude', help = 'Exclude a new list of TV shows.' )
    parser_exclude.add_argument( 'tvshow', metavar='tvshow', type=str, action='store', nargs='*',
                                help = 'Set of TV shows to exclude from update.' )
    #
    ##
    args = parser.parse_args( )
    #
    ## first get token and URL for Plex server
    dat = plexcore.checkServerCredentials( doLocal = args.do_local, verify = args.do_verify )
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
        if '*' in set( args.tvshow ):
            print( "Error, cannot exclude ALL shows." )
            return                  
        excluded_shows = set( args.tvshow ) & set( tvdata )
        if len( excluded_shows ) == 0:
            print( "Found NO shows to exclude that are in the Plex TV library." )
            return
        original_excluded_shows = show_excluded_shows( tvdata )
        if set( original_excluded_shows ) == excluded_shows:
            print( "No change in collection of excluded shows." )
            return
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
        return
                                                                               
            
