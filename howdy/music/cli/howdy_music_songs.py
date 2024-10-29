import signal
from howdy import signal_handler
signal.signal( signal.SIGINT, signal_handler )
import os, sys, datetime, io, zipfile, logging, requests
from argparse import ArgumentParser
#
from howdy.core import core, return_error_raw
from howdy.music import music
from howdy.email import email, emailAddress, emailName

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
    youtube = music.get_youtube_service( verify = verify )
    videos = music.youtube_search( youtube, name, max_results = maxnum )
    if videos is None: return None
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

def _process_data_album_dict(
        hm, lastfm, alb_name, a_name, do_whichone, mi = None,
        process_to_end = True, do_direct = False ):
    assert( do_whichone in ( 'GRACENOTE', 'LASTFM', 'MUSICBRAINZ' ) ), "error, metadata service = %s should be one of GRACENOTE, LASTFM, or MUSICBRAINZ" % do_whichone
    if do_whichone == 'GRACENOTE':
        album_data_dict, status = hm.get_music_metadatas_album(
            a_name, alb_name )
        if status == 'SUCCESS': return album_data_dict, status
        if not_process_to_end:
            return return_error_raw( status )

        #
        ## now lastfm
        album_data_dict, status = lastfm.get_music_metadatas_album(
            a_name, alb_name )
        if status == 'SUCCESS': return album_data_dict, status
        
        #
        ## now musicbrainz
        if mi is not None:
            assert( mi.artist_name == a_name )
        else: mi = music.MusicInfo( a_name, do_direct = do_direct )
        album_data_dict, status = mi.get_music_metadatas_album( alb_name )
        if status == 'SUCCESS': return album_data_dict, status
        return return_error_raw( status )
    elif do_whichone == 'LASTFM':
        album_data_dict, status = lastfm.get_music_metadatas_album(
            a_name, alb_name )
        if status == 'SUCCESS': return album_data_dict, status
        if not process_to_end: return return_error_raw( status )
        
        #
        ## now musicbrainz
        if mi is not None:
            assert( mi.artist_name == a_name )
        else: mi = music.MusicInfo( a_name )
        album_data_dict, status = mi.get_music_metadatas_album( alb_name )
        if status == 'SUCCESS': return album_data_dict, status
        return return_error_raw( status )
    else:
        if mi is not None:
            assert( mi.artist_name == a_name )
        else: mi = music.MusicInfo( a_name )
        album_data_dict, status = mi.get_music_metadatas_album( alb_name )
        if status == 'SUCCESS': return album_data_dict, status
        return return_error_raw( status )

def _process_data_song_dict(
        hm, lastfm, s_name, a_name, do_whichone, mi = None,
        process_to_end = True, do_direct = False ):
    assert( do_whichone in ( 'GRACENOTE', 'LASTFM', 'MUSICBRAINZ' ) ), "error, metadata service = %s should be one of GRACENOTE, LASTFM, or MUSICBRAINZ" % do_whichone
    if do_whichone == 'GRACENOTE':
        data_dict, status = hm.get_music_metadata(
            song_name = s_name, artist_name = a_name )
        if status == 'SUCCESS': return data_dict, status
        if not process_to_end:
            return return_error_raw( status )
        
        #
        ## now lastfm
        data_dict, status = lastfm.get_music_metadata(
            song_name = s_name, artist_name = a_name )
        if status == 'SUCCESS': return data_dict, status
         
        #
        ## now musicbrainz
        if mi is not None:
            assert( mi.artist_name == a_name )
        else:
            mi = music.MusicInfo( a_name, do_direct = do_direct )
            data_dict, status = mi.get_music_metadata( s_name )
            if status == 'SUCCESS': return data_dict, status
            return return_error_raw( status )
    elif do_whichone == 'LASTFM':
        data_dict, status = lastfm.get_music_metadata(
            song_name = s_name, artist_name = a_name )
        if status == 'SUCCESS': return data_dict, status
        if not process_to_end: return return_error_raw( status )
        
        #
        ## now musicbrainz
        if mi is not None:
            assert( mi.artist_name == a_name )
        else: mi = music.MusicInfo( a_name )
        data_dict, status = mi.get_music_metadata( s_name )
        if status == 'SUCCESS': return data_dict, status
        return return_error_raw( status )
    else:
        if mi is not None:
            assert( mi.artist_name == a_name )
        else: mi = music.MusicInfo( a_name )
        data_dict, status = mi.get_music_metadata( s_name )
        if status == 'SUCCESS': return data_dict, status
        return return_error_raw( status) 

def _download_actual_song(
        hm, lastfm, s_name, a_name, maxnum, do_whichone = 'GRACENOTE',
        mi = None, process_to_end = True, do_direct = False ):
    assert( do_whichone in ( 'GRACENOTE', 'LASTFM', 'MUSICBRAINZ' ) ), "error, metadata service = %s should be one of GRACENOTE, LASTFM, or MUSICBRAINZ" % do_whichone
    try:
        data_dict, status = _process_data_song_dict(
            hm, lastfm, s_name, a_name, do_whichone, mi = mi, process_to_end = process_to_end, do_direct = do_direct )
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
    track_number = data_dict[ 'tracknumber' ]
    total_tracks = data_dict[ 'total tracks' ]
    if 'duration' in data_dict:
        try:
            dur = int( data_dict[ 'duration' ] )
        except: dur = 0
        song_name_after = _get_final_song_name( song_name, dur )
    print( 'ACTUAL ARTIST: %s' % artist_name )
    print( 'ACTUAL ALBUM: %s' % album_name )
    if 'duration' not in data_dict: print( 'ACTUAL SONG: %s' % song_name )
    else: print( 'ACTUAL SONG: (%02d/%02d) %s' % (
        track_number, total_tracks, song_name_after ) )
    #
    ## now get the youtube song selections
    youtubeURL = _choose_youtube_item( '%s %s' % ( artist_name, song_name ),
                                       maxnum = maxnum, verify = hm.verify )
    if youtubeURL is None: return None
    #
    ## now download the song into the given filename
    ## replace '/' in artist and song name with ';'
    filename = '%s.%s.m4a' % ( artist_name.replace( '/', '-' ), '; '.join(map(lambda tok: tok.strip( ), song_name.split('/') ) ) )
    music.get_youtube_file( youtubeURL, filename )
    #
    ## now fill out the metadata
    music.fill_m4a_metadata( filename, data_dict, verify = hm.verify )
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
    # status, _ = core.oauthCheckGoogleCredentials( verify = opts.do_verify )
    # if not status:
    #     print( "Error, do not have correct Google credentials." )
    #    return
    songs_by_list = '\n'.join( map(
        lambda tup: '* %s - %s.' % ( tup[0], tup[1] ),
        all_songs_downloaded ) )
    num_songs = len( all_songs_downloaded )
    num_artists = len( set( map(lambda tup: tup[0], all_songs_downloaded ) ) )
    if num_songs == 1: num_songs_string = "1 song"
    else: num_songs_string = "%d songs" % num_songs
    if num_artists == 1: num_artists_string = "1 artist"
    else: num_artists_string = "%d artists" % num_artists
    if emailName is not None: name = emailName
    else: name = 'Your friendly Howdy admin'
    #
    body = """I have emailed you %s from %s:
    %s
    Have a good day!
    
    %s
    """ % ( num_songs_string, num_artists_string,
            songs_by_list, name )
    finalString = '\n'.join([ 'Hello Friend,', '', body ])
    htmlString = core.rstToHTML( finalString )
    subject = 'The %s with %s you requested.' % (
        num_songs_string, num_artists_string )
    # attachData, attachName = _create_archive_songs( all_songs_downloaded )
    attachNames = list(map(lambda tup: tup[-1], all_songs_downloaded ) )
    email.send_individual_email_full_withattachs(
        htmlString, subject, opts.email,
        name = opts.email_name,
        attachDatas = list(map(lambda attachName: open(attachName, 'rb').read( ), attachNames)),
        attachNames = attachNames )

def _download_songs_newformat( args ):
    assert( args.song_names is not None )
    assert( args.artist_names is not None )
    assert( len(list(filter(lambda tok: tok is True,
                            ( args.do_lastfm, args.do_musicbrainz ) ) ) ) <= 1 )
    #
    ## first get the music metadata
    hm = music.HowdyMusic( verify = args.do_verify )
    lastfm = music.HowdyLastFM( verify = args.do_verify )
    do_whichone = 'GRACENOTE'
    if args.do_lastfm: do_whichone = 'LASTFM'
    if args.do_musicbrainz: do_whichone = 'MUSICBRAINZ'
    song_names = list(
        map(lambda song_name: song_name.strip( ), args.song_names.split(';')))
    artist_names = list(
        map(lambda artist_name: artist_name.strip( ), args.artist_names.split(';')))
    artist_names_dict = dict(map(lambda artist_name: ( artist_name, None ), set( artist_names ) ) )
    if args.do_musicbrainz:
        artist_names_dict = dict(map(lambda artist_name: (
            artist_name, music.MusicInfo( artist_name ) ), set( artist_names ) ) )
    all_songs_downloaded = list(
        filter(None, map(lambda tup: _download_actual_song(
            hm, lastfm, tup[0], tup[1], args.maxnum, do_whichone = do_whichone,
            mi = artist_names_dict[ tup[ 1 ] ], process_to_end = True ),
                         filter(None, zip( song_names, artist_names ) ) ) ) )
    return all_songs_downloaded

def _download_songs_oldformat( args ):
    assert( args.artist_name is not None )
    #
    ## first get music metadata
    hm = music.HowdyMusic( verify = args.do_verify )
    lastfm = music.HowdyLastFM( verify = args.do_verify )
    
    #
    ## scenario #1: just get the list of albums
    # if args.do_albums: # use the --artist=<arg> --albums
    #     try:
    #         mi = music.MusicInfo( args.artist_name.strip( ) )
    #         mi.print_format_album_names( )
    #         return
    #     except Exception as e:
    #         logging.error( e, exc_info = True )
    #         print( 'Could not get find artist = %s with Musicbrainz.' % (
    #             args.artist_name.strip( ) ) )
    #         return   
    if args.album_name is not None: # use the --artist= --album=
        all_songs_downloaded = [ ]
        #
        ## figure out order of music metadata services to get
        mi = None
        if args.do_lastfm:
            do_whichone = 'LASTFM'
        elif args.do_musicbrainz:
            do_whichone = 'MUSICBRAINZ'
            mi = music.MusicInfo( args.artist_name, do_direct = args.do_direct, artist_mbid = args.artist_mbid )
        else: do_whichone = 'GRACENOTE'
        album_data_dict, status = _process_data_album_dict(
            hm, lastfm, args.album_name.strip( ), args.artist_name,
            do_whichone, mi = mi, do_direct = args.do_direct )
        if status != 'SUCCESS':
            print( status )
            return
        #
        ##
        data_dict = album_data_dict[ 0 ]
        artist_name = data_dict[ 'artist' ]
        album_name = data_dict[ 'album' ]
        album_tracks = data_dict[ 'total tracks' ]
        album_url = data_dict[ 'album url' ]
        image_data = None
        if album_url != '':
            image_data = io.BytesIO(
                requests.get( album_url, verify = args.do_verify ).content )
        print( 'ACTUAL ARTIST: %s' % artist_name )
        print( 'ACTUAL ALBUM: %s' % album_name )
        if 'year' in data_dict:
            album_year = data_dict[ 'year' ]
            print( 'ACTUAL YEAR: %d' % album_year )
        print( 'ACTUAL NUM TRACKS: %d' % album_tracks )
        for data_dict in album_data_dict:
            song_name = data_dict[ 'song' ]
            track_number = data_dict[ 'tracknumber' ]
            if 'duration' in data_dict:
                dur = int( data_dict[ 'duration' ] )
                song_name_after = _get_final_song_name( song_name, dur )
                print( 'ACTUAL SONG: (%02d/%02d) %s' % (
                  track_number, album_tracks, song_name_after ) )
            else: print( 'ACTUAL SONG: (%02d/%02d) %s' % (
                track_number, album_tracks, song_name ) )
            #
            ## now get the youtube song selections
            youtubeURL = _choose_youtube_item( '%s %s' % ( artist_name, song_name ),
                                               maxnum = args.maxnum, verify = hm.verify )
            if youtubeURL is None:
                continue
            #
            ## now download the song into the given filename
            filename = '%s.%s.m4a' % ( artist_name, '; '.join(map(lambda tok: tok.strip( ), song_name.split('/') ) ) )
            music.get_youtube_file( youtubeURL, filename )
            #
            ## now fill out the metadata
            music.fill_m4a_metadata( filename, data_dict, verify = hm.verify,
                                         image_data = image_data )
            #
            ##
            try:
                os.chmod( filename, 0o644 )
                all_songs_downloaded.append( ( artist_name, song_name, filename ) )
            except: pass
    else: # use --artist= --songs=
        assert( args.song_names is not None )
        #0
        ## order of the music metadata to get
        mi = None
        if args.do_lastfm:
            do_whichone = 'LASTFM'
        elif args.do_musicbrainz:
            do_whichone = 'MUSICBRAINZ'
            mi = music.MusicInfo( args.artist_name, do_direct = args.do_direct )
        else: do_whichone = 'GRACENOTE'
        #
        ## now do the processing
        song_names = list(
            map(lambda song_name: song_name.strip( ), args.song_names.split(';')))
        all_songs_downloaded = list(filter(
            None,
            map(lambda song_name:
                _download_actual_song(
                    hm, lastfm, song_name, args.artist_name, args.maxnum,
                    do_whichone, mi = mi, process_to_end = False,
                    do_direct = args.do_direct ),
                song_names ) ) )
    return all_songs_downloaded

def main( ):
    parser = ArgumentParser( )
    parser.add_argument( '-a', '--artist', dest='artist_name', type=str, action='store',
                         help = 'Name of the artist to put into the M4A file.' )
    parser.add_argument( '-s', '--songs', dest='song_names', type=str, action='store',
                         help = 'Names of the song to put into M4A files. Separated by ;' )
    parser.add_argument( '--maxnum', dest='maxnum', type=int, action='store',
                         default = 10, help = ' '.join([ 
                             'Number of YouTube video choices to choose for each of your songs.'
                             'Default is 10.' ]))
    parser.add_argument( '-A', '--album', dest='album_name', type=str, action='store',
                         help = 'If defined, then get all the songs in order from the album.' )
    #parser.add_argument( '--albums', dest='do_albums', action='store_true', default = False,
    #                   help = 'If chosen, then print out all the studio albums this artist has put out.' )
    #parser.add_argument( '-e', '--email', dest='email', type=str, action='store',
    #                   help = 'If defined with an email address, will email these songs to the recipient with that email address.')
    #parser.add_argument( '-n', '--ename', dest='email_name', type=str, action='store',
    #                   help = 'Only works if --email is defined. Optional argument to include the name of the recipient.' )
    parser.add_argument( '--new', dest='do_new', action='store_true', default = False,
                         help = ' '.join([
                             "If chosen, use the new format for getting the song list.",
                             "Instead of -a or --artist, will look for --artists.",
                             "Each artist is separated by a ';'." ]))
    parser.add_argument( '--artists', dest='artist_names', type=str, action='store',
                         help = "List of artists. Each artist is separated by a ';'.")
    parser.add_argument( '-L', '--lastfm', dest='do_lastfm', action='store_true', default = False,
                         help = 'If chosen, then only use the LastFM API to get song metadata.' )
    parser.add_argument(
        '-M', '--musicbrainz', dest='do_musicbrainz', action='store_true', default = False,
        help = ' '.join( [
            'If chosen, use Musicbrainz to get the artist metadata.',
            'Note that this is expensive.' ] ) )
    parser.add_argument(
        '-m', '--mbid', dest='artist_mbid', action = 'store', type = str, default = None,
        help = ' '.join([
            'Optional argument, the ARTIST MusicBrainz ID to use to select on artist (in addition to the -a flag).',
            'Only makes sense and is used when running with MusicBrainz.' ] ) )
    parser.add_argument(
        '--noverify', dest='do_verify', action='store_false', default=True,
        help = 'Do not verify SSL transactions if chosen.' )
    parser.add_argument(
        '--debuglevel', dest='debug_level', action='store', type=str, default = 'NONE', choices = [ 'NONE', 'ERROR', 'INFO', 'DEBUG' ],
        help = 'Choose the debug level for the system logger. Default is NONE (no logging). Can be one of NONE (no logging), ERROR, INFO, or DEBUG.' )
    parser.add_argument( '-D', '--direct', dest='do_direct', action='store_true', default=False,
                         help = 'Only makes sense when running with MusicBrainz. Option of using direct instead of indexed search on the artist. Default is False.' )
    args = parser.parse_args( )
    music.MusicInfo.get_set_musicbrainz_useragent( emailAddress )
    music.MusicInfo.set_musicbrainz_verify( verify = args.do_verify )
    logger = logging.getLogger( )
    logging_dict = { 'ERROR' : logging.ERROR, 'INFO' : logging.INFO, 'DEBUG' : logging.DEBUG }
    if args.debug_level in logging_dict: logger.setLevel( logging_dict[ args.debug_level ] )
    #
    ## must set TRUE only ONE of --lastfm or --musicbrainz
    assert( len(list(filter(lambda tok: tok is True, ( args.do_lastfm, args.do_musicbrainz ) ) ) ) <= 1 ), "error, can do at most one of --lastfm or --musicbrainz"

    if not args.do_new: all_songs_downloaded = _download_songs_oldformat( args )
    else: all_songs_downloaded = _download_songs_newformat( args )
    # if args.email is not None: _email_songs( args, all_songs_downloaded )
