#!/usr/bin/env python3

import os, sys, time, logging, signal, subprocess, shlex
# code to handle Ctrl+C, convenience method for command line tools
def _signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, _signal_handler )
from argparse import ArgumentParser
#
from plexstuff.plexcore import plexcore_rsync

def main( ):
    parser = ArgumentParser( )
    parser.add_argument('-S', '--string', dest='string', type=str, action='store', default = '*.mkv',
                        help = 'the globbed string to rsync from on the remote account. Default is "*.mkv".' )
    parser.add_argument('-N', '--numtries', dest='numtries', type=int, action='store', default=10,
                        help = 'number of attempts to go through an rsync process. Default is 10.' )
    parser.add_argument('-D', '--debug', dest='do_debug', action='store_true', default = False,
                        help = 'if chosen, then write debug output.' )
    parser.add_argument('-R', '--reverse', dest='do_reverse', action='store_true', default = False,
                        help = ' '.join([ 'If chosen, push files from local server to remote.',
                                         'Since files are deleted from source once done,',
                                         'you should probably make a copy of the source files if',
                                         'you want to still keep them afterwards.' ]))
    #
    ## now pushing credentials
    parser.add_argument('-P', '--push', dest='do_push', action='store_true', default = False,
                        help = 'push RSYNC credentials into configuration file.' )
    parser.add_argument('-L', dest='local_dir', action='store', type=str, default = os.path.abspath( os.getcwd( ) ),
                        help = 'Name of the local directory into which we download files and directory. Default is %s.' %
                        ( os.path.abspath( os.getcwd( ) ) ) )
    parser.add_argument('--ssh', dest='sshpath', action='store', type=str,
                        help = 'SSH path from which to get files.' )
    parser.add_argument('--subdir', dest='subdir', action='store', type=str,
                        help = 'name of the remote sub directory from which to get files. Optional.' )
    #
    ##
    args = parser.parse_args( )
    if args.do_debug: logging.basicConfig( level = logging.DEBUG )
    if args.do_push:
        assert( all(map(lambda tok: tok is not None, ( args.local_dir, args.sshpath ) ) ) )
        assert( os.path.isdir( os.path.abspath( args.local_dir ) ) )
        plexcore_rsync.push_credentials( args.local_dir, args.sshpath, subdir = args.subdir )
        return
    
    #
    ## otherwise run
    assert( args.numtries > 0 )
    assert( len( args.string.strip( ).split( ) ) == 1 ) # no spaces in this string
    plexcore_rsync.download_upload_files(
        args.string.strip( ), args.numtries, debug_string = args.do_debug,
        do_reverse = args.do_reverse )
        
if __name__=='__main__':
    main( )
