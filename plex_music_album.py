#!/usr/bin/env python2

from __future__ import unicode_literals
import codecs, os
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
    opts, args = parser.parse_args( )
    assert(all(map(lambda tok: tok is not None, ( opts.artist_name, opts.album_name ) ) ) )
    #
    ##    
    pm = plexmusic.PlexMusic( )
    if not opts.do_songs:
        pm.get_song_image( opts.artist_name, opts.album_name )
    else:
        track_listing = pm.get_song_listing( opts.artist_name, album_name = opts.album_name )
        print track_listing
        for title, trkno in track_listing:
            print '%02d - %s' % ( trkno, title )
