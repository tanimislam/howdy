import sys, signal
from howdy import signal_handler
signal.signal( signal.SIGINT, signal_handler )
import codecs, os, tabulate, logging
from argparse import ArgumentParser
#
from howdy.music import music
from howdy.email import emailAddress

def main( ):
    parser = ArgumentParser( )
    parser.add_argument( '-a', '--artist', dest='artist_name', type=str, action='store',
                         help = 'Name of the artist to get album image for.', required = True )
    parser.add_argument( '-A', '--album', dest='album_name', type=str, action='store',
                         help = 'Name of the album to get album image for.' )
    parser.add_argument( '--songs', dest='do_songs', action='store_true', default = False,
                         help = 'If chosen, get the song listing instead of downloading the album image.')
    parser.add_argument( '--formatted', dest='do_formatted', action='store_true', default = False,
                         help = ' '.join([
                             'If chosen, print the song listing in a format recognized by plex_music_metafill.py',
                             'for downloading a collection of songs.' ]) )
    parser.add_argument( '--albums', dest='do_albums', action='store_true', default = False,
                         help = 'If chosen, then get a list of all the songs in all studio albums for the artist.' )
    parser.add_argument( '--debug', dest='do_debug', action='store_true', default=False,
                         help = 'Run with debug mode turned on.' )
    parser.add_argument( '--noverify', dest='do_verify', action='store_false', default = True,
                         help = 'If chosen, do not verify SSL connections.' )
    parser.add_argument( '-M', '--musicbrainz', dest='do_musicbrainz', action='store_true', default = False,
                        help = ' '.join([
                            'If chosen, use Musicbrainz to get the artist metadata.',
                            'Note that this is expensive, and is always applied when the --albums flag is set.' ]))
    parser.add_argument( '-D', '--direct', dest='do_direct', action='store_true', default = False,
                        help = ' '.join([ 'Only makes sense when running with MusicBrainz.',
                                         'Option of using direct instead of indexed search on the artist.',
                                         'Default is False.' ]) )
    parser.add_argument( '-m', '--mbid', dest='artist_mbid', action = 'store', type = str, default = None,
                        help = ' '.join([
                            'Optional argument, the ARTIST MusicBrainz ID to use to select on artist (in addition to the -a flag).',
                            'Only makes sense and is used when running with MusicBrainz.' ] ) )
                                         
    args = parser.parse_args( )
    music.MusicInfo.get_set_musicbrainz_useragent( emailAddress )
    music.MusicInfo.set_musicbrainz_verify( verify = args.do_verify )
    assert( args.artist_name is not None )
    if not args.do_albums: assert( args.album_name is not None )
    logger = logging.getLogger( )
    if args.do_debug: logger.setLevel( logging.DEBUG )
    #
    ##
    hlastfm = music.HowdyLastFM( verify = args.do_verify )
    if args.do_albums:
        mi = music.MusicInfo( args.artist_name.strip( ), do_direct = args.do_direct, artist_mbid = args.artist_mbid )
        mi.print_format_album_names( )
        return
    
    if not args.do_songs: # just get the song image        
        if args.do_musicbrainz:
            mi = music.MusicInfo( args.artist_name.strip( ), do_direct = args.do_direct, artist_mbid = args.artist_mbid )
            _, status = mi.get_album_image( args.album_name )
        else:
            _, status = hlastfm.get_album_image( args.artist_name, args.album_name )
        if status != 'SUCCESS':
            print( status )
        return

    #
    ## now get song listing, --songs is chosen
    if args.do_musicbrainz:
        mi = music.MusicInfo( args.artist_name.strip( ), do_direct = args.do_direct, artist_mbid = args.artist_mbid )
        track_listing, status = mi.get_song_listing(
            args.album_name )
    else:
        track_listing, status = hlastfm.get_song_listing(
            args.artist_name, album_name = args.album_name )
    if status != 'SUCCESS':
        print( status )
        return

    if not args.do_formatted:
        print( '\n%s\n' %
               tabulate.tabulate( track_listing, headers = [ 'Song', 'Track #' ] ) )
    else:
        print( '\n%s\n' % ';'.join(map(lambda title_trkno: title_trkno[0], track_listing)) )
