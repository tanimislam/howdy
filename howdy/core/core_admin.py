import requests, os, sys, numpy
from plexapi.server import PlexServer
#
from howdy.core import core

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
