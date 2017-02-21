#!/usr/bin/env python2

import codecs, os, sys, base64, requests
from optparse import OptionParser

def get_song( email, artist, song ):
    url = 'https://tanimislam.ddns.net/flask/plex/sendmusic'
    data = { 'mode' : 'SENDARTISTSONG',
             'artist' : artist,
             'song' : song }
    response = requests.post( url, json = data,
                              auth = ( email, 'initialplexserver' ) )
    if response.status_code == 401:
        print "ERROR, email '%s' is not known by the Plex Server. Please choose a valid email." % \
            email
        return
    elif response.status_code == 400:
        message = response.json( )['message']
        print message
        return
    elif response.status_code == 200:
        data_dict = response.json( )['data_dict']
        videos = response.json( )['videos']
    else:
        print 'ERROR, server https://tanimislam.ddns.net/flask may be down.'
        return
    #
    ##
    if len( videos ) != 1:
        sortdict = { idx + 1 : item for (idx, item) in enumerate(videos) }
        bs = codecs.encode( 'Choose YouTube video:\n%s\n' %
                            '\n'.join(map(lambda idx: '%d: %s' % ( idx, sortdict[ idx ][ 0 ] ),
                                          sorted( sortdict ) ) ), 'utf-8' )
        iidx = raw_input( bs )
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
    data2 = { 'data_dict' : data_dict,
              'youtubeURL' : youtubeURL,
              'mode' : 'SENDCHOICE' }
    response2 = requests.post( url, json = data2,
                               auth = ( email, 'initialplexserver' ) )
    if response.status_code == 400:
        message = response.json( )['message']
        print message
        return
    elif response.status_code == 200:
        filename = response2.json( )['filename']
        filedata = response2.json( )['filedata']
        with open( filename, 'wb') as openfile:
            openfile.write( base64.b64decode( filedata ) )
        print 'FINISHED WRITING OUT SONG %s.' % filename
    else:
        print 'ERROR, server https://tanimislam.ddns.net/flask may be down.'
        return

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option( '--song', dest='song_name', type=str, action='store',
                       help = 'Name of the song to put into the M4A file.' )
    parser.add_option( '--artist', dest='artist_name', type=str, action='store',
                       help = 'Name of the artist to put into the M4A file.' )
    parser.add_option( '--email', dest='email', type=str, action='store',
                       help = 'Email of person who has access to the Plex server.' )
    opts, args = parser.parse_args( )
    assert(all(map(lambda tok: tok is not None,
                   ( opts.song_name, opts.artist_name, opts.email ) ) ) )
    get_song( opts.email, opts.artist_name, opts.song_name )
