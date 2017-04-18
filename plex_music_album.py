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
    opts, args = parser.parse_args( )
    assert(all(map(lambda tok: tok is not None, ( opts.artist_name, opts.album_name ) ) ) )
    #
    ##
    pm = plexmusic.PlexMusic( )
    pm.get_song_image( opts.artist_name, opts.album_name )
