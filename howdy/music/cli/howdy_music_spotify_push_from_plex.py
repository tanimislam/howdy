import os, sys, numpy, glob, pandas, time, datetime, logging, tabulate
from pathos.multiprocessing import Pool, cpu_count
from plexapi.server import PlexServer
#
from howdy.core import core
from howdy.music import music, music_spotify
#
from argparse import ArgumentParser

#
## prints out the AUDIO playlists on the local Plex server
def get_plex_audio_playlists( ):
    fullURL, token = core.checkServerCredentials( doLocal=True )
    plex = PlexServer( fullURL, token )
    playlists = list(filter(lambda playlist: playlist.playlistType == 'audio', plex.playlists( ) ) )
    if len( playlists ) == 0:
        print( 'FOUND ZERO AUDIO PLAYLISTS' )
        return
    def _get_playlist_info( playlist ):
        name = playlist.title
        num_items = len( playlist.items( ) )
        added_at = playlist.addedAt.date( )
        updated_at = playlist.updatedAt.date( )
        return {
            'name' : name,
            'number of items' : num_items,
            'added at' : added_at,
            'updated at' : updated_at }
    with Pool( processes = min( len( playlists ), cpu_count( ) ) ) as pool:
        list_of_playlists = sorted(
            pool.map( _get_playlist_info, playlists ),
            key = lambda entry: -entry[ 'number of items' ] )
        df_plex_playlists_summary = pandas.DataFrame({
            'name' : list(map(lambda entry: entry['name'], list_of_playlists ) ),
            'number of items' : numpy.array( list(map(lambda entry: entry['number of items'], list_of_playlists ) ), dtype=int ),
            'created' : list(map(lambda entry: entry['added at'], list_of_playlists ) ),
            'updated' : list(map(lambda entry: entry['updated at'], list_of_playlists ) ) } )
        return df_plex_playlists_summary

def print_plex_audio_playlists( df_plex_playlists_summary ):
    headers = [ 'name', 'number of items', 'created', 'updated' ]
    def _get_data( rowno ):
        df_sub = df_plex_playlists_summary[
            df_plex_playlists_summary.index == rowno ]
        return (
            max( df_sub.name ),
            max( df_sub['number of items' ] ),
            max( df_sub['created'] ).strftime( '%d %B %Y' ),
            max( df_sub['updated'] ).strftime( '%d %B %Y' ) )
    print( 'summary info for %d plex audio playlists.\n' % df_plex_playlists_summary.shape[ 0 ] )
    print( '%s\n' % tabulate.tabulate(
        list(map(_get_data, range( df_plex_playlists_summary.shape[ 0 ] ) ) ),
        headers = headers ) )

def create_spotify_public_playlist( name, description ):
    oauth2_access_token = music_spotify.get_or_push_spotify_oauth2_token( )
    assert( oauth2_access_token is not None )
    status = music_spotify.create_public_playlist(
        oauth2_access_token, name, description )
    if not status:
        print( "ERROR, SPOTIFY PUBLIC PLAYLIST WITH NAME = %s ALREADY EXISTS. JUST USE THAT ONE!" % name )
        return
    print( "SUCCESSFULLY CREATED SPOTIFY PUBLIC PLAYLIST WITH NAME = %s." % name )

def print_spotify_public_playlists( ):
    oauth2_access_token = music_spotify.get_or_push_spotify_oauth2_token( )
    assert( oauth2_access_token is not None )
    spotify_data_playlists = music_spotify.get_public_playlists( oauth2_access_token )
    headers = [ 'name', 'number of items', 'description' ]
    data = list(map(lambda entry: ( entry['name'], entry['number of tracks'], entry['description' ] ),
                    spotify_data_playlists ) )
    print( 'summary info for %d public Spotify audio playlists.\n' % len( spotify_data_playlists ) )
    print( '%s\n' % tabulate.tabulate( data, headers = headers ) )

def push_plex_to_spotify_playlist(
    plex_playlist_name,
    spotify_playlist_name,
    numprocs = cpu_count( ),
    npurify = 1 ):
    assert( numprocs >= 1 )
    assert( npurify >= 0 )
    #
    ## first get the playlist
    fullURL, token = core.checkServerCredentials( doLocal= True )
    plex = PlexServer( fullURL, token )
    playlists = list( filter(lambda playlist: playlist.title == plex_playlist_name and
                             playlist.playlistType == 'audio', plex.playlists()))
    if len( playlists ) == 0:
        print( "ERROR, COULD FIND NO AUDIO PLEX PLAYLISTS = %s. EXITING..." % plex_playlist_name )
        return False
    #
    ## now get the non-oauth2 spotify access token
    spotify_access_token = music_spotify.get_spotify_session( )
    assert( spotify_access_token is not None )
    #
    ## now get the SPOTIFY playlist
    oauth2_access_token = music_spotify.get_or_push_spotify_oauth2_token( )
    assert( oauth2_access_token is not None )
    spotify_playlists = list(filter(lambda entry: entry['name'] == spotify_playlist_name,
                                    music_spotify.get_public_playlists( oauth2_access_token ) ) )
    if len( spotify_playlists ) != 1:
        print( "ERROR, PUBLIC SPOTIFY PLAYLIST = %s DOES NOT EXIST." % spotify_playlist_name )
        return False
    spotify_playlist = spotify_playlists[ 0 ]
    my_userid = spotify_playlist[ 'user id' ]
    
    playlist = playlists[ 0 ]
    df_plex_playlist = music.plexapi_music_playlist_info( playlist, use_internal_metadata=True )
    #
    ## now put in the SPOTIFY ID column (and add in the appropriate entries where none are)
    df_spotify_playlist = music_spotify.process_dataframe_playlist_spotify_multiproc(
        df_plex_playlist, spotify_access_token, numprocs )
    #
    ## HACKISH FIX trying to fix the bad
    for iteration in range( npurify ):
        with Pool( processes = numprocs ) as pool: 
            ngoods_rows_tuples = list(
                pool.map(
                lambda idx: music_spotify.process_dataframe_playlist_spotify_bads(
                    df_spotify_playlist[idx::numprocs], spotify_access_token ),
                range( numprocs ) ) )
            ngoods_tots = sum(list(map(lambda tup: tup[0], ngoods_rows_tuples ) ) )
            nrows_tots  = sum(list(map(lambda tup: tup[1], ngoods_rows_tuples ) ) )
            print( 'in iteration %d / %d fixed total of %d / %d bad SPOTIFY IDs in Plex audio playlist = %s.' % (
                iteration + 1, npurify, ngoods_tots, nrows_tots, plex_playlist_name ) )
            if nrows_tots == 0: break
        #
        ## we have not MODIFIED the plex playlist, but getting the spotify playlist AGAIN
        df_spotify_playlist = music_spotify.process_dataframe_playlist_spotify_multiproc(
            df_plex_playlist, spotify_access_token, numprocs )
    
    #
    ## STATUS PRINTOUT
    ngoods = df_spotify_playlist[ df_spotify_playlist[ 'SPOTIFY ID' ].str.startswith(
        'spotify:track:' ) ].shape[ 0 ]
    print( 'found %d / %d good SPOTIFY IDs in Plex audio playlist = %s.' % (
        ngoods, df_spotify_playlist.shape[ 0 ], plex_playlist_name ) )
    print( 'found %d tracks in public Spotify audio playlist = %s.' % (
        spotify_playlist[ 'number of tracks' ], spotify_playlist[ 'name' ] ) )
    #
    ## now get the list of SPOTIFY IDs in the Plex audio playlist
    spotify_ids_list = list(
        df_spotify_playlist[
            df_spotify_playlist['SPOTIFY ID'].str.startswith('spotify:track:') ]['SPOTIFY ID'] )
    #
    ## now get the list of SPOTIFY IDs in the public Spotify playlist
    spotify_playlist_id = spotify_playlist[ 'id' ]
    spotify_ids_in_playlist = None
    for iteration in range( 15 ):
        try:
            spotify_ids_in_playlist = music_spotify.get_existing_track_ids_in_spotify_playlist(
                spotify_playlist_id, oauth2_access_token )
            break
        except:
            print( 'failed iteration %02d / 15. Trying again...' % ( iteration + 1 ) )
            time.sleep( 1.0 )
            pass
    if spotify_ids_in_playlist is None:
        print( "ERROR, IN 15 TRIES COULD NOT GET COLLECTION OF SPOTIFY IDS IN SPOTIFY PLAYLIST = $s." %
              spotify_playlist_name )
        return False
    print( 'SUBTRACTING %d TRACKS FROM SPOTIFY PLAYLIST = %s.' % (
        len( set( spotify_ids_in_playlist ) - set( spotify_ids_list ) ),
        spotify_playlist_name ) )
    print( 'ADDING %d TRACKS TO SPOTIFY PLAYLIST = %s.' % (
        len( set( spotify_ids_list ) - set( spotify_ids_in_playlist ) ),
        spotify_playlist_name ) )
    #
    ## NOW ACTUALLY CHANGE THE SPOTIFY PLAYLIST TO HAVE SAME TRACKS AS FOUND IN PLEX AUDIO PLAYLIST
    music_spotify.modify_existing_playlist_with_new_tracks(
        spotify_playlist_id, oauth2_access_token, spotify_ids_list,
        spotify_ids_in_playlist = spotify_ids_in_playlist )
    return True
          
    
def main( ):
    time0 = time.perf_counter( )
    #
    parser = ArgumentParser( )
    parser.add_argument(
        '-I', '--info', dest='do_info', action='store_true', default = False,
        help = 'If chosen, then print out INFO level logging statements.' )
    #
    subparsers = parser.add_subparsers(
        #help = '\n'.join([
        #    'Choose one of four options:',
        #    '(plex): list all the PLEX AUDIO playlists on this Plex server',
        #    '(spotify_list): list the public SPOTIFY playlists on your SPOTIFY account',
        #    '(spotify_create): create a public SPOTIFY playlist on your SPOTIFY account',
        #    '(push): make the collection of songs on a specific SPOTIFY playlist match the SPOTIFY-identified songs on the specific PLEX AUDIO playlist.' ] ),
        dest = 'choose_option', required = True )
    #
    ## the plex option
    subparsers_plex = subparsers.add_parser(
        'plex',
        help = 'list all the PLEX audio playlists on the local Plex server.' )
    #
    ## now the spotify list one
    subparsers_spotify_list = subparsers.add_parser(
        'spotify_list',
        help = 'List the public SPOTIFY playlists on your SPOTIFY account.' )
    #
    ## now the spotify create one
    subparsers_spotify_create = subparsers.add_parser(
        'spotify_create',
        help = 'Create a public SPOTIFY playlist on your SPOTIFY account.' )
    subparsers_spotify_create.add_argument(
        '-n', '--name', dest = 'name', type = str, action = 'store',
        help = 'Name of the public SPOTIFY playlist.' )
    subparsers_spotify_create.add_argument(
        '-d', '--description', dest = 'description', type = str, action = 'store',
        help = 'Description of the public SPOTIFY playlist.' )
    #
    ## now the push one
    subparsers_push = subparsers.add_parser(
        'push',
        help = 'make the collection of songs on a specific SPOTIFY playlist match the SPOTIFY-identified songs on the specific PLEX AUDIO playlist.' )
    subparsers_push.add_argument(
        '-i', '--input', dest = 'plex_input', type = str, action = 'store',
        help = 'The input PLEX AUDIO playlist to push into a public SPOTIFY playlist.' )
    subparsers_push.add_argument(
        '-o', '--output', dest = 'spotify_output', type = str, action = 'store',
        help = "The output public SPOTIFY playlist. Intent = the public SPOTIFY playlist's songs will MATCH the PLEX AUDIO playlist's collection of SPOTIFY identified songs." )
    subparsers_push.add_argument(
        '-N', '--nprocs', dest = 'numprocs', type = int, action = 'store', default = cpu_count( ),
        help = 'The number of processors used to perform the calculations. Must be >= 1. Default = %d.' % cpu_count( ) )
    subparsers_push.add_argument(
        '-M', '--npurify', dest = 'npurify', type = int, action = 'store', default = 0,
        help = ' '.join([
            'The number of times to PURIFY the finding-spotify-ids in our Plex audio playlist. Must be >= 0.'
            'Default is 0.' ]) )
    #
    ## now do the needful
    args = parser.parse_args( )
    #
    ## turn on debug logging
    logger = logging.getLogger( )
    if args.do_info: logger.setLevel( logging.INFO )
    #
    ##
    if args.choose_option not in ( 'plex', 'spotify_create', 'spotify_list', 'push' ):
        print( "ERROR, MUST CHOOSE ONE OF 'plex', 'spotify_list', 'spotify_create', or 'push'. Instead chosen %s." %
              args.choose_option )
        return
    #
    ## the plex option
    if args.choose_option == 'plex':
        print_plex_audio_playlists( get_plex_audio_playlists( ) )
    elif args.choose_option == 'spotify_list':
        print_spotify_public_playlists( )
    elif args.choose_option == 'spotify_create':
        assert( args.name is not None )
        assert( args.description is not None )
        name = args.name.strip( )
        description = args.description.strip( )
        create_spotify_public_playlist( name, description )
    elif args.choose_option == 'push':
        assert( args.plex_input is not None )
        assert( args.spotify_output is not None )
        assert( args.numprocs >= 1 )
        assert( args.npurify >= 0 )
        plex_playlist_name = args.plex_input.strip( )
        spotify_playlist_name = args.spotify_output.strip( )
        status = push_plex_to_spotify_playlist(
            plex_playlist_name,
            spotify_playlist_name,
            numprocs = args.numprocs,
            npurify = args.npurify )
    #
    ## how long did this take?
    print( 'took %0.3f seconds to process.' % ( time.perf_counter( ) - time0 ) )
    
