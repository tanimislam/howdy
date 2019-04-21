import os, subprocess, time, logging, shlex
from . import session, Base, PlexConfig
from sqlalchemy import Column, Integer, String

def push_credentials( local_dir, sshpath, subdir = None ):
    assert( os.path.isdir( os.path.abspath( local_dir ) ) )
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
            'subdir' : subdir } )
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

def get_rsync_command( data, mystr ):
    if data['subdir'] is not None: mainStr = os.path.join( data['subdir'], mystr.strip( ) )
    else: mainStr = mystr.strip( )
    mycmd = 'rsync --remove-source-files -P -avz -e ssh %s:%s %s/' % ( data[ 'sshpath' ], mainStr, data['local_dir'] )
    return mycmd

def get_credentials( ):
    query = session.query( PlexConfig ).filter(
        PlexConfig.service == 'rsync' ).first( )
    if val is None:
        logging.debug('ERROR, RSYNC configuration does not exist.' )
        return None
    data = val.data
    local_dir = data['localdir']
    sshpath = data['sshpath']
    subdir = data['subdir']
    data = { 'local_dir' : local_dir,
             'sshpath' : sshpath }
    if subdir is None: data['subdir'] = None
    else: data['subdir'] = subdir.strip( )
    return data

def download_files( glob_string, numtries = 10, debug_string = False ):
    assert( numtries > 0 )
    data = get_credentials( )
    if data is None:
        return "FAILURE", "could not get credentials for performing rsync operation"
    local_dir = data[ 'local_dir' ].strip( )
    sshpath = data[ 'sshpath' ].strip( )
    mycmd = get_rsync_command( data, glob_string )
    mystr_split = [ 'STARTING THIS RSYNC CMD: %s' % mycmd ]
    if debug_string: print( mystr_split[-1] )
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
