import os, sys, numpy, logging, base64, subprocess
from shutil import which
#
from howdy.core import session, PlexConfig, core_torrents
_deluge_exec = which( 'deluge' )


# copied from deluge.ui.console.commands.info
_status_keys = [
    'state',
    'download_location',
    'tracker_host',
    'tracker_status',
    'next_announce',
    'name',
    'total_size',
    'progress',
    'num_seeds',
    'total_seeds',
    'num_peers',
    'total_peers',
    'eta',
    'download_payload_rate',
    'upload_payload_rate',
    'ratio',
    'distributed_copies',
    'num_pieces',
    'piece_length',
    'total_done',
    'files',
    'file_priorities',
    'file_progress',
    'peers',
    'is_seed',
    'is_finished',
    'active_time',
    'seeding_time',
    'time_since_transfer',
    'last_seen_complete',
    'seed_rank',
    'all_time_download',
    'total_uploaded',
    'total_payload_download',
    'total_payload_upload',
    'time_added',
]

def create_deluge_client( url, port, username, password ):
    """
    Creates a minimal Deluge torrent client to the Deluge seedbox server.

    :param str url: URL of the Deluge server.
    :param int port: port used to access the Deluge server.
    :param str username: server account username.
    :param str password: server account password.

    :returns: previously a lightweight `Deluge RPC client`_, although now it is a :py:class:`DelugeRPCClient <howdy.core.deluge_client_tanim.client.DelugeRPCClient>`.

    .. seealso::
    
       * :py:meth:`get_deluge_client <howdy.core.core_deluge.get_deluge_client>`.
       * :py:meth:`get_deluge_credentials <howdy.core.core_deluge.get_deluge_credentials>`.
       * :py:meth:`push_deluge_credentials <howdy.core.core_deluge.push_deluge_credentials>`.

    .. _`Deluge RPC client`: https://github.com/JohnDoee/deluge-client
    """
    from howdy.core.deluge_client_tanim import DelugeRPCClient
    client = DelugeRPCClient( url, port, username, password )
    client.connect( )
    assert( client.connected ) # make sure we can connect
    return client
    
def get_deluge_client( ):
    """
    Using a minimal Deluge torrent client from server credentials stored in the SQLite3_ configuration database.

    :returns: a :py:class:`tuple`. If successful, the first element is a lightweight `Deluge RPC client`_ and the second element is the string ``'SUCCESS'``. If unsuccessful, the first element is ``None`` and the second element is an error string.
    :rtype: tuple

    .. seealso::
    
       * :py:meth:`create_deluge_client <howdy.core.core_deluge.create_deluge_client>`.
       * :py:meth:`get_deluge_credentials <howdy.core.core_deluge.get_deluge_credentials>`.
       * :py:meth:`push_deluge_credentials <howdy.core.core_deluge.push_deluge_credentials>`.
    """
    query = session.query( PlexConfig ).filter(
        PlexConfig.service == 'deluge' )
    val = query.first( )
    if val is None:
        error_message = "ERROR, DELUGE CLIENT SETTINGS NOT DEFINED."
        logging.debug( error_message )
        return None, error_message
    data = val.data
    url = data['url']
    port = data['port']
    username = data['username']
    password = data['password']
    #
    ## now check that we have the correct info
    try:
        client = create_deluge_client( url, port, username, password )
        return client, 'SUCCESS'
    except Exception as e: # cannot connect to these settings
        error_message = 'ERROR, INVALID SETTINGS FOR DELUGE CLIENT.'
        logging.debug( str( e ) )
        return None, error_message

def get_deluge_credentials( ):
    """
    Gets the Deluge server credentials from the SQLite3_ configuration database. The data looks like this.

    .. code-block:: python
    
      { 'url': XXXX,
        'port': YYYY,
        'username': AAAA,
        'password': BBBB }
   
    :returns: dictionary of Deluge server settings.
    :rtype: dict

    .. seealso::
    
       * :py:meth:`create_deluge_client <howdy.core.core_deluge.create_deluge_client>`.
       * :py:meth:`get_deluge_client <howdy.core.core_deluge.get_deluge_client>`.
       * :py:meth:`push_deluge_credentials <howdy.core.core_deluge.push_deluge_credentials>`.
    """
    val = session.query( PlexConfig ).filter(
        PlexConfig.service == 'deluge' ).first( )
    if val is None: return None
    return val.data

def push_deluge_credentials( url, port, username, password ):
    """
    Stores the Deluge server credentials into the SQLite3_ configuration database.

    :param str url: URL of the Deluge server.
    :param int port: port used to access the Deluge server.
    :param str username: server account username.
    :param str password: server account password.
    
    :returns: if successful (due to correct Deluge server settings), returns ``'SUCCESS'``. If unsuccessful, returns ``'ERROR, INVALID SETTINGS FOR DELUGE CLIENT.'``
    :rtype: str

    .. seealso::
    
       * :py:meth:`create_deluge_client <howdy.core.core_deluge.create_deluge_client>`.
       * :py:meth:`get_deluge_client <howdy.core.core_deluge.get_deluge_client>`.
       * :py:meth:`get_deluge_credentials <howdy.core.core_deluge.get_deluge_credentials>`.
    """
    
    #
    ## first check that the configurations are valid
    try:
        client = create_deluge_client( url, port, username, password )
    except:
        error_message = 'ERROR, INVALID SETTINGS FOR DELUGE CLIENT.'
        logging.debug( error_message )
        return error_message
    #
    ## now put into the database
    query = session.query( PlexConfig ).filter(
        PlexConfig.service == 'deluge' )
    val = query.first( )
    if val is not None:
        session.delete( val )
        session.commit( )
    newval = PlexConfig(
        service = 'deluge',
        data = { 'url' : url,
                 'port' : port,
                 'username' : username,
                 'password' : password } )
    session.add( newval )
    session.commit( )
    return 'SUCCESS'

def deluge_get_torrents_info( client ):
    """
    Returns a :py:class:`dict` of status info for every torrent on the Deluge server through the `Deluge RPC client`_. The key in this :py:class:`dict` is the MD5 hash of the torrent, and its value is a status :py:class:`dict`.  For each torrent, here are the keys in the status :py:class:`dict`: ``active_time``, ``all_time_download``, ``distributed_copies``, ``download_location``, ``download_payload_rate``, ``eta``, ``file_priorities``, ``file_progress``, ``files``, ``is_finished``, ``is_seed``, ``last_seen_complete``, ``name``, ``next_announce``, ``num_peers``, ``num_pieces``, ``num_seeds``, ``peers``, ``piece_length``, ``progress``, ``ratio``, ``seed_rank``, ``seeding_time``, ``state``, ``time_added``, ``time_since_transfer``, ``total_done``, ``total_payload_download``, ``total_payload_upload``, ``total_peers``, ``total_seeds``, ``total_size``, ``total_uploaded``, ``tracker_host``, ``tracker_status``, ``upload_payload_rate``.

    :param client: the `Deluge RPC client`_.
    :returns: a :py:class:`dict` of status :py:class:`dict` for each torrent on the Deluge server.
    :rtype: dict
    """
    torrent_dict = client.call('core.get_torrents_status', {},
                        _status_keys )
    torrent_dict_final = dict()
    for torrentId_b in torrent_dict:
        torrentId = torrentId_b.decode('utf8').lower( )
        status = torrent_dict[ torrentId_b ]
        torrent_dict_final[ torrentId ] = {
            'name'                  : status[ b'name'  ].decode('utf8'),
            'state'                 : status[ b'state' ].decode('utf8'),
            'download_payload_rate' : status[ b'download_payload_rate' ],
            'upload_payload_rate'   : status[ b'upload_payload_rate' ],
            'eta'                   : status[ b'eta'],
            'num_seeds'             : status[ b'num_seeds' ],
            'total_seeds'           : status[ b'total_seeds' ],
            'num_peers'             : status[ b'num_peers' ],
            'total_peers'           : status[ b'total_peers' ],
            'distributed_copies'    : status[ b'distributed_copies' ],
            'total_done'            : status[ b'total_done' ],
            'total_size'            : status[ b'total_size' ],
            'ratio'                 : status[ b'ratio' ],
            'seeding_time'          : status[ b'seeding_time' ],
            'active_time'           : status[ b'active_time' ],
            'tracker_status'        : status[ b'tracker_status' ].decode( 'utf8' ),
            'is_finished'           : status[ b'is_finished' ],
            'progress'              : status[ b'progress' ],
        }
        if b'files' in status:
            torrent_dict_final[ torrentId ][ 'files' ] = list(
                map(lambda entry: {
                    'path' : entry[ b'path' ].decode( 'utf8' ),
                    'size' : entry[ b'size' ] }, status[ b'files' ] ) )
            
    #return dict(map(lambda entry: ( entry[0].decode('utf8').lower( ), entry[1] ), torrent_dict.items( ) ) )
    return torrent_dict_final

def deluge_add_torrent_file( client, torrent_file_name ):
    """
    Higher level method that takes a torrent file on disk and uploads to the Deluge server through the `Deluge RPC client`_.

    :param client: the `Deluge RPC client`_.
    :param str torrent_file_name: name of the candidate file.
    
    :returns: if successful, returns the MD5 hash of the uploaded torrent as a :py:class:`str`. If unsuccessful, returns ``None``.

    .. seealso:: :py:meth:`deluge_add_torrent_file_as_data <howdy.core.core_deluge.deluge_add_torrent_file_as_data>`.
    """
    if not core_torrents.torrent_is_torrent_file( torrent_file_name ): return None
    return deluge_add_torrent_file_as_data(
        client, torrent_file_name,
        open( torrent_file_name, 'rb' ).read( ) )

def deluge_add_torrent_file_as_data( client, torrent_file_name,
                                     torrent_file_data ):
    """
    Higher level method that takes a torrent file name, and its byte data representation, and uploads to the Deluge server through the `Deluge RPC client`_.

    :param client: the `Deluge RPC client`_.
    :param str torrent_file_name: name of the candidate file.
    :param bytes torrent_file_data: byte representation of the torrent file data.
    
    :returns: if successful, returns the MD5 hash of the uploaded torrent as a :py:class:`str`. If unsuccessful, returns ``None``.

    .. seealso:: :py:meth:`deluge_add_torrent_file <howdy.core.core_deluge.deluge_add_torrent_file>`.
    """
    baseName = os.path.basename( torrent_file_name )
    torrentId = client.call(
        'core.add_torrent_file', baseName,
        base64.b64encode( torrent_file_data ), {} )
    #
    ## check if the magnet link is in there already
    ## this is an obvious failure mode that I had not considered
    return torrentId
    
def deluge_add_magnet_file( client, magnet_uri ):
    """
    Uploads a `Magnet URI`_ to the Deluge server through the `Deluge RPC client`_.

    :param client: the `Deluge RPC client`_.
    :param str magnet_uri: the Magnet URI to upload.

    :returns: if successful, returns the MD5 hash of the uploaded torrent as a :py:class:`str`. If unsuccessful, returns ``None``.
    
    .. _`Magnet URI`: https://en.wikipedia.org/wiki/Magnet_URI_scheme
    """
    #
    ## check if the magnet link is in there already
    ## this is an obvious failure mode that I had not considered
    torrentIds = set( deluge_get_matching_torrents( client, ['*'] ) )
    cand_torr_id = parse_qs( magnet_uri )['magnet:?xt'][0].split(':')[-1].strip( ).lower( )
    if cand_torr_id in torrentIds: return cand_torr_id
    #
    ## otherwise NEW torrent
    torrentId = client.call(
        'core.add_torrent_magnet', magnet_uri, {} )
    if torrentId is not None: return torrentId.decode( 'utf8' ).lower( )
    #
    ## cannot find, exit
    return None

def deluge_add_url( client, torrent_url ):
    """
    Adds a torrent file via URL to the Deluge server through the `Deluge RPC client`_. If the URL is valid, then added. If the URL is invalid, then nothing happens.

    :param client: the `Deluge RPC client`_.
    :param str torrent_url: candidate URL.
    """
    if core_torrents.torrent_is_url( torrent_url ): client.call( 'core.add_torrent_url', torrent_url, {} )

def deluge_get_matching_torrents( client, torrent_id_strings ):
    """
    Given a :py:class:`list` of possibly truncated MD5 hashes of candidate torrents on the Deluge server, returns a :py:class:`list` of MD5 sums of torrents that match what was provided.

    :param client: the `Deluge RPC client`_.
    
    :param torrent_id_strings: the candidate :py:class:`list` of truncated MD5 hashes on the Deluge server. The ``[ '*' ]`` input means to look for all torrents on the Deluge server.

    :returns: a :py:class:`list` of candidate torrents, as their MD5 hash, tat match ``torrent_id_strings``. If ``torrent_id_strings == ['*']``, then return all the torrents (as MD5 hashes) on the Deluge server.
    :rtype: list
    
    """
    torrentIds = set( deluge_get_torrents_info( client ) )
    if torrent_id_strings == [ "*" ]: return torrentIds
    act_torrentIds = [ ]
    torrent_id_strings_lower = set(
        map(lambda tid_s: tid_s.strip( ).lower( ), torrent_id_strings ) )
    sizes = set(map(lambda tid_s: len( tid_s ), torrent_id_strings_lower ) )
    torrentId_dict_tot = dict(map(lambda siz: ( siz, dict(map(lambda torrentId: ( torrentId[:siz], torrentId ), torrentIds ) ) ),
                                  sizes ) )
    for tid_s in torrent_id_strings_lower:
        size = len( tid_s )
        if tid_s in torrentId_dict_tot[ size ]:
            act_torrentIds.append( torrentId_dict_tot[ size ][ tid_s ] )
    return set( act_torrentIds )

def deluge_remove_torrent( client, torrent_ids, remove_data = False ):
    """
    Remove torrents from the Deluge server through the `Deluge RPC client`_.

    :param client: the `Deluge RPC client`_.
    :param torrent_ids: :py:class:`list` of MD5 hashes on the Deluge server.
    :param bool remove_data: if ``True``, remove the torrent and delete all data associated with the torrent on disk. If ``False``, just remove the torrent.
    """
    act_torrentIds = deluge_get_matching_torrents( client, torrent_ids )
    for torrentId in act_torrentIds:
        client.call( 'core.remove_torrent', torrentId, remove_data )

def deluge_pause_torrent( client, torrent_ids ):
    """
    Pauses torrents on the Deluge server. Unlike other methods here, this does not use the `Deluge RPC client`_ lower-level RPC calls, but system command line calls to the deluge-console client. If the deluge-console executable cannot be found, then this does nothing. I do not know the `Deluge RPC client`_ is not working.

    :param client: the `Deluge RPC client`_. In this case, only the configuration info (username, password, URL, and port) are used.
    :param torrent_ids: :py:class:`list` of MD5 hashes on the Deluge server.
    """
    if _deluge_exec is None: return
    username = client.username
    password = client.password
    port = client.port
    url = client.host
    torrentId_strings = ' '.join(
        set(map(lambda torrentId: torrentId.lower( ), torrent_ids ) ) )
    retval = os.system(  '%s "connect %s:%d %s %s; pause %s; exit"' % (
        _deluge_exec, url, port, username, password, torrentId_strings ) )

def deluge_resume_torrent( client, torrent_ids ):
    """
    Resumes torrents on the Deluge server. Unlike other methods here, this does not use the `Deluge RPC client`_ lower-level RPC calls, but system command line calls to the deluge-console client. If the deluge-console executable cannot be found, then this does nothing. I do not know the `Deluge RPC client`_ is not working.

    :param client: the `Deluge RPC client`_. In this case, only the configuration info (username, password, URL, and port) are used.
    :param torrent_ids: :py:class:`list` of MD5 hashes on the Deluge server.
    """
    if _deluge_exec is None: return
    username = client.username
    password = client.password
    port = client.port
    url = client.host
    torrentId_strings = ' '.join(
        set(map(lambda torrentId: torrentId.lower( ), torrent_ids ) ) )
    retval = os.system(  '%s "connect %s:%d %s %s; resume %s; exit"' % (
        _deluge_exec, url, port, username, password, torrentId_strings ) )
