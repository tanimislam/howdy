import sys, signal
from howdy import signal_handler
signal.signal( signal.SIGINT, signal_handler )
import codecs, os, tabulate, logging, datetime
from argparse import ArgumentParser
#
from howdy.music import music
from howdy.email import emailAddress
#

def get_list_of_artists( artist_name ):
    all_artist_entries = music.MusicInfo.get_artist_direct_search_MBID_ALL( artist_name )
    if all_artist_entries is None: return None
    #
    ## now get info on EACH artist, return table
    all_data = [ ]
    for elem in all_artist_entries:
        info = max( music.MusicInfo.get_artist_datas_LL( artist_name, artist_mbid= elem[ 'mbid' ] ) )
        start_year = '?'
        if 'life-span' in info:
            start_year = info[ 'life-span']['begin' ]
        all_data.append( ( elem[ 'mbid' ], elem[ 'description' ], start_year ) )
    return sorted( all_data, key = lambda row: row[-1] )

def main( ):
    parser = ArgumentParser( )
    parser.add_argument( '-a', '--artist', dest='artist_name', type=str, action='store',
                         help = 'Name of the artist to get album image for.', required = True )
    #
    args = parser.parse_args( )
    #
    music.MusicInfo.get_set_musicbrainz_useragent( emailAddress )
    artist_name = args.artist_name.strip( )
    all_data = get_list_of_artists( artist_name )
    if all_data is None:
        print( "ERROR, could find no artists that match name = %s on MusicBrainz. Exiting..." % artist_name )
        return
    #
    ## now format data
    print('Found %d matching artists on MusicBrainz with name = %s.\n' % ( len( all_data ), artist_name ) )
    print( '%s\n' % tabulate.tabulate( all_data, headers = [ 'MUSICBRAINZ ID (MBID)', 'DESCRIPTION', 'START' ] ) )
