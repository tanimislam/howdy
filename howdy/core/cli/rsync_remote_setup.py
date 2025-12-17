import signal
from howdy import signal_handler
signal.signal( signal.SIGINT, signal_handler )
import time, logging, subprocess, shlex, tabulate, sys, os
from argparse import ArgumentParser
#
from howdy.core import core_rsync, SSHUploadPaths

def _show_all_remote_directory_collections( fulldict ):
    data = [ ]
    return

def main( ):
    parser = ArgumentParser( )
    parser.add_argument('-D', '--debug', dest='do_debug', action='store_true', default = False,
                        help = 'if chosen, then write debug output.' )
    #
    subparser = parser.add_subparsers( help = 'Choose one of these three modes of operation: show, add, remove.',
                                       dest = 'choose_option' )
    #
    ## show all the remote plex server directory collections
    parser_show   = subparser.add_parser( 'show', help = "Show all the remote media directory collections." )
    #
    ## now adding remote plex server directory collection
    parser_add    = subparser.add_parser( 'add', help = 'Add a NEW/replace existing remote media directory collection.' )
    parser_add.add_argument( '-A', '--alias', dest = 'add_alias', type = str, action = 'store', required = True,
                             help = 'The alias to identify the remote media directory collection.' )
    parser_add.add_argument( '-T', '--mediatype', dest = 'add_mediatype', type = str, choices = sorted( SSHUploadPaths.mediatype_enum_mapping_rev ),
                             default = SSHUploadPaths.MediaType.movie.name,
                             help = 'The type of media for this remote media directory collection. Choices are %s. Default is %s.' % (
                                 sorted( SSHUploadPaths.mediatype_enum_mapping_rev ),
                                 SSHUploadPaths.MediaType.movie.name ) )
    parser_add.add_argument( '-s', '--sshpath', dest = 'add_sshpath', type = str, action = 'store', required = True,
                             help = "The full path with username and host name for the SSH server. Format is 'username@hostname'." )
    parser_add.add_argument( '-P', '--password', dest = 'add_password', type = str, action = 'store', required = True,    
                             help = 'The password to the SSH Plex media server.' )
    parser_add.add_argument( '-M', '--maindir', dest = 'add_maindir', type = str, action = 'store', required = True,
                             help = 'The full top level directory path on the remote server.' )
    parser_add.add_argument( '-S', '--subdirs', dest = 'add_subdirs', type = str, nargs = '+', default = [],
                             help = 'Optional argument. Collection of sub directories underneath the main directory in the remote media directory collection.' )
    #
    ## now remove single plex server directory collection
    parser_remove = subparser.add_parser( 'remove', help = 'Remove existing remote media directory collection.' )
    parser_remove.add_argument( '-a', '--alias', dest = 'remove_alias', type = str, action = 'store', required = True,
                                help = 'Remove an existing remote directory collection, by alias.' )
    #
    ##
    args = parser.parse_args( )
    logger = logging.getLogger( )
    if args.do_debug: logging.basicConfig( level = logging.DEBUG )
    #
    ## show remote media directory collections
    if args.choose_option == 'show':
        data_remote_collections = core_rsync.get_remote_connections( )
        data_to_show = [ ]
        for alias in sorted( data_remote_collections ):
            subdirs_full_path = ''
            if len( data_remote_collections[ alias ][ 'sub directories' ] ) > 0:
                subdirs_full_path = tabulate.tabulate(
                    list(map(lambda key: ( key, data_remote_collections[ alias ][ 'sub directories' ][ key ] ),
                             data_remote_collections[ alias ][ 'sub directories' ] ) ),
                    headers = [ 'ALIAS', 'FULL PATH' ] )
                
            row_data = [ alias,
                         data_remote_collections[ alias ][ 'media type' ],
                         data_remote_collections[ alias ][ 'ssh path'   ],
                         data_remote_collections[ alias ][ 'main directory' ],
                         subdirs_full_path ]
            data_to_show.append( row_data )
        print( 'FOUND %d REMOTE MEDIA DIRECTORY COLLECTIONS.' % len( data_remote_collections ) )
        print( '' )
        print( '%s' % tabulate.tabulate( data_to_show, headers = [
            'ALIAS', 'MEDIA TYPE', 'SSH PATH', 'MAIN DIRECTORY', 'FULL SUB DIRECTORIES' ] ) )
        return
    #
    ## add remote media directory collection
    if args.choose_option == 'add':
        add_alias     = args.add_alias.strip( )
        add_mediatype = SSHUploadPaths.mediatype_enum_mapping_rev[ args.add_mediatype ]
        add_sshpath   = args.add_sshpath.strip( )
        add_password  = args.add_password.strip( )
        add_maindir   = args.add_maindir.strip( )
        add_subdirs   = set(map(lambda entry: entry.strip( ), args.add_subdirs ) )
        subdirs_dict  = dict(zip( add_subdirs, add_subdirs ) )
        core_rsync.push_remote_connection(
            add_alias, add_mediatype, add_sshpath,
            add_password, add_maindir, subdirs_dict = subdirs_dict )
