#!/usr/bin/env python3

import os, sys, time, logging, signal, subprocess, shlex
# code to handle Ctrl+C, convenience method for command line tools
def _signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, _signal_handler )
#
from plexcore import plexcore_rsync
from optparse import OptionParser

def main( ):
    parser = OptionParser( )
    parser.add_option('-S', '--string', dest='string', type=str, action='store', default = '*.mkv',
                      help = 'the globbed string to rsync from on the remote account. Default is "*.mkv".' )
    parser.add_option('-N', '--numtries', dest='numtries', type=int, action='store', default=10,
                      help = 'number of attempts to go through an rsync process. Default is 10.' )
    parser.add_option('-D', '--debug', dest='do_debug', action='store_true', default = False,
                      help = 'if chosen, then write debug output.' )
    parser.add_option('-R', '--reverse', dest='do_reverse', action='store_true', default = False,
                      help = ' '.join([ 'If chosen, push files from local server to remote.',
                                        'Since files are deleted from source once done,',
                                        'you should probably make a copy of the source files if',
                                        'you want to still keep them afterwards.' ]))
    #
    ## now pushing credentials
    parser.add_option('-P', '--push', dest='do_push', action='store_true', default = False,
                      help = 'push RSYNC credentials into configuration file.' )
    parser.add_option('-L', dest='local_dir', action='store', type=str, default = os.path.abspath( os.getcwd( ) ),
                      help = 'Name of the local directory into which we download files and directory. Default is %s.' %
                      ( os.path.abspath( os.getcwd( ) ) ) )
    parser.add_option('--ssh', dest='sshpath', action='store', type=str,
                      help = 'SSH path from which to get files.' )
    parser.add_option('--subdir', dest='subdir', action='store', type=str,
                      help = 'name of the remote sub directory from which to get files. Optional.' )
    #
    ##
    opts, args = parser.parse_args( )
    if opts.do_debug: logging.basicConfig( level = logging.DEBUG )
    if opts.do_push:
        assert( all(map(lambda tok: tok is not None, ( opts.local_dir, opts.sshpath ) ) ) )
        assert( os.path.isdir( os.path.abspath( opts.local_dir ) ) )
        plexcore_rsync.push_credentials( opts.local_dir, opts.sshpath, subdir = opts.subdir )
        return
    
    #
    ## otherwise run
    assert( opts.numtries > 0 )
    assert( len( opts.string.strip( ).split( ) ) == 1 ) # no spaces in this string
    plexcore_rsync.download_upload_files(
        opts.string.strip( ), opts.numtries, debug_string = opts.do_debug,
        do_reverse = opts.do_reverse )
        
if __name__=='__main__':
    main( )
