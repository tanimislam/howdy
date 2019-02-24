#!/usr/bin/env python3

import codecs, os, sys, base64, requests, time, signal
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Just quitting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
from optparse import OptionParser

def get_album( artist, album ):
    url = 'https://***REMOVED***islam.ddns.net/flask/plex/sendmusic'
    data = { 'mode' : 'SENDARTISTALBUM',
             'artist' : artist,
             'album' : album }
    response = requests.post( url, json = data,
                              auth = ( '***REMOVED***_shahriar_islam@yahoo.com',
                                       'initialplexserver' ) )
    if response.status_code == 401:
        print( "ERROR, email '%s' is not known by the Plex Server. Please choose a valid email." % '***REMOVED***_shahriar_islam@yahoo.com' )
        return
    elif response.status_code == 400:
        message = response.json( )['message']
        print( message )
        return
    elif response.status_code == 200:
        data_dict = response.json( )['data_dict']
    else:
        print( 'ERROR, server https://***REMOVED***islam.ddns.net/flask may be down.' )
        return
    tracks = data_dict[ 'tracks' ]
    print( 'ACTUAL NUM TRACKS: %d' % len( tracks ) )
    for song in tracks: get_song( artist, song )
    
def get_song( artist, song ):
    url = 'https://***REMOVED***islam.ddns.net/flask/plex/sendmusic'
    data = { 'mode' : 'SENDARTISTSONG',
             'artist' : artist,
             'song' : song }
    response = requests.post( url, json = data,
                              auth = ( '***REMOVED***_shahriar_islam@yahoo.com',
                                       'initialplexserver' ) )
    if response.status_code == 401:
        print( "ERROR, email '%s' is not known by the Plex Server. Please choose a valid email." % '***REMOVED***_shahriar_islam@yahoo.com' )
        return
    elif response.status_code == 400:
        message = response.json( )['message']
        print( message )
        return
    elif response.status_code == 200:
        data_dict = response.json( )['data_dict']
        videos = response.json( )['videos']
    else:
        print( 'ERROR, server https://***REMOVED***islam.ddns.net/flask may be down.' )
        return
    #
    ##
    print( "ACTUAL ARTIST: %s" % data_dict[ 'artist' ] )
    print( "ACTUAL ALBUM: %s" % data_dict[ 'album' ] )
    print( "ACTUAL SONG: %s" % data_dict[ 'song' ] )
    if len( videos ) != 1:
        sortdict = { idx + 1 : item for (idx, item) in enumerate(videos) }
        bs = 'Choose YouTube video:\n%s\n' % (
            '\n'.join(map(lambda idx: '%d: %s' % ( idx, sortdict[ idx ][ 0 ] ),
                          sorted( sortdict ) ) ) )
        iidx = input( bs )
        try:
            iidx = int( iidx.strip( ) )
            if iidx not in sortdict:
                print('Error, need to choose one of the YouTube videos. Exiting...')
                return None
            _, youtubeURL = sortdict[ iidx ]
        except:
            print('Error, did not choose a valid integer. Exiting...')
            return
    elif len( videos ) == 1: _, youtubeURL = videos[0]
    time0 = time.time( )
    data2 = { 'data_dict' : data_dict,
              'youtubeURL' : youtubeURL,
              'mode' : 'SENDCHOICE' }
    response2 = requests.post( url, json = data2,
                               auth = ( '***REMOVED***_shahriar_islam@yahoo.com',
                                        'initialplexserver' ) )
    if response2.status_code == 400:
        message = response.json( )['message']
        print( message )
        return
    elif response2.status_code == 200:
        filename = response2.json( )['filename']
        filedata = response2.json( )['filedata']
        with open( filename, 'wb') as openfile:
            openfile.write( base64.b64decode( filedata ) )
        os.chmod( filename, 0o644 )
        print( 'finished downloading song %s in %0.3f seconds. Enjoy!' % (
            filename, time.time( ) - time0 ) )
    else:
        print( 'ERROR STATUS CODE: %d' % response.status_code )
        print( 'ERROR, server https://***REMOVED***islam.ddns.net/flask may be down.' )
        return

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option( '-s', '--song', dest='song_name', type=str, action='store',
                       help = 'Name of the song.' )
    parser.add_option( '-a', '--artist', dest='artist_name', type=str, action='store',
                       help = 'Name of the artist.' )
    parser.add_option( '-A', '--album', dest='album_name', type=str, action='store',
                       help = 'Name of the album to download. If defined, then ignore song.' )
    opts, args = parser.parse_args( )
    assert opts.artist_name is not None
    assert(any(list(map(lambda tok: tok is not None, ( opts.song_name, opts.album_name ) ) ) ) )
    if opts.album_name is not None: get_album( opts.artist_name, opts.album_name )
    else: get_song( opts.artist_name, opts.song_name )
