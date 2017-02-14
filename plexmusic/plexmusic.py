import os, sys, glob, numpy, titlecase
from . import mainDir, pygn
try:
    from ConfigParser import RawConfigParser
except:
    from configparser import RawConfigParser

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
