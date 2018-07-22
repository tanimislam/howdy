import os, sys, glob, numpy, titlecase, mutagen.mp4, httplib2
import requests, youtube_dl, gmusicapi
from contextlib import contextmanager
from googleapiclient.discovery import build
from PIL import Image
from io import StringIO, BytesIO
from urllib.parse import urljoin
from configparser import RawConfigParser
from . import mainDir, pygn, parse_youtube_date, format_youtube_date
from plexcore import plexcore, baseConfDir

#
## gmusicapi stuff
def _get_gmusic_resource_abspath( ):
    filename = 'gmusic_credentials.conf'
    absPath = os.path.join( baseConfDir, filename )
    return absPath

_gmusic_absPath = _get_gmusic_resource_abspath( )

@contextmanager
def gmusicmanager( useMobileclient = False ):
    mmg = get_gmusicmanager( useMobileclient = useMobileclient )
    try: yield mmg
    finally: mmg.logout( )

def get_gmusicmanager( useMobileclient = False ):
    if not useMobileclient:
        mmg = gmusicapi.Musicmanager( )
        mmg.login( oauth_credentials = os.path.join( baseConfDir, 'google_authentication.json' ) )
    else:
        mmg = gmusicapi.Mobileclient( )
        if not os.path.isfile( _gmusic_absPath ):
            raise ValueError( "Error, default configuration file = %s does not exist." % absPath )
        cparser = RawConfigParser( )
        cparser.read( _gmusic_absPath )
        if not cparser.has_section( 'GMUSIC_CREDENTIALS' ):
            raise ValueError( "Error, configuration file has not defined GMUSIC_CREDENTIALS." )
        if not all([ cparser.has_option('GMUSIC_CREDENTIALS', tok) for tok in
                     ( 'email', 'password' ) ]):
            raise ValueError( "Error, configuration file has not defined both email and password." )
        email = cparser.get( 'GMUSIC_CREDENTIALS', 'email' )
        password = cparser.get( 'GMUSIC_CREDENTIALS', 'password' )
        mmg.login( email, password, gmusicapi.Mobileclient.FROM_MAC_ADDRESS )
    return mmg

"""
Took stuff from http://unofficial-google-music-api.readthedocs.io/en/latest/usage.html#usage                                                                    
"""
def save_gmusic_creds( email, password ):
    cparser = RawConfigParser( )
    cparser.add_section( 'GMUSIC_CREDENTIALS' )
    cparser.set( 'GMUSIC_CREDENTIALS', 'email', email )
    cparser.set( 'GMUSIC_CREDENTIALS', 'password', password )
    with open( _gmusic_absPath, 'w') as openfile:
        cparser.write( openfile )
    os.chmod( _gmusic_absPath, 0o600 )

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
    youtube = build( "youtube", "v3", http = credentials.authorize(httplib2.Http()))                     
    return youtube

def push_gracenote_credentials( client_ID ):
    try:
        userID = pygn.register( client_ID )
        cParser = RawConfigParser( )
        cParser.add_section( 'GRACENOTE' )
        cParser.set( 'GRACENOTE', 'clientID', client_ID )
        cParser.set( 'GRACENOTE', 'userID', userID )
        absPath = os.path.join( mainDir, 'resources', 'gracenote_api.conf' )
        with open( absPath, 'w') as openfile:
            cParser.write( openfile )
        os.chmod( absPath, 0o600 )
    except:
        raise ValueError("Error, %s is invalid." % client_ID )

def get_gracenote_credentials( ):
    cParser = RawConfigParser( )
    absPath = os.path.join( mainDir, 'resources', 'gracenote_api.conf' )
    if not os.path.isfile( absPath ):
        raise ValueError("ERROR, GRACENOTE CREDENTIALS NOT FOUND" )
    cParser.read( absPath )
    if not cParser.has_section( 'GRACENOTE' ):
        raise ValueError("Error, gracenote_api.conf does not have a GRACENOTE section.")
    if not cParser.has_option( 'GRACENOTE', 'clientID' ):
        raise ValueError("Error, conf file does not have clientID.")
    if not cParser.has_option( 'GRACENOTE', 'userID' ):
        raise ValueError("Error, conf file does not have userID.")
    return cParser.get( "GRACENOTE", "clientID" ), cParser.get( "GRACENOTE", "userID" )

#def fill_m4a_metadata( filename, artist_name, song_name ):
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
    mp4tags[ '\xa9day' ] = [ str(data_dict[ 'year' ]), ]
    mp4tags[ 'trkn' ] = [ ( data_dict[ 'tracknumber' ],
                            data_dict[ 'total tracks' ] ), ]
    if data_dict[ 'album url' ] != '':
        csio = BytesIO( requests.get( data_dict[ 'album url' ] ).content )
        csio2 = BytesIO( )
        img = Image.open( csio )
        img.save( csio2, format = 'png' )
        mp4tags[ 'covr' ] = [
            mutagen.mp4.MP4Cover( csio2.getvalue( ),
                                  mutagen.mp4.MP4Cover.FORMAT_PNG ), ]
        csio.close( )
        csio2.close( )
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
    
class PlexMusic( object ):
    def __init__( self ):
        self.clientID, self.userID = get_gracenote_credentials( )

    def get_album_image( self, artist_name, album_name ):
        metadata_album = pygn.search( clientID = self.clientID, userID = self.userID,
                                      album = album_name,
                                      artist = titlecase.titlecase( artist_name ) )
        if 'album_art_url' not in metadata_album or len( metadata_album[ 'album_art_url' ].strip( ) ) == 0:
            print( 'Could not find album = %s for artist = %s.' % (
                album_name, titlecase.titlecase( artist_name ) ) )
            return None
        filename = '%s.%s.png' % ( artist_name, album_name.replace('/', '-') )
        img = Image.open( BytesIO( requests.get( metadata_album[ 'album_art_url' ] ).content ) )
        img.save( filename, format = 'png' )
        os.chmod( filename, 0o644 )
        return True, filename
    
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
