#!/usr/bin/env python3

from optparse import OptionParser
from plexcore import plexcore, get_formatted_duration, get_formatted_size

def _print_summary( library_key, library_dict, token = None, fullURL = 'http://localhost:32400' ):
    data = plexcore.get_library_stats( library_key, token = token, fullURL = fullURL )
    fullURL, title, mediatype = data[:3]
    if mediatype == 'movie':
        num_movies, totdur, totsize = data[3:]
        print( ' '.join([ '%s is a movie library.' % library_dict[ library_key ],
                          'There are %d movies here.' % num_movies,
                          'The total size of movie media is %s.' %
                          get_formatted_size( totsize ),
                          'The total duration of movie media is %s.' % 
                          get_formatted_duration( totdur ) ]) )
    elif mediatype == 'show':
        num_tveps, num_tvshows, totdur, totsize = data[3:]
        print( ' '.join([ '%s is a TV library.' % library_dict[ library_key ],
                          'There are %d TV files in %d TV shows.' % ( num_tveps, num_tvshows ),
                          'The total size of TV media is %s.' %
                          get_formatted_size( totsize ),
                          'The total duration of TV shows is %s.' % 
                          get_formatted_duration( totdur ) ]) )
    elif mediatype == 'artist':
        num_songs, num_albums, num_artists, totdur, totsize = data[3:]
        print( ' '.join([ '%s is a music library.' % library_dict[ library_key ],
                          'There are %d songs made by %d artists in %d albums.' %
                          ( num_songs, num_artists, num_albums ),
                          'The total size of music media is %s.' %
                          get_formatted_size( totsize ),
                          'The total duration of music media is %s.' %
                          get_formatted_duration( totdur ) ]) )

def main( ):
    parser = OptionParser( )
    parser.add_option('--librarynames', dest='do_librarynames', action='store_true', default=False,
                      help = 'If chosen, just give the sorted names of all libraries in the Plex server.')
    parser.add_option('--refresh', dest='do_refresh', action='store_true', default=False,
                      help = 'If chosen, refresh a chosen library in the Plex server. Must give a valid name for the library.')
    parser.add_option('--summary', dest='do_summary', action='store_true', default=False,
                      help = 'If chosen, perform a summary of the chosen library in the Plex server. Must give a valid name for the library.')
    parser.add_option('--library', dest='library', type=str, action='store',
                      help = 'Name of a (valid) library in the Plex server.')
    parser.add_option('--remote', dest='do_remote', action='store_true', default = False,
                      help = 'If chosen, use the given Plex username and password to get the libraries.' )
    parser.add_option('--username', dest='username', action='store', type=str,
                      help = 'Plex user email.' )
    parser.add_option('--password', dest='password', action='store', type=str,
                      help = 'Plex password.' )
    parser.add_option('--servername', dest='servername', action='store', type=str,
                      help = 'Optional name of the server to check for.' )
    parser.add_option('--servernames', dest='do_servernames', action='store_true', default=False,
                      help = 'If chosen, print out all the servers owned by the user.')
    opts, args = parser.parse_args( )
    if not opts.do_remote:
        assert( len( list( filter( lambda tok: tok is True, ( opts.do_librarynames, opts.do_refresh, opts.do_summary ) ) ) ) == 1 )
        #
        ## first get the token
        data = plexcore.checkServerCredentials( doLocal = True )
        if data is None:
            print('Sorry, now we need to provide an user name and password. Please get one!')
            return
        _, token = data
        library_dict = plexcore.get_libraries( token = token )
        if opts.do_librarynames:
            print('Here are the %d libraries in this Plex server.' % len( library_dict ) )
            for libraryName in sorted( library_dict.values( ) ):
                print( libraryName )
            return
        assert( opts.library is not None )
        if opts.library not in library_dict.values( ):
            print('ERROR, candidate library %s not in %s.' % ( opts.library, sorted( set( library_dict.values( ) ) ) ) )
            return      
        library_key = max(filter(lambda key: library_dict[ key ] == opts.library, library_dict ) )
        if opts.do_refresh:
            plexcore.refresh_library( library_key, library_dict, token = token )
            return
        _print_summary( library_key, library_dict, token = token )
    else:
        assert( len( list( filter( lambda tok: tok is True, ( opts.do_librarynames, opts.do_refresh, opts.do_servernames,
                                                        opts.do_summary ) ) ) ) == 1 )
        assert( opts.username is not None )
        assert( opts.password is not None )
        token = plexcore.getTokenForUsernamePassword( opts.username, opts.password )
        if token is None:
            print( 'INVALID USERNAME/PASSWORD' )
            return
        server_dicts = plexcore.get_all_servers( token )
        if server_dicts is None:
            print( 'COULD FIND NO SERVERS OWNED OR ACCESIBLE TO %s.' % opts.username )
            return
        if opts.do_servernames:
            server_names = sorted( server_dicts[ 'owned' ].keys( ) )
            print( 'SERVERS OWNED BY %s:' % opts.username )
            for server_name in server_names:
                print( '%s => %s' % ( server_name, server_dicts[ 'owned' ][ server_name ] ) )
            server_names = sorted( server_dicts[ 'unowned' ].keys( ) )
            print( 'SERVERS ACCESSIBLE TO %s:' % opts.username )
            for server_name in server_names:
                print( '%s => %s' % ( server_name, server_dicts[ 'unowned' ][ server_name ] ) )
            return
        if opts.servername is None:
            servername = min( server_dicts[ 'owned' ] )
        else:
            servername = opts.servername
        server_dicts_all = { }
        for stat in [ 'owned', ]:
            for name in server_dicts[ stat ]:
                server_dicts_all[ name ] = ( server_dicts[ stat ][ name ], stat )
        assert( servername in server_dicts_all.keys( ) )
        fullURL = 'https://%s' % server_dicts_all[ servername ][ 0 ]
        library_dict = plexcore.get_libraries( token = token,
                                               fullURL = fullURL )
        if opts.do_librarynames:
            print('Here are the %d libraries on Plex server %s (%s).' %
                  ( len( library_dict ), servername, fullURL ) )
            for libraryName in sorted( library_dict.values( ) ):
                print( libraryName )
            return
        assert( opts.library is not None )
        if opts.library not in library_dict.values( ):
            print('ERROR, candidate library %s not in %s.' % (
                opts.library, sorted( set( library_dict.values( ) ) ) ) )
            return
        library_key = max(filter(lambda key: library_dict[ key ] == opts.library, library_dict ) )
        if opts.do_refresh:
            plexcore.refresh_library( library_key, library_dict, fullURL = fullURL, token = token )
            return
        _print_summary( library_key, library_dict, token = token, fullURL = fullURL )
        
if __name__=='__main__':
    main( )
