import os, sys, signal, textwrap
from howdy import signal_handler
signal.signal( signal.SIGINT, signal_handler )
from os import get_terminal_size
from tabulate import tabulate
from argparse import ArgumentParser
#
from howdy.core import core, get_formatted_duration, get_formatted_size

def _print_summary( library_key, library_dict, token, fullURL ):
    data = core.get_library_stats( library_key, token, fullURL = fullURL )
    mediatype = data[ 'mediatype' ]
    title = data[ 'title' ]
    columns = min( 100, get_terminal_size( ).columns )
    if mediatype == 'movie':
        mystr = ' '.join([ '"%s" is a movie library.' % title,
                           'There are %d movies here.' % data[ 'num_movies' ],
                           'The total size of movie media is %s.' %
                           get_formatted_size( data[ 'totsize' ] ),
                           'The total duration of movie media is %s.' % 
                           get_formatted_duration( data[ 'totdur' ] ) ] )
    elif mediatype == 'show':
        mystr =' '.join([ '"%s" is a TV library.' % title,
                              'There are %d TV files in %d TV shows.' % (
                                  data[ 'num_tveps' ], data[ 'num_tvshows' ] ),
                              'The total size of TV media is %s.' %
                              get_formatted_size( data[ 'totsize' ] ),
                              'The total duration of TV shows is %s.' % 
                              get_formatted_duration( data[ 'totdur' ] ) ] )
    elif mediatype == 'artist':
        num_songs = data[ 'num_songs' ]
        num_artists = data[ 'num_artists' ]
        num_albums = data[ 'num_albums' ]
        totsize = data[ 'totsize' ]
        totdur = data[ 'totdur' ]
        mystr = ' '.join([ '"%s" is a music library.' % title,
                           'There are %d songs made by %d artists in %d albums.' %
                           ( num_songs, num_artists, num_albums ),
                           'The total size of music media is %s.' %
                           get_formatted_size( totsize ),
                           'The total duration of music media is %s.' %
                           get_formatted_duration( totdur ) ] )
    print( '\n%s\n' % '\n'.join( textwrap.fill( mystr, width = columns ).split('\n') ) )    

def main( ):
    parser = ArgumentParser( )
    parser.add_argument('--libraries', dest='do_libraries', action='store_true', default=False,
                        help = 'If chosen, just give the sorted names of all libraries in the Plex server.')
    parser.add_argument('--refresh', dest='do_refresh', action='store_true', default=False,
                        help = 'If chosen, refresh a chosen library in the Plex server. Must give a valid name for the library.')
    parser.add_argument('--summary', dest='do_summary', action='store_true', default=False,
                        help = 'If chosen, perform a summary of the chosen library in the Plex server. Must give a valid name for the library.')
    parser.add_argument('--library', dest='library', type=str, action='store',
                        help = 'Name of a (valid) library in the Plex server.')
    parser.add_argument('--servername', dest='servername', action='store', type = str,
                        help = 'Optional name of the server to check for.' )
    parser.add_argument('--servernames', dest='do_servernames', action='store_true', default=False,
                        help = 'If chosen, print out all the servers owned by the user.')
    parser.add_argument('--noverify', dest='do_verify', action='store_false', default = True,
                        help = 'Do not verify SSL transactions if chosen.' )
    args = parser.parse_args( )
    #
    ##
    _, token = core.checkServerCredentials( doLocal = False, verify = args.do_verify )
    #
    ## only one of possible actions
    assert( len( list( filter( lambda tok: tok is True, (
        args.do_libraries, args.do_refresh, args.do_summary, args.do_servernames ) ) ) ) == 1 ), \
        "error, must choose one of --libraries, --refresh, --summary, --servernames"
    
    #
    ## if list of servernames, --servernames
    if args.do_servernames:
        server_dicts = core.get_all_servers( token, verify = args.do_verify )
        if server_dicts is None:
            print( 'COULD FIND NO SERVERS ACCESIBLE TO USER.' )
            return
        server_formatted_data = list(
            map(lambda name:
                ( name, server_dicts[ name ][ 'owned' ],
                  server_dicts[ name ][ 'url' ] ), server_dicts ) )
        print( '\n%s\n' %
               tabulate( server_formatted_data, headers = [ 'Name', 'Is Owned', 'URL' ] ) )
        return

    #
    ## check that server name we choose is owned by us.
    server_dicts = core.get_all_servers( token, verify = args.do_verify )
    server_names_owned = sorted(
        set(filter(lambda name: server_dicts[ name ][ 'owned' ],
                   server_dicts ) ) )
    assert( len( server_names_owned ) > 0 ), "error, none of these Plex servers is owned by us."
    if args.servername is None:
        args.servername = max( server_names_owned )
    
    assert( args.servername in server_names_owned ), "error, server %s not in list of owned servers: %s." % (
        args.servername, server_names_owned )

    #
    ## get URL and token from server_dicts
    fullURL = server_dicts[ args.servername ][ 'url' ]
    token = server_dicts[ args.servername ][ 'access token' ]

    #
    ## if get list of libraries, --libraries
    if args.do_libraries:
        library_dict = core.get_libraries( token, fullURL = fullURL, do_full = True )
        print( '\nHere are the %d libraries in this Plex server: %s.' % (
            len( library_dict ), args.servername ) )
        libraries_library_dict = dict(map(lambda keynum: ( library_dict[ keynum ][ 0 ], library_dict[ keynum ][ 1 ] ),
                                          library_dict.keys( ) ) )        
        library_names = sorted( libraries_library_dict )
        libraries_formatted_data = list(
            map(lambda name: ( name, libraries_library_dict[ name ] ), library_names ) )
        print( '\n%s\n' %
               tabulate( libraries_formatted_data, headers = [ 'Name', 'Library Type' ] ) )
        return

    #
    ## now gone through here, must define a --library
    assert( args.library is not None ), "error, library must be defined."
    library_dict = core.get_libraries( token, fullURL = fullURL, do_full = True )
    library_names = sorted(map(lambda keynum: library_dict[ keynum ][ 0 ], library_dict.keys( ) ) )
    assert( args.library in library_names ), "error, library = %s not in %s." % (
        args.library, library_names )
    library_key = max(filter(lambda keynum: library_dict[ keynum ][ 0 ] == args.library, library_dict ) )

    #
    ## if summary is chosen, --summary
    if args.do_summary:
        _print_summary( library_key, library_dict, token, fullURL )
        return

    #
    ## otherwise refresh is chosen, --refresh
    if args.do_refresh:
        core.refresh_library( library_key, library_dict, fullURL = fullURL, token = token )
        print( 'refreshed library %s.' % args.library )
        return
