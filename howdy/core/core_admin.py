import requests, os, sys, numpy, requests
from plexapi.server import PlexServer
from tqdm import tqdm
#
from howdy.core import core, return_error_raw

def get_tautulli_apikey( username, password, endpoint ):
    """
    Gets the tautulli API key with provided Tautulli_ username and password.
    
    :param str username: the Tautulli_ username.
    :param str password: the Tautulli_ password.
    :param str endpoint: the Tautulli_ server endpoint.
    :returns: the Tautulli_ API key.
    :rtype: str

    .. _Tautulli: https://tautulli.com
    """
    full_url = os.path.join( endpoint, 'api', 'v2' )
    #
    ## follow this reference: https://github.com/Tautulli/Tautulli/wiki/Tautulli-API-Reference#get_apikey
    response = requests.get( full_url,
                            params = {
                                'username' : username,
                                'password' : password,
                                'cmd' : 'get_apikey' } )
    if response.status_code != 200:
        raise ValueError("Error, could not find the Tautulli API key.")

    return response.json( )[ 'response' ][ 'data' ]

def get_tautulli_activity( endpoint, apikey ):
    """
    Gets the activity on the Plex_ server (using Tautulli_).
    
    :param str endpoint: the Tautulli_ server endpoint.
    :param str apikey: the Tautulli_ API Key.
    """
    full_url = os.path.join( endpoint, 'api', 'v2' )
    #
    ## follow this reference: https://github.com/Tautulli/Tautulli/wiki/Tautulli-API-Reference#get_activity
    response = requests.get( full_url,
                            params = {
                                'apikey' : apikey,
                                'cmd' : 'get_activity' })
    if response.status_code != 200:
        raise ValueError("Error, could not get the activity from the Plex server.")
    #
    ## now the data
    data = response.json( )[ 'response' ][ 'data' ]
    if data['stream_count'] == 0: return [ ]
    #
    ## now if there are streams
    def get_relevant_info( session_info ):
        session_dat = {
            'title' : session_info['title'], 'type' : session_info['media_type'].upper( ),
            'username' : session_info['username'], 'progress' : int( session_info['progress_percent'] ) }
        if 'friendly_name' in session_info:
            session_dat['friendly name'] = session_info[ 'friendly_name' ]
        return session_dat
    return list(map(get_relevant_info, data['sessions'] ) )

def plex_check_for_update( token, fullURL = 'http://localhost:32400' ):
    """
    Determines whether there are any new Plex_ server releases.
    
    :param str token: the Plex_ server access token.
    :param str fullURL: the Plex_ server address.
    :returns: a :py:class:`tuple` of :py:class:`Release <plexapi.server.Release>` and "SUCCESS" if successful. Otherwise returns the :py:class:`tuple` returned by :py:meth:`return_error_raw <howdy.core.return_error_raw>`.
    :rtype: tuple

    .. _Plex: https://plex.tv
    """
    try:
        plex = PlexServer( fullURL, token )
        release = plex.checkForUpdate( )
        return release, "SUCCESS"
    except Exception as e:
        return return_error_raw( str( e ) )

def plex_download_release( release, destination_dir = os.getcwd( ), do_progress = False ):
    """
    Downloads the Plex_ update into a specific directory, with optional progress bar.
    
    :param release: the :py:class:`Release <plexapi.server.Release>` containing the Plex_ update information.
    :type release: :py:class:`Release <plexapi.server.Release>`
    :pararm str destination_dir: the destination directory into which to download.
    :param bool do_progress: whether to show the progress bar or not. Default is ``False``.
    :returns: If unsuccessful an error message. If successful, the full path of the downloaded file.
    :rtype: str
    """
    downloadURL = release.downloadURL
    response = requests.get( downloadURL, stream = True )
    if not response.ok:
        return "ERROR, %s IS NOT ACCESSIBLE" % downloadURL
    #
    ## destination of the PLEX download
    r2 = requests.head( downloadURL )
    if not r2.ok:
        return "ERROR, %s IS NOT ACCESSIBLE WITH REQUESTS.HEAD" % downloadURL
    destination = os.path.join( destination_dir, os.path.basename( r2.headers['Location'] ) )
    #
    ## following instructions from https://stackoverflow.com/a/37573701/3362358
    total_size_in_bytes = int(response.headers.get('content-length', 0))
    block_size = 1 << 16
    if not do_progress:
        with open( destination, 'wb' ) as openfile:
            for chunk in response.iter_content( block_size ):
                openfile.write( chunk )
            return destination
    #
    ## have a progress bar
    with tqdm( total = total_size_in_bytes, unit='iB', unit_scale=True) as progress_bar, open( destination, 'wb' ) as openfile:
        for chunk in response.iter_content( block_size ):
            progress_bar.update(len(chunk))
            openfile.write( chunk )
        if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
            return "ERROR, something went wrong"
        return destination
