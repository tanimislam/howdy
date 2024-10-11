import os, requests, datetime, time, io, re, pandas, mutagen.mp4, logging, json
from pathos.multiprocessing import Pool, cpu_count
from authlib.integrations.requests_client import OAuth2Session
from requests.auth import HTTPBasicAuth
from rapidfuzz.fuzz import partial_ratio
#
from howdy.core import core, baseConfDir, session, PlexConfig
from howdy.music.music import get_m4a_metadata

def push_spotify_credentials( client_id, client_secret, verify = True ):
    """
    Pushes the Spotify_ API configuration into the SQLite3_ configuration database. Take a look at `this blog article on the Spotify API <https://tanimislam.gitlab.io/blog/spotify-web-api.html>`_ for some more information on setting up your Spotify_ web API client.
        
    :param str client_id: the Spotify_ client ID.
    :param str client_secret: the Spotify_ client secret.
    :param bool verify: if ``True``, then use HTTPS authentication. Otherwise do not. Default is ``True``.
    
    .. _Spotify: https://open.spotify.com
    .. _SQLite3: https://www.sqlite.org/index.html
    """
    #
    ## first check that it is a valid Spotify credential
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers = { 'Content-Type' : 'application/x-www-form-urlencoded' },
        data = {
            'grant_type'    : 'client_credentials',
            'client_id'     : client_id,
            'client_secret' : client_secret }, verify = verify )
    if not response.ok:
        raise ValueError("ERROR, INVALID SPOTIFY CREDENTIALS" )
    val = session.query( PlexConfig ).filter(
        PlexConfig.service == 'spotify' ).first( )
    if val is not None:
        session.delete( val )
        session.commit( )
    session.add(
        PlexConfig( service = 'spotify',
                   data = { 'client_id' : client_id,
                           'client_secret' : client_secret } ) )
    session.commit( )

def get_spotify_credentials( ):
    """
    :returns: a :py:class:`dict` whose two keys and values are the ``client_id`` and the ``client_secret`` for the Spotify_ web API client in the SQLite3_ configuration database.
    :rtype: dict
    """
    val = session.query( PlexConfig ).filter(
        PlexConfig.service == 'spotify' ).first( )
    if val is None:
        raise ValueError( "ERROR, SPOTIFY WEB API CLIENT CREDENTIALS NOT FOUND OR SET" )
    return val.data

def get_spotify_session( ):
    """
    Returns the session token from a valid Spotify_ API account.
    :rtype: str
    """
    data = get_spotify_credentials( )
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers = { 'Content-Type' : 'application/x-www-form-urlencoded' },
        data = {
            'grant_type'    : 'client_credentials',
            'client_id'     : data['client_id'],
            'client_secret' : data['client_secret'] } )
    assert( response.ok )
    data_auth = response.json( )
    return data_auth[ 'access_token' ]


def get_or_push_spotify_oauth2_token( ):
    """
    :returns: the Spotify_ API token that allows you to add, delete, and modify Spotify_ playlists.
    :rtype: dict
    """
    scope = ["user-read-private", "user-read-email", "playlist-modify-public" ]
    redirect_uri = 'http://localhost' # for my app, probably should put it in the 'spotify' configs
    #
    ## from https://requests-oauthlib.readthedocs.io/en/latest/examples/spotify.html
    authorization_base_url = "https://accounts.spotify.com/authorize"
    token_url = "https://accounts.spotify.com/api/token"
    #
    def _get_spotify_token( spotify_client_id, spotify_client_secret ):
        spotify = OAuth2Session( spotify_client_id, scope = scope, redirect_uri=redirect_uri)
        #
        authorization_url, state = spotify.create_authorization_url(authorization_base_url)
        #
        redirect_response = input( 'Please put in the URL when you visit this website: %s' % authorization_url )
        redirect_response = re.sub( '^http:', 'https:', redirect_response )
        logging.info( 'REDIRECT RESPONSE FOR SPOTIFY TOKEN = %s,' % redirect_response )
        #
        token = spotify.fetch_token(
            token_url,
            auth = HTTPBasicAuth( spotify_client_id, spotify_client_secret ),
            authorization_response = redirect_response )
        return token

    def _get_refreshed_spotify_token( spotify_client_id, spotify_client_secret, token ):
        spotify = OAuth2Session( spotify_client_id, token = token )
        new_token = spotify.refresh_token(
            token_url, client_id = spotify_client_id,
            client_secret = spotify_client_secret )
        return new_token
        
    try:
        #
        ## first get the credentials
        client_data = get_spotify_credentials( )
        #
        ## now search for the token
        val = session.query( PlexConfig ).filter(
            PlexConfig.service == 'spotify oauth2 token' ).first( )
        #
        ## now recover the token
        if val is None:
            token = _get_spotify_token( client_data[ 'client_id' ], client_data[ 'client_secret' ] )
        else:
            old_token = val.data
            #
            ## if timestamp < 0.0 then use OLD token
            seconds_left = time.time( ) - old_token[ 'expires_at' ]
            if seconds_left < 0: return old_token
            token = _get_refreshed_spotify_token( client_data[ 'client_id' ], client_data[ 'client_secret' ], old_token )
            session.delete( val )
            session.commit( )
        #
        ## now put the token into the 'spotify oauth2 token' service
        newval = PlexConfig(
            service = 'spotify oauth2 token',
            data = token )
        session.add( newval )
        session.commit( )
        return token
    except Exception as e:
        logging.error( str( e ) )
        return None            


def push_spotify_song_id_to_file( spotify_id, filename ):
    """
    This *copies* the Spotify_ ID of a song to a given M4A_ file. This puts the Spotify_ ID into the comments tags in the M4A_ file.

    :param str spotify_id: The Spotify_ ID of a song. For example, the song `All I Need <https://en.wikipedia.org/wiki/All_I_Need_(Air_song)>`_ by `Air <https://en.wikipedia.org/wiki/Air_(French_band)>`_ has a Spotify_ ID = ``spotify:track:6T10XPeC9X5xEaD6tMcK6M``. It can be found on Spotify_ at `this link <https://open.spotify.com/track/6T10XPeC9X5xEaD6tMcK6M>`_.
    :param str filename: the M4A_ song file name.
    """
    _error_expired_token = 'The access token expired'
    if spotify_id.strip( ) == _error_expired_token:
        logging.debug( 'ACTUAL MESSAGE IS EXPIRED TOKEN. DOING NOTHING.' )
        return
    #
    ## final comments list has no SPOTIFY: things in it
    song_metadata_dict = get_m4a_metadata( filename )
    if 'comment' not in song_metadata_dict:
        comments = list(filter(lambda cmnt: not cmnt.startswith('SPOTIFY: '), [ ] ) )
    else:
        comments = list(filter(lambda cmnt: not cmnt.startswith('SPOTIFY: '), song_metadata_dict[ 'comment' ] ) )
        
    comments.append( 'SPOTIFY: %s' % spotify_id )

    mp4tags = mutagen.mp4.MP4( filename )
    mp4tags[ '\xa9cmt' ] = comments
    mp4tags.save( )
    
def get_spotify_song_id_filename( filename ):
    song_metadata_dict = get_m4a_metadata( filename )
    if 'comment' not in song_metadata_dict:
        logging.debug( 'ERROR, NO COMMENTS IN %s.' % os.path.abspath( filename ) )
        return None
    comments = list(filter(lambda cmnt: cmnt.startswith('SPOTIFY: '), song_metadata_dict[ 'comment' ] ) )
    if len( comments ) != 1:
        logging.debug( 'ERROR, NOT JUST ONE SPOTIFY: ENTRY IN COMMENTS IN %s.' % os.path.abspath( filename ) )
        return None

    spotify_id = re.sub('^SPOTIFY:', '', comments[0] ).strip( )
    return spotify_id
    
def get_spotify_song_id(
    spotify_access_token, song_metadata_dict, song_limit = 5, market = 'us', dump_response = False,
    response_file = 'foo.json' ):
    assert( song_limit > 0 )
    #
    def _get_track_query_string( song_metadata_dict ):
        assert( 'song' in song_metadata_dict )
        return 'track:%s' % song_metadata_dict[ 'song' ]
    def _get_artist_query_string( song_metadata_dict ):
        assert( 'artist' in song_metadata_dict )
        return 'artist:%s' % song_metadata_dict[ 'artist' ]
    def _get_year_query_string( song_metadata_dict ):
        assert( 'date' in song_metadata_dict )
        return 'year:%d' % song_metadata_dict[ 'date' ].year
    def _get_album_query_string( song_metadata_dict ):
        assert( 'album' in song_metadata_dict )
        return 'album:%s' % song_metadata_dict[ 'album' ]

    #
    ## now create a dictionary of song metadata keys (4) to above methods
    query_dict = {
        'song'   : _get_track_query_string,
        'artist' : _get_artist_query_string,
        'date'   : _get_year_query_string,
        'album'  : _get_album_query_string }

    def _get_track_date( track_elem ):
        try: return datetime.datetime.strptime( track_elem[ 'album' ][ 'release_date' ], '%Y-%m-%d' ).date( )
        except: pass
        try: return datetime.datetime.strptime( track_elem[ 'album' ][ 'release_date' ], '%Y-%m' ).date( )
        except: pass
        return datetime.datetime.strptime( track_elem[ 'album' ][ 'release_date' ], '%Y' ).date( )
        
    
    def _get_info_track_elem( track_elem ):
        track_album = track_elem['album']['name']
        track_date = _get_track_date( track_elem )
        track_name = track_elem[ 'name' ]
        track_artist = track_elem[ 'artists' ][ 0 ][ 'name' ]
        return {
            'song'   : track_name,
            'artist' : track_artist,
            'date'   : track_date,
            'album'  : track_album }
    
    def _get_spotify_query( song_dict, query_keys ):
        spotify_query = ' '.join(map(lambda key: query_dict[ key ]( song_dict ), query_keys ) )
        logging.debug( 'SPOTIFY QUERY FOR SONG = %s.' % spotify_query )
        return spotify_query
    
    def _get_comparative_score( track_elem ):
        query_keys = sorted(set( song_metadata_dict ) & set( query_dict ) )
        initial_query = _get_spotify_query( song_metadata_dict, query_keys )
        track_query = _get_spotify_query(
            _get_info_track_elem( track_elem ),
            query_keys )
        return partial_ratio( initial_query, track_query )
    #
    ## now essential keys in song_metadata_dict
    essential_keys = set([ 'song', 'artist' ] )
    assert( len( essential_keys - set( song_metadata_dict ) ) == 0 ) # must have AT LEAST these two
    #
    ## now the final query
    query_keys = sorted(set( song_metadata_dict ) & set( query_dict ) )
    spotify_query = _get_spotify_query( song_metadata_dict, query_keys )
    logging.debug( 'SPOTIFY QUERY FOR SONG = %s.' % spotify_query )
    #
    ## now get the track query
    resp_track = requests.get(
        "https://api.spotify.com/v1/search",
        headers = { 'Authorization' : 'Bearer %s' % spotify_access_token },
        params = {
            'q' : spotify_query,
            'type' : 'track',
            'market' : market,
            'limit'  : song_limit } )
    #
    ## check that we have a good response
    if not resp_track.ok:
        error_json = resp_track.json( )
        return error_json[ 'error' ][ 'message' ]
    #
    ## now get the best track
    data_track = resp_track.json( )
    if dump_response: json.dump( data_track, open( response_file, 'w' ), indent = 1 )
    try:
        best_elem = max( data_track['tracks']['items'], key = lambda track_elem: _get_comparative_score( track_elem ) )
        logging.debug( 'BEST SCORE TRACK_ELEM = %0.1f' % _get_comparative_score( best_elem ) )
        return best_elem['uri']
    except Exception as e:
        return "CANNOT FIND SPOTIFY TRACK ID FOR %s." % spotify_query
    
def process_dataframe_playlist_spotify_bads( df_playlist_spotify, spotify_access_token ):
    time0 = time.perf_counter( )
    #
    ## first ONLY THE ONES with non-good spotify IDs
    df_playlist_bads = df_playlist_spotify[ -df_playlist_spotify['SPOTIFY ID'].str.startswith('spotify:track:')]
    df_dict = df_playlist_bads.to_dict( orient = 'list' )
    nrows = df_playlist_bads.shape[ 0 ]
    #
    ## df_list_proc is the list of dictionaries to process in order with SPOTIFY API
    ## SPOTIFY API process: 1) if SPOTIFY ID in music file, return that; 2) if SPOTIFY ID not in music file, find it out and push into file then return that.
    df_list_proc = list(map(lambda tup: {
        'order' : tup[0], 'filename' : tup[1], 'song' : tup[2], 'artist' : tup[3], 'album' : tup[4], 'year' : tup[5] },
                            zip(
                                df_dict['order in playlist'], df_dict['filename'],
                                df_dict['song name'], df_dict[ 'artist' ], df_dict[ 'album' ],
                                df_dict['album year'] ) ) )

    def _get_process_spotify_id_entry( df_list_entry, access_token ):
        filename = df_list_entry['filename']
        order = df_list_entry['order']
        #spotify_id_fname = get_spotify_song_id_filename( filename )
        #if spotify_id_fname is not None:
        #    return ( order, spotify_id_fname )
        #
        ## otherwise get spotify ID and push into file
        artist_replace = re.sub( '[fF]eat.*', '', df_list_entry[ 'artist' ] ).strip( )
        artist_replace = re.sub( '[fF]eat.*', '', artist_replace ).strip( )
        song_metadata_dict = {
            'song'   : df_list_entry[ 'song'   ],
            'artist' : artist_replace,
            'date'   : datetime.datetime.strptime( '%04d' % df_list_entry[ 'year' ], '%Y' ).date( ),
            'album'  : df_list_entry[ 'album' ]
        }
        #
        ## now fix the spotify IDs and push into file if good.
        spotify_id = get_spotify_song_id( access_token, song_metadata_dict )
        if spotify_id.startswith( 'spotify:track:'):
            push_spotify_song_id_to_file( spotify_id, filename )
            return ( order, spotify_id )
        #
        ## pop out the date to help
        song_metadata_dict.pop( 'date' )
        spotify_id = get_spotify_song_id( access_token, song_metadata_dict )
        if spotify_id.startswith( 'spotify:track:'):
            push_spotify_song_id_to_file( spotify_id, filename )
            return ( order, spotify_id )
        #
        ## pop out the album to help
        song_metadata_dict.pop( 'album' )
        spotify_id = get_spotify_song_id( access_token, song_metadata_dict )
        if spotify_id.startswith( 'spotify:track:'):
            push_spotify_song_id_to_file( spotify_id, filename )
        return ( order, spotify_id )

    spotify_ids_list = sorted(
        map(lambda df_list_entry: _get_process_spotify_id_entry( df_list_entry, spotify_access_token), df_list_proc ),
        key = lambda tup: tup[0] )

    #
    ## number of good SPOTIFY IDs now fixed
    ngoods = len(list(filter(lambda tup: tup[1].startswith('spotify:track:'), spotify_ids_list ) ) )
    #
    ##
    logging.info( 'fixed %02d / out of %02d bad SPOTIFY IDs in %0.3f seconds.' % (
        ngoods, nrows, time.perf_counter( ) - time0 ) )
    return ( ngoods, nrows )

def get_existing_track_ids_in_spotify_playlist(
    spotify_playlist_id, oauth2_access_token ):
    #
    ## first get the number of tracks
    resp_num_in_playlist = requests.get(
        'https://api.spotify.com/v1/playlists/%s/tracks' % spotify_playlist_id,
        headers = { 'Authorization' : 'Bearer %s' % oauth2_access_token['access_token'] },
    params = { 'fields' : 'total' } )
    assert( resp_num_in_playlist.ok )
    tot_num_in_playlist = resp_num_in_playlist.json( )['total']
    #
    ## now get all the IDs by units of 100
    num, rem = divmod( tot_num_in_playlist, 100 )
    if rem != 0: num += 1
    #
    ## chunk out in units of 100 from 0..num-1
    time0 = time.perf_counter( )
    spotify_ids = [ ]
    for idx in range( num ):
        resp_track_ids = requests.get(
            'https://api.spotify.com/v1/playlists/%s/tracks' % spotify_playlist_id,
            headers = { 'Authorization' : 'Bearer %s' % oauth2_access_token['access_token'] },
            params = { 'fields' : 'items(track.id)', 'offset' : idx * 100, 'limit' : 100 } )
        assert( resp_track_ids.ok )
        data_resp_track_ids = resp_track_ids.json( )
        spotify_ids += list(
            map(lambda entry: 'spotify:track:%s' % entry['track']['id'], data_resp_track_ids['items'] ) )
        logging.info( 'added %02d / %02d (%d items) at %0.3f seconds' % (
            idx + 1, num, len( data_resp_track_ids['items'] ), time.perf_counter( ) - time0 ) )
    logging.info( 'returned list of %d tracks for SPOTIFY track %s in %0.3f seconds.' % (
        len( spotify_ids ), spotify_playlist_id, time.perf_counter( ) - time0 ) )
    return spotify_ids

def get_public_playlists( oauth2_access_token, my_userid = None ):
    #
    ## get the userID of ME
    if my_userid is None:
        resp_userid = requests.get(
            'https://api.spotify.com/v1/me',
            headers  = { 'Authorization' : 'Bearer %s' % oauth2_access_token['access_token'] } )
        assert( resp_userid.ok )
        userid_data = resp_userid.json( )
        my_userid = userid_data['id']
    #
    ## now get my playlists
    resp_playlists = requests.get(
        'https://api.spotify.com/v1/users/%s/playlists' % my_userid,
        headers = { 'Authorization' : 'Bearer %s' % oauth2_access_token['access_token'] } )
    assert( resp_playlists.ok )
    data_playlists = resp_playlists.json( )
    def _get_number_tracks( spotify_playlist_id ):
        resp_num_in_playlist = requests.get(
            'https://api.spotify.com/v1/playlists/%s/tracks' % spotify_playlist_id,
            headers = { 'Authorization' : 'Bearer %s' % oauth2_access_token['access_token'] },
            params = { 'fields' : 'total' } )
        assert( resp_num_in_playlist.ok )
        tot_num_in_playlist = resp_num_in_playlist.json( )['total']
        return tot_num_in_playlist
    #
    ## now get the actual playlists and number of tracks
    actual_playlists = sorted(
        map(lambda entry: {
            'name' : entry['name'],
            'description' : entry['description'],
            'id' : entry['id'],
            'user id' : my_userid,
            'number of tracks' : _get_number_tracks( entry[ 'id' ] ) },
        filter(lambda entry: entry['public'] is True, data_playlists['items'] ) ),
        key = lambda entry: -entry['number of tracks' ] )
    return actual_playlists

def create_public_playlist(
    oauth2_access_token, name, description, my_userid = None ):
    #
    ## get the userID of ME
    if my_userid is None:
        resp_userid = requests.get(
            'https://api.spotify.com/v1/me',
            headers  = { 'Authorization' : 'Bearer %s' % oauth2_access_token['access_token'] } )
        assert( resp_userid.ok )
        userid_data = resp_userid.json( )
        my_userid = userid_data['id']
    #
    ## now get my playlists
    spotify_data_playlists = get_public_playlists(
        oauth2_access_token, my_userid = my_userid )
    #
    ## now CREATE the playlist
    actual_playlist = list(
        filter(lambda entry: entry['name'] == name, spotify_data_playlists))
    if len( actual_playlist ) != 0:
        logging.error( "ERROR, PUBLIC PLAYLIST WITH NAME = %s ALREADY EXISTS. JUST USE THAT ONE!" % name )
        return False
    #
    ## otherwise create the playlist
    resp_create_playlist = requests.post(
        'https://api.spotify.com/v1/users/%s/playlists' % my_userid,
        headers = { 'Authorization' : 'Bearer %s' % oauth2_access_token[ 'access_token' ],
                   'Content-Type' : 'application/json' },
        json = {
            'name' : name,
            'description' : description,
            'public' : True } )
    assert( resp_create_playlist.ok )
    return True

def process_dataframe_playlist_spotify_multiproc(
    df_playlist, spotify_access_token, numprocs = cpu_count( ) ):
    assert( numprocs >= 1 )
    with Pool( processes = numprocs ) as pool: 
        df_playlist_spotify = pandas.concat( list(
            pool.map(
              lambda idx: process_dataframe_playlist_spotify( df_playlist[idx::numprocs], spotify_access_token ),
              range( numprocs ) ) ) ).sort_values( 'order in playlist' )
        return df_playlist_spotify

def process_dataframe_playlist_spotify( df_playlist, spotify_access_token ):
    time0 = time.perf_counter( )
    df_dict = df_playlist.to_dict( orient = 'list' )
    #
    ## df_list_proc is the list of dictionaries to process in order with SPOTIFY API
    ## SPOTIFY API process: 1) if SPOTIFY ID in music file, return that; 2) if SPOTIFY ID not in music file, find it out and push into file then return that.
    df_list_proc = list(map(lambda tup: {
        'order' : tup[0], 'filename' : tup[1], 'song' : tup[2], 'artist' : tup[3], 'album' : tup[4], 'year' : tup[5] },
                            zip(
                                df_dict['order in playlist'], df_dict['filename'],
                                df_dict['song name'], df_dict[ 'artist' ], df_dict[ 'album' ],
                                df_dict['album year'] ) ) )

    def _get_process_spotify_id_entry( df_list_entry, access_token ):
        filename = df_list_entry['filename']
        order = df_list_entry['order']
        spotify_id_fname = get_spotify_song_id_filename( filename )
        if spotify_id_fname is not None:
            return ( order, spotify_id_fname )
        #
        ## otherwise get spotify ID and push into file
        song_metadata_dict = {
            'song'   : df_list_entry[ 'song'   ],
            'artist' : df_list_entry[ 'artist' ],
            'date'   : datetime.datetime.strptime( '%04d' % df_list_entry[ 'year' ], '%Y' ).date( ),
            'album'  : df_list_entry[ 'album' ]
        }
        spotify_id = get_spotify_song_id( access_token, song_metadata_dict )
        if spotify_id.startswith( 'spotify:track:'):
            push_spotify_song_id_to_file( spotify_id, filename )
            return ( order, spotify_id )
        #
        artist_replace = re.sub( '[fF]eat.*', '', df_list_entry[ 'artist' ] ).strip( )
        artist_replace = re.sub( '[fF]eat.*', '', artist_replace ).strip( )
        song_metadata_dict[ 'artist' ] = artist_replace
        spotify_id = get_spotify_song_id( access_token, song_metadata_dict )
        if spotify_id.startswith( 'spotify:track:'):
            push_spotify_song_id_to_file( spotify_id, filename )
            return ( order, spotify_id )
        #
        song_metadata_dict.pop( 'date' )
        spotify_id = get_spotify_song_id( access_token, song_metadata_dict )
        if spotify_id.startswith( 'spotify:track:'):
            push_spotify_song_id_to_file( spotify_id, filename )
            return ( order, spotify_id )
        #
        song_metadata_dict.pop( 'album' )
        spotify_id = get_spotify_song_id( access_token, song_metadata_dict )
        push_spotify_song_id_to_file( spotify_id, filename )
        return ( order, spotify_id )

    spotify_ids_list = sorted(
        map(lambda df_list_entry: _get_process_spotify_id_entry( df_list_entry, spotify_access_token), df_list_proc ),
        key = lambda tup: tup[0] )
    #
    ## number of good SPOTIFY IDs
    ngoods = len(list(filter(lambda tup: tup[1].startswith('spotify:track:'), spotify_ids_list ) ) )
    #
    df_playlist_out = df_playlist.copy( ).sort_values( 'order in playlist' )
    nrows = df_playlist_out.shape[ 0 ]
    ncols = df_playlist_out.shape[ 1 ]
    df_playlist_out.insert( ncols, "SPOTIFY ID", list(zip(*spotify_ids_list ))[1] )
    #
    ##
    logging.info( 'found %02d / %02d good SPOTIFY IDs in playlist dataframe in %0.3f seconds.' % (
        ngoods, nrows, time.perf_counter( ) - time0 ) )
    return df_playlist_out    


def modify_existing_playlist_with_new_tracks(
    spotify_playlist_id, oauth2_access_token, spotify_ids_list,
    spotify_ids_in_playlist = None ):
    #
    if spotify_ids_in_playlist is None:
        spot_ids_in_pl = get_existing_track_ids_in_spotify_playlist(
            spotify_playlist_id, oauth2_access_token )
    else:
        spot_ids_in_pl = spotify_ids_in_playlist
    #
    track_ids_to_sub = list( set( spot_ids_in_pl ) - set( spotify_ids_list ) )
    track_ids_to_add = list( set( spotify_ids_list ) - set( spot_ids_in_pl ) )
    #
    ## first subtract these items from the playlist
    def _sub_playlist( track_ids_to_sub ):
        if len( track_ids_to_sub ) == 0:
            return # do nothing
        resp_tracks_delete = requests.delete(
            'https://api.spotify.com/v1/playlists/%s/tracks' % spotify_playlist_id,
            headers = { 'Authorization' : 'Bearer %s' % oauth2_access_token['access_token'] },
            json = { "tracks" : list( map(lambda track_id: { "uri" : track_id }, track_ids_to_sub ) ) } )
        assert( resp_tracks_delete.ok )
    #
    ## now add items TO the playlist
    def _add_playlist( track_ids_to_add ):
        time0 = time.perf_counter( )
        if len( track_ids_to_add ) == 0:
            return # do nothing
        num, rem = divmod( len( track_ids_to_add ), 100 )
        if rem != 0: num += 1
        for idx in range( num ):
            resp_tracks_add = requests.post(
                'https://api.spotify.com/v1/playlists/%s/tracks' % spotify_playlist_id,
                headers = { 'Authorization' : 'Bearer %s' % oauth2_access_token['access_token'] },
                json = { "uris" : track_ids_to_add[idx*100:(idx+1)*100] } )
            assert( resp_tracks_add.ok )
            logging.info( "added %02d / %02d (%d tracks) to %s at %0.3f seconds." % (
                idx + 1, num, len( track_ids_to_add[idx*100:(idx+1)*100] ), spotify_playlist_id,
                time.perf_counter( ) - time0 ) )
        logging.info( 'added %d tracks to %s in %0.3f seconds.' % (
            len( track_ids_to_add ), spotify_playlist_id, time.perf_counter( ) - time0 ) )
    #
    ## first do the subtract
    _sub_playlist( track_ids_to_sub )
    #
    ## then do the add
    _add_playlist( track_ids_to_add )

