"""
pygn.py

pygn (pronounced "pigeon") is a simple Python client for the Gracenote Music 
Web API, which can retrieve Artist, Album and Track metadata with the most 
common options.

You will need a Gracenote Client ID to use this module. Please contact 
developers@gracenote.com to get one.
"""

from __future__ import print_function
import xml.etree.ElementTree, json, requests, logging

try:
    import urllib.request as urllib_request #for python 3
    import urllib.parse   as urllib_parse

except ImportError:
    import urllib2 as urllib_request # for python 2
    import urllib as urllib_parse # for python 2

# Set DEBUG to True if you want this module to print out the query and response XML
DEBUG = True # change back to FALSE

class gnmetadata(dict):
	"""
	This class is a dictionary containing metadata fields that are available for the queried item.
	"""
	def __init__(self):
		# Basic Metadata
		self['track_artist_name'] = ''
		self['album_artist_name'] = ''
		self['album_title'] = ''
		self['album_year'] = ''
		self['track_title'] = ''
		self['track_number'] = ''

		# Descriptors
		self['genre'] = {}
		self['artist_origin'] = {}
		self['artist_era'] = {}
		self['artist_type'] = {}
		self['mood'] = {}
		self['tempo'] = {}

		# Related Content
		self['album_art_url'] = ''
		self['artist_image_url'] = ''
		self['artist_bio_url'] = ''
		self['review_url'] = ''

		# Gracenote IDs
		self['album_gnid'] = ''
		self['track_gnid'] = ''

		#Radio ID
		self['radio_id'] = ''

		#  External IDs: Special content rights in license required
		self['xid'] =''

def register(clientID, verify = True):
    """
    This function registers an application as a user of the Gracenote service.
    
    It takes as a parameter a clientID string in the form of "NNNNNNN-NNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN" and returns a userID in a similar format.
    
    As the quota of number of users (installed applications or devices) is typically much lower than the number of queries, best practices are for a given installed application to call this only once, store the UserID in persistent storage (e.g. filesystem), and then use these IDs for all subsequent calls to the service.
    
    :param str clientID: the Gracenote_ client ID.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :returns: the Gracenote_ user ID if valid client ID.
    :rtype str

    .. _Gracenote: https://developer.gracenote.com/web-api    
    """
    
    # Create XML request
    query = _gnquery()
    query.addQuery('REGISTER')
    query.addQueryClient(clientID)
    
    queryXML = query.toString()
    
    # POST query
    response = requests.post( _gnurl( clientID ), data = queryXML, verify = verify )
    responseXML = response.content
    #response = urllib_request.urlopen(_gnurl(clientID), queryXML)
    #responseXML = response.read()
    
    # Parse response
    responseTree = xml.etree.ElementTree.fromstring(responseXML)
    
    responseElem = responseTree.find('RESPONSE')
    if responseElem.attrib['STATUS'] == 'OK':
        userElem = responseElem.find('USER')
        userID = userElem.text
        
    return userID

def createRadio(clientID, userID, artist = '', track = '', mood = '', era = '',
                genre = '', popularity = None, similarity = None, count = 10, verify = True):
    """
    Queries a set of radio stations on Gracenote_ to create, and returns a :py:class:`list` of :py:class:`gnmetadata <plexmusic.pygn.gnmetadata>` dictionaries corresponding to those radio stations that have been created. This was created by the GitHub_ user Fabian_ to cover the `Gracenote Rhythm`_ API.

    :param str clientID: the Gracenote_ client ID.
    :param str userID: the Gracenote_ user ID.
    :param str artist: the artist name.
    :param str track: the song name.
    :param str mood: the song mood.
    :param str era: the song era.
    :param str genre: the genre.
    :param str popularity: optional argument. The song popularity.
    :param str similarity: optional argument. The song similariy.
    :param int count: optional argument, the maximum number of matches to return, must be :math:`\ge 1`. Default is ``10``.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.

    :returns: a :py:class:`list` of :py:class:`gnmetadata <plexmusic.pygn.gnmetadata>` radio stations that match the above query.
    :rtype: list

    :raise ValueError: if all of ``artist``, ``track``, ``mood``, ``era``, and ``genre`` are empty.
    :raise ValueError: if ``count`` :math:`\le 0`.

    .. _GitHub: https://github.com
    .. _`Gracenote Rhythm`: https://developer.gracenote.com/rhythm-api
    .. _Fabian: https://github.com/fabian1811
    """
    # if clientID=='' or userID=='':
    #     print('ClientID and UserID are required')
    #     return None

    # if artist=='' and track=='' and mood=='' and era=='' and genre=='':
    #     print('Must query with at least one field (artist, track, genre, mood, era)')
    #     return None
    assert( len(list(map(lambda val: val.strip( ) != '', ( artist, track, mood, era, genre ) ) ) ) != 0), "error, must query with at least one field (artist, track, genre, mood, era)"
    assert( count >= 1 )

    #Create XML request
    query = _gnquery()
	
    # Build the user header 
    query.addAuth(clientID, userID)
	
    query.addQuery('RADIO_CREATE')
	
    if artist!='' or track!='':
        query.addTextSeed(artist, track)

    if mood!='' or era!='' or genre!='':
        query.addAttributeSeed(mood, era, genre)
			
    query.addQueryOption('SELECT_EXTENDED', 'COVER,REVIEW,ARTIST_BIOGRAPHY,ARTIST_IMAGE,ARTIST_OET,MOOD,TEMPO,LINK')
    query.addQueryOption('SELECT_DETAIL', 'GENRE:3LEVEL,MOOD:2LEVEL,TEMPO:3LEVEL,ARTIST_ORIGIN:4LEVEL,ARTIST_ERA:2LEVEL,ARTIST_TYPE:2LEVEL')	

    if popularity is not None:
        query.addQueryOption('FOCUS_POPULARITY', popularity)
    if similarity is not None:
        query.addQueryOption('FOCUS_SIMILARITY', similarity)

    query.addQueryOption('RETURN_COUNT', '%d' % count )

    queryXML = query.toString()
    
    logging.debug('QUERY:')
    logging.debug(queryXML)

    # POST query
    response = requests.post( _gnurl( clientID ), data = queryXML, verify = verify )
    responseXML = response.content
    #response = urllib_request.urlopen(_gnurl(clientID), queryXML)
    #`responseXML = response.read()

    myPlaylist = list(map(lambda x: _parseRadioMetadata( responseXML, x ), range( 1, count ) ) )
    return myPlaylist

#*****************************************************************************************************************************************		
# Added by Fabian in order to cover the Rhythm API
# Returns a list of gnmetadata dictionaries 


def radioEvent(clientID, userID, radioID, GNID, event ='TRACK_PLAYED',
               count = 10, popularity = None, similarity = None, verify = True):
    """
    Queries a set of radio stations on Gracenote_ to find based on certain queries, and returns a :py:class:`list` of :py:class:`gnmetadata <plexmusic.pygn.gnmetadata>` dictionaries corresponding to those radio stations that have been found. This was created by the GitHub_ user Fabian_ to cover the `Gracenote Rhythm`_ API.

    :param str clientID: the Gracenote_ client ID.
    :param str userID: the Gracenote_ user ID.
    :param str GNID: the Gracenote_ music ID of the music data.
    :param str event: optional argument, search on what happened to the song whose Gracenote_ ID is ``GNID``. Default is ``TRACK_PLAYED``.
    :param str genre: the genre.
    :param int count: optional argument, the maximum number of matches to return, must be :math:`\ge 1`. Default is ``10``.
    :param str popularity: optional argument. The song popularity.
    :param str similarity: optional argument. The song similariy.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.

    :returns: a :py:class:`list` of :py:class:`gnmetadata <plexmusic.pygn.gnmetadata>` radio stations that match the above query.
    :rtype: list
    
    :raise ValueError: if ``count`` :math:`\le 0`.
    """
    # if clientID=='' or userID=='':
    #     print('ClientID and UserID are required')
    #     return None

    # if radioID=='' or GNID=='':
    #     print('Event query must contain the radioID and GNID')
    #     return None
    assert( count >= 1 )
    
    
    #Create XML request
    query = _gnquery()
    
    # Build the user header 
    query.addAuth(clientID, userID)
    
    query.addQuery('RADIO_EVENT')
    
    query.addRadioID(radioID)
    
    query.addQueryEVENT(event, GNID)
    
    query.addQueryOption('RETURN_COUNT', '%d' % count)
    
    if popularity is not None:
        query.addQueryOption('FOCUS_POPULARITY', popularity)
    if similarity is not None:
        query.addQueryOption('FOCUS_SIMILARITY', similarity)

    query.addQueryOption('SELECT_EXTENDED', 'COVER,REVIEW,ARTIST_BIOGRAPHY,ARTIST_IMAGE,ARTIST_OET,MOOD,TEMPO,LINK')
    query.addQueryOption('SELECT_DETAIL', 'GENRE:3LEVEL,MOOD:2LEVEL,TEMPO:3LEVEL,ARTIST_ORIGIN:4LEVEL,ARTIST_ERA:2LEVEL,ARTIST_TYPE:2LEVEL')
    
    query.addQueryOption('RETURN_SETTINGS', 'YES')
    
    queryXML = query.toString( )
    logging.debug('QUERY:')
    logging.debug(queryXML)
        	
    # POST query
    response = requests.post( _gnurl( clientID ), data = queryXML, verify = verify )
    responseXML = response.content
    #response = urllib_request.urlopen(_gnurl(clientID), queryXML)
    #responseXML = response.read()
    
    myPlaylist = list(map(lambda x: _parseRadioMetadata( responseXML, x ), range( 1, count ) ) )
    return myPlaylist

#***********************************************************************************************************************
def search(clientID, userID, artist='', album='', track='', toc='', verify = True ):
    """
    Queries the Gracenote service for a track, album, artist, or TOC entry. TOC is a string of offsets in the format, ``150 20512 30837 50912 64107 78357 ...``.

    :param str clientID: the Gracenote_ API client ID.
    :param str userID: the Gracenote_ API user ID.
    :param str artist: the artist name.
    :param str album: the song album.
    :param str track: the song name.
    :param str toc: the album's string of offsets in the following format, ``150 20512 30837 50912 64107 78357 ...``.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: a :py:class:`gnmetadata <plexmusic.pygn.gnmetadata>` of album metadata corresponding to this query.
    :rtype: :py:class:`gnmetadata <plexmusic.pygn.gnmetadata>`

    :raise ValueError: if all of ``artist``, ``album``, ``track``, ``toc``, are empty.
    :raise ValueError: if ``count`` :math:`\le 0`.
    """
    assert( count >= 1 )
    assert( len(list(map(lambda val: val.strip( ) != '', ( artist, album, track, toc ) ) ) ) != 0 ), 'Must query with at least one field (artist, album, track, toc)'
	
    # Create XML request
    query = _gnquery()
    
    query.addAuth(clientID, userID)
	
    if (toc != ''):
        query.addQuery('ALBUM_TOC')
        query.addQueryMode('SINGLE_BEST_COVER')
        query.addQueryTOC(toc)
    else:
        query.addQuery('ALBUM_SEARCH')
        query.addQueryMode('SINGLE_BEST_COVER')
        query.addQueryTextField('ARTIST', artist)
        query.addQueryTextField('ALBUM_TITLE', album)
        query.addQueryTextField('TRACK_TITLE', track)
        query.addQueryOption('SELECT_EXTENDED', 'COVER,REVIEW,ARTIST_BIOGRAPHY,ARTIST_IMAGE,ARTIST_OET,MOOD,TEMPO')
        query.addQueryOption('SELECT_DETAIL', 'GENRE:3LEVEL,MOOD:2LEVEL,TEMPO:3LEVEL,ARTIST_ORIGIN:4LEVEL,ARTIST_ERA:2LEVEL,ARTIST_TYPE:2LEVEL')
	
    queryXML = query.toString()
    
    logging.debug('------------')
    logging.debug('QUERY XML')
    logging.debug('------------')
    logging.debug(queryXML)
	
    # POST query
    #response = urllib_request.urlopen(_gnurl(clientID), queryXML)
    #responseXML = response.read()
    response = requests.post( _gnurl( clientID ), data = queryXML, verify = verify )
    responseXML = response.content
  
    logging.debug('------------')
    logging.debug('RESPONSE XML')
    logging.debug('------------')
    logging.debug(responseXML)

    # Create GNTrackMetadata object
    metadata = gnmetadata()
    
    # Parse response
    responseTree = xml.etree.ElementTree.fromstring(responseXML)
    responseElem = responseTree.find('RESPONSE')
    if responseElem.attrib['STATUS'] == 'OK':
        # Find Album element
        albumElem = responseElem.find('ALBUM')

        # Parse album metadata
        metadata['album_gnid'] = _getElemText(albumElem, 'GN_ID')
        metadata['album_artist_name'] = _getElemText(albumElem, 'ARTIST')
        metadata['album_title'] = _getElemText(albumElem, 'TITLE')
        metadata['album_year'] = _getElemText(albumElem, 'DATE')
        metadata['album_art_url'] = _getElemText(albumElem, 'URL', 'TYPE', 'COVERART')
        metadata['genre'] = _getMultiElemText(albumElem, 'GENRE', 'ORD', 'ID')
        metadata['artist_image_url'] = _getElemText(albumElem, 'URL', 'TYPE', 'ARTIST_IMAGE')
        metadata['artist_bio_url'] = _getElemText(albumElem, 'URL', 'TYPE', 'ARTIST_BIOGRAPHY')
        metadata['review_url'] = _getElemText(albumElem, 'URL', 'TYPE', 'REVIEW')
        
    # Look for OET
    artistOriginElem = albumElem.find('ARTIST_ORIGIN')
    if artistOriginElem is not None:
        metadata['artist_origin'] = _getMultiElemText(albumElem, 'ARTIST_ORIGIN', 'ORD', 'ID')
        metadata['artist_era'] = _getMultiElemText(albumElem, 'ARTIST_ERA', 'ORD', 'ID')
        metadata['artist_type'] = _getMultiElemText(albumElem, 'ARTIST_TYPE', 'ORD', 'ID')
    else:
        # Try to get OET again by fetching album by GNID
        metadata['artist_origin'], metadata['artist_era'], metadata['artist_type'] = _getOET(clientID, userID, metadata['album_gnid'])
			
    # Parse track metadata
    matchedTrackElem = albumElem.find('MATCHED_TRACK_NUM')
    if matchedTrackElem is not None:
        trackElem = albumElem.find('TRACK')
        
        metadata['track_number'] = _getElemText(trackElem, 'TRACK_NUM')
        metadata['track_gnid'] = _getElemText(trackElem, 'GN_ID')
        metadata['track_title'] = _getElemText(trackElem, 'TITLE')
        metadata['track_artist_name'] = _getElemText(trackElem, 'ARTIST')
        
        metadata['mood'] = _getMultiElemText(trackElem, 'MOOD', 'ORD', 'ID')
        metadata['tempo'] = _getMultiElemText(trackElem, 'TEMPO', 'ORD', 'ID')
				
        
        # If track-level GOET exists, overwrite metadata from album			
        if trackElem.find('GENRE') is not None:
            metadata['genre']	= _getMultiElemText(trackElem, 'GENRE', 'ORD', 'ID')
        if trackElem.find('ARTIST_ORIGIN') is not None:
            metadata['artist_origin'] = _getMultiElemText(trackElem, 'ARTIST_ORIGIN', 'ORD', 'ID')
        if trackElem.find('ARTIST_ERA') is not None:
            metadata['artist_era'] = _getMultiElemText(trackElem, 'ARTIST_ERA', 'ORD', 'ID')
        if trackElem.find('ARTIST_TYPE') is not None:
            metadata['artist_type'] = _getMultiElemText(trackElem, 'ARTIST_TYPE', 'ORD', 'ID')

    # Parse tracklist
    def create_trackdata( trackElem ):
        trackdata = { }
        
        trackdata['track_number'] = _getElemText(trackElem, 'TRACK_NUM')
        trackdata['track_gnid'] = _getElemText(trackElem, 'GN_ID')
        trackdata['track_title'] = _getElemText(trackElem, 'TITLE')
        trackdata['track_artist_name'] = _getElemText(trackElem, 'ARTIST')
        
        trackdata['mood'] = _getMultiElemText(trackElem, 'MOOD', 'ORD', 'ID')
        trackdata['tempo'] = _getMultiElemText(trackElem, 'TEMPO', 'ORD', 'ID')
        
        # If track-level GOET exists, overwrite metadata from album			
        if trackElem.find('GENRE') is not None:
            trackdata['genre']	 = _getMultiElemText(trackElem, 'GENRE', 'ORD', 'ID')
        if trackElem.find('ARTIST_ORIGIN') is not None:
            trackdata['artist_origin'] = _getMultiElemText(trackElem, 'ARTIST_ORIGIN', 'ORD', 'ID')
        if trackElem.find('ARTIST_ERA') is not None:
            trackdata['artist_era'] = _getMultiElemText(trackElem, 'ARTIST_ERA', 'ORD', 'ID')
        if trackElem.find('ARTIST_TYPE') is not None:
            trackdata['artist_type'] = _getMultiElemText(trackElem, 'ARTIST_TYPE', 'ORD', 'ID')

        return trackdata
    metadata['tracks'] = list(map(create_trackdata, albumElem.iter('TRACK')))
    return metadata

def _parseRadioMetadata(responseXML, number):
	# Create GNTrackMetadata object
	metadata = gnmetadata()
	
	# Parse response
	responseTree = xml.etree.ElementTree.fromstring(responseXML)
	responseElem = responseTree.find('RESPONSE')
	if responseElem.attrib['STATUS'] == 'OK':
		#find the radio ID
		RadioElem = responseElem.find('RADIO')
		metadata['radio_id'] = _getElemText(RadioElem, 'ID')
		
		# Find Album the right album element
		albums = responseElem.findall('ALBUM')
		for albumElem in albums:
			if albumElem.attrib["ORD"] == str(number):
				# Parse album metadata
				metadata['album_gnid'] = _getElemText(albumElem, 'GN_ID')
				metadata['album_artist_name'] = _getElemText(albumElem, 'ARTIST')
				metadata['album_title'] = _getElemText(albumElem, 'TITLE')
				metadata['album_year'] = _getElemText(albumElem, 'DATE')
				metadata['album_art_url'] = _getElemText(albumElem, 'URL', 'TYPE', 'COVERART')
				metadata['genre'] = _getMultiElemText(albumElem, 'GENRE', 'ORD', 'ID')
				metadata['artist_image_url'] = _getElemText(albumElem, 'URL', 'TYPE', 'ARTIST_IMAGE')
				metadata['artist_bio_url'] = _getElemText(albumElem, 'URL', 'TYPE', 'ARTIST_BIOGRAPHY')
				metadata['review_url'] = _getElemText(albumElem, 'URL', 'TYPE', 'REVIEW')
	
				# Look for OET
				artistOriginElem = albumElem.find('ARTIST_ORIGIN')
				if artistOriginElem is not None:
					metadata['artist_origin'] = _getMultiElemText(albumElem, 'ARTIST_ORIGIN', 'ORD', 'ID')
					metadata['artist_era'] = _getMultiElemText(albumElem, 'ARTIST_ERA', 'ORD', 'ID')
					metadata['artist_type'] = _getMultiElemText(albumElem, 'ARTIST_TYPE', 'ORD', 'ID')
				else:
					# Try to get OET again by fetching album by GNID
					metadata['artist_origin'], metadata['artist_era'], metadata['artist_type'] = _getOET(clientID, userID, metadata['album_gnid'])
		
				# Parse track metadata
				trackElem = albumElem.find('TRACK')
		
				metadata['track_number'] = _getElemText(trackElem, 'TRACK_NUM')
				metadata['track_gnid'] = _getElemText(trackElem, 'GN_ID')
				metadata['track_title'] = _getElemText(trackElem, 'TITLE')
				metadata['track_artist_name'] = _getElemText(trackElem, 'ARTIST')

				metadata['mood'] = _getMultiElemText(trackElem, 'MOOD', 'ORD', 'ID')
				metadata['tempo'] = _getMultiElemText(trackElem, 'TEMPO', 'ORD', 'ID')
		
				# If track-level GOET exists, overwrite metadata from album			
				if trackElem.find('GENRE') is not None:
					metadata['genre']	= _getMultiElemText(trackElem, 'GENRE', 'ORD', 'ID')
				if trackElem.find('ARTIST_ORIGIN') is not None:
					metadata['artist_origin'] = _getMultiElemText(trackElem, 'ARTIST_ORIGIN', 'ORD', 'ID')
				if trackElem.find('ARTIST_ERA') is not None:
					metadata['artist_era'] = _getMultiElemText(trackElem, 'ARTIST_ERA', 'ORD', 'ID')
				if trackElem.find('ARTIST_TYPE') is not None:
					metadata['artist_type'] = _getMultiElemText(trackElem, 'ARTIST_TYPE', 'ORD', 'ID')
				if trackElem.find('XID') is not None: 
					metadata

				return metadata

def get_discography(clientID, userID, artist, rangeStart = 1, rangeEnd = 10,
                    verify = True ):
    """
    Queries the Gracenote_ API service for all albums containing an artist.

    :param str clientID: the Gracenote_ client ID.
    :param str userID: the Gracenote_ user ID.
    :param str artist: the artist name.
    :param int rangeStart: optional argument. This is the order for the *HIGHEST* cardinal rank of an album that matches a given album name associated with the artist (lower number is better). Must be :math:`\ge 1`, and default is ``1``.
    :param int rangeEnd: optional argument. This is the order for the *LOWEST* cardinal rank of an album that matches a given album name associated with the artist (lower number is better). Must be :math:`\ge 1`, :math:`ge` ``rangeStart``, and default is ``10``.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.

    :returns: a :py:class:`list` of all albums found for ``artist``. Each album is stored as :py:class:`gnmetadata <plexmusic.pygn.gnmetadata>`.
    :rtype: :py:class:`gnmetadata <plexmusic.pygn.gnmetadata>`
    """

    if clientID=='' or userID=='':
        print('ClientID and UserID are required')
        return None

    if artist=='':
        print('Must specify artist')
        return None

    # Create XML request
    query = _gnquery()
    
    query.addAuth(clientID, userID)
    query.addQuery('ALBUM_SEARCH')
    query.addQueryTextField('ARTIST', artist)
    query.addQueryOption('SELECT_EXTENDED', 'COVER,REVIEW,ARTIST_BIOGRAPHY,ARTIST_IMAGE,ARTIST_OET,MOOD,TEMPO')
    query.addQueryOption('SELECT_DETAIL', 'GENRE:3LEVEL,MOOD:2LEVEL,TEMPO:3LEVEL,ARTIST_ORIGIN:4LEVEL,ARTIST_ERA:2LEVEL,ARTIST_TYPE:2LEVEL')
    query.addQueryRange(rangeStart,rangeEnd)
    
    queryXML = query.toString()

    logging.debug('------------')
    logging.debug('QUERY XML')
    logging.debug('------------')
    logging.debug(queryXML)
        
    # POST query
    response = reqests.post( _gnurl( clientID ), data = queryXML, verify = verify )
    responeXML = response.content
    #response = urllib_request.urlopen(_gnurl(clientID), queryXML)
    #responseXML = response.read()
    
    logging.debug('------------')
    logging.debug('RESPONSE XML')
    logging.debug('------------')
    logging.debug(responseXML)

    # Create result array
    discography = []

    # Parse response
    responseTree = xml.etree.ElementTree.fromstring(responseXML)
    responseElem = responseTree.find('RESPONSE')
    if responseElem.attrib['STATUS'] == 'OK':
        # Find Album element
        albumElems = responseElem.findall('ALBUM')

    for albumElem in albumElems:
        
        metadata = gnmetadata()
        
        # Parse album metadata
        metadata['album_gnid'] = _getElemText(albumElem, 'GN_ID')
        metadata['album_artist_name'] = _getElemText(albumElem, 'ARTIST')
        
        metadata['album_title'] = _getElemText(albumElem, 'TITLE')
        metadata['album_year'] = _getElemText(albumElem, 'DATE')
        metadata['album_art_url'] = _getElemText(albumElem, 'URL', 'TYPE', 'COVERART')
        metadata['genre'] = _getMultiElemText(albumElem, 'GENRE', 'ORD', 'ID')
        metadata['artist_image_url'] = _getElemText(albumElem, 'URL', 'TYPE', 'ARTIST_IMAGE')
        metadata['artist_bio_url'] = _getElemText(albumElem, 'URL', 'TYPE', 'ARTIST_BIOGRAPHY')
        metadata['review_url'] = _getElemText(albumElem, 'URL', 'TYPE', 'REVIEW')

        # Look for OET
        artistOriginElem = albumElem.find('ARTIST_ORIGIN')
        if artistOriginElem is not None:
            metadata['artist_origin'] = _getMultiElemText(albumElem, 'ARTIST_ORIGIN', 'ORD', 'ID')
            metadata['artist_era'] = _getMultiElemText(albumElem, 'ARTIST_ERA', 'ORD', 'ID')
            metadata['artist_type'] = _getMultiElemText(albumElem, 'ARTIST_TYPE', 'ORD', 'ID')
        
        # Parse tracklist
        metadata['tracks'] = []
        for trackElem in albumElem.iter('TRACK'):
            trackdata = {}
        
            trackdata['track_number'] = _getElemText(trackElem, 'TRACK_NUM')
            trackdata['track_gnid'] = _getElemText(trackElem, 'GN_ID')
            trackdata['track_title'] = _getElemText(trackElem, 'TITLE')
            trackdata['track_artist_name'] = _getElemText(trackElem, 'ARTIST')
            
            trackdata['mood'] = _getMultiElemText(trackElem, 'MOOD', 'ORD', 'ID')
            trackdata['tempo'] = _getMultiElemText(trackElem, 'TEMPO', 'ORD', 'ID')
            
            # If track-level GOET exists, overwrite metadata from album			
            if trackElem.find('GENRE') is not None:
                trackdata['genre']	 = _getMultiElemText(trackElem, 'GENRE', 'ORD', 'ID')
            if trackElem.find('ARTIST_ORIGIN') is not None:
                trackdata['artist_origin'] = _getMultiElemText(trackElem, 'ARTIST_ORIGIN', 'ORD', 'ID')
            if trackElem.find('ARTIST_ERA') is not None:
                trackdata['artist_era'] = _getMultiElemText(trackElem, 'ARTIST_ERA', 'ORD', 'ID')
            if trackElem.find('ARTIST_TYPE') is not None:
                trackdata['artist_type'] = _getMultiElemText(trackElem, 'ARTIST_TYPE', 'ORD', 'ID')
            metadata['tracks'].append(trackdata)
        discography.append(metadata)
    return discography

def fetch(clientID, userID, GNID, verify = True ):
    """
    Fetches a track or album by their Gracenote_ API ID.

    :param str clientID: the Gracenote_ API client ID.
    :param str userID: the Gracenote_ API user ID.
    :param str GNID: the Gracenote_ music ID of the music data.

    :returns: a :py:class:`gnmetadata <plexmusic.pygn.gnmetadata>` containing the metadata for the album.
    :rtype: :py:class:`gnmetadata <plexmusic.pygn.gnmetadata>`
    """
    
    if clientID=='' or userID=='':
        print('ClientID and UserID are required')
        return None
    
    if GNID=='':
        print('GNID is required')
        return None
	
    # Create XML request
    query = _gnquery()
    
    query.addAuth(clientID, userID)
    query.addQuery('ALBUM_FETCH')
    query.addQueryGNID(GNID)
    query.addQueryOption('SELECT_EXTENDED', 'COVER,REVIEW,ARTIST_BIOGRAPHY,ARTIST_IMAGE,ARTIST_OET,MOOD,TEMPO')
    query.addQueryOption('SELECT_DETAIL', 'GENRE:3LEVEL,MOOD:2LEVEL,TEMPO:3LEVEL,ARTIST_ORIGIN:4LEVEL,ARTIST_ERA:2LEVEL,ARTIST_TYPE:2LEVEL')
    
    queryXML = query.toString()
    
    logging.debug('------------')
    logging.debug('QUERY XML')
    logging.debug('------------')
    logging.debug(queryXML)
    
    # POST query
    response = requests.post( _gnurl( clientID ), data = queryXML, verify = verify )
    responseXML = response.content
    #response = urllib_request.urlopen(_gnurl(clientID), queryXML)
    #responseXML = response.read()
    
    logging.debug('------------')
    logging.debug('RESPONSE XML')
    logging.debug('------------')
    logging.debug(responseXML)
    
    # Create GNTrackMetadata object
    metadata = gnmetadata()
    
    # Parse response
    responseTree = xml.etree.ElementTree.fromstring(responseXML)
    responseElem = responseTree.find('RESPONSE')
    if responseElem.attrib['STATUS'] == 'OK':
        
        # Find Album element
        albumElem = responseElem.find('ALBUM')
        
        # Parse album metadata
        metadata['album_gnid'] = _getElemText(albumElem, 'GN_ID')
        metadata['album_artist_name'] = _getElemText(albumElem, 'ARTIST')
        metadata['album_title'] = _getElemText(albumElem, 'TITLE')
        metadata['album_year'] = _getElemText(albumElem, 'DATE')
        metadata['album_art_url'] = _getElemText(albumElem, 'URL', 'TYPE', 'COVERART')
        metadata['genre'] = _getMultiElemText(albumElem, 'GENRE', 'ORD', 'ID')
        metadata['artist_image_url'] = _getElemText(albumElem, 'URL', 'TYPE', 'ARTIST_IMAGE')
        metadata['artist_bio_url'] = _getElemText(albumElem, 'URL', 'TYPE', 'ARTIST_BIOGRAPHY')
        metadata['review_url'] = _getElemText(albumElem, 'URL', 'TYPE', 'REVIEW')
        
    # Look for OET
    artistOriginElem = albumElem.find('ARTIST_ORIGIN')
    if artistOriginElem is not None:
        metadata['artist_origin'] = _getMultiElemText(albumElem, 'ARTIST_ORIGIN', 'ORD', 'ID')
        metadata['artist_era'] = _getMultiElemText(albumElem, 'ARTIST_ERA', 'ORD', 'ID')
        metadata['artist_type'] = _getMultiElemText(albumElem, 'ARTIST_TYPE', 'ORD', 'ID')
    else:
        # Try to get OET again by fetching album by GNID
        metadata['artist_origin'], metadata['artist_era'], metadata['artist_type'] = _getOET(clientID, userID, metadata['album_gnid'])
        
    # Parse track metadata
    matchedTrackElem = albumElem.find('MATCHED_TRACK_NUM')
    if matchedTrackElem is not None:
        trackElem = albumElem.find('TRACK')
        
        metadata['track_number'] = _getElemText(trackElem, 'TRACK_NUM')
        metadata['track_gnid'] = _getElemText(trackElem, 'GN_ID')
        metadata['track_title'] = _getElemText(trackElem, 'TITLE')
        metadata['track_artist_name'] = _getElemText(trackElem, 'ARTIST')
        
        metadata['mood'] = _getMultiElemText(trackElem, 'MOOD', 'ORD', 'ID')
        metadata['tempo'] = _getMultiElemText(trackElem, 'TEMPO', 'ORD', 'ID')
        
        # If track-level GOET exists, overwrite metadata from album			
        if trackElem.find('GENRE') is not None:
            metadata['genre']	= _getMultiElemText(trackElem, 'GENRE', 'ORD', 'ID')
        if trackElem.find('ARTIST_ORIGIN') is not None:
            metadata['artist_origin'] = _getMultiElemText(trackElem, 'ARTIST_ORIGIN', 'ORD', 'ID')
        if trackElem.find('ARTIST_ERA') is not None:
            metadata['artist_era'] = _getMultiElemText(trackElem, 'ARTIST_ERA', 'ORD', 'ID')
        if trackElem.find('ARTIST_TYPE') is not None:
            metadata['artist_type'] = _getMultiElemText(trackElem, 'ARTIST_TYPE', 'ORD', 'ID')

    # Parse tracklist
    metadata['tracks'] = [ ]
    for trackElem in albumElem.iter('TRACK'):
        trackdata = {}
        
        trackdata['track_number'] = _getElemText(trackElem, 'TRACK_NUM')
        trackdata['track_gnid'] = _getElemText(trackElem, 'GN_ID')
        trackdata['track_title'] = _getElemText(trackElem, 'TITLE')
        trackdata['track_artist_name'] = _getElemText(trackElem, 'ARTIST')
        
        trackdata['mood'] = _getMultiElemText(trackElem, 'MOOD', 'ORD', 'ID')
        trackdata['tempo'] = _getMultiElemText(trackElem, 'TEMPO', 'ORD', 'ID')
        
        # If track-level GOET exists, overwrite metadata from album			
        if trackElem.find('GENRE') is not None:
            trackdata['genre']	 = _getMultiElemText(trackElem, 'GENRE', 'ORD', 'ID')
        if trackElem.find('ARTIST_ORIGIN') is not None:
            trackdata['artist_origin'] = _getMultiElemText(trackElem, 'ARTIST_ORIGIN', 'ORD', 'ID')
        if trackElem.find('ARTIST_ERA') is not None:
            trackdata['artist_era'] = _getMultiElemText(trackElem, 'ARTIST_ERA', 'ORD', 'ID')
        if trackElem.find('ARTIST_TYPE') is not None:
            trackdata['artist_type'] = _getMultiElemText(trackElem, 'ARTIST_TYPE', 'ORD', 'ID')
        metadata['tracks'].append(trackdata)
        
    return metadata

def _gnurl( clientID ):
    """
    Helper function to form URL to Gracenote_ API service.
    
    :param str clientID: the Gracenote_ client ID.
    :returns: the lower level URL to the Gracenote_ API.
    :rtype: str
    """
    clientIDprefix = clientID.split('-')[0]
    return 'https://c%s.web.cddbp.net/webapi/xml/1.0/' % clientIDprefix
	
def _getOET(clientID, userID, GNID, verify = True ):
    """
    Helper function to retrieve Origin, Era, and Artist Type by direct album fetch.
    
    :param str clientID: the Gracenote_ client ID.
    :param str userID: the Gracenote_ user ID.
    :param str GNID: the Gracenote_ music ID of the music data.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: a :py:class:`tuple` of ``artistOrigin``, ``artistEra``, and ``artistType``.
    :retype: tuple
    """
    # Create XML request
    query = _gnquery()
    
    query.addAuth(clientID, userID)
    query.addQuery('ALBUM_FETCH')
    query.addQueryGNID(GNID)
    query.addQueryOption('SELECT_EXTENDED', 'ARTIST_OET')
    query.addQueryOption('SELECT_DETAIL', 'ARTIST_ORIGIN:4LEVEL,ARTIST_ERA:2LEVEL,ARTIST_TYPE:2LEVEL')
    
    queryXML = query.toString()
    
    logging.debug('------------')
    logging.debug('QUERY XML (from _getOET())')
    logging.debug('------------')
    logging.debug(queryXML)
        
    # POST query
    response = requests.post( _gnurl( clientID ), data = queryXML, verify = verify )
    albumXML = response.content
    #response = urllib_request.urlopen(_gnurl(clientID), queryXML)
    #albumXML = response.read()
    
    logging.debug('------------')
    logging.debug('RESPONSE XML (from _getOET())')
    logging.debug('------------')
    logging.debug(albumXML)
    
    # Parse XML
    responseTree = xml.etree.ElementTree.fromstring(albumXML)
    responseElem = responseTree.find('RESPONSE')
    if responseElem.attrib['STATUS'] == 'OK':
        albumElem = responseElem.find('ALBUM')
        artistOrigin = _getMultiElemText(albumElem, 'ARTIST_ORIGIN', 'ORD', 'ID')
        artistEra = _getMultiElemText(albumElem, 'ARTIST_ERA', 'ORD', 'ID')
        artistType = _getMultiElemText(albumElem, 'ARTIST_TYPE', 'ORD', 'ID')
    return artistOrigin, artistEra, artistType
	
class _gnquery( object ):
    """
    A utility class for creating and configuring an XML query for POST'ing to the Gracenote service.
    
    :var Element root: the :py:class:`XML Element <xml.etree.ElementTree.Element>` root used for storing and querying XML data. This element has tag ``QUERIES``.
    """
    
    def __init__(self):
        self.root = xml.etree.ElementTree.Element('QUERIES')
        
    def addAuth(self, clientID, userID):
        """
        Adds authentication information as a sub-element of ``root``, ``auth``, with tag ``AUTH``. The two sub-elements of ``auth`` are ``client`` (with tag ``CLIENT``) and ``user`` (with tag ``USER``).
        
        :param str clientID: the Gracenote_ client ID.
        :param str userID: the Gracenote_ user ID.
        """
        auth = xml.etree.ElementTree.SubElement(self.root, 'AUTH')
        client = xml.etree.ElementTree.SubElement(auth, 'CLIENT')
        user = xml.etree.ElementTree.SubElement(auth, 'USER')
	
        client.text = clientID
        user.text = userID
	
    def addQuery(self, cmd):
        """
        Adds a query element as a sub-element of ``root``, with tag ``QUERY``.
        
        :param str cmd: the command to add to the XML tree data.
        """
        query = xml.etree.ElementTree.SubElement(self.root, 'QUERY')
        query.attrib['CMD'] = cmd
    
    def addQueryMode(self, modeStr):
        query = self.root.find('QUERY')
        mode = xml.etree.ElementTree.SubElement(query, 'MODE')
        mode.text = modeStr

    def addQueryTextField(self, fieldName, value):
        query = self.root.find('QUERY')
        text = xml.etree.ElementTree.SubElement(query, 'TEXT')
        text.attrib['TYPE'] = fieldName
        text.text = value
	
    def addQueryOption(self, parameterName, value):
        query = self.root.find('QUERY')
        option = xml.etree.ElementTree.SubElement(query, 'OPTION')
        parameter = xml.etree.ElementTree.SubElement(option, 'PARAMETER')
        parameter.text = parameterName
        valueElem = xml.etree.ElementTree.SubElement(option, 'VALUE')
        valueElem.text = value
    
    def addQueryGNID(self, GNID):
        query = self.root.find('QUERY')
        GNIDElem = xml.etree.ElementTree.SubElement(query, 'GN_ID')
        GNIDElem.text = GNID
        
    def addQueryClient(self, clientID):
        query = self.root.find('QUERY')
        client = xml.etree.ElementTree.SubElement(query, 'CLIENT')
        client.text = clientID
        
    def addQueryRange(self, start, end):
        query = self.root.find('QUERY')
        queryRange = xml.etree.ElementTree.SubElement(query, 'RANGE')
        rangeStart = xml.etree.ElementTree.SubElement(queryRange, 'START')
        rangeStart.text = str(start)
        rangeEnd = xml.etree.ElementTree.SubElement(queryRange, 'END')
        rangeEnd.text = str(end)
    
    def addQueryTOC(self, toc):
        # TOC is a string of format '150 20512 30837 50912 64107 78357 ...' 
        query = self.root.find('QUERY')
        tocElem = xml.etree.ElementTree.SubElement(query, 'TOC')
        offsetElem = xml.etree.ElementTree.SubElement(tocElem, 'OFFSETS')
        offsetElem.text = toc
		
    def toString(self):
        return xml.etree.ElementTree.tostring(self.root)

    #Methods added by Fabian to reflect the Rhythm use case

    def addAttributeSeed(self, moodID, eraID, genreID):
        query = self.root.find('QUERY')
        seed = xml.etree.ElementTree.SubElement(query, 'SEED')
        seed.attrib['TYPE'] = "ATTRIBUTE"
        if genreID!='':
            genreElement = xml.etree.ElementTree.SubElement(seed, 'GENRE')
            genreElement.attrib['ID'] = genreID
        if moodID!='':		
            genreElement = xml.etree.ElementTree.SubElement(seed, 'MOOD')
            genreElement.attrib['ID'] = moodID
        if eraID!='':
            genreElement = xml.etree.ElementTree.SubElement(seed, 'ERA')
            genreElement.attrib['ID'] = eraID

    def addTextSeed(self, artist, track):
        query = self.root.find('QUERY')
        seed = xml.etree.ElementTree.SubElement(query, 'SEED')
        seed.attrib['TYPE'] = "TEXT"
        if artist!='':
            text = xml.etree.ElementTree.SubElement(seed, 'TEXT')
            text.attrib['TYPE'] = "ARTIST"
            text.text = artist
        if track!='':
            text = xml.etree.ElementTree.SubElement(seed, 'TEXT')
            text.attrib['TYPE'] = "TRACK"
            text.text = track
            
    def addQueryEVENT(self, eventType, GNID):
        query = self.root.find('QUERY')
        event = xml.etree.ElementTree.SubElement(query, 'EVENT')
        event.attrib['TYPE'] = eventType
        gnidTag = xml.etree.ElementTree.SubElement(event, 'GN_ID')
        gnidTag.text = GNID
        
    def addRadioID(self, radioID):
        query = self.root.find('QUERY')
        radio = xml.etree.ElementTree.SubElement(query, 'RADIO')
        myradioid = xml.etree.ElementTree.SubElement(radio, 'ID')
        myradioid.text = radioID
        
        
def _getElemText(parentElem, elemName, elemAttribName=None, elemAttribValue=None):
    """
    XML parsing helper function to find child element with a specific name, and return the text value. Either both ``elemAttribName`` and ``elemAttribValue`` are ``None``, or neither is ``None``.
    
    :param SubElement parentElem: the :py:class:`XML SubElement <xml.etree.ElementTree.SubElement>` to query.
    :param str elemName: search for XML elements with this tag.
    :param str elemAttribName: optional argument. If defined, filter on those XML elements with this attribute name.
    :param str elemAttribValue: optional argument. If defined, filter on those XML elements whose attribute name is given by ``elemAttribName`` and whose value is ``elemAttribValue``.

    :returns: the text associated with the XML element, if found. Otherwise, returns ``""``.
    :rtype: str
    """
    elems = parentElem.findall(elemName)
    for elem in elems:
        if elemAttribName is not None and elemAttribValue is not None:
            if elem.attrib[elemAttribName] == elemAttribValue:
                return urllib_parse.unquote(elem.text)
            else:
                continue
        else: # Just return the first one
            return urllib_parse.unquote(elem.text)
    return ''

def _getElemAttrib(parentElem, elemName, elemAttribName):
    """
    XML parsing helper function to find child element with a specific name, and return the value of a specified attribute.
    
    :param SubElement parentElem: the :py:class:`XML SubElement <xml.etree.ElementTree.SubElement>` to query.
    :param str elemName: search for XML elements with this tag.
    :param str elemAttribName: filter on those XML elements with this attribute name.
    
    :returns: the attribute value associated with the XML element whose tag is ``elemName`` and whose attribute is ``elemAttribName``.
    :rtype: str
    """
    elem = parentElem.find(elemName)
    if elem is not None:
        return elem.attrib[elemAttribName]
    return None

def _getMultiElemText(parentElem, elemName, topKey, bottomKey):
    """
    XML parsing helper function to return a 2-level :py:class:`dict` of multiple elements by a specified name, using ``topKey`` as the first key, and ``bottomKey`` as the second key.
    
    :param SubElement parentElem: the :py:class:`XML SubElement <xml.etree.ElementTree.SubElement>` to query.
    :param str elemName: search for XML elements with this tag.
    :param str topKey: filter on those XML elements with this attribute name.
    :param str bottomKey: filter on those XML elements with this attribute name.

    :returns: a two-level :py:class:`dict` consisting of keys given by ``elem.attrib[ topKey ]``, and values given by a dictionary: ``{ bottomKey: elem.attrib[ bottomKey ], 'TEXT' : elem.text }``. In addition, for an element whose attributes are not in ``topKey``, there is a key of ``0`` and value of ``{ bottomKey: elem.attrib[ bottomKey ], 'TEXT' : elem.text }``.
    :rtype: dict
    """
    elems = parentElem.findall(elemName)
    result = {} # 2-level dictionary of items, keyed by topKey and then bottomKey
    if elems is not None:
        for elem in elems:
            if topKey in elem.attrib:
                result[elem.attrib[topKey]] = {bottomKey:elem.attrib[bottomKey], 'TEXT':elem.text}
            else:
                result['0'] = {bottomKey:elem.attrib[bottomKey], 'TEXT':elem.text}
    return result
