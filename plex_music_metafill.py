#!/usr/bin/env python2

from plexmusic.plexmusic import fill_m4a_metadata
from optparse import OptionParser

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option( '--inputfile', dest='filename', type=str, action='store',
                       help = 'Name of the M4A file to write metadata to.' )
    parser.add_option( '--song', dest='song_name', type=str, action='store',
                       help = 'Name of the song to put into the M4A file.' )
    parser.add_option( '--artist', dest='artist_name', type=str, action='store',
                       help = 'Name of the artist to put into the M4A file.' )
    opts, args = parser.parse_args( )
    assert(all(map(lambda tok: tok is not None,
                   ( opts.filename, opts.song_name, opts.artist_name ) ) ) )
    fill_m4a_metadata( opts.filename, opts.artist_name, opts.song_name )
