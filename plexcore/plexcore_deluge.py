import os, sys, numpy, logging, magic, base64, subprocess
from urllib.parse import parse_qs
from distutils.spawn import find_executable
from . import baseConfDir, session, PlexConfig, get_formatted_size

_deluge_exec = find_executable( 'deluge' )

#
## copied from deluge.common
def format_size( fsize_b ):
    """
    Formats the bytes value into a string with KiB, MiB or GiB units. This code has been copied from :py:meth:`deluge's format_size <deluge.ui.console.utils.format_utils.format_size>`.

    :param int fsize_b: the filesize in bytes.
    :returns: formatted string in KiB, MiB or GiB units.
    :rtype: str

    **Usage**
    
    >>> format_size( 112245 )
    '109.6 KiB'

    """
    fsize_kb = fsize_b / 1024.0
    if fsize_kb < 1024:
        return "%.1f KiB" % fsize_kb
    fsize_mb = fsize_kb / 1024.0
    if fsize_mb < 1024:
        return "%.1f MiB" % fsize_mb
    fsize_gb = fsize_mb / 1024.0
    return "%.1f GiB" % fsize_gb

# copied from deluge.ui.console.commands.info
def format_time( seconds ):
    """
    Formats the time, in seconds, to a nice format. Unfortunately, the :py:class:`datetime <datetime.datetime>` class is too unwieldy for this type of formatting. This code is copied from :py:meth:`deluge's format_time <deluge.ui.console.utils.format_utils.format_time>`.

    :param int seconds: number of seconds.
    :returns: formatted string in the form of ``1 days 03:05:04``.
    :rtype: str

    **Usage**
    
    >>> format_time( 97262 )
    '1 days 03:01:02'

    """
    minutes = seconds // 60
    seconds = seconds - minutes * 60
    hours = minutes // 60
    minutes = minutes - hours * 60
    days = hours // 24
    hours = hours - days * 24
    return "%d days %02d:%02d:%02d" % (days, hours, minutes, seconds)

# copied from deluge.ui.console.commands.info
def format_progressbar(progress, width):
    """
    Returns a string of a progress bar. This code has been copied from :py:meth:`deluge's format_progressbar <deluge.ui.console.utils.format_utils.format_progress>`.

    :param float progress: a value between 0-100.

    :returns: str, a progress bar based on width.
    :rtype: str

    **Usage**
    
    >>> format_progressbar( 87.6, 100 )
    '[######################################################################################~~~~~~~~~~~~]'
    
    """
    w = width - 2 # we use a [] for the beginning and end
    s = "["
    p = int(round((progress/100) * w))
    s += "#" * p
    s += "~" * (w - p)
    s += "]"
    return s

# copied from deluge.common
def format_speed(bps):
    """
    Formats a string to display a transfer speed utilizing :py:func:`fsize`. This is code has been copied from :py:meth:`deluge's format_speed <deluge.ui.console.utils.format_utils.format_speed>`.

    :param int bps: bytes per second.
    :returns: a formatted string representing transfer speed
    :rtype: str

    **Usage**

    >>> format_speed( 43134 )
    '42.1 KiB/s'

    """
    fspeed_kb = bps / 1024.0
    if fspeed_kb < 1024:
        return "%.1f KiB/s" % fspeed_kb
    fspeed_mb = fspeed_kb / 1024.0
    if fspeed_mb < 1024:
        return "%.1f MiB/s" % fspeed_mb
    fspeed_gb = fspeed_mb / 1024.0
    return "%.1f GiB/s" % fspeed_gb

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

    :returns: a lightweight `Deluge RPC client`_.

    .. seealso:: 
      * :py:meth:`get_deluge_client <plexcore.plexcore_deluge.get_deluge_client>`
      * :py:meth:`get_deluge_credentials <plexcore.plexcore_deluge.get_deluge_credentials>`
      * :py:meth:`push_deluge_credentials <plexcore.plexcore_deluge.push_deluge_credentials>`

    .. _`Deluge RPC client`: https://github.com/JohnDoee/deluge-client
    """
    from deluge_client import DelugeRPCClient
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
      * :py:meth:`create_deluge_client <plexcore.plexcore_deluge.create_deluge_client>`
      * :py:meth:`get_deluge_credentials <plexcore.plexcore_deluge.get_deluge_credentials>`
      * :py:meth:`push_deluge_credentials <plexcore.plexcore_deluge.push_deluge_credentials>`
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
    except: # cannot connect to these settings
        error_message = 'ERROR, INVALID SETTINGS FOR DELUGE CLIENT.'        
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
      * :py:meth:`create_deluge_client <plexcore.plexcore_deluge.create_deluge_client>`
      * :py:meth:`get_deluge_client <plexcore.plexcore_deluge.get_deluge_client>`
      * :py:meth:`push_deluge_credentials <plexcore.plexcore_deluge.push_deluge_credentials>`
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
      * :py:meth:`create_deluge_client <plexcore.plexcore_deluge.create_deluge_client>`
      * :py:meth:`get_deluge_client <plexcore.plexcore_deluge.get_deluge_client>`
      * :py:meth:`get_deluge_credentials <plexcore.plexcore_deluge.get_deluge_credentials>`
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
    return client.call('core.get_torrents_status', {},
                       _status_keys )

def deluge_is_torrent_file( torrent_file_name ):
    """
    Check if a file is a torrent file.

    :param str torrent_file_name: name of the candidate file.

    :returns: ``True`` if it is a torrent file, ``False`` otherwise.
    :rtype: bool
    """
    if not os.path.isfile( torrent_file_name ): return False
    if not os.path.basename( torrent_file_name ).endswith( '.torrent' ): return False
    if magic.from_file( torrent_file_name ) != 'BitTorrent file': return False
    return True

def deluge_add_torrent_file( client, torrent_file_name ):
    """
    Higher level method that takes a torrent file on disk and uploads to the Deluge server through the `Deluge RPC client`_.

    :param client: the `Deluge RPC client`_.
    :param str torrent_file_name: name of the candidate file.
    
    :returns: if successful, returns the MD5 hash of the uploaded torrent as a :py:class:`str`. If unsuccessful, returns ``None``.

    .. seealso:: :py:meth:`deluge_add_torrent_file_as_data <plexcore.plexcore_deluge.deluge_add_torrent_file_as_data>`
    """
    if not deluge_is_torrent_file( torrent_file_name ): return None
    return deluge_add_torrent_file_as_data(
        client, torrent_file_name,
        open( torrent_file_name, 'rb' ).read( ) )

def deluge_add_torrent_file_as_data( client, torrent_file_name,
                                     torrent_file_data ):
    """
    Higher level method that takes a torrent file name, and its byte data representation, and uploads to the Deluge server through the `Deluge RPC client`_.

    :param client: the `Deluge RPC client`_.
    :param str torrent_file_name: name of the candidate file.
    :param byte torrent_file_data: byte representation of the torrent file data.
    
    :returns: if successful, returns the MD5 hash of the uploaded torrent as a :py:class:`str`. If unsuccessful, returns ``None``.

    .. seealso:: :py:meth:`deluge_add_torrent_file <plexcore.plexcore_deluge.deluge_add_torrent_file>`
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
    torrentId = client.call(
        'core.add_torrent_magnet', magnet_uri, {} )
    #
    ## check if the magnet link is in there already
    ## this is an obvious failure mode that I had not considered
    if torrentId is not None: return torrentId

    torrentIds = set(map(lambda torId: torId.lower( ),
                         deluge_get_matching_torrents( client, ['*'] ) ) )
    cand_torr_id = parse_qs( magnet_uri )['magnet:?xt'][0].split(':')[-1].strip( )
    if cand_torr_id in torrentIds: return cand_torr_id
    return None

def deluge_is_url( torrent_url ):
    """
    Checks whether an URL is valid, following `this prescription <https://stackoverflow.com/questions/7160737/python-how-to-validate-a-url-in-python-malformed-or-not>`_.

    :param str torrent_url: candidate URL.
    
    :returns: ``True`` if it is a valid URL, ``False`` otherwise.
    :rtype: bool
    """
    from urllib.parse import urlparse
    try:
        result = urlparse( torrent_url )
        return all([result.scheme, result.netloc, result.path])
    except Exception as e: return False

def deluge_add_url( client, torrent_url ):
    """
    Adds a torrent file via URL to the Deluge server through the `Deluge RPC client`_. If the URL is valid, then added. If the URL is invalid, then nothing happens.

    :param client: the `Deluge RPC client`_.
    :param str torrent_url: candidate URL.
    """
    if deluge_is_url( torrent_url ): client.call( 'core.add_torrent_url', torrent_url, {} )

def deluge_get_matching_torrents( client, torrent_id_strings ):
    """
    Given a :py:class:`list` of possibly truncated MD5 hashes of candidate torrents on the Deluge server, returns a :py:class:`list` of MD5 sums of torrents that match what was provided.

    :param client: the `Deluge RPC client`_.
    
    :param torrent_id_strings: the candidate :py:class:`list` of truncated MD5 hashes on the Deluge server. The ``[ '*' ]`` input means to look for all torrents on the Deluge server.

    :returns: a :py:class:`list` of candidate torrents, as their MD5 hash, tat match ``torrent_id_strings``. If ``torrent_id_strings == ['*']``, then return all the torrents (as MD5 hashes) on the Deluge server.
    :rtype: list
    
    """
    torrentIds = list( deluge_get_torrents_info( client ).keys( ) )
    if torrent_id_strings == [ "*" ]: return torrentIds
    act_torrentIds = [ ]
    torrentIdDicts = dict(map(lambda torrentId: (
        torrentId.decode('utf-8').lower( ), torrentId ), torrentIds ) )
    torrent_id_strings_lower = set(map(lambda tid_s:
                                       tid_s.strip( ).lower( ), torrent_id_strings ) )
    for tid_s in torrent_id_strings_lower:
        size = len( tid_s )
        for torrentId_s in torrentIdDicts:
            if tid_s == torrentId_s[:size]:
                act_torrentIds.append( torrentIdDicts[ torrentId_s ] )
                break
    return act_torrentIds

def deluge_remove_torrent( client, torrent_ids, remove_data = False ):
    """
    Remove torrents from the Deluge server through the `Deluge RPC client`_.

    :param client: the `Deluge RPC client`_.
    :param torrent_ids: :py:class:`list` of MD5 hashes on the Deluge server.
    :param bool remove_data: if ``True``, remove the torrent and delete all data associated with the torrent on disk. If ``False``, just remove the torrent.
    """
    for torrentId in torrent_ids:
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
        list(map(lambda torrentId: torrentId.decode('utf-8').lower( ), torrent_ids ) ) )
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
        list(map(lambda torrentId: torrentId.decode('utf-8').lower( ), torrent_ids ) ) )
    retval = os.system(  '%s "connect %s:%d %s %s; resume %s; exit"' % (
        _deluge_exec, url, port, username, password, torrentId_strings ) )
    
def deluge_format_info( status, torrent_id ):
    """
    Returns a nicely formatted representation of the status of a torrent.

    **Usage**
    
    >>> print( '%s\' % deluge_format_info( status, 'ed53ba61555cab24946ebf2f346752805601a7fb' ) )
    
    Name: ubuntu-19.10-beta-desktop-amd64.iso
    ID: ed53ba61555cab24946ebf2f346752805601a7fb
    State: Downloading
    Down Speed: 73.4 MiB/s Up Speed: 0.0 KiB/s ETA: 0 days 00:00:23
    Seeds: 24 (67) Peers: 1 (4) Availability: 24.22
    Size: 474.5 MiB/2.1 GiB Ratio: 0.000
    Seed time: 0 days 00:00:00 Active: 0 days 00:00:05
    Tracker status: ubuntu.com: Announce OK
    Progress: 21.64% [##################################~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~]
    
    :param dict status: the status :py:class:`dict` for a given torrent, generated from :py:meth:`deluge_get_torrents_info <plexcore.plexcore_deluge.deluge_get_torrents_info>`.
    :param str torrent_id: the MD5 hash of that torrent.
    
    :returns: a nicely formatted representation of that torrent on the Deluge server.
    :rtype: str

    .. seealso:: :py:meth:`deluge_get_torrents_info <plexcore.plexcore_deluge.deluge_get_torrents_info>`.
    """
    cols, _ = os.get_terminal_size( )
    mystr_split = [
        "Name: %s" % status[ b'name' ].decode('utf-8'),
        "ID: %s" % torrent_id.decode('utf-8').lower( ),
        "State: %s" % status[ b'state' ].decode('utf-8') ]
    if status[ b'state' ] in ( b'Seeding', b'Downloading' ):
        line_split = [ ]
        if status[b'state'] != b'Seeding':
            line_split.append(
                "Down Speed: %s" % format_speed(
                    status[ b'download_payload_rate' ] ) )
        line_split.append(
            "Up Speed: %s" % format_speed(
                status[ b'upload_payload_rate' ] ) )
        if status[ b'eta' ]:
            line_split.append(
                "ETA: %s" % format_time( status[ b'eta' ] ) )
        mystr_split.append( ' '.join( line_split ) )
    #
    if status[ b'state' ] in ( b'Seeding', b'Downloading', b'Queued' ):
        line_split = [ 
            "Seeds: %s (%s)" % (
                status[ b'num_seeds' ],
                status[ b'total_seeds' ] ),
            "Peers: %s (%s)" % (
                status[ b'num_peers' ],
                status[ b'total_peers' ] ),
            "Availability: %0.2f" % status[ b'distributed_copies' ] ]
        mystr_split.append( ' '.join( line_split ) )
    #
    total_done = format_size( status[ b'total_done' ] )
    total_size = format_size( status[ b'total_size' ] )
    mystr_split.append(
        "Size: %s/%s Ratio: %0.3f" % ( total_done, total_size,
                                       status[ b'ratio' ] ) )
    #
    mystr_split.append(
        "Seed time: %s Active: %s" % ( format_time( status[ b'seeding_time' ] ),
                                       format_time( status[ b'active_time' ] ) ) )
    #
    mystr_split.append(
        "Tracker status: %s" % status[ b'tracker_status' ].decode('utf-8' ) )
    #
    if not status[ b'is_finished' ]:
        pbar = format_progressbar( status[ b'progress' ],
                                    cols - (13 + len('%0.2f%%' % status[ b'progress'] ) ) )
        mystr_split.append( "Progress: %0.2f%% %s" % ( status[ b'progress' ], pbar ) )
    return '\n'.join( mystr_split )
