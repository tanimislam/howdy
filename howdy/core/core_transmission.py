import os, sys, numpy, logging, magic, base64, subprocess, titlecase
from urllib.parse import parse_qs
from pathlib import Path
from shutil import which
#
from howdy.core import session, PlexConfig, get_formatted_size
from howdy.core.core_deluge import format_size, format_time, format_progressbar, deluge_is_torrent_file


def push_transmission_credentials( url, username, password ):
    """
    Stores the Transmission server credentials into the SQLite3_ configuration database.

    :param str url: URL of the Transmission server.
    :param int port: port used to access the Transmission server.
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
        'port': YYYY,
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
    torrent_info_dict = dict()
    for torrent in all_torrents:
        tracker_status = ""
        if len( torrent.tracker_stats ) > 0: # take first tracker
            tracker_name = torrent.tracker_stats[0].announce
            announce     = torrent.tracker_stats[0].last_announce_result
            tracker_status = "%s: Announce %s" % ( tracker_name, announce )            
        torrent_hash = torrent.info_hash
        torrent_info_dict[ torrent_hash ] = {
            'name'           : torrent.name,
            'state'          : titlecase.titlecase( str( torrent.status ) ),
            'download rate'  : torrent.rate_download,
            'upload rate'    : torrent.rate_upload,
            'eta'            : torrent.eta, # warning may be None if not started
            'num seeds'      : sum(map(lambda tstat: max( 0, tstat.seeder_count ), torrent.tracker_stats ) ),
            'total seeds'    : sum(map(lambda tstat: max( 0, tstat.seeder_count ), torrent.tracker_stats ) ) + torrent.webseeds_sending_to_us,
            'num peers'      : torrent.peers_connected,
            'total peers'    : sum( torrent.peers_from.values( ) ),
            'availability'   : torrent.available,
            'total done'     : sum(map(lambda fstat: fstat.bytesCompleted, torrent.file_stats ) ),
            'total size'     : torrent.size_when_done,
            'ratio'          : torrent.ratio,
            'seed time'      : torrent.seconds_seeding,
            'active time'    : torrent.seconds_downloading,
            'tracker status' : tracker_status,
            'progress'       : torrent.progress,
        }
    return torrent_info_dict

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
        client, torrent_file_name, torrent_file_data ):
    """
    Higher level method that takes a torrent file name, and its byte data representation, and uploads to the Transmission server through the `Transmission RPC client`_.

    :param client: the `Transmission RPC client`_.
    :param str torrent_file_name: name of the candidate file.
    :param byte torrent_file_data: byte representation of the torrent file data.
    
    :returns: if successful, returns the MD5 hash of the uploaded torrent as a :py:class:`str`. If unsuccessful, returns ``None``.

    .. seealso:: :py:meth:`transmission_add_torrent_file <howdy.core.core_transmission.transmission_add_torrent_file>`.
    """
    baseName = os.path.basename( torrent_file_name )
    torrentId = client.call(
        'core.add_torrent_file', baseName,
        base64.b64encode( torrent_file_data ), {} )
    #
    ## check if the magnet link is in there already
    ## this is an obvious failure mode that I had not considered
    return torrentId
