import os, sys, numpy, logging, magic, subprocess, titlecase
from urllib.parse import parse_qs, urlparse
from pathlib import Path
from shutil import which
#
from howdy.core import session, PlexConfig
from howdy.core.core_deluge import (
    deluge_is_torrent_file, deluge_is_url, deluge_format_info )

def push_transmission_credentials( url, username, password ):
    """
    Stores the Transmission server credentials into the SQLite3_ configuration database.

    :param str url: URL of the Transmission server.
    :param str username: server account username.
    :param str password: server account password.
    
    :returns: if successful (due to correct Transmission server settings), returns ``'SUCCESS'``. If unsuccessful, returns ``'ERROR, INVALID SETTINGS FOR TRANSMISSION CLIENT.'``
    :rtype: str

    .. seealso::
    
       * :py:meth:`create_transmission_client <howdy.core.core_transmission.create_transmission_client>`.
       * :py:meth:`get_transmission_client <howdy.core.core_transmission.get_transmission_client>`.
       * :py:meth:`get_transmission_credentials <howdy.core.core_transmission.get_transmission_credentials>`.
    """
    
    #
    ## first check that the configurations are valid
    try:
        client = create_transmission_client( url, username, password )
    except:
        error_message = 'ERROR, INVALID SETTINGS FOR DELUGE CLIENT.'
        logging.debug( error_message )
        return error_message
    #
    ## now put into the database
    query = session.query( PlexConfig ).filter(
        PlexConfig.service == 'transmission' )
    val = query.first( )
    if val is not None:
        session.delete( val )
        session.commit( )
    newval = PlexConfig(
        service = 'transmission',
        data = { 'url' : url,
                 'username' : username,
                 'password' : password } )
    session.add( newval )
    session.commit( )
    return 'SUCCESS'

def get_transmission_credentials( ):
    """
    Gets the Deluge server credentials from the SQLite3_ configuration database. The data looks like this.

    .. code-block:: python
    
      { 'url': XXXX,
        'username': AAAA,
        'password': BBBB }
   
    :returns: dictionary of Transmission server settings.
    :rtype: dict

    .. seealso::
    
       * :py:meth:`create_transmission_client <howdy.core.core_transmission.create_transmission_client>`.
       * :py:meth:`get_transmission_client <howdy.core.core_transmission.get_transmission_client>`.
       * :py:meth:`push_transmission_credentials <howdy.core.core_transmission.push_transmission_credentials>`.
    """
    val = session.query( PlexConfig ).filter(
        PlexConfig.service == 'transmission' ).first( )
    if val is None: return None
    return val.data

def create_transmission_client( url, username, password ):
    """
    Creates a minimal Transmission torrent client to the Transmission seedbox server.

    :param str url: URL of the Transmission server.
    :param str username: server account username.
    :param str password: server account password.

    :returns: previously a lightweight `Transmission RPC client`_, although now it is a :py:class:`TransmissionRPCClient <howdy.core.transmission_client_tanim.client.TransmissionRPCClient>`.

    .. seealso::
    
       * :py:meth:`get_transmission_client <howdy.core.core_transmission.get_transmission_client>`.
       * :py:meth:`get_transmission_credentials <howdy.core.core_transmission.get_transmission_credentials>`.
       * :py:meth:`push_transmission_credentials <howdy.core.core_transmission.push_transmission_credentials>`.

    .. _`Transmission RPC client`: https://github.com/JohnDoee/transmission-client
    """
    from transmission_rpc import Client
    client = Client( protocol='https', host = url, port = 443,
                     path = '/%s/transmission/rpc' % username,
                     username = username, password = password )
    return client

def get_transmission_client( ):
    """
    Using a minimal Transmission torrent client from server credentials stored in the SQLite3_ configuration database.

    :returns: a :py:class:`tuple`. If successful, the first element is a lightweight `Transmission RPC client`_ and the second element is the string ``'SUCCESS'``. If unsuccessful, the first element is ``None`` and the second element is an error string.
    :rtype: tuple

    .. seealso::
    
       * :py:meth:`create_transmission_client <howdy.core.core_transmission.create_transmission_client>`.
       * :py:meth:`get_transmission_credentials <howdy.core.core_transmission.get_transmission_credentials>`.
       * :py:meth:`push_transmission_credentials <howdy.core.core_transmission.push_transmission_credentials>`.
    """
    query = session.query( PlexConfig ).filter(
        PlexConfig.service == 'transmission' )
    val = query.first( )
    if val is None:
        error_message = "ERROR, TRANSMISSION CLIENT SETTINGS NOT DEFINED."
        logging.debug( error_message )
        return None, error_message
    data = val.data
    url = data['url']
    username = data['username']
    password = data['password']
    #
    ## now check that we have the correct info
    try:
        client = create_transmission_client( url, username, password )
        return client, 'SUCCESS'
    except Exception as e: # cannot connect to these settings
        error_message = 'ERROR, INVALID SETTINGS FOR TRANSMISSION CLIENT.'
        logging.debug( str( e ) )
        return None, error_message

def transmission_get_torrents_info( client ):
    """
    Returns a :py:class:`dict` of status info for every torrent on the Transmission server through the Transmission RPC client.

    The key in this :py:class:`dict` is the MD5 hash of the torrent, and its value is a status :py:class:`dict`.

    For each torrent, here are the keys in the status :py:class:`dict`: ``name``, ``state``, ``download rate``, ``upload rate``, ``eta`` (which may be ``None`` if download has *not* started), ``num seeds``, ``total seeds``, ``num peers``, ``total peers``, ``availability``, ``total done``, ``total size``, ``ratio``, ``seed time``, ``active time``, ``tracker status``, and ``progress``.

    :param client: the Transmission RPC client.
    :returns: a :py:class:`dict` of status :py:class:`dict` for each torrent on the Transmission server.
    :rtype: dict
    """
    all_torrents = client.get_torrents( )
    torrent_dict_final = dict()
    for torrent in all_torrents:
        tracker_status = ""
        is_finished = False
        eta = -1
        if len( torrent.tracker_stats ) > 0: # take first tracker
            tracker_name = torrent.tracker_stats[0].announce
            announce     = torrent.tracker_stats[0].last_announce_result
            tracker_status = "%s: Announce %s" % ( tracker_name, announce )
            if torrent.left_until_done == 0: is_finished = True
            if torrent.eta is not None: eta = torrent.eta.seconds
        torrentId = torrent.info_hash
        torrent_dict_final[ torrentId ] = {
            'name'                   : torrent.name,
            'state'                  : titlecase.titlecase( str( torrent.status ) ),
            'download_payload_rate'  : torrent.rate_download,
            'upload_payload_rate'    : torrent.rate_upload,
            'eta'                    : eta,
            'num_seeds'              : sum(map(lambda tstat: max( 0, tstat.seeder_count ), torrent.tracker_stats ) ),
            'total_seeds'            : sum(map(lambda tstat: max( 0, tstat.seeder_count ), torrent.tracker_stats ) ) + torrent.webseeds_sending_to_us,
            'num_peers'              : torrent.peers_connected,
            'total_peers'            : sum( torrent.peers_from.values( ) ),
            'distributed_copies'     : torrent.available,
            'total_done'             : sum(map(lambda fstat: fstat.bytesCompleted, torrent.file_stats ) ),
            'total_size'             : torrent.size_when_done,
            'ratio'                  : torrent.ratio,
            'seeding_time'           : torrent.seconds_seeding,
            'active_time'            : torrent.seconds_downloading,
            'tracker_status'         : tracker_status,
            'is_finished'            : is_finished,
            'progress'               : torrent.progress,
        }
        if len( torrent.get_files( ) ) > 0:
            torrent_dict_final[ torrentId ][ 'files' ] = list(
                map(lambda file_entry: {
                    'path' : file_entry.name,
                    'size' : file_entry.size }, torrent.get_files( ) ) )
        
    return torrent_dict_final

def transmission_add_torrent_file( client, torrent_file_name ):
    """
    Higher level method that takes a torrent file on disk and uploads to the Transmission server through the `Transmission RPC client`_.

    :param client: the `Transmission RPC client`_.
    :param str torrent_file_name: name of the candidate file.
    
    :returns: if successful, returns the MD5 hash of the uploaded torrent as a :py:class:`str`. If unsuccessful, returns ``None``.

    .. seealso:: :py:meth:`transmission_add_torrent_file_as_data <howdy.core.core_transmission.transmission_add_torrent_file_as_data>`.
    """
    if not deluge_is_torrent_file( torrent_file_name ): return None
    tor = client.add_torrent( Path( torrent_file_name ) )
    return tor.info_hash

def transmission_add_torrent_file_as_data(
        client, torrent_file_data ):
    """
    Higher level method that takes a torrent file name, and its byte data representation, and uploads to the Transmission server through the `Transmission RPC client`_.

    :param client: the `Transmission RPC client`_.
    :param byte torrent_file_data: byte representation of the torrent file data.
    
    :returns: if successful, returns the MD5 hash of the uploaded torrent as a :py:class:`str`. If unsuccessful, returns ``None``.

    .. seealso:: :py:meth:`transmission_add_torrent_file <howdy.core.core_transmission.transmission_add_torrent_file>`.
    """
    tor = client.add_torrent( torrent_file_data )
    #
    ## check if the magnet link is in there already
    ## this is an obvious failure mode that I had not considered
    return tor.info_hash

def transmission_add_magnet_file( client, magnet_uri ):
    """
    Uploads a `Magnet URI`_ to the Transmission server through the `Transmission RPC client`_.

    :param client: the `Transmission RPC client`_.
    :param str magnet_uri: the Magnet URI to upload.

    :returns: if successful, returns the MD5 hash of the uploaded torrent as a :py:class:`str`. If unsuccessful, returns ``None``.
    
    .. _`Magnet URI`: https://en.wikipedia.org/wiki/Magnet_URI_scheme
    """
    #
    ## check if the magnet link is in there already
    ## this is an obvious failure mode that I had not considered
    torrentIds = set( transmission_get_torrents_info( client ) )
    cand_torr_id = parse_qs( magnet_uri )['magnet:?xt'][0].split(':')[-1].strip( ).lower( )
    if cand_torr_id in torrentIds: return cand_torr_id
    #
    ## otherwise NEW torrent
    torr = client.add_torrent( magnet_uri )
    return torr.info_hash

def transmission_add_url( client, torrent_url ):
    """
    Adds a torrent file via URL to the Transmission server through the `Transmission RPC client`_. If the URL is valid, then added. If the URL is invalid, then nothing happens.

    :param client: the `Transmission RPC client`_.
    :param str torrent_url: candidate URL.
    """
    if deluge_is_url( torrent_url ): client.add_torrent( torrent_url )

def transmission_get_matching_torrents( client, torrent_id_strings ):
    """
    Given a :py:class:`list` of possibly truncated MD5 hashes of candidate torrents on the Transmission server, returns a :py:class:`list` of MD5 sums of torrents that match what was provided.

    :param client: the `Transmission RPC client`_.
    
    :param torrent_id_strings: the candidate :py:class:`list` of truncated MD5 hashes on the Transmission server. The ``[ '*' ]`` input means to look for all torrents on the Transmission server.

    :returns: a :py:class:`list` of candidate torrents, as their MD5 hash, tat match ``torrent_id_strings``. If ``torrent_id_strings == ['*']``, then return all the torrents (as MD5 hashes) on the Transmission server.
    :rtype: list
    
    """
    torrentIds = set( transmission_get_torrents_info( client ) )
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

def transmission_remove_torrent( client, torrent_ids, remove_data = False ):
    """
    Remove torrents from the Transmission server through the `Transmission RPC client`_.

    :param client: the `Transmission RPC client`_.
    :param torrent_ids: :py:class:`list` of MD5 hashes on the Transmission server.
    :param bool remove_data: if ``True``, remove the torrent and delete all data associated with the torrent on disk. If ``False``, just remove the torrent.
    """
    act_torrentIds = list( transmission_get_matching_torrents( client, torrent_ids ) )
    client.remove_torrent( act_torrentIds, delete_data = remove_data )

def transmission_pause_torrent( client, torrent_ids ):
    """
    Pauses torrents on the Transmission server.

    :param client: the `Transmission RPC client`_.
    :param torrent_ids: :py:class:`list` of MD5 hashes on the Transmission server.
    """
    act_torrentIds = list( transmission_get_matching_torrents( client, torrent_ids ) )
    client.stop_torrent( act_torrentIds )

def transmission_resume_torrent( client, torrent_ids ):
    """
    Resumes torrents on the Transmission server.

    :param client: the `Transmission RPC client`_. In this case, only the configuration info (username, password, URL, and port) are used.
    :param torrent_ids: :py:class:`list` of MD5 hashes on the Transmission server.
    """
    act_torrentIds = list( transmission_get_matching_torrents( client, torrent_ids ) )
    client.start_torrent( act_torrentIds )
