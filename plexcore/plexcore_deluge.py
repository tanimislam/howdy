import os, sys, numpy, logging, magic, base64, subprocess
from urllib.parse import parse_qs
from configparser import RawConfigParser
from . import baseConfDir, session, PlexConfig, get_formatted_size

#
## copied from deluge.common
def format_size( fsize_b ):
    """
    Formats the bytes value into a string with KiB, MiB or GiB units

    :param fsize_b: the filesize in bytes
    :type fsize_b: int
    :returns: formatted string in KiB, MiB or GiB units
    :rtype: string

    **Usage**

    >>> fsize(112245)
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
def _format_time( seconds ):
    minutes = seconds // 60
    seconds = seconds - minutes * 60
    hours = minutes // 60
    minutes = minutes - hours * 60
    days = hours // 24
    hours = hours - days * 24
    return "%d days %02d:%02d:%02d" % (days, hours, minutes, seconds)

# copied from deluge.ui.console.commands.info
def _format_progressbar(progress, width):
    """
    Returns a string of a progress bar.

    :param progress: float, a value between 0-100

    :returns: str, a progress bar based on width
    
    """
    w = width - 2 # we use a [] for the beginning and end
    s = "["
    p = int(round((progress/100) * w))
    s += "#" * p
    s += "~" * (w - p)
    s += "]"
    return s

# copied from deluge.common
def _format_speed(bps):
    """
    Formats a string to display a transfer speed utilizing :func:`fsize`

    :param bps: bytes per second
    :type bps: int
    :returns: a formatted string representing transfer speed
    :rtype: string

    **Usage**

    >>> fspeed(43134)
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
    from deluge_client import DelugeRPCClient
    client = DelugeRPCClient( url, port, username, password )
    client.connect( )
    assert( client.connected ) # make sure we can connect
    return client
    
def get_deluge_client( ):
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
    val = session.query( PlexConfig ).filter(
        PlexConfig.service == 'deluge' ).first( )
    if val is None: return None
    return val.data

def push_deluge_credentials( url, port, username, password ):
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
    return client.call('core.get_torrents_status', {},
                       _status_keys )

def deluge_is_torrent_file( torrent_file_name ):
    if not os.path.isfile( torrent_file_name ): return False
    if not os.path.basename( torrent_file_name ).endswith( '.torrent' ): return False
    if magic.from_file( torrent_file_name ) != 'BitTorrent file': return False
    return True

def deluge_add_torrent_file( client, torrent_file_name ):
    if not deluge_is_torrent_file( torrent_file_name ): return None
    return deluge_add_torrent_file_as_data(
        client, torrent_file_name,
        open( torrent_file_name, 'rb' ).read( ) )

def deluge_add_torrent_file_as_data( client, torrent_file_name,
                                     torrent_file_data ):
    baseName = os.path.basename( torrent_file_name )
    torrentId = client.call(
        'core.add_torrent_file', baseName,
        base64.b64encode( torrent_file_data ), {} )
    #
    ## check if the magnet link is in there already
    ## this is an obvious failure mode that I had not considered
    return torrentId
    

def deluge_add_magnet_file( client, magnet_uri ):
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

#
## From https://stackoverflow.com/questions/7160737/python-how-to-validate-a-url-in-python-malformed-or-not
def deluge_is_url( torrent_url ):
    from urllib.parse import urlparse
    try:
        result = urlparse( torrent_url )
        return all([result.scheme, result.netloc, result.path])
    except Exception as e: return False

def deluge_add_url( client, torrent_url ):
    if deluge_is_url( torrent_url ): client.call( 'core.add_torrent_url', torrent_url, {} )

def deluge_get_matching_torrents( client, torrent_id_strings ):
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
    for torrentId in torrent_ids:
        client.call( 'core.remove_torrent', torrentId, remove_data )

#
## this isn't working with DelugeRPCClient, don't know why...
def deluge_pause_torrent( client, torrent_ids ):
    username = client.username
    password = client.password
    port = client.port
    url = client.host
    torrentId_strings = ' '.join(
        list(map(lambda torrentId: torrentId.decode('utf-8').lower( ), torrent_ids ) ) )
    retval = os.system(  '/usr/bin/deluge-console "connect %s:%d %s %s; pause %s; exit"' % (
        url, port, username, password, torrentId_strings ) )

#
## this isn't working with DelugeRPCClient, don't know why...
def deluge_resume_torrent( client, torrent_ids ):
    username = client.username
    password = client.password
    port = client.port
    url = client.host
    torrentId_strings = ' '.join(
        list(map(lambda torrentId: torrentId.decode('utf-8').lower( ), torrent_ids ) ) )
    retval = os.system(  '/usr/bin/deluge-console "connect %s:%d %s %s; resume %s; exit"' % (
        url, port, username, password, torrentId_strings ) )
    
def deluge_format_info( status, torrent_id ):
    cols, _ = os.get_terminal_size( )
    mystr_split = [
        "Name: %s" % status[ b'name' ].decode('utf-8'),
        "ID: %s" % torrent_id.decode('utf-8').lower( ),
        "State: %s" % status[ b'state' ].decode('utf-8') ]
    if status[ b'state' ] in ( b'Seeding', b'Downloading' ):
        line_split = [ ]
        if status[b'state'] != b'Seeding':
            line_split.append(
                "Down Speed: %s" % _format_speed(
                    status[ b'download_payload_rate' ] ) )
        line_split.append(
            "Up Speed: %s" % _format_speed(
                status[ b'upload_payload_rate' ] ) )
        if status[ b'eta' ]:
            line_split.append(
                "ETA: %s" % _format_time( status[ b'eta' ] ) )
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
        "Seed time: %s Active: %s" % ( _format_time( status[ b'seeding_time' ] ),
                                       _format_time( status[ b'active_time' ] ) ) )
    #
    mystr_split.append(
        "Tracker status: %s" % status[ b'tracker_status' ].decode('utf-8' ) )
    #
    if not status[ b'is_finished' ]:
        pbar = _format_progressbar( status[ b'progress' ],
                                    cols - (13 + len('%0.2f%%' % status[ b'progress'] ) ) )
        mystr_split.append( "Progress: %0.2f%% %s" % ( status[ b'progress' ], pbar ) )
    return '\n'.join( mystr_split )
