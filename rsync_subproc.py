#!/usr/bin/env python3

import os, sys, numpy, subprocess, shlex, time, logging
from optparse import OptionParser
from configparser import RawConfigParser

_mainFile = os.path.join( os.path.expanduser( '~/.config/plexstuff' ),
                          'plex_creds.conf' )
                          
def _push_credentials( local_dir, sshpath, subdir = None ):
    assert( os.path.isdir( os.path.abspath( local_dir ) ) )
    cparser = RawConfigParser( )
    if os.path.isfile( _mainFile ):
        cparser.read( _mainFile )
    cparser.remove_section( 'RSYNC' )
    cparser.add_section( 'RSYNC' )
    cparser.set( 'RSYNC', 'local_dir', os.path.abspath( local_dir ) )
    cparser.set( 'RSYNC', 'sshpath', sshpath.strip( ) )
    if subdir is not None: cparser.set( 'RSYNC', 'subdir', subdir.strip( ) )
    mystr_split = [
        'local directory to download to: %s' % os.path.abspath( local_dir ),
        'SSH path from which to get files: %s' % sshpath.strip( ),
    ]
    if subdir is not None:
        mystr_split.append( 'sub directory on local machine from which to get files: %s' % subdir )
    logging.debug('\n'.join( mystr_split ) )
    with open( _mainFile, 'w') as openfile:
        cparser.write( openfile )
    os.chmod( _mainFile, 0o600 )

def _get_rsync_command( data, mystr ):
    if data['subdir'] is not None: mainStr = os.path.join( data['subdir'], mystr.strip( ) )
    else: mainStr = mystr.strip( )
    mycmd = 'rsync -P -avz -e ssh %s:%s .' % ( data[ 'sshpath' ], mainStr )
    return mycmd
    
def _get_credentials( ):
    if not os.path.isfile( _mainFile ):
        logging.debug('ERROR, %s does not exist.' % _mainFile )
        return None
    cparser = RawConfigParser( )
    cparser.read( _mainFile )
    if not cparser.has_section( 'RSYNC' ):
        logging.debug( 'ERROR, RSYNC section not in config file.' )
        return None
    if any(map(lambda tok: not cparser.has_option( 'RSYNC', tok ),
               [ 'local_dir', 'sshpath' ] ) ):
        logging.debug('ERROR, RSYNC section missing one of %s.' % (
            [ 'local_dir', 'sshpath' ] ) )
        return None
    data = dict(map(lambda tok: ( tok, cparser.get( 'RSYNC', tok ).strip( ) ),
                    [ 'local_dir', 'sshpath' ] ) )
    if not cparser.has_option( 'RSYNC', 'subdir' ): data['subdir'] = None
    else: data['subdir'] = cparser.get( 'RSYNC', 'subdir' ).strip( )
    return data


def main( ):
    parser = OptionParser( )
    parser.add_option('-S', '--string', dest='string', type=str, action='store', default = '*.mkv',
                      help = 'the globbed string to rsync from on the remote account. Default is "*.mkv".' )
    parser.add_option('-N', '--numtries', dest='numtries', type=int, action='store', default=10,
                      help = 'number of attempts to go through an rsync process. Default is 10.' )
    parser.add_option('-D', '--debug', dest='do_debug', action='store_true', default = False,
                      help = 'if chosen, then write debug output.' )
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
    opts, args = parser.parse_args( )
    if opts.do_debug: logging.basicConfig( level = logging.DEBUG )
    if opts.do_push:
        assert( all(map(lambda tok: tok is not None, ( opts.local_dir, opts.sshpath ) ) ) )
        assert( os.path.isdir( os.path.abspath( opts.local_dir ) ) )
        _push_credentials( opts.local_dir, opts.sshpath, subdir = opts.subdir )
        return

    #
    ## otherwise get credentials and run
    data = _get_credentials( )
    if data is None: return
    local_dir = data[ 'local_dir' ].strip( )
    sshpath = data[ 'sshpath' ].strip( )
    if os.path.abspath( os.getcwd( ) ) != local_dir:
        print('ERROR, not in %s. Exiting...' % local_dir )
        return
    assert( opts.numtries > 0 )
    assert( len( opts.string.strip( ).split( ) ) == 1 ) # no spaces in this string
    #
    mycmd = _get_rsync_command( data, opts.string.strip( ) )
    print('STARTING THIS RSYNC CMD: %s' % mycmd )
    success = False
    time0 = time.time( )
    for idx in range( opts.numtries ):
        time00 = time.time( )
        proc = subprocess.Popen( shlex.split( mycmd ), stdout = subprocess.PIPE,
                                 stderr = subprocess.STDOUT )
        stdout_val, stderr_val = proc.communicate( )
        if not any(map(lambda line: 'dispatch_run_fatal' in line, stdout_val.decode('utf-8').split('\n'))):
            print('SUCCESSFUL ATTEMPT %d / %d IN %0.3f SECONDS.' % ( idx + 1, opts.numtries,
                                                                     time.time( ) - time00 ) )
            success = True
            logging.debug( '%s\n' % stdout_val.decode( 'utf-8' ) )
            break
        print('FAILED ATTEMPT %d / %d IN %0.3f SECONDS.' % ( idx + 1, opts.numtries,
                                                             time.time( ) - time00 ) )
        logging.debug( '%s\n' % stdout_val.decode( 'utf-8' ) )

    if not success:
        print('ATTEMPTED AND FAILED %d TIMES IN %0.3f SECONDS TOTAL.' % (
            opts.numtries, time.time( ) - time0 ) )
        
    logging.debug('%s\n' % stdout_val.decode( 'utf-8' ) )

if __name__=='__main__':
    main( )
