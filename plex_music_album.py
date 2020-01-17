#!/usr/bin/env python3

import sys, signal
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import codecs, os, tabulate, logging
from plexmusic import plexmusic
from plexemail import emailAddress
from argparse import ArgumentParser

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
    parser.add_argument( '--musicbrainz', dest='do_musicbrainz', action='store_true', default = False,
                         help = ' '.join([
                             'If chosen, use Musicbrainz to get the artist metadata.',
                             'Note that this is expensive, and is always applied when the --albums flag is set.' ]))
    args = parser.parse_args( )
    plexmusic.MusicInfo.get_set_musicbrainz_useragent( emailAddress )
    plexmusic.MusicInfo.set_musicbrainz_verify( verify = args.do_verify )
    assert( args.artist_name is not None )
    if not args.do_albums: assert( args.album_name is not None )
    logger = logging.getLogger( )
    if args.do_debug: logger.setLevel( logging.DEBUG )
    #
    ##    
    plastfm = plexmusic.PlexLastFM( verify = args.do_verify )
    if args.do_albums:
        mi = plexmusic.MusicInfo( args.artist_name.strip( ) )
        mi.print_format_album_names( )
        return
    
    if not args.do_songs: # just get the song image
        if args.do_musicbrainz:
            mi = plexmusic.MusicInfo( args.artist_name.strip( ) )
            _, status = mi.get_album_image( args.album_name )
        else:
            _, status = plastfm.get_album_image( args.artist_name, args.album_name )
        if status != 'SUCCESS':
            print( status )
        return

    #
    ## now get song listing, --songs is chosen
    if args.do_musicbrainz:
        mi = plexmusic.MusicInfo( args.artist_name.strip( ) )
        track_listing, status = mi.get_song_listing(
            args.album_name )
    else:
        track_listing, status = plastfm.get_song_listing(
            args.artist_name, album_name = args.album_name )
    if status != 'SUCCESS':
        print( status )
        return

    if not args.do_formatted:
        print( '\n%s\n' %
               tabulate.tabulate( track_listing, headers = [ 'Song', 'Track #' ] ) )
    else:
        print( '\n%s\n' % ';'.join(map(lambda title_trkno: title_trkno[0], track_listing)) )

if __name__ == '__main__':
    try:
        main( )
    except Exception as e:
        print( e )
