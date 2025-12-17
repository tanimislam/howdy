import os, subprocess, time, logging, shlex, sys
from shutil import which
from fabric import Connection
from patchwork.files import exists, directory
#
from howdy.core import session, PlexConfig, SSHUploadPaths

def check_remote_connection_paths( sshpath, password, mainDir_remote, subdirs_dict = dict() ):
    """
    Checks whether one can upload to the following remote directory, ``mainDir_remote``, and the following subdirectories in the :py:class:`dict` of ``subdirs_dict``.

    ``subdirs_dict`` need not be populated (may be empty). If it is, each key is an identifying name, and each value is a subdirectory attached to mainDir_remote.

    :param str sshpath: the full path with username and host name for the SSH server. Format is ``'username@hostname'``.
    :param str password: the password to connect as the SSH server.
    :param str mainDir_remote: the full top level directory path on the remote server.
    :param dict subdirs_dict: the dictionary of remote paths on the remote server. The key is an identifying name, such as ``foo``; the value is a full subdirectory off ``mainDir_remote``. For example, if the value is ``full/subdir/path``, then the directory name on the remote server is ``mainDir_remote/full/subdir/path``.

    :returns: if everything works, return ``'SUCCESS'``. If fails, return specific illuminating error messages.
    :rtype: str
    """

    try:
        #
        ## first, can we login with username and password?
        uname = sshpath.split('@')[0]
        hostname = sshpath.split('@')[1]
        # raises a ValueError if cannot do so
        # needs to pass in look_for_keys = False so not use id_* keys
        with Connection( hostname, user = uname,
                         connect_kwargs = {
                             'password' : password,
                             'look_for_keys' : False } ) as conn:
            conn.run( 'ls', hide = True ) # errors out if not a valid connection
            if not exists( conn, mainDir_remote ):
                raise ValueError( "Error, %s does not exist in remote server." % mainDir_remote )
            #
            ## will raise an error if this is a file
            directory( conn, mainDir_remote )

            all_subdirs = set(map(lambda subdir: os.path.join( mainDir_remote, subdir ), set(subdirs_dict.values( ) )) )
            logging.info( 'checking through %d possible subdirectories' % len( all_subdirs ) )
            logging_messages = [ ]
            for full_subdir in all_subdirs:
                if not exists( conn, full_subdir ):
                    logging_messages.append(
                        "Error, %s does not exist in remote server." % full_subdir )
                    continue
                try:
                    directory( conn, full_subdir )
                except:
                    logging_message.append(
                        "Error, %s exists on remote server, but it is a file." % full_subdir )
            
            if len( logging_messages ) == 0:
                return 'SUCCESS'
            raise ValueError( '\n'.join( logging_messages ) )
    except Exception as e:
        return str( e )

def push_remote_connection( alias, mediatype, sshpath, password, mainDir_remote, subdirs_dict = dict() ):
    """
    Push the rsync-ing upload configuration to the Plex_ server (``alias``, ``sshpath``, ``password``, ``mainDir_remote``, and ``subdirs_dict``), if working, into the SQLite3_ database of SSH media uplodads.

    :param str alias: the alias used to uniquely identify the collection of directories, each identified by keys, to the remote Plex_ and SSH server.
    :param mediatype: the :py:class:`Enum <enum.Enum>` that defines the type of media in the directory collection.
    :type: :py:class:`MediaType <howdy.core.SSHUploadPaths.MediaType>`
    :param str sshpath: the full path with username and host name for the SSH server. Format is ``'username@hostname'``.
    :param str password: the password to connect as the SSH server.
    :param str mainDir_remote: the full top level directory path on the remote server.
    :param dict subdirs_dict: the dictionary of remote paths on the remote server. The key is an identifying name, such as ``foo``; the value is a full subdirectory off ``mainDir_remote``. For example, if the value is ``full/subdir/path``, then the directory name on the remote server is ``mainDir_remote/full/subdir/path``.

    :returns: if everything works, return ``'SUCCESS'``. If fails, return specific illuminating error messages.
    :rtype: str
    """
    status = check_remote_connection_paths(
        sshpath, password, mainDir_remote, subdirs_dict = subdirs_dict )
    if status != 'SUCCESS':
        return "ERROR, COULD NOT SET UP A VALID CONNECTION TO REMOTE SERVER = %s." % sshpath
    #
    ## success
    val = session.query( SSHUploadPaths ).filter(
        SSHUploadPaths.alias == alias ).first( )
    if val is not None:
        session.delete( val )
        session.commit( )
    newval = SSHUploadPaths(
        alias = alias,
        mediatype = mediatype,
        sshpath = sshpath,
        password = password,
        maindir = mainDir_remote,
        subdirs = subdirs_dict )
    session.add( newval )
    session.commit( )

def remove_remote_connection( alias ):
    """
    Remove a single remote media directory collection, identified by its alias.

    :param str alias: the alias used to uniquely identify the collection of directories, each identified by keys, to the remote Plex_ and SSH server.

    :returns: if alias exists, return ``'SUCCESS'``. Otherwise, return nothing.
    :rtype: str
    """
    val = session.query( SSHUploadPaths ).filter(
        SSHUploadPaths.alias == alias ).first( )
    if val is None:
        return "Could not find remote directory collection identified by alias = %s." % alias
    session.delete( val )
    session.commit( )
    return "SUCCESS"

def get_remote_connections( show_password = False ):
    """
    Get *all* the remote connections.

    :param bool show_password: by default ``False``. If ``True``, then also include the password associated with each remote media directory collection.
    
    :returns: a :py:class:`dict` of all the remote Plex_ media directory collections. The key is the ``alias`` string.
    :rtype: dict
    """
    dict_to_return = dict()
    for entry in sorted(session.query( SSHUploadPaths ), key = lambda entr: entr.alias ):
        alias = entry.alias
        data = {
            'ssh path' : entry.sshpath,
            'media type' : entry.mediatype.name,
            'main directory' : entry.maindir,
            'sub directories' : dict(
                map(lambda key: (key, os.path.join( entry.maindir, entry.subdirs[ key ] ) ),
                    entry.subdirs ) ),
        }
        if show_password:
            data[ 'password' ] = entry.password
        dict_to_return[ alias ] = data
    return dict_to_return
    
    
## see if the data is valid
def check_credentials( local_dir, sshpath, password, subdir = None ):
    """
    Checks whether one can download to (or upload from) the directory ``local_dir`` on the Plex_ server to the remote SSH server.

    :param str local_dir: the local directory, on the Plex_ server, into which to download files from the remote SSH server.
    :param str sshpath: the full path with username and host name for the SSH server. Format is ``'username@hostname'``.
    :param str password: the password to connect as the SSH server.
    :param str subdir: if not ``None``, the subdirectory on the remote SSH server from which to download files.

    :returns: if everything works, return ``'SUCCESS'``. If fails, return specific illuminating error messages.
    :rtype: str

    .. seealso::
    
       * :py:meth:`push_credentials <howdy.core.core_rsync.push_credentials>`.
       * :py:meth:`get_credentials <howdy.core.core_rsync.get_credentials>`.
    """
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
    """
    Push the rsync'ing setup (``local_dir``, ``sshpath``, ``password``, and ``subdir``), if working, into the SQLite3_ configuration database.
    
    :param str local_dir: the local directory, on the Plex_ server, into which to download files from the remote SSH server.
    :param str sshpath: the full path with username and host name for the SSH server. Format is ``'username@hostname'``.
    :param str password: the password to connect as the SSH server.
    :param str subdir: if not ``None``, the subdirectory on the remote SSH server from which to download files.
    
    :returns: if successful, return ``'SUCCESS'``. If not, return error messages.
    :rtype: str
    
    .. seealso::
    
       * :py:meth:`check_credentials <howdy.core.core_rsync.check_credentials>`.
       * :py:meth:`get_credentials <howdy.core.core_rsync.get_credentials>`.
    """
    
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
    """
    Returns the rsync'ing setup from the SQLite3_ configuration database as a :py:class:`dict` in the following form.
    
    .. code-block:: python

       { 'local_dir' : XXXX,
         'sshpath' : YYYY@ZZZZ,
         'password' : AAAA,
         'subdir' : BBBB }

    :returns: the :py:class:`dict` of the rsync'ing setup if in the SQLite3_ configuration database, otherwise ``None``.
    :rtype: dict
    
    .. seealso::
    
       * :py:meth:`check_credentials <howdy.core.core_rsync.check_credentials>`.
       * :py:meth:`push_credentials <howdy.core.core_rsync.push_credentials>`.
    """
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

def get_rsync_command( data, mystr, do_download = True, do_local_rsync = False, use_local_dir_for_upload = True ):
    """
    Returns a :py:class:`tuple` of the actual rsync_ command, and the command with password information obscured, to download from or upload to the remote SSH server from the Plex_ server. *We require that sshpass_ exists and is accessible on this system*.
    
    :param data: the :py:class:`dict` of rsync'ing configuration, described in :py:meth:`get_credentials <howdy.core.core_rsync.get_credentials>`.
    :param str mystr: the specific rsync_ syntax describing those files/folders to upload or download. See, e.g., `this website <https://www.tecmint.com/rsync-local-remote-file-synchronization-commands/>`_ for some practical examples of file or directory listings.

    :param bool do_download: if ``True``, then download from remote SSH server. If ``False``, then upload to remote SSH server.

    :param bool do_local_rsync: if ``True``, then instead of SSH-ing do an effectively move command from path = ``os.path.expanduser( os.path.join( "~", data[ 'subdir' ], mystr ) )`` into ``data['local_dir']`` via rsync. This *requires* that data['subdir'] is *not* ``None``.

    :param bool use_local_dir_for_upload: when ``do_download`` is False (doing upload), and if ``True``, then the full path to upload to remote server adds the directory defined by ``data['local_dir']`` to the source file or directory path. Otherwise, *do not* append ``data['local_dir']`` to the source when setting the full path.

    :returns: a :py:class:`tuple` of the actual rsync_ command, and the command with password information obscured, to download from or upload to the remote SSH server from the Plex_ server.
    :rtype: tuple

    .. _sshpass: https://linux.die.net/man/1/sshpass
    """
    #
    ## do local_rsync, return simplified command command, data[ 'subdir' ] must NOT be None
    if do_local_rsync:
        assert( data[ 'subdir' ] is not None )
        mainStr = os.path.expanduser( os.path.join( '~', data[ 'subdir' ], mystr ) )
        mycmd = 'mv %s %s/' % (
            mainStr, data[ 'local_dir' ] )
        return mycmd, mycmd    
    #
    ## now do remote instead
    sshpass_exec = which( 'sshpass' )
    assert( sshpass_exec is not None )
    if do_download:
        if data['subdir'] is not None:
            mainStr = os.path.join( data['subdir'], mystr.strip( ) )
        else: mainStr = mystr.strip( )
        mycmd = 'rsync --remove-source-files -P -avzs --info=progress2 --rsh="%s %s ssh" -e ssh %s:%s %s/' % (
            sshpass_exec, data[ 'password' ], data[ 'sshpath' ], mainStr, data['local_dir'] )
        mxcmd = 'rsync --remove-source-files -P -avzs --info=progress2 --rsh="%s XXXX ssh" -e ssh %s:%s %s/' % (
            sshpass_exec, data[ 'sshpath' ], mainStr, data['local_dir'] )
    else:
        fullpath = mystr
        if use_local_dir_for_upload:
            fullpath = os.path.join( data['local_dir'], mystr )
        #
        if data['subdir'] is not None:
            mycmd = 'rsync --remove-source-files -P --info=progress2 --rsh="%s %s ssh" -avzs -e ssh "%s" "%s:%s/"' % (
                sshpass_exec, data[ 'password' ], fullpath, data[ 'sshpath' ], data['subdir'] )
            mxcmd = 'rsync --remove-source-files -P --rsh="%s XXXX ssh" -avzs -e ssh "%s" "%s:%s/"' % (
                sshpass_exec, fullpath, data[ 'sshpath' ], data['subdir'] )
        else:
            mycmd = 'rsync --remove-source-files -P -avzs --info=progress2 --rsh="%s %s ssh" -e ssh %s %s:' % (
                sshpass_exec, data[ 'password' ], fullpath, data[ 'sshpath' ] )
            mxcmd = 'rsync --remove-source-files -P -avzs --info=progress2 --rsh="%s XXXX ssh" -e ssh %s %s:' % (
                sshpass_exec, fullpath, data[ 'sshpath' ] )
    return mycmd, mxcmd

def download_upload_files( glob_string, numtries = 10, debug_string = False,
                           do_reverse = False, do_local_rsync = False ):
    """
    Run the system process, using rsync_, to download files and directories from, or upload to, the remote SSH server. *On completion, the source files are all deleted*.

    :param str glob_string: the description of files and directories (such as ``'*.mkv'`` to represent all MKV files) to upload/download.
    :param int numtries: the number of attempts to run rsync_ before giving up on uploading or downloading.
    :param bool debug_string: if ``True``, then print out the password-stripped rsync_ command that is being run.
    :param bool do_reverse: if ``True``, then upload files to remote SSH server. If ``False`` (the default), then download files from the SSH server.
    :param bool do_local_rsync: if ``True``, then instead of SSH-ing do an effectively move command from path = ``os.path.expanduser( "~", data[ 'subdir' ], mystr )`` into ``data['local_dir']`` via rsync. This *requires* that data['subdir'] is *not* ``None``.

    :returns: a :py:class:`tuple` of "SUCCESS" and the log of rsync_ command, otherwise "FAILURE" and specific reason for failure.
    :rtype: tuple
    """
    assert( numtries > 0 )
    data = get_credentials( )
    if data is None:
        return "FAILURE", "could not get credentials for performing rsync operation"
    local_dir = data[ 'local_dir' ].strip( )
    sshpath = data[ 'sshpath' ].strip( )
    mycmd, mxcmd = get_rsync_command( data, glob_string, do_download = not do_reverse, do_local_rsync = do_local_rsync )
    #mycmd, mxcmd = get_rsync_command( data, glob_string, do_download = not do_reverse ) # not working for now...
    mystr_split = [ 'STARTING THIS RSYNC CMD: %s' % mxcmd ]
    if debug_string:
        print( mystr_split[-1] )
        print( 'TRYING UP TO %d TIMES.' % numtries )
    time0 = time.perf_counter( )
    for idx in range( numtries ):
        time00 = time.perf_counter( )
        stdout_val = subprocess.check_output(
            shlex.split( mycmd ), stderr = subprocess.STDOUT )
        if not any(map(lambda line: 'dispatch_run_fatal' in line, stdout_val.decode('utf-8').split('\n'))):
            mystr_split.append(
                'SUCCESSFUL ATTEMPT %d / %d IN %0.3f SECONDS.' % (
                    idx + 1, numtries, time.perf_counter( ) - time00 ) )
            if debug_string: print( mystr_split[-1] )
            logging.debug( '%s\n' % stdout_val.decode( 'utf-8' ) )
            return "SUCCESS", '\n'.join( mystr_split )
        mystr_split.append('FAILED ATTEMPT %d / %d IN %0.3f SECONDS.' % (
            idx + 1, numtries, time.perf_counter( ) - time00 ) )
        if debug_string: print( mystr_split[-1] )
        logging.debug( '%s\n' % stdout_val.decode( 'utf-8' ) )
    mystr_split.append( 'ATTEMPTED AND FAILED %d TIMES IN %0.3f SECONDS TOTAL.' % (
        numtries, time.perf_counter( ) - time0 ) )
    if debug_string: print( mystr_split[-1] )
    return "FAILURE", '\n'.join( mystr_split )
