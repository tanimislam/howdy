import sys, os, signal
# code to handle Ctrl+C, convenience method for command line tools
def _signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, _signal_handler )
from argparse import ArgumentParser
#
from plexstuff.plexcore import plexcore_deluge

def _get_matching_torrents( client, list_of_torrents, operation_if_size_1 = False ):
    if any(map(lambda tok: tok == "*", list_of_torrents ) ):
        return plexcore_deluge.deluge_get_matching_torrents( client, [ "*" ] )
    if operation_if_size_1 and len( list_of_torrents ) <= 1:
        return plexcore_deluge.deluge_get_matching_torrents( client, [ "*" ] )
    return plexcore_deluge.deluge_get_matching_torrents( client, list_of_torrents )

def main( ):
    parser = ArgumentParser( )
    subparser = parser.add_subparsers( help = 'Choose one of these three modes of operation: rm, add, pause, resume, or push.',
                                       dest = 'choose_option' )
    #
    ## torrent info
    parser_info = subparser.add_parser( 'info', help = 'Print summary info on a specific torrent, or all torrents.' )
    parser_info.add_argument( 'info_torrent', metavar='torrent', type=str, nargs='*', # can be even ZERO arguments
                             help = ' '.join([
                                 'The hash ID, or identifying initial substring, of torrents for which to get information.',
                                 'Example usage is "plex_deluge_console info ab1 bc2", where "ab1" and "bc2" are the first three digits of the MD5 hashes of torrents to examine.' ]))
    #
    ## resume
    parser_resume = subparser.add_parser( 'resume', help = 'Resume selected torrents, or all torrents.' )
    parser_resume.add_argument( 'resume_torrent', metavar='torrent', type=str, nargs='+',
                               help = ' '.join([
                                   'The hash ID, or identifying initial substring, of torrents to resume.',
                                   'Example usage is "plex_deluge_console resume ab1 bc2", where "ab1" and "bc2" are the first three digits of the MD5 hashes of torrents to resume.' ]))
    #
    ## pause
    parser_pause = subparser.add_parser( 'pause', help = 'Pause selected torrents, or all torrents.' )
    parser_pause.add_argument( 'pause_torrent', metavar = 'torrent', type=str, nargs='+',
                              help = '\n'.join([
                                  'The hash ID, or identifying initial substring, of torrents to pause.',
                                  'Example usage is "plex_deluge_console resume ab1 bc2", where "ab1" and "bc2" are the first three digits of the MD5 hashes of torrents to pause.' ]))
    #
    ## remove/delete
    parser_remove = subparser.add_parser( 'rm', aliases = [ 'del' ], help = 'Remove selected torrents, or all torrents.' )
    parser_remove.add_argument( 'remove_torrent', metavar = 'torrent', type=str, nargs='+',
                               help = 'The hash ID, or identifying initial substring, of torrents to remove.' )
    parser_remove.add_argument( '-R', '--remove_data', dest = 'remove_data', action='store_true', default = False,
                               help = "Remove the torrent's data." )
    #
    ## add a SINGLE torrent
    parser_add = subparser.add_parser( 'add', help = 'Add a single torrent, as a magnet link or a file.' )
    parser_add.add_argument( 'add_torrent', metavar = 'torrent', type=str,
                            help = 'The fully realized magnet link, or file, to add to the torrent server.' )
    #
    ## push settings for new deluge server
    parser_push = subparser.add_parser( 'push', help = 'Push settings for a new deluge server to configuration.' )
    parser_push.add_argument( '--host', dest='push_url', metavar = 'url', action = 'store', type = str, default = 'localhost',
                             help = 'URL of the deluge server. Default is localhost.' )
    parser_push.add_argument('--port', dest='push_port', metavar = 'port', action='store', type=int, default = 12345,
                             help = 'Port for the deluge server. Default is 12345.' )
    parser_push.add_argument('--username', dest='port_username', metavar = 'username', action='store', type=str, default = 'admin',
                             help = 'Username to login to the deluge server. Default is admin.' )
    parser_push.add_argument('--password', dest='push_password', metavar = 'password', action='store', type=str, default = 'admin',
                            help = 'Password to login to the deluge server. Default is admin.' )
    #
    ## start operation
    args = parser.parse_args( )
    client, status = plexcore_deluge.get_deluge_client( )
    if status != 'SUCCESS':
        print( "ERROR, COULD NOT GET VALID DELUGE CLIENT." )
        return

    #
    ## torrent info
    if args.choose_option == 'info':
        info_torrents = args.info_torrent
        torrentIds = _get_matching_torrents( client, info_torrents, operation_if_size_1 = True )
        torrentInfo = plexcore_deluge.deluge_get_torrents_info( client )
        infos = list(map(lambda torrentId: plexcore_deluge.deluge_format_info(
            torrentInfo[ torrentId ], torrentId ), torrentIds ) )
        if len( infos ) != 0:
            print( '%s\n' % '\n'.join(map(lambda info: '%s\n' % info, infos)))
        return
    if args.choose_option == 'resume':
        resume_torrents = args.resume_torrent
        torrentIds = _get_matching_torrents( client, resume_torrents )
        plexcore_deluge.deluge_resume_torrent( client, torrentIds )
        return
    if args.choose_option == 'pause':
        pause_torrents = args.pause_torrent
        torrentIds = _get_matching_torrents( client, pause_torrents )
        plexcore_deluge.deluge_pause_torrent( client, torrentIds )
        return
    if args.choose_option in ( 'rm', 'del' ):
        remove_torrents = args.remove_torrent
        torrentIds = _get_matching_torrents( client, remove_torrents )
        plexcore_deluge.deluge_remove_torrent( client, torrentIds, remove_data = args.remove_data )
        return
    if args.choose_option == 'push':
        status = plexcore_deluge.push_deluge_credentials(
            args.push_url, args.push_port, args.push_username, args.push_password )
        if status != 'SUCCESS': print( status )
        return
    if args.choose_option == 'add': # adds a single torrent file or magnet URL
        candidate_add = args.add_torrent
        if candidate_add.startswith( 'magnet' ): # is magnet
            plexcore_deluge.deluge_add_magnet_file( client, candidate_add )
            return
        if plexcore_deluge.deluge_is_url( candidate_add ): # is an URL
            plexcore_deluge.deluge_add_url( client, candidate_add )
            return
        if plexcore_deluge.deluge_is_torrent_file( candidate_add ): # is a torrent file
            plexcore_deluge.deluge_add_torrent_file( client, candidate_add )
            return
        return
