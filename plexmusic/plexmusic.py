import os, sys, glob, numpy, titlecase, mutagen.mp4, httplib2
import requests, apiclient.discovery
from cStringIO import StringIO
from urlparse import urljoin
from . import mainDir, pygn, parse_youtube_date, format_youtube_date
from ConfigParser import RawConfigParser
from plexstuff.plexcore import plexcore

def get_youtube_service( ):
    credentials = plexcore.getOauthYoutubeCredentials( )
    if credentials is None:
        raise ValueError( "Error, could not build the YouTube service." )
    youtube = apiclient.discovery.build( "youtube", "v3",
                                         http = credentials.authorize(httplib2.Http()))
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

def fill_m4a_metadata( filename, artist_name, song_name ):
    assert( os.path.isfile( filename ) )
    assert( os.path.basename( filename ).lower( ).endswith( '.m4a' ) )
    #
    ## now start it off
    pm = PlexMusic( )
    data_dict, status = pm.get_music_metadata( song_name = song_name,
                                               artist_name = artist_name )
    if status != 'SUCCESS':
        print 'ERROR, %s' % status
        return
    mp4tags = mutagen.mp4.MP4( filename )
    mp4tags[ '\xa9nam' ] = [ data_dict[ 'song' ], ]
    mp4tags[ '\xa9alb' ] = [ data_dict[ 'album' ], ]
    mp4tags[ '\xa9ART' ] = [ data_dict[ 'artist' ], ]
    mp4tags[ 'aART' ] = [ data_dict[ 'artist' ], ]
    mp4tags[ '\xa9day' ] = [ str(data_dict[ 'year' ]), ]
    mp4tags[ 'trkn' ] = [ ( data_dict[ 'tracknumber' ],
                            data_dict[ 'total tracks' ] ), ]
    if data_dict[ 'album url' ] != '':
        csio = StringIO( requests.get( data_dict[ 'album url' ] ).content )
        img = Image.open( csio )
        csio2 = StringIO( )
        img.save( csio2, format = 'png' )
        mp4tags[ 'covr' ] = [ mutagen.mp4.MP4Cover( csio2.getvalue( ), mutagen.mp4.MP4Cover.FORMAT_PNG ), ]
        csio.close( )
        csio2.close( )
    mp4tags.save( )


def youtube_search(youtube, query, max_results = 10):
    assert( max_results >= 5 )
    search_response = youtube.search().list(
        q=query,
        order="relevance",
        type="video",
        part="id,snippet",
        #part="id",
        maxResults=50).execute()

    search_videos = map(lambda search_result:
                        search_result['id']['videoId'],
                        search_response.get('items', []) )
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
            print e
            pass
    return videos

class PlexMusic( object ):
    def __init__( self ):
        self.clientID, self.userID = get_gracenote_credentials( )

    def get_music_metadata( self, song_name, artist_name ):
        metadata_song = pygn.search( clientID = self.clientID, userID = self.userID,
                                     artist = titlecase.titlecase( artist_name ),
                                     track = titlecase.titlecase( song_name ) )
        if titlecase.titlecase( metadata_song['track_title'] ) != \
           titlecase.titlecase( song_name ):
            return None, "ERROR, COULD NOT FIND ARTIST = %s, SONG = %s." % (
                titlecase.titlecase( artist_name ), titlecase.titlecase( song_name ) )
        #
        ## now see if I can get the album name
        if 'album_title' not in metadata_song:
            return None, "ERROR, COULD NOT FIND ALBUM FOR ARTIST = %s, SONG = %s." % (
                titlecase.titlecase( artist_name ), titlecase.titlecase( song_name ) )
        if 'track_number' not in metadata_song:
            return None, "ERROR, COULD NOT FIND TRACK NUMBER FOR ARTIST = %s, SONG = %s." % (
                titlecase.titlecase( artist_name ), titlecase.titlecase( song_name ) )
        track_number = int( metadata_song[ 'track_number' ] )
        album_title = metadata_song[ 'album_title' ]
        metadata_album = pygn.search(clientID = self.clientID, userID = self.userID,
                                     artist = titlecase.titlecase( artist_name ),
                                     album = album_title )
        total_tracks = len( metadata_album['tracks'] )
        album_url = ''
        if 'album_art_url' in metadata_album:
            album_url = metadata_album[ 'album_art_url' ]
        album_year = int( metadata_album[ 'album_year' ] )
        data_dict = { 'song' : titlecase.titlecase( song_name ),
                      'artist' : titlecase.titlecase( artist_name ),
                      'tracknumber' : track_number,
                      'total tracks' : total_tracks,
                      'year' : album_year,
                      'album url' : album_url,
                      'album' : titlecase.titlecase( album_title ) }
        return data_dict, 'SUCCESS'
