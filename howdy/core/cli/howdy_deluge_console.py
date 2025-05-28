import sys, os, signal, tabulate, datetime
# code to handle Ctrl+C, convenience method for command line tools
def _signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, _signal_handler )
from argparse import ArgumentParser
#
from howdy.core import core_deluge, core_torrents

def _get_matching_torrents( client, list_of_torrents, operation_if_size_1 = False ):
    if any(map(lambda tok: tok == "*", list_of_torrents ) ):
        return core_deluge.deluge_get_matching_torrents( client, [ "*" ] )
    if operation_if_size_1 and len( list_of_torrents ) == 0:
        return core_deluge.deluge_get_matching_torrents( client, [ "*" ] )
    return core_deluge.deluge_get_matching_torrents( client, list_of_torrents )

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
                                 'Example usage is "howdy_deluge_console info ab1 bc2", where "ab1" and "bc2" are the first three digits of the MD5 hashes of torrents to examine.' ]))
    parser_info.add_argument( '-f', '--file', dest='info_do_filename', action='store_true', default = False,
                             help = 'If chosen, then spit out the torrent selections into a debug output file. Name of the file is given by howdy_deluge_console.YYYYMMDD-HHMMSS.txt' )
    #
    ## resume
    parser_resume = subparser.add_parser( 'resume', help = 'Resume selected torrents, or all torrents.' )
    parser_resume.add_argument( 'resume_torrent', metavar='torrent', type=str, nargs='+',
                               help = ' '.join([
                                   'The hash ID, or identifying initial substring, of torrents to resume.',
                                   'Example usage is "howdy_deluge_console resume ab1 bc2", where "ab1" and "bc2" are the first three digits of the MD5 hashes of torrents to resume.' ]))
    #
    ## pause
    parser_pause = subparser.add_parser( 'pause', help = 'Pause selected torrents, or all torrents.' )
    parser_pause.add_argument( 'pause_torrent', metavar = 'torrent', type=str, nargs='+',
                              help = '\n'.join([
                                  'The hash ID, or identifying initial substring, of torrents to pause.',
                                  'Example usage is "howdy_deluge_console resume ab1 bc2", where "ab1" and "bc2" are the first three digits of the MD5 hashes of torrents to pause.' ]))
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
    parser_push.add_argument('--username', dest='push_username', metavar = 'username', action='store', type=str, default = 'admin',
                             help = 'Username to login to the deluge server. Default is admin.' )
    parser_push.add_argument('--password', dest='push_password', metavar = 'password', action='store', type=str, default = 'admin',
                            help = 'Password to login to the deluge server. Default is admin.' )
    #
    ## start operation
    args = parser.parse_args( )
    client, status = core_deluge.get_deluge_client( )
    if status != 'SUCCESS':
        print( "ERROR, COULD NOT GET VALID DELUGE CLIENT." )
        return

    #
    ## torrent info
    if args.choose_option == 'info':
        info_torrents = args.info_torrent
        torrentIds = _get_matching_torrents( client, info_torrents, operation_if_size_1 = True )
        torrentInfo = core_deluge.deluge_get_torrents_info( client )
        infos = list(map(lambda torrentId: core_torrents.torrent_format_info(
            torrentInfo[ torrentId ], torrentId ), torrentIds ) )
        if len( infos ) == 0: return
        mystr = '\n'.join(map(lambda info: '%s\n' % info, infos))
        if args.info_do_filename:
            fname = 'howdy_deluge_console.%s.txt' % (
                datetime.datetime.now( ).strftime( '%Y%m%d-%H%M%s' ) )
            with open( fname, 'w' ) as openfile:
                openfile.write( '%s\n' % mystr )
        else: print( '%s\n' % mystr )
        return
    if args.choose_option == 'resume':
        resume_torrents = args.resume_torrent
        torrentIds = _get_matching_torrents( client, resume_torrents )
        core_deluge.deluge_resume_torrent( client, torrentIds )
        return
    if args.choose_option == 'pause':
        pause_torrents = args.pause_torrent
        torrentIds = _get_matching_torrents( client, pause_torrents )
        core_deluge.deluge_pause_torrent( client, torrentIds )
        return
    if args.choose_option in ( 'rm', 'del' ):
        remove_torrents = args.remove_torrent
        torrentIds = core_deluge.deluge_get_matching_torrents( client, remove_torrents )
        core_deluge.deluge_remove_torrent( client, torrentIds, remove_data = args.remove_data )
        return
    if args.choose_option == 'push':
        status = core_deluge.push_deluge_credentials(
            args.push_url, args.push_port, args.push_username, args.push_password )
        if status != 'SUCCESS': print( status )
        return
    if args.choose_option == 'add': # adds a single torrent file or magnet URL
        candidate_add = args.add_torrent
        if candidate_add.startswith( 'magnet' ): # is magnet
            core_deluge.deluge_add_magnet_file( client, candidate_add )
            return
        if core_torrents.torrent_is_url( candidate_add ): # is an URL
            core_deluge.deluge_add_url( client, candidate_add )
            return
        if core_torrents.torrent_is_torrent_file( candidate_add ): # is a torrent file
            core_deluge.deluge_add_torrent_file( client, candidate_add )
            return
        return
