#!/usr/bin/env python3

import sys, os, signal
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
from plexmusic import plexmusic
from optparse import OptionParser

def choose_youtube_item( name, maxnum = 10, verify = True ):
    youtube = plexmusic.get_youtube_service( verify = verify )
    videos = plexmusic.youtube_search( youtube, name, max_results = maxnum )
    if len( videos ) != 1:
        sortdict = { idx + 1 : item for (idx, item) in enumerate(videos) }
        bs = 'Choose YouTube video:\n%s\n' % '\n'.join(
            map(lambda idx: '%d: %s' % ( idx, sortdict[ idx ][ 0 ] ),
                sorted( sortdict ) ) )
        iidx = input( bs )
        try:
            iidx = int( iidx.strip( ) )
            if iidx not in sortdict:
                print('Error, need to choose one of the YouTube videos. Exiting...')
                return None
            _, youtubeURL = sortdict[ iidx ]
        except:
            print('Error, did not choose a valid integer. Exiting...')
            return None
    elif len( videos ) == 1:
        _, youtubeURL = videos[0]
    else:
        print('Could find no YouTube videos: %s' % name)
        return None
    return youtubeURL

def main( ):
    parser = OptionParser( )
    parser.add_option( '-s', '--songs', dest='song_names', type=str, action='store',
                       help = 'Names of the song to put into M4A files. Separated by ;' )
    parser.add_option( '-a', '--artist', dest='artist_name', type=str, action='store',
                       help = 'Name of the artist to put into the M4A file.' )
    parser.add_option( '--maxnum', dest='maxnum', type=int, action='store',
                       default = 10, help =' '.join([ 
                           'Number of YouTube video choices to choose for your song.',
                           'Default is 10.' ]) )
    parser.add_option( '-A', '--album', dest='album_name', type=str, action='store',
                       help = 'If defined, then use ALBUM information to get all the songs in order from the album.' )
    parser.add_option( '--noverify', dest='do_verify', action='store_false', default = True,
                       help = 'If chosen, do not verify SSL connections.' )
    opts, args = parser.parse_args( )
    assert( opts.artist_name is not None )
    assert( len(list(filter(lambda tok: tok is not None, ( opts.song_names, opts.album_name ) ) ) ) == 1 ), "error, must choose one of --songs or --album"
    #
    ## first get music metadata
    pm = plexmusic.PlexMusic( verify = opts.do_verify )

    if opts.album_name is not None:
        album_data_dict, status = pm.get_music_metadatas_album(
            opts.artist_name, opts.album_name )
        if status != 'SUCCESS':
            print( status )
            return
        data_dict = album_data_dict[ 0 ]
        artist_name = data_dict[ 'artist' ]
        album_name = data_dict[ 'album' ]
        album_year = data_dict[ 'year' ]
        album_tracks = data_dict[ 'total tracks' ]        
        print( 'ACTUAL ARTIST: %s' % artist_name )
        print( 'ACTUAL ALBUM: %s' % album_name )
        print( 'ACTUAL YEAR: %d' % album_year )
        print( 'ACTUAL NUM TRACKS: %d' % album_tracks )
        for data_dict in album_data_dict:
            song_name = data_dict[ 'song' ]
            print( 'ACTUAL SONG: %s' % song_name )
            #
            ## now get the youtube song selections
            youtubeURL = choose_youtube_item(
                '%s %s' % ( artist_name, song_name ),
                maxnum = opts.maxnum, verify = opts.do_verify )
            
            if youtubeURL is None:
                continue
            #
            ## now download the song into the given filename
            filename = '%s.%s.m4a' % ( artist_name, song_name )
            plexmusic.get_youtube_file( youtubeURL, filename )
            #
            ## now fill out the metadata
            plexmusic.fill_m4a_metadata( filename, data_dict )
            #
            ##
            os.chmod( filename, 0o644 )
    else:
        assert( opts.song_names is not None )
        song_names = map(lambda song_name: song_name.strip( ), opts.song_names.split(';'))
        for song_name in song_names:
            try:
                data_dict, status = pm.get_music_metadata(
                    song_name = song_name,
                    artist_name = opts.artist_name )
                if status != 'SUCCESS':
                    print( status )
                    continue
            except Exception as e:
                print( e )
                continue
            artist_name = data_dict[ 'artist' ]
            song_name = data_dict[ 'song' ]
            album_name = data_dict[ 'album' ]
            print( 'ACTUAL ARTIST: %s' % artist_name )
            print( 'ACTUAL ALBUM: %s' % album_name )
            print( 'ACTUAL SONG: %s' % song_name )
            #
            ## now get the youtube song selections
            youtubeURL = choose_youtube_item( '%s %s' % ( artist_name, song_name ),
                                              maxnum = opts.maxnum )
            if youtubeURL is None:
                continue
            #
            ## now download the song into the given filename
            filename = '%s.%s.m4a' % ( artist_name, song_name )
            plexmusic.get_youtube_file( youtubeURL, filename )
            #
            ## now fill out the metadata
            plexmusic.fill_m4a_metadata( filename, data_dict )
            #
            ##
            os.chmod( filename, 0o644 )
    
if __name__=='__main__':
    main( )
        
