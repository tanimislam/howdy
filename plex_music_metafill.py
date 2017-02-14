#!/usr/bin/env python2

from plexmusic import plexmusic
from optparse import OptionParser
from cStringIO import StringIO
from PIL import Image
import mutagen.mp4, os, requests

def fill_m4a_metadata( filename, artist_name, song_name ):
    assert( os.path.isfile( filename ) )
    assert( os.path.basename( filename ).lower( ).endswith( '.m4a' ) )
    #
    ## now start it off
    pm = plexmusic.PlexMusic( )
    data_dict, status = pm.get_music_metadata( song_name = song_name,
                                               artist_name = artist_name )
    if status != 'SUCCESS':
        print 'ERROR, %s' % status
        return
    mp4tags = mutagen.mp4.MP4( filename )
    mp4tags[ '\xa9nam' ] = [ data_dict[ 'song' ], ]
    mp4tags[ '\xa9alb' ] = [ data_dict[ 'album' ], ]
    mp4tags[ '\xa9ART' ] = [ data_dict[ 'artist' ], ]
    mp4tags[ 'aART' ] = [ data_dict[ 'artist' ], ]
    mp4tags[ '\xa9day' ] = [ str(data_dict[ 'year' ]), ]
    mp4tags[ 'trkn' ] = [ ( data_dict[ 'tracknumber' ],
                            data_dict[ 'total tracks' ] ), ]
    if data_dict[ 'album url' ] != '':
        csio = StringIO( requests.get( data_dict[ 'album url' ] ).content )
        img = Image.open( csio )
        csio2 = StringIO( )
        img.save( csio2, format = 'png' )
        mp4tags[ 'covr' ] = [ mutagen.mp4.MP4Cover( csio2.getvalue( ), mutagen.mp4.MP4Cover.FORMAT_PNG ), ]
        csio.close( )
        csio2.close( )
    mp4tags.save( )

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
