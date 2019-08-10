#!/usr/bin/env python3

import signal, sys
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import os, datetime, io, zipfile, logging
from plexmusic import plexmusic
from plexcore import plexcore
from plexemail import plexemail, emailAddress
from optparse import OptionParser

def _get_final_song_name( song_name, dur ):
    assert( dur >= 0 )
    if dur < 3600:
        return '%s (%s)' % (
            song_name,
            datetime.datetime.fromtimestamp( dur ).strftime('%M:%S') )
    else:
        return '%s (%s)' % (
            song_name,
            datetime.datetime.fromtimestamp( dur ).strftime('%H:%M:%S') )

def _choose_youtube_item( name, maxnum = 10, verify = True ):
    youtube = plexmusic.get_youtube_service( verify = verify )
    videos = plexmusic.youtube_search( youtube, name, max_results = maxnum )
    if len( videos ) != 1:
        sortdict = { idx + 1 : item for (idx, item) in enumerate(videos) }
        bs = 'Choose YouTube video:\n%s\n' % '\n'.join(
            map(lambda idx: '%d: %s' % ( idx, sortdict[ idx ][ 0 ] ),
                sorted( sortdict ) ) )
        iidx = input( bs )
        if iidx.strip( ).lower( ) == 'qq':
            print( 'Doing a hard quit. Exiting...' )
            sys.exit( 0 )
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

def _download_actual_song( pm, lastfm, s_name, a_name, maxnum, do_lastfm ):
    try:
        if not do_lastfm:
            data_dict, status = pm.get_music_metadata( song_name = s_name,
                                                       artist_name = a_name )
        else: status = 'FAILURE'
        if status != 'SUCCESS':
            data_dict, status = lastfm.get_music_metadata(
                song_name = s_name, artist_name = a_name, all_data = True )
            if status != 'SUCCESS':
                print( 'PROBLEM GETTING %s, %s: %s.' % ( s_name, a_name, status ) )
                return None
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stdout)
        return None

    if 'tracknumber' not in data_dict:
        data_dict[ 'tracknumber' ] = 1
        data_dict[ 'total tracks' ] = 1
    artist_name = data_dict[ 'artist' ]
    song_name = data_dict[ 'song' ]
    album_name = data_dict[ 'album' ]
    if 'duration' in data_dict:
        dur = int( data_dict[ 'duration' ] )
        song_name_after = _get_final_song_name( song_name, dur )
    print( 'ACTUAL ARTIST: %s' % artist_name )
    print( 'ACTUAL ALBUM: %s' % album_name )
    if 'duration' not in data_dict: print( 'ACTUAL SONG: %s' % song_name )
    else: print( 'ACTUAL SONG: %s' % song_name_after )
    #
    ## now get the youtube song selections
    youtubeURL = _choose_youtube_item( '%s %s' % ( artist_name, song_name ),
                                       maxnum = maxnum, verify = pm.verify )
    if youtubeURL is None: return None
    #
    ## now download the song into the given filename
    filename = '%s.%s.m4a' % ( artist_name, song_name )
    plexmusic.get_youtube_file( youtubeURL, filename )
    #
    ## now fill out the metadata
    plexmusic.fill_m4a_metadata( filename, data_dict, verify = pm.verify )
    #
    ##
    os.chmod( filename, 0o644 )
    return ( artist_name, song_name, filename )

def _create_archive_songs( all_songs_downloaded ):
    mf = io.BytesIO( )
    with zipfile.ZipFile( mf, 'w', compression=zipfile.ZIP_DEFLATED ) as zf:                          
        for tup in all_songs_downloaded: zf.write( tup[-1] )
    return mf.getvalue( ), 'songs.zip'

def _email_songs( opts, all_songs_downloaded ):
    if len( all_songs_downloaded ) == 0: return
    # status, _ = plexcore.oauthCheckGoogleCredentials( verify = opts.do_verify )
    # if not status:
    #     print( "Error, do not have correct Google credentials." )
    #    return
    songs_by_list = '\n'.join(map(lambda tup: '\item %s - %s.' % ( tup[0], tup[1] ),
                                  all_songs_downloaded ) )
    num_songs = len( all_songs_downloaded )
    num_artists = len( set( map(lambda tup: tup[0], all_songs_downloaded ) ) )
    if num_songs == 1: num_songs_string = "1 song"
    else: num_songs_string = "%d songs" % num_songs
    if num_artists == 1: num_artists_string = "1 artist"
    else: num_artists_string = "%d artists" % num_artists
    body = """I have emailed you %s from %s:
    \\begin{enumerate}
    %s
    \end{enumerate}
    Have a good day!
    
    Tanim
    """ % ( num_songs_string,
            num_artists_string,
            songs_by_list )
    finalString = '\n'.join([ 'Hello Friend,', '', body ])
    htmlString = plexcore.latexToHTML( finalString )
    subject = 'The %s with %s you requested.' % (
        num_songs_string, num_artists_string )
    # attachData, attachName = _create_archive_songs( all_songs_downloaded )
    attachNames = list(map(lambda tup: tup[-1], all_songs_downloaded ) )
    plexemail.send_individual_email_full_withattachs(
        htmlString, subject, opts.email,
        name = opts.email_name,
        attachDatas = list(map(lambda attachName: open(attachName, 'rb').read( ), attachNames)),
        attachNames = attachNames )

def _download_songs_newformat( opts ):
    assert( opts.song_names is not None )
    assert( opts.artist_names is not None )
    #
    ## first get the music metadata
    pm = plexmusic.PlexMusic( verify = opts.do_verify )
    song_names = map(lambda song_name: song_name.strip( ), opts.song_names.split(';'))
    artist_names = map(lambda artist_name: artist_name.strip( ), opts.artist_names.split(';'))
    all_songs_downloaded = list(
        filter(None, map(lambda tup: _download_actual_song( pm, tup[0], tup[1], opts.maxnum, opts.do_lastfm ),
                         filter(None, zip( song_names, artist_names ) ) ) ) )    
    return all_songs_downloaded

def _download_songs_oldformat( opts ):
    assert( opts.artist_name is not None )
    #
    ## first get music metadata
    pm = plexmusic.PlexMusic( verify = opts.do_verify )
    lastfm = plexmusic.PlexLastFM( verify = opts.do_verify )

    #
    ## scenario #1: just get the list of albums
    if opts.do_albums:
        try:
            mi = plexmusic.MusicInfo( opts.artist_name.strip( ) )
            mi.print_format_album_names( )
            return
        except Exception as e:
            logging.error( e, exc_info = True )
            print( 'Could not get find artist = %s with Musicbrainz.' % (
                opts.artist_name.strip( ) ) )
            return   
        
    elif opts.album_name is not None:
        all_songs_downloaded = [ ]
        if opts.do_lastfm:
            album_data_dict, status = lastfm.get_music_metadatas_album(
                opts.artist_name, opts.album_name )
            if status != 'SUCCESS':
                print( status )
                return
        elif opts.do_musicbrainz:
            try:
                mi = plexmusic.MusicInfo( opts.artist_name.strip( ) )
                album_data_dict, status = mi.get_music_metadatas_album(
                    opts.album_name.strip( ) )
                if status != 'SUCCESS':
                    print( status )
                    return
            except Exception as e:
                print( 'Could not get find artist = %s with Musicbrainz.' % (
                    opts.artist_name.strip( ) ) )
                return
        else:
            album_data_dict, status = pm.get_music_metadatas_album(
                opts.artist_name, opts.album_name )
            if status != 'SUCCESS':
                album_data_dict, status = lastfm.get_music_metadatas_album(
                    opts.artist_name, opts.album_name )
                if status != 'SUCCESS':
                    print( status )
                    return
        data_dict = album_data_dict[ 0 ]
        artist_name = data_dict[ 'artist' ]
        album_name = data_dict[ 'album' ]
        album_tracks = data_dict[ 'total tracks' ]        
        print( 'ACTUAL ARTIST: %s' % artist_name )
        print( 'ACTUAL ALBUM: %s' % album_name )
        if 'year' in data_dict:
            album_year = data_dict[ 'year' ]
            print( 'ACTUAL YEAR: %d' % album_year )
        print( 'ACTUAL NUM TRACKS: %d' % album_tracks )
        for data_dict in album_data_dict:
            song_name = data_dict[ 'song' ]
            if 'duration' in data_dict:
                dur = int( data_dict[ 'duration' ] )
                song_name_after = _get_final_song_name( song_name, dur )
                print( 'ACTUAL SONG: %s' % song_name_after )
            else: print( 'ACTUAL SONG: %s' % song_name )
            #
            ## now get the youtube song selections
            youtubeURL = _choose_youtube_item( '%s %s' % ( artist_name, song_name ),
                                               maxnum = opts.maxnum, verify = pm.verify )
            if youtubeURL is None:
                continue
            #
            ## now download the song into the given filename
            filename = '%s.%s.m4a' % ( artist_name, song_name )
            plexmusic.get_youtube_file( youtubeURL, filename )
            #
            ## now fill out the metadata
            plexmusic.fill_m4a_metadata( filename, data_dict, verify = pm.verify )
            #
            ##
            os.chmod( filename, 0o644 )
            all_songs_downloaded.append( ( artist_name, song_name, filename ) )
    else:
        assert( opts.song_names is not None )
        song_names = map(lambda song_name: song_name.strip( ), opts.song_names.split(';'))
        all_songs_downloaded = list(filter(
            None,  map(lambda song_name: _download_actual_song(
                pm, lastfm, song_name, opts.artist_name, opts.maxnum, opts.do_lastfm ),
                       song_names ) ) )
    return all_songs_downloaded

def main( ):
    plexmusic.MusicInfo.get_set_musicbrainz_useragent( emailAddress )
    parser = OptionParser( )
    parser.add_option( '-s', '--songs', dest='song_names', type=str, action='store',
                       help = 'Names of the song to put into M4A files. Separated by ;' )
    parser.add_option( '-a', '--artist', dest='artist_name', type=str, action='store',
                       help = 'Name of the artist to put into the M4A file.' )
    parser.add_option( '--maxnum', dest='maxnum', type=int, action='store',
                       default = 10, help = ' '.join([ 
                           'Number of YouTube video choices to choose for each of your songs.'
                           'Default is 10.' ]))
    parser.add_option( '-A', '--album', dest='album_name', type=str, action='store',
                       help = 'If defined, then use ALBUM information to get all the songs in order from the album.' )
    parser.add_option( '--albums', dest='do_albums', action='store_true', default = False,
                       help = 'If chosen, then print out all the studio albums this artist has put out.' )
    parser.add_option( '-e', '--email', dest='email', type=str, action='store',
                       help = 'If defined with an email address, will email these songs to the recipient with that email address.')
    parser.add_option( '-n', '--ename', dest='email_name', type=str, action='store',
                       help = 'Only works if --email is defined. Optional argument to include the name of the recipient.' )
    parser.add_option( '--new', dest='do_new', action='store_true', default = False,
                       help = ' '.join([
                           "If chosen, use the new format for getting the song list.",
                           "Instead of -a or --artist, will look for --artists.",
                           "Each artist is separated by a ';'." ]))
    parser.add_option( '--artists', dest='artist_names', type=str, action='store',
                       help = "List of artists. Each artist is separated by a ';'.")
    parser.add_option( '--lastfm', dest='do_lastfm', action='store_true', default = False,
                       help = 'If chosen, then only use the LastFM API to get song metadata.' )
    parser.add_option( '--musicbrainz', dest='do_musicbrainz', action='store_true', default = False,
                       help = ' '.join([
                           'If chosen, use Musicbrainz to get the artist metadata.',
                           'Note that this is expensive, and only applies if the -A (--album) or --albums flag is chosen.' ]))
    parser.add_option( '--noverify', dest='do_verify', action='store_false', default=True,
                       help = 'Do not verify SSL transactions if chosen.' )
    parser.add_option( '--debug', dest='do_debug', action='store_true', default=False,
                       help = 'Run with debug mode turned on.' )
    opts, args = parser.parse_args( )
    logger = logging.getLogger( )
    logger.setLevel( logging.CRITICAL )
    if opts.do_debug: logger.setLevel( logging.DEBUG )

    if not opts.do_new: all_songs_downloaded = _download_songs_oldformat( opts )
    else: all_songs_downloaded = _download_songs_newformat( opts )
    if opts.email is not None: _email_songs( opts, all_songs_downloaded )
        
if __name__=='__main__':
    main( )
