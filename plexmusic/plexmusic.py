import os, sys, glob, numpy, titlecase, mutagen.mp4, httplib2, json, logging
import requests, youtube_dl, gmusicapi, datetime, musicbrainzngs, time
import pathos.multiprocessing as multiprocessing
from contextlib import contextmanager
from googleapiclient.discovery import build
from PIL import Image
from io import StringIO, BytesIO
from urllib.parse import urljoin
from . import mainDir, pygn, parse_youtube_date, format_youtube_date
from plexcore import plexcore, baseConfDir, session, PlexConfig
from sqlalchemy import Integer, String, Column

#
## get all the tracks, by order, of all the official albums of an artist.
## this is not tested all that much, but perhaps it is useful to some people
class MusicInfo( object ):

    @classmethod
    def get_artist_datas_LL( cls, artist_name, min_score = 100, do_strict = True ):
        assert( min_score <= 100 and min_score >= 0 )
        adata = list(filter(lambda entry: int(entry['ext:score']) >= min_score,
                            musicbrainzngs.search_artists(
                                artist=artist_name, strict = do_strict )['artist-list'] ) )
        return adata

    
    def __init__( self, artist_name ):
        time0 = time.time( )
        #
        ## first get out artist MBID, called ambid, with score = 100
        adata = MusicInfo.get_artist_datas_LL( artist_name, min_score = 100 )
        if len(adata) == 0:
            raise ValueError( 'Could not find artist = %s in MusicBrainz.' % artist_name )
        self.artist = adata[ 0 ]
        self.ambid = self.artist[ 'id' ]
        self.artist_name = artist_name
        logging.debug('found artist %s with artist mbid = %s.' % (
            artist_name, self.ambid ) )
        rgdata = self.get_albums_lowlevel( )
        albums = list( filter(lambda dat: dat['type'] == 'Album', rgdata ) )
        with multiprocessing.Pool( processes = multiprocessing.cpu_count( ) ) as pool:
            self.alltrackdata = dict(
                pool.map( self.get_album_info, albums  ) )
        logging.debug( 'processed %d albums for %s in %0.3f seconds.' % (
            len( self.alltrackdata ), artist_name, time.time( ) - time0 ) )
        
    #
    ## now get all the albums of this artist.
    ## musicbrainz probably does a "make functionality so general that easy use cases
    ## are much harder than expected" implementation.
    ##
    ## first, get all the release-groups of the artist
    def get_albums_lowlevel( self ):
        rgdata = musicbrainzngs.get_artist_by_id(
            self.ambid, includes='release-groups',
            release_type=['album'] )['artist']['release-group-list']
        return rgdata

    def get_album_info( self, album ):
        time0 = time.time( )
        rgid = album['id']
        rgdate = album['first-release-date']
        rtitle = album['title']
        rgdate_date = None
        for fmt in ( '%Y-%m-%d', '%Y-%m', '%Y' ):
            try:
                rgdata_date = datetime.datetime.strptime(
                    rgdate, fmt ).date( )
            except: pass
        if rgdate is None:
            print("Error, could not find correct release info for %s because no date defined." % rtitle )
            return None
        rdata = musicbrainzngs.get_release_group_by_id( rgid, includes=['releases'] )[
            'release-group']['release-list']
        try:
            release = list(filter(lambda dat: 'date' in dat and dat['date'] == rgdate, rdata ) )
            if len( release ) == 0:
                logging.debug("Error, could not find correct release info for %s." % rtitle )
                return None
            release = release[ 0 ]
        except Exception as e:
            logging.debug("Error, could not find correct release info for %s." % rtitle )
            return None
        rid = release['id']
        trackinfo = musicbrainzngs.get_release_by_id( rid, includes = ['recordings'] )[
            'release']['medium-list']
        #
        ## collapse multiple discs into single disk with more tracknumbers
        track_counts = list(map(lambda cd_for_track: cd_for_track['track-count'], trackinfo))
        act_counts = numpy.concatenate([ [ 0, ], numpy.cumsum( track_counts ) ])
        albumdata = { 'release-date' : rgdata_date }
        albumdata[ 'tracks' ] = { }
        alltracknos = set(range(1, 1 + act_counts[-1]))
        for idx, cd_for_track in enumerate( trackinfo ):
            assert( len( cd_for_track[ 'track-list' ]) == cd_for_track[ 'track-count' ] )
            for track in cd_for_track[ 'track-list' ]:
                try: number = int( track[ 'position' ] )
                except:
                    logging.debug( 'error, track = %s does not have defined position.' % track )
                    return None
                title = track[ 'recording' ][ 'title' ]
                albumdata[ 'tracks' ][ act_counts[ idx ] + number ] = title
        assert( set( albumdata[ 'tracks' ] ) == alltracknos )
        logging.debug( 'processed %s in %0.3f seconds.' % ( rtitle, time.time( ) - time0 ) )
        return rtitle, albumdata

@contextmanager
def gmusicmanager( useMobileclient = False ):
    mmg = get_gmusicmanager( useMobileclient = useMobileclient )
    try: yield mmg
    finally: mmg.logout( )

def get_gmusicmanager( useMobileclient = False ):
    if not useMobileclient:
        mmg = gmusicapi.Musicmanager( )
        credentials = plexcore.oauthGetOauth2ClientGoogleCredentials( )
        if credentials is None:
            raise ValueError( "Error, do not have Google Music credentials." )
        mmg.login( oauth_credentials = credentials )
    else:
        mmg = gmusicapi.Mobileclient( )
        val = session.query( PlexConfig ).filter(
            PlexConfig.service == 'gmusic' ).first( )
        if val is None:
            raise ValueError( "Error, do not have Google Music credentials." )
        data = val.data
        email = data['email'].strip( )
        password = data['password'].strip( )
        mmg.login( email, password, gmusicapi.Mobileclient.FROM_MAC_ADDRESS )
    return mmg

"""
Took stuff from http://unofficial-google-music-api.readthedocs.io/en/latest/usage.html#usage                                                                    
"""
def save_gmusic_creds( email, password ):
    query = session.query( PlexConfig ).filter( PlexConfig.service == 'gmusic' )
    val = query.first( )
    if val is not None:
        session.delete( val )
        session.commit( )
    newval = PlexConfig(
        service = 'gmusic',
        data = { 'email' : email.strip( ),
                 'password' : password.strip( ) } )
    session.add( newval )
    session.commit( )

def get_gmusic_all_songs( ):
    with gmusicmanager( useMobileclient = True ) as mmg:
        allSongs = mmg.get_all_songs( )
        allSongsDict = dict( map(lambda song: (
            song.get('id'),
            {
                "album":       song.get('album').encode('utf-8'),
                "artist":      song.get('artist').encode('utf-8'),
                "name":        song.get('title').encode('utf-8'),
                "trackNumber": song.get('trackNumber'),
                "playCount":   song.get('playCount')
            } ), allSongs ) )
        return allSongsDict

def upload_to_gmusic(filenames):
    filenames_valid = list(filter(lambda fname: os.path.isfile(fname), set(filenames)))
    if len(filenames_valid) != 0:
        with gmusicmanager( useMobileclient = False ) as mmg:
            mmg.upload(filenames_valid)
        
def get_youtube_service( ):
    credentials = plexcore.oauthGetGoogleCredentials( )
    if credentials is None:
        raise ValueError( "Error, could not build the YouTube service." )
    youtube = build( "youtube", "v3", credentials = credentials ) 
    #outube = build( "youtube", "v3", http = credentials.authorize(httplib2.Http()))
    return youtube

def fill_m4a_metadata( filename, data_dict ):
    assert( os.path.isfile( filename ) )
    assert( os.path.basename( filename ).lower( ).endswith( '.m4a' ) )
    #
    ## now start it off
    mp4tags = mutagen.mp4.MP4( filename )
    mp4tags[ '\xa9nam' ] = [ data_dict[ 'song' ], ]
    mp4tags[ '\xa9alb' ] = [ data_dict[ 'album' ], ]
    mp4tags[ '\xa9ART' ] = [ data_dict[ 'artist' ], ]
    mp4tags[ 'aART' ] = [ data_dict[ 'artist' ], ]
    if 'year' in data_dict: mp4tags[ '\xa9day' ] = [ str(data_dict[ 'year' ]), ]
    mp4tags[ 'trkn' ] = [ ( data_dict[ 'tracknumber' ],
                            data_dict[ 'total tracks' ] ), ]
    if data_dict[ 'album url' ] != '':
        with BytesIO( requests.get( data_dict[ 'album url' ] ).content ) as csio, BytesIO( ) as csio2:
            img = Image.open( csio )
            img.save( csio2, format = 'png' )
            mp4tags[ 'covr' ] = [
                mutagen.mp4.MP4Cover( csio2.getvalue( ),
                                      mutagen.mp4.MP4Cover.FORMAT_PNG ), ]
    mp4tags.save( )

def get_youtube_file( youtube_URL, outputfile ):
    assert( os.path.basename( outputfile ).lower( ).endswith( '.m4a' ) )
    ydl_opts = { 'format' : '140',
                 'outtmpl' : outputfile }
    with youtube_dl.YoutubeDL( ydl_opts ) as ydl:
        ydl.download([ youtube_URL ])

def youtube_search(youtube, query, max_results = 10):
    assert( max_results >= 5 )
    search_response = youtube.search().list(
        q=query,
        order="relevance",
        type="video",
        part="id,snippet",
        #part="id",
        maxResults=50).execute()

    search_videos = list( map(lambda search_result:
                              search_result['id']['videoId'],
                              search_response.get('items', []) ) )
    # Merge video ids
    video_ids = ",".join(search_videos)
    if len( search_videos ) == 0:
        return

    # Call the videos.list method to retrieve details for each video.
    video_response = youtube.videos().list(
        id=video_ids,
        part='snippet, recordingDetails, contentDetails'
    ).execute()

    videos = []
    # Add each result to the list, and then display the list of matching videos.
    for video_result in video_response.get("items", [])[:max_results]:
        duration_string = video_result['contentDetails']['duration']
        try:
            dt_duration = parse_youtube_date( duration_string )
            dstring = format_youtube_date( dt_duration )
            videos.append(("%s (%s)" % ( video_result["snippet"]["title"], dstring ),
                           urljoin("https://youtu.be", video_result['id'] ) ) )
        except Exception as e:
            print( e )
            pass
    return videos

class PlexLastFM( object ):
    
    @classmethod
    def push_lastfm_credentials( cls, api_data ):
        assert( len(set(api_data) - set([ 'api_key', 'api_secret', 'application_name',
                                          'username' ]) ) == 0 )
        query = session.query( PlexConfig ).filter(
            PlexConfig.service == 'lastfm' )
        val = query.first( )
        if val is not None:
            session.delete( val )
            session.commit( )
        session.add(
            PlexConfig( service = 'lastfm',
                        data = { key : api_data[key] for key in
                                 ( 'api_key', 'api_secret', 'application_name', 'username' ) } ) )
        session.commit( )
    
    @classmethod
    def get_lastfm_credentials( cls ):
        query = session.query( PlexConfig ).filter(
            PlexConfig.service == 'lastfm' )
        val = query.first( )
        if val is None:
            raise ValueError("ERROR, LASTFM CREDENTIALS NOT FOUND" )
        data = val.data
        return { key : data[key] for key in
                 ( 'api_key', 'api_secret', 'application_name', 'username' ) }
        
    @classmethod
    def get_album_url( cls, album_url_entries ):
        sorting_list_size = { 'large' : 0,
                              'extralarge' : 1,
                              'mega' : 2, 'medium' : 3, 'small' : 4,
                              '' : 5 }
        sorted_entries = sorted( filter(lambda entry: 'size' in entry and
                                        '#text' in entry and
                                        entry['size'] in sorting_list_size, album_url_entries ),
                                 key = lambda entry: sorting_list_size[ entry['size'] ] )
        if len( sorted_entries ) == 0: return None
        return sorted_entries[ 0 ][ '#text' ]

    @classmethod
    def get_album_release_year( cls, album_mbid ):
        # this uses the MusicBrainz REST API to get release info
        endpoint = 'https://musicbrainz.org/ws/2/release/'
        headers = {'User-Agent': 'TanimIslamMusicBrainz/1.0 (***REMOVED***.islam@gmail.com)'}
        response = requests.get( urljoin( endpoint, album_mbid ), headers = headers,
                                 params = { 'fmt' : 'json' } )
        if response.status_code != 200: return None
        data = response.json( )
        if 'date' not in data: return None
        try: release_date = datetime.datetime.strptime( data['date'], '%Y-%m-%d' ).date( )
        except: release_date = datetime.datetime.strptime( data['date'], '%Y' ).date( )
        return release_date.year
    
    def __init__( self ):
        data = PlexLastFM.get_lastfm_credentials( )
        self.api_key = data[ 'api_key' ]
        self.api_secret = data[ 'api_secret' ]
        self.application_name = data[ 'application_name' ]
        self.username = data[ 'username' ]
        self.endpoint = 'http://ws.audioscrobbler.com/2.0'

    def get_collection_album_info( self, album_name ):
        response = requests.get( self.endpoint,
                                 params = { 'method' : 'album.search',
                                            'album' : album_name,
                                            'api_key' : self.api_key,
                                            'format' : 'json',
                                            'lang' : 'en' } )
        data = response.json( )
        if 'error' in data:
            return None, "ERROR: %s" % data['message']
        return data, 'SUCCESS'
        
        
    def get_album_info( self, artist_name, album_name ):
        response = requests.get( self.endpoint,
                                 params = { 'method' : 'album.getinfo',
                                            'album' : album_name,
                                            'artist' : artist_name,
                                            'api_key' : self.api_key,
                                            'format' : 'json',
                                            'lang' : 'en' } )
        data = response.json( )
        if 'error' in data:
            return None, "ERROR: %s" % data['message']
        return data['album'], 'SUCCESS'
        
    def get_album_image( self, artist_name, album_name ):
        album, status = self.get_album_info( artist_name, album_name )
        if status != 'SUCCESS':
            return None, status
        if 'image' not in album:
            error_message = 'Could not find album art for album = %s for artist = %s.' % (
                album_name, artist_name )
            return None, error_message
        album_url = PlexLastFM.get_album_url( album[ 'image' ] )
        if album_url is None:
            error_message = "Could not find album art for album = %s for artist = %s." % (
                album_name, artist_name )
            return None, error_message
        filename = '%s.%s.png' % ( artist_name, album_name.replace('/', '-' ) )
        img = Image.open( BytesIO( requests.get( album_url ).content ) )
        img.save( filename, format = 'png' )
        os.chmod( filename, 0o644 )
        return filename, 'SUCCESS'
        
    def get_song_listing( self, artist_name, album_name ):
        album, status = self.get_album_info( artist_name, album_name )
        if status != 'SUCCESS': return None, status
        track_listing = sorted(map(lambda track: ( titlecase.titlecase( track['name'] ),
                                                   int( track[ '@attr' ][ 'rank' ] ) ),
                                   album['tracks']['track'] ), key = lambda tup: tup[1] )
        return track_listing, 'SUCCESS'

    #
    ## note that lastfm does not provide a releasedate at all. This music metadata is not going to arrive at all
    ## see, e.g., https://github.com/pylast/pylast/issues/177.
    ## also, https://github.com/feross/last-fm/issues/2.
    ## documentation found here, https://www.last.fm/api/show/album.getInfo, is incorrect.
    def get_music_metadata( self, song_name, artist_name, all_data = False ):
        response = requests.get( self.endpoint,
                                 params = { 'method' : 'track.getinfo',
                                            'artist' : artist_name,
                                            'track' : titlecase.titlecase( song_name ),
                                            'autocorrect' : 1,
                                            'api_key' : self.api_key,
                                            'format' : 'json',
                                            'lang' : 'en' } )
        data = response.json( )
        if 'error' in data:
            return None, "ERROR: %s" % data[ 'message' ]
        track = data['track']
        #
        ## now see if we have an album with mbid
        if 'mbid' in track[ 'album' ]:
            album_mbid = track[ 'album' ][ 'mbid' ]
            album_year = PlexLastFM.get_album_release_year( album_mbid )
        else: album_year = None
        music_metadata = { 'artist' : track['artist']['name'],
                           'song' : titlecase.titlecase( track['name'] ),
                           'album' : track[ 'album' ][ 'title' ],
                           'duration' : float(track['duration']) * 1e-3 }
        if album_year is not None:
            music_metadata[ 'year' ] = album_year
        if 'image' in track[ 'album' ]:
            album_url = PlexLastFM.get_album_url( track[ 'album' ][ 'image' ] )
            if album_url is not None:
                music_metadata[ 'album url' ] = album_url
        if not all_data:
            return music_metadata, 'SUCCESS'
        #
        ## now if we want to get total number of tracks for this album, and track number for song
        track_listing, status = self.get_song_listing( artist_name = artist_name,
                                                       album_name = track[ 'album' ][ 'title' ] )
        if track_listing is None:
            return music_metadata, 'SUCCESS'
        track_listing_dict = dict( track_listing )
        if titlecase.titlecase( song_name ) in track_listing_dict or song_name in track_listing_dict:
            music_metadata[ 'tracknumber' ] = track_listing_dict[
                titlecase.titlecase( song_name ) ]
            music_metadata[ 'total tracks' ] = len( track_listing_dict )
        else:
            music_metadata[ 'tracknumber' ] = 1
            music_metadata[ 'total tracks' ] = 1
        return music_metadata, 'SUCCESS'

    def get_music_metadatas_album( self, artist_name, album_name ):
        album, status = self.get_album_info( artist_name = artist_name,
                                             album_name = album_name )
        if status != 'SUCCESS':
            return None, status
        if len( album[ 'tracks' ][ 'track' ] ) == 0:
            return None, "Error, could find no tracks for artist = %s, album = %s." % (
                artist_name, album_name )
        track_listing = sorted(map(lambda track: ( titlecase.titlecase( track['name'] ),
                                                   int( track[ '@attr' ][ 'rank' ] ),
                                                   float( track[ 'duration' ] ) ),
                                   album['tracks']['track'] ), key = lambda tup: tup[1] )
        if 'mbid' in album:
            album_mbid = album['mbid']
            album_year = PlexLastFM.get_album_release_year( album_mbid )
        else: album_year = None
        if album_year is not None:
            album_data_dict = list( map(lambda title_num:
                                    { 'song' : titlecase.titlecase( title_num[ 0 ] ),
                                      'artist' : album[ 'artist' ],
                                      'tracknumber' : title_num[ 1 ],
                                      'total tracks' : len( track_listing ),
                                      'duration' : title_num[ 2 ],
                                      'year' : album_year,
                                      'album url' : PlexLastFM.get_album_url( album[ 'image' ] ),
                                      'album' : album[ 'name' ] },
                                    track_listing ) )
        else:
            album_data_dict = list( map(lambda title_num:
                                    { 'song' : titlecase.titlecase( title_num[ 0 ] ),
                                      'artist' : album[ 'artist' ],
                                      'tracknumber' : title_num[ 1 ],
                                      'total tracks' : len( track_listing ),
                                      'duration' : title_num[ 2 ],
                                      'album url' : PlexLastFM.get_album_url( album[ 'image' ] ),
                                      'album' : album[ 'name' ] },
                                    track_listing ) )
            
        return album_data_dict, 'SUCCESS'
    
class PlexMusic( object ):
    
    @classmethod
    def push_gracenote_credentials( cls, client_ID ):
        try:
            userID = pygn.register( client_ID )
            query = session.query( PlexConfig ).filter(
                PlexConfig.service == 'gracenote' )
            val = query.first( )
            if val is not None:
                session.delete( val )
                session.commit( )
            session.add(
                PlexConfig( service = 'gracenote',
                            data = { 'clientID' : client_ID,
                                     'userID' : userID } ) )
            session.commit( )
        except:
            raise ValueError("Error, %s is invalid." % client_ID )

    @classmethod
    def get_gracenote_credentials( cls ):
        query = session.query( PlexConfig ).filter(
            PlexConfig.service == 'gracenote' )
        val = query.first( )
        if val is None:
            raise ValueError("ERROR, GRACENOTE CREDENTIALS NOT FOUND" )
        data = val.data
        clientID = data['clientID']
        userID = data['userID']
        return clientID, userID
    
    def __init__( self ):
        self.clientID, self.userID = PlexMusic.get_gracenote_credentials( )

    def get_album_image( self, artist_name, album_name ):
        metadata_album = pygn.search( clientID = self.clientID, userID = self.userID,
                                      album = album_name,
                                      artist = titlecase.titlecase( artist_name ) )
        if 'album_art_url' not in metadata_album or len( metadata_album[ 'album_art_url' ].strip( ) ) == 0:
            return None, 'Could not find album = %s for artist = %s.' % (
                album_name, titlecase.titlecase( artist_name ) )
        filename = '%s.%s.png' % ( artist_name, album_name.replace('/', '-') )
        img = Image.open( BytesIO( requests.get( metadata_album[ 'album_art_url' ] ).content ) )
        img.save( filename, format = 'png' )
        os.chmod( filename, 0o644 )
        return filename, 'SUCCESS'
    
    def get_song_listing( self, artist_name, album_name ):
        metadata_album = pygn.search( clientID = self.clientID, userID = self.userID,
                                      album = album_name,
                                      artist = titlecase.titlecase( artist_name ) )
        track_listing = sorted(map(lambda track: ( track['track_title'], int( track['track_number'])),
                                   metadata_album['tracks']), key = lambda title_num: title_num[1] )
        return track_listing

    def get_music_metadata_lowlevel( self, metadata_song, album_title = None ):
        song_name = titlecase.titlecase( metadata_song[ 'track_title' ] )
        track_number = int( metadata_song[ 'track_number' ] )
        if album_title is None: album_title = metadata_song[ 'album_title' ]
        artist_name = metadata_song[ 'album_artist_name' ]
        metadata_album = pygn.search(clientID = self.clientID, userID = self.userID,
                                     artist = titlecase.titlecase( artist_name ),
                                     album = album_title )
        total_tracks = len( metadata_album['tracks'] )
        album_url = ''
        if 'album_art_url' in metadata_album:
            album_url = metadata_album[ 'album_art_url' ]
        try:
            album_year = int( metadata_album[ 'album_year' ] )
        except:
            album_year = 1900
        data_dict = { 'song' : titlecase.titlecase( song_name ),
                      'artist' : artist_name,
                      'tracknumber' : track_number,
                      'total tracks' : total_tracks,
                      'year' : album_year,
                      'album url' : album_url,
                      'album' : album_title }
        return data_dict, 'SUCCESS'

    def get_music_metadatas_album( self, artist_name, album_name ):
        metadata_album = pygn.search( clientID = self.clientID, userID = self.userID,
                                      album = album_name,
                                      artist = artist_name )
        if titlecase.titlecase( album_name ) != \
           titlecase.titlecase( metadata_album[ 'album_title' ] ):
            return None, 'COULD NOT FIND ALBUM = %s FOR ARTIST = %s' % (
                album_name, artist_name )
        album_url = ''
        if 'album_art_url' in metadata_album:
            album_url = metadata_album[ 'album_art_url' ]
        try:
            album_year = int( metadata_album[ 'album_year' ] )
        except:
            album_year = 1900
        total_tracks = len( metadata_album['tracks'] )
        track_listing = sorted(map(lambda track: ( track['track_title'],
                                                   int( track['track_number'] ) ),
                                   metadata_album['tracks']),
                               key = lambda title_num: title_num[1] )
        album_data_dict = sorted(map(lambda title_num:
                                     { 'song' : titlecase.titlecase( title_num[ 0 ] ),
                                       'artist' : artist_name,
                                       'tracknumber' : title_num[ 1 ],
                                       'total tracks' : total_tracks,
                                       'year' : album_year,
                                       'album url' : album_url,
                                       'album' : album_name },
                                     track_listing ), key = lambda tok: tok['tracknumber'])
        return album_data_dict, 'SUCCESS'

    def get_music_metadata( self, song_name, artist_name ):
        metadata_song = pygn.search( clientID = self.clientID, userID = self.userID,
                                     artist = artist_name,
                                     track = titlecase.titlecase( song_name ) )
        #
        ## now see if I can get the necessary metadata
        if 'album_artist_name' not in metadata_song:
            return None, "ERROR, COULD NOT FIND ARTIST = %s" % artist_name
        if metadata_song[ 'album_artist_name' ] != artist_name:
            return None, "ERROR, COULD NOT FIND ARTIST = %s" % artist_name
        #
        if 'track_title' not in metadata_song:
            return None, 'ERROR, COULD NOT FIND SONG = %s FOR ARTIST = %s.' % (
                titlecase.titlecase( song_name ), artist_name )
        if titlecase.titlecase( metadata_song['track_title'] ) != \
           titlecase.titlecase( song_name ):
            return None, "ERROR, COULD NOT FIND ARTIST = %s, SONG = %s." % (
                artist_name, titlecase.titlecase( song_name ) )
        #
        if 'album_title' not in metadata_song:
            return None, "ERROR, COULD NOT FIND ALBUM FOR ARTIST = %s, SONG = %s." % (
                artist_name, titlecase.titlecase( song_name ) )
        #
        if 'track_number' not in metadata_song:
            return None, "ERROR, COULD NOT FIND TRACK NUMBER FOR ARTIST = %s, SONG = %s." % (
                artist_name, titlecase.titlecase( song_name ) )
        #
        ##
        return self.get_music_metadata_lowlevel( metadata_song )
