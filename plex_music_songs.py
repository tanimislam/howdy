#!/usr/bin/env python3

import codecs, sys, os
from plexmusic import plexmusic
from plexcore import plexcore
from plexemail import plexemail
from optparse import OptionParser

def _choose_youtube_item( name, maxnum = 10 ):
    youtube = plexmusic.get_youtube_service( )
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

def _download_actual_song( pm, s_name, a_name, maxnum ):
    try:
        data_dict, status = pm.get_music_metadata( song_name = s_name,
                                                   artist_name = a_name )
        if status != 'SUCCESS':
            print( status )
            return None
    except Exception as e:
        print( e )
        return None
    artist_name = data_dict[ 'artist' ]
    song_name = data_dict[ 'song' ]
    album_name = data_dict[ 'album' ]
    print( 'ACTUAL ARTIST: %s' % artist_name )
    print( 'ACTUAL ALBUM: %s' % album_name )
    print( 'ACTUAL SONG: %s' % song_name )
    #
    ## now get the youtube song selections
    youtubeURL = _choose_youtube_item( '%s %s' % ( artist_name, song_name ),
                                       maxnum = maxnum )
    if youtubeURL is None: return None
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
    return ( artist_name, song_name, filename )

def _create_archive_songs( all_songs_downloaded ):
    from io import BytesIO
    import zipfile
    mf = BytesIO( )
    with zipfile.ZipFile( mf, 'w', compression=zipfile.ZIP_DEFLATED ) as zf:                          
        for tup in all_songs_downloaded: zf.write( tup[-1] )
    return mf.getvalue( ), 'songs.zip'

def _email_songs( opts, all_songs_downloaded ):
    if len( all_songs_downloaded ) == 0: return
    status, _ = plexcore.oauthCheckGoogleCredentials( )
    if not status:
        print( "Error, do not have correct Google credentials." )
        return
    songs_by_list = '\n'.join(map(lambda tup: '\item %s - %s.' % ( tup[0], tup[1] ),
                                  all_songs_downloaded ) )
    num_songs = len( all_songs_downloaded )
    num_artists = len( set( map(lambda tup: tup[0], all_songs_downloaded ) ) )
    if num_songs == 1: num_songs_string = "1 song"
    else: num_songs_string = "%d songs" % num_songs
    if num_artists == 1: num_artists_string = "1 artist"
    else: num_artists_string = "%d artists" % num_artists
    body = """I have emailed you %s from %s in an attached zip file, songs.zip:
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
    attachData, attachName = _create_archive_songs( all_songs_downloaded )
    plexemail.send_individual_email_full_withsingleattach(
        htmlString, subject, opts.email,
        name = opts.email_name,
        attachData = attachData,
        attachName = attachName )

def _download_songs_newformat( opts ):
    assert( opts.song_names is not None )
    assert( opts.artist_names is not None )
    #
    ## first get the music metadata
    pm = plexmusic.PlexMusic( )
    song_names = map(lambda song_name: song_name.strip( ), opts.song_names.split(';'))
    artist_names = map(lambda artist_name: artist_name.strip( ), opts.artist_names.split(';'))
    all_songs_downloaded = list(
        filter(None, map(lambda tup: _download_actual_song( pm, tup[0], tup[1], opts.maxnum ),
                         filter(None, zip( song_names, artist_names ) ) ) ) )    
    return all_songs_downloaded

def _download_songs_oldformat( opts ):
    assert( opts.artist_name is not None )
    #
    ## first get music metadata
    pm = plexmusic.PlexMusic( )
    if opts.album_name is not None:
        all_songs_downloaded = [ ]
        album_data_dict, status = pm.get_music_metadatas_album( opts.artist_name,
                                                                opts.album_name )
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
            youtubeURL = _choose_youtube_item( '%s %s' % ( artist_name, song_name ),
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
            all_songs_downloaded.append( ( artist_name, song_name, filename ) )
    else:
        assert( opts.song_names is not None )
        song_names = map(lambda song_name: song_name.strip( ), opts.song_names.split(';'))
        all_songs_downloaded = list(filter(
            None,  map(lambda song_name: _download_actual_song( pm, song_name, opts.artist_name, opts.maxnum ),
                       song_names ) ) )
    return all_songs_downloaded

<<<<<<< HEAD
def main( ):
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
    opts, args = parser.parse_args( )

    if not opts.do_new: all_songs_downloaded = _download_songs_oldformat( opts )
    else: all_songs_downloaded = _download_songs_newformat( opts )
    
    if opts.email is not None: _email_songs( opts, all_songs_downloaded )
=======
    if opts.email is not None:
        status, _ = plexcore.oauthCheckGoogleCredentials( )
        if not status:
            print( "Error, do not have correct Google credentials." )
            return
        songs_by_list = '\n'.join(map(lambda tup: '%s - %s' % ( tup[0], tup[1] ),
                                      all_songs_downloaded ) )
        body = """I have emailed you %d songs from %d artists as attachments:
        \\begin{list}
          %s
        \end{list}
        Have a good day!

        Tanim
        """ % ( len( all_songs_downloaded ),
                len( set( map(lambda tup: tup[0], all_songs_downloaded ) ) ),
                songs_by_list )
        finalString = '\n'.join([ 'Hello Friend,', '', body ])
        htmlString = plexcore.latexToHTML( finalString )
        subject = 'The %d songs with %d artists you requested.' % (
             len( all_songs_downloaded ),
                len( set( map(lambda tup: tup[0], all_songs_downloaded ) ) ) )
        plexemail.send_individual_email_full_withattachs( htmlString, subject, opts.email,
                                                          name = opts.email_name,
                                                          attachNames = list(map(lambda tup: tup[-1],
                                                                                 all_songs_downloaded ) ) )
>>>>>>> parent of ea17b20... fixed emailing songs functionality in plex_music_songs.py and plexemail/plexemail.py
        
if __name__=='__main__':
    main( )
        
