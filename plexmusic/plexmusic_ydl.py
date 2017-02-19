from __future__ import unicode_literals
import plexmusic

def download_best_song( artist_name, song_name, youtube = None ):
    if youtube is not None:
        youtube = plexmusic.get_youtube_service( )
    pm = plexmusic.PlexMusic( )
    data_dict, status = pm.get_music_metadata( song_name = song_name,
                                               artist_name = artist_name )
    if status != 'SUCCESS':
        return None
    artist_name = data_dict[ 'artist' ]
    song_name = data_dict[ 'song' ]
    name = '%s %s' % ( artist_name, song_name )
    videos = plexmusic.youtube_search( youtube, name, max_results = 10 )
    if len( videos ) == 0:
        return None
    _, youtubeURL = videos[0]
    filename = '%s.%s.m4a' % ( artist_name, song_name )
    plexmusic.get_youtube_file( youtubeURL, filename )
    plexmusic.fill_m4a_metadata( filename, data_dict )
    return filename
