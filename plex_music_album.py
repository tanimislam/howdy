#!/usr/bin/env python3

import codecs, os, sys, signal
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
from plexmusic import plexmusic
from optparse import OptionParser

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option( '--artist', dest='artist_name', type=str, action='store',
                       help = 'Name of the artist to get album image for.' )
    parser.add_option( '--album', dest='album_name', type=str, action='store',
                       help = 'Name of the album to get album image for.' )
    parser.add_option( '--songs', dest='do_songs', action='store_true', default = False,
                       help = 'If chosen, get the song listing instead of downloading the album image.')
    parser.add_option( '--formatted', dest='do_formatted', action='store_true', default = False,
                       help = ' '.join([ 'If chosen, print the song listing in a format recognized by plex_music_metafill.py'
                                         'for downloading a collection of songs.' ]) )
    opts, args = parser.parse_args( )
    assert(all(map(lambda tok: tok is not None, ( opts.artist_name, opts.album_name ) ) ) )
    #
    ##    
    pm = plexmusic.PlexMusic( )
    if not opts.do_songs:
        _, status = pm.get_album_image( opts.artist_name, opts.album_name )
        if status != 'SUCCESS': print( status )
    else:
        track_listing = pm.get_song_listing( opts.artist_name, album_name = opts.album_name )
        if not opts.do_formatted:
            for title, trkno in track_listing:
                print( '%02d - %s' % ( trkno, title ) )
        else:
            print( ';'.join(map(lambda title_trkno: title_trkno[0], track_listing)) )
