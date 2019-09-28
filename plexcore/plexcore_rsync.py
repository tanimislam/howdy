import os, subprocess, time, logging, shlex, sys
from functools import reduce
_mainDir = reduce(lambda x,y: os.path.dirname( x ), range( 2 ),
                  os.path.abspath( __file__ ) )
sys.path.append( _mainDir )
from distutils.spawn import find_executable
from fabric import Connection
from patchwork.files import exists, directory

from plexcore import session, PlexConfig

## see if the data is valid
def check_credentials( local_dir, sshpath, password, subdir = None ):
    try:
        #
        ## first, does local directory exist?        
        if not os.path.isdir( os.path.abspath( local_dir ) ):
            raise ValueError( "Error, %s is not a directory." %
                              os.path.abspath( local_dir ) )
        #
        ## second, can we login with username and password?
        uname = sshpath.split('@')[0]
        hostname = sshpath.split('@')[1]
        print( uname, hostname )
        # raises a ValueError if cannot do so
        # needs to pass in look_for_keys = False so not use id_* keys
        with Connection( hostname, user = uname,
                         connect_kwargs = {
                             'password' : password,
                             'look_for_keys' : False } ) as conn:
            conn.run( 'ls', hide = True ) # errors out if not a valid connection
            #
            ## third, if subdir is None does it exist?
            if subdir is not None:
                if not exists( conn, subdir ):
                    raise ValueError( "Error, %s does not exist." % subdir )
                # will raise an error if this is a file
                directory( conn, subdir )
        return 'SUCCESS'
    except Exception as e:
        return str( e )

def push_credentials( local_dir, sshpath, password, subdir = None ):
    #
    ## validation to see if the data is valid
    #
    ## first, does local directory exist?
    status = check_credentials( local_dir, sshpath, password,
                                 subdir = subdir )
    if status != 'SUCCESS':
        return "ERROR, COULD NOT SET RSYNC SSH CONNECTION CREDENTIALS"

    #
    ## success
    val = session.query( PlexConfig ).filter(
        PlexConfig.service == 'rsync' ).first( )
    if val is not None:
        session.delete( val )
        session.commit( )
    newval = PlexConfig(
        service = 'rsync',
        data = {
            'localdir' : os.path.abspath( local_dir.strip( ) ),
            'sshpath' : sshpath.strip( ),
            'subdir' : subdir,
            'password' : password } )
    session.add( newval )
    session.commit( )
    mystr_split = [
        'local directory to download to: %s' % os.path.abspath( local_dir.strip( ) ),
        'SSH path from which to get files: %s' % sshpath.strip( ),
    ]
    if subdir is not None:
        mystr_split.append( 'sub directory on local machine from which to get files: %s' % subdir )
        logging.debug('\n'.join( mystr_split ) )
    if subdir is not None:
        mystr_split.append( 'sub directory on local machine from which to get files: %s' % subdir )
    logging.debug('\n'.join( mystr_split ) )
    return 'SUCCESS'

def get_credentials( ):
    val = session.query( PlexConfig ).filter(
        PlexConfig.service == 'rsync' ).first( )
    if val is None:
        logging.debug('ERROR, RSYNC configuration does not exist.' )
        return None
    data = val.data
    local_dir = data['localdir']
    sshpath = data['sshpath']
    subdir = data['subdir']
    datan = { 'local_dir' : local_dir,
              'sshpath' : sshpath }
    if 'password' not in data:
        datan[ 'password'] = None
    else: datan[ 'password' ] = data['password']
    if subdir is None: datan['subdir'] = None
    else: datan['subdir'] = subdir.strip( )
    return datan

def get_rsync_command( data, mystr, do_download = True ):
    if do_download:
        if data['subdir'] is not None:
            mainStr = os.path.join( data['subdir'], mystr.strip( ) )
        else: mainStr = mystr.strip( )
        mycmd = 'rsync --remove-source-files -P -avz --rsh="/usr/bin/sshpass %s ssh" -e ssh %s:%s %s/' % (
            data[ 'password' ], data[ 'sshpath' ], mainStr, data['local_dir'] )
        mxcmd = 'rsync --remove-source-files -P -avz --rsh="/usr/bin/sshpass XXXX ssh" -e ssh %s:%s %s/' % (
            data[ 'sshpath' ], mainStr, data['local_dir'] )
    else:
        fullpath = os.path.join( data['local_dir'], mystr )
        if data['subdir'] is not None:
            mycmd = 'rsync --remove-source-files -P --rsh="/usr/bin/sshpass %s ssh" -avz -e ssh %s %s:%s/' % (
                data[ 'password' ], fullpath, data[ 'sshpath' ], data['subdir'] )
            mxcmd = 'rsync --remove-source-files -P --rsh="/usr/bin/sshpass XXXX ssh" -avz -e ssh %s %s:%s/' % (
                fullpath, data[ 'sshpath' ], data['subdir'] )
        else:
            mycmd = 'rsync --remove-source-files -P -avz --rsh="/usr/bin/sshpass %s ssh" -e ssh %s %s:' % (
                data[ 'password' ], fullpath, data[ 'sshpath' ] )
            mxcmd =  'rsync --remove-source-files -P -avz --rsh="/usr/bin/sshpass XXXX ssh" -e ssh %s %s:' % (
                fullpath, data[ 'sshpath' ] )
    return mycmd, mxcmd

def download_upload_files( glob_string, numtries = 10, debug_string = False,
                           do_reverse = False ):
    assert( numtries > 0 )
    data = get_credentials( )
    if data is None:
        return "FAILURE", "could not get credentials for performing rsync operation"
    local_dir = data[ 'local_dir' ].strip( )
    sshpath = data[ 'sshpath' ].strip( )
    mycmd, mxcmd = get_rsync_command( data, glob_string, do_download = not do_reverse )
    mystr_split = [ 'STARTING THIS RSYNC CMD: %s' % mxcmd ]
    if debug_string:
        print( mystr_split[-1] )
        print( 'TRYING UP TO %d TIMES.' % numtries )
    time0 = time.time( )
    for idx in range( numtries ):
        time00 = time.time( )
        proc = subprocess.Popen( shlex.split( mycmd ), stdout = subprocess.PIPE,
                                 stderr = subprocess.STDOUT )
        stdout_val, stderr_val = proc.communicate( )
        if not any(map(lambda line: 'dispatch_run_fatal' in line, stdout_val.decode('utf-8').split('\n'))):
            mystr_split.append(
                'SUCCESSFUL ATTEMPT %d / %d IN %0.3f SECONDS.' % (
                    idx + 1, numtries, time.time( ) - time00 ) )
            if debug_string: print( mystr_split[-1] )
            logging.debug( '%s\n' % stdout_val.decode( 'utf-8' ) )
            return "SUCCESS", '\n'.join( mystr_split )
        mystr_split.append('FAILED ATTEMPT %d / %d IN %0.3f SECONDS.' % (
            idx + 1, numtries, time.time( ) - time00 ) )
        if debug_string: print( mystr_split[-1] )
        logging.debug( '%s\n' % stdout_val.decode( 'utf-8' ) )
    mystr_split.append( 'ATTEMPTED AND FAILED %d TIMES IN %0.3f SECONDS TOTAL.' % (
        numtries, time.time( ) - time0 ) )
    if debug_string: print( mystr_split[-1] )
    return "FAILURE", '\n'.join( mystr_split )
