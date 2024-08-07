import os, sys, glob, numpy, titlecase, httplib2, json, logging, oauth2client.client, mutagen.mp4
import requests, datetime, musicbrainzngs, time, io, tabulate, validators, subprocess, uuid, re
import pathos.multiprocessing as multiprocessing
from bs4 import BeautifulSoup
from contextlib import contextmanager
from googleapiclient.discovery import build
from itertools import chain
from PIL import Image
from urllib.parse import urljoin
from shutil import which
from rapidfuzz.fuzz import partial_ratio
#
from howdy import resourceDir
from howdy.core import core, baseConfDir, session, PlexConfig
from howdy.core import return_error_raw, get_maximum_matchval
from howdy.music import pygn, parse_youtube_date, format_youtube_date, fill_m4a_metadata, get_m4a_metadata

def oauth_store_google_credentials( credentials ):
    """
    Stores the `Google OAuth2`_ credentials, in the form of a :py:class:`AccessTokenCredentials <oauth2client.client.AccessTokenCredentials>` object, into the SQLite3_ configuration database for the :py:class:`MobileClient <gmusicapi.mobileclient.MobileClient>` manager.
    
    :param credentials: the :py:class:`AccessTokenCredentials <oauth2client.client.AccessTokenCredentials>` object to store into the database.
    
    .. seealso:: :py:meth:`oauth_get_google_credentials <howdy.music.music.oauth_get_google_credentials>`.

    .. _`Google OAuth2` : https://developers.google.com/identity/protocols/OAuth2
    """
    val = session.query( PlexConfig ).filter( PlexConfig.service == 'gmusic_mobileclient' ).first( )
    if val is not None:
        session.delete( val )
        session.commit( )

    newval = PlexConfig(
        service = 'gmusic_mobileclient',
        data = json.loads( credentials.to_json( ) ) )
    session.add( newval )
    session.commit( )

def oauth_get_google_credentials( ):
    """
    Gets the `Google Oauth2`_ credentials, stored in the SQLite3_ configuration database, in the form of a refreshed :py:class:`AccessTokenCredentials <oauth2client.client.AccessTokenCredentials>` object. This OAuth2 authentication method IS used only for the GMusicAPI Mobileclient manager.

    :returns: a :py:class:`AccessTokenCredentials <oauth2client.client.AccessTokenCredentials>` form of the `Google Oauth2`_ credentials for various Oauth2 services.
    :rtype: :py:class:`AccessTokenCredentials <oauth2client.client.AccessTokenCredentials>`

    .. seealso:: :py:meth:`oauth_store_google_credentials <howdy.music.music.oauth_store_google_credentials>`.
    """
    val = session.query( PlexConfig ).filter( PlexConfig.service == 'gmusic_mobileclient' ).first( )
    if val is None: return None
    cred_data = val.data
    credentials = oauth2client.client.OAuth2Credentials.from_json(
        json.dumps( cred_data ) )
    return credentials

#
## get all the tracks, by order, of all the official albums of an artist.
## this is not tested all that much, but perhaps it is useful to some people
class MusicInfo( object ):
    """
    This object uses the MusicBrainz_ API, through the higher level :py:mod:`musicbrainzngs` Python module, to get information on songs, albums, and artists.

    :param str artist_name: the artist over which to search.
    :param str artist_mbid: optional argument. If not ``None``, then information on this artist uses this MusicBrainz_ artist ID to get its info. Default is ``None``.
    :param bool do_direct: optional argument. If ``True``, then perform a *direct* search on the artist rather than using the default indexed search at a low lebvel. Default is ``False``. See :py:meth`get_artist_direct_search_MBID <howdy.music.music.MusicInfo.get_artist_direct_search_MBID>` for the low-level functionality.
    
    :var dict artist: the low level information on a specific artist, returned by :py:mod:`musicbrainzngs`. For example, for the artist _Air, this looks like,

      .. code-block:: python

            {'id': 'cb67438a-7f50-4f2b-a6f1-2bb2729fd538',
             'type': 'Group',
             'ext:score': '100',
             'name': 'Air',
             'sort-name': 'Air',
             'country': 'FR',
             'area': {'id': '08310658-51eb-3801-80de-5a0739207115',
              'type': 'Country',
              'name': 'France',
              'sort-name': 'France',
              'life-span': {'ended': 'false'}},
             'begin-area': {'id': '2322e571-1d9b-4023-a31c-7222509407ab',
              'type': 'City',
              'name': 'Versailles',
              'sort-name': 'Versailles',
              'life-span': {'ended': 'false'}},
             'disambiguation': 'French band',
             'isni-list': ['0000000123694584'],
             'life-span': {'begin': '1995', 'ended': 'false'},
             'alias-list': [
              {'sort-name': 'Air French Band', 'alias': 'Air French Band'},
              {'sort-name': 'Air (French Band)', 'alias': 'Air (French Band)'},
              {'sort-name': 'Aïr', 'alias': 'Aïr'}],
             'tag-list': [{'count': '2', 'name': 'trip-hop'},
              {'count': '10', 'name': 'electronic'},
              {'count': '7', 'name': 'downtempo'},
              {'count': '0', 'name': 'soundtrack'},
              {'count': '0', 'name': 'pop'},
              {'count': '2', 'name': 'chillout'},
              {'count': '5', 'name': 'ambient'},
              {'count': '0', 'name': 'jazz'},
              {'count': '7', 'name': 'french'},
              {'count': '1', 'name': 'idm'},
              {'count': '0', 'name': 'france'},
              {'count': '0', 'name': 'français'},
              {'count': '3', 'name': 'electronica'},
              {'count': '0', 'name': 'producer'},
              {'count': '0', 'name': 'composer'},
              {'count': '0', 'name': 'lyricist'},
              {'count': '0', 'name': 'european'},
              {'count': '0', 'name': 'parolier'},
              {'count': '0', 'name': 'compositeur'},
              {'count': '0', 'name': 'producteur'},
              {'count': '0', 'name': 'dance and electronica'},
              {'count': '2', 'name': 'ambient pop'}]}

    :var str artist_name: the artist's name.
    :var int ambid: the MusicBrainz_ artist ID.
    :var dict alltrackdata: the low-level :py:class:`dict` of information on all studio albums produced by the artist. Each key in this top level dictionary is a studio album. Each value is a lower level dictionary of summary information on that album, with the following keys.
      
      * ``release-date`` is the :py:class:`date <datetime.date>` when that album was released.
      * ``album-url`` if defined, is the URL to the album's image. If not defined, then it is an empty :py:class:`str`.
      * ``tracks`` is a :py:class:`dict` of tracks on this album. Each key is the track number, and each value is a :py:class:`tuple` of song name, and song length.

      For example, here is information on the `Moon Safari`_ album released by Air_.
      
      .. code-block:: python

         {'release-date': datetime.date(1998, 1, 16),
          'album url': '',
          'tracks': {1: ('La Femme D’argent', 429.56),
           2: ('Sexy Boy', 298.466),
           3: ('All I Need', 268.333),
           4: ('Kelly, Watch the Stars!', 225.746),
           5: ('Talisman', 256.48),
           6: ('Remember', 154.293),
           7: ('You Make It Easy', 240.826),
           8: ('Ce Matin-Là', 218.506),
           9: ('New Star in the Sky (Chanson Pour Solal)', 340.8),
           10: ('Le Voyage De Pénélope', 190.866)}}

    .. _MusicBrainz: https://musicbrainz.org/doc/Development/XML_Web_Service/Version_2
    .. _Spotify: https://open.spotify.com
    .. _SQLite3: https://www.sqlite.org/index.html
    .. _Air: https://en.wikipedia.org/wiki/Air_(band)
    .. _`Moon Safari`: https://en.wikipedia.org/wiki/Moon_Safari
    """

    @classmethod
    def get_artist_direct_search_MBID( cls, artist_name ):
        """
        Sometimes the MusicBrainz_ server does not update. Fixes-when-broken of the MusicBrainz_ server do not happen on a schedule, or even a quickness. In such an instance, you can specify the *specific* artist using direct search rather than indexed search. This method returns the artist's MBID of the artist one queries. *If there is more than one match*, then returns ``None``.

        :param str artist_name: the artist over which to perform a search.
        :returns: the MBID of the artist. If more than one matching artist is found, or *no* matching artists, then returns ``None``.
        """
        response = requests.get( 'https://musicbrainz.org/search', params = {
            'query' : '+'.join( artist_name.split()),
            'type' : 'artist',
            'limit' : 25,
            'method' : 'direct' }, verify = False )
        if response.status_code != 200:
            return None
        html = BeautifulSoup( response.content, 'html.parser' )
        table = html.find_all('table', { 'class' : 'tbl'})
        if len( table ) != 1:
            return None
        table = table[ 0 ]
        all_elems = list(filter(lambda elem: 'href' in elem.attrs and '/artist/' in elem['href'] and elem.text.strip( ) == artist_name, table.find_all('a')))
        if len( all_elems ) != 1: return None
        #
        ## success
        elem = all_elems[ 0 ]
        return os.path.basename( elem['href'] )
    
    @classmethod
    def get_artist_datas_LL(
        cls, artist_name, min_score = 100,
        do_strict = True, artist_mbid = None, do_direct = False ):
        """
        :param str artist_name: the artist over which to search.
        :param int min_score: optional argument. Filter on this minimum score on artist name matches to ``artist_name``. 0 :math:`\le` ``min_score`` :math:`\le 100`. Default is ``100``.
        :param bool do_strict: optional argument. If ``True``, performs a strict search using the :py:meth:`musicbrainzngs search_artists <musicbrainz.search_artists>` method. Default is ``True``.
        :param str artist_mbid: optional argument. If not ``None``, then uses musicbrainzngs's :py:meth:`get_artist_by_id <musicbrainzngs.get_artist_by_id>` to get information on an artist. Otherwise, gets all artist matches. Default is ``None``.
        :param bool do_direct: Sometimes the MusicBrainz_ server does not update. Fixes-when-broken of the MusicBrainz_ server do not happen on a schedule, or even a quickness. In such an instance, you can specify the *specific* artist using direct search rather than indexed search. See :py:meth`get_artist_direct_search_MBID <howdy.music.music.MusicInfo.get_artist_direct_search_MBID>`.
        
        :returns: a :py:class:`list` of artist information matches to ``artist_name``. If ``artist_mbid`` is not ``None``, then gets a *SINGLE* artist match. Otherwise gets all matches found.
        :rtype: list
        """
        #
        ## when do_direct is TRUE
        if do_direct:
            artist_mbid = MusicInfo.get_artist_direct_search_MBID( artist_name )
            if artist_mbid is None: return None
            adata = [ musicbrainzngs.get_artist_by_id( artist_mbid )[ 'artist' ] ]
            return adata
        
        if artist_mbid is not None:
            adata = [ musicbrainzngs.get_artist_by_id( artist_mbid )[ 'artist' ] ]
            return adata
        assert( min_score <= 100 and min_score >= 0 )
        adata = list(filter(lambda entry: int(entry['ext:score']) >= min_score,
                            musicbrainzngs.search_artists(
                                artist=artist_name, strict = do_strict )['artist-list'] ) )
        return adata

    @classmethod
    def get_set_musicbrainz_useragent( cls, email_address ):
        """
        :param str email_address: a valid email address to provide to provide to the MusicBrainz_ API's user agent.
        :returns: a :py:class:`dict` whose two keys and values are,

          * ``appname`` is the application name registered with the MusicBrainz_ API.
          * ``version`` is the application version.

          This information comes from the SQLite3_ configuration database.
        
        :rtype: dict
        
        :raise ValueError: if the MusicBrainz_ API configuration information cannot be found.
        """
        val = session.query( PlexConfig ).filter(
            PlexConfig.service == 'musicbrainz' ).first( )
        if val is None:
            raise ValueError( "ERROR, MUSICBRAINZ USERAGENT DATA NOT FOUND OR SET" )
        data = val.data
        appname = data[ 'appname' ]
        version = data[ 'version' ]
        musicbrainzngs.set_useragent( appname, version, email_address )
        return { 'appname' : appname, 'version' : version }

    @classmethod
    def push_musicbrainz_useragent( cls, appname, version ):
        """
        Pushes the MusicBrainz_ API configuration into the SQLite3_ configuration database.
        
        :param str appname: the application name registered with the MusicBrainz_ API.
        :param str version: the application version.
        """
        val = session.query( PlexConfig ).filter(
            PlexConfig.service == 'musicbrainz' ).first( )
        if val is not None:
            session.delete( val )
            session.commit( )
        session.add( PlexConfig( service = 'musicbrainz',
                                 data = { 'appname' : appname,
                                          'version' : version } ) )
        session.commit( )

    @classmethod
    def set_musicbrainz_verify( cls, verify = True ):
        """
        Makes the MusicBrainz_ API to use either HTTPS (if verifying traffic) or HTTP (if not verifying traffic)
        
        :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
        """
        musicbrainzngs.set_hostname( 'musicbrainz.org', use_https = verify )

    @classmethod
    def push_spotify_credentials( cls, client_id, client_secret, verify = True ):
        """
        Pushes the Spotify_ API configuration into the SQLite3_ configuration database. Take a look at `this blog article on the Spotify API <https://tanimislam.gitlab.io/blog/spotify-web-api.html>`_ for some more information on setting up your Spotify_ web API client.
        
        :param str client_id: the Spotify_ client ID.
        :param str client_secret: the Spotify_ client secret.
        :param bool verify: if ``True``, then use HTTPS authentication. Otherwise do not. Default is ``True``.
        """
        #
        ## first check that it is a valid Spotify credential
        response = requests.post(
            "https://accounts.spotify.com/api/token",
            headers = { 'Content-Type' : 'application/x-www-form-urlencoded' },
            data = {
                'grant_type'    : 'client_credentials',
                'client_id'     : client_id,
                'client_secret' : client_secret }, verify = verify )
        if not response.ok:
            raise ValueError("ERROR, INVALID SPOTIFY CREDENTIALS" )
        val = session.query( PlexConfig ).filter(
            PlexConfig.service == 'spotify' ).first( )
        if val is not None:
            session.delete( val )
            session.commit( )
        session.add(
            PlexConfig( service = 'spotify',
                       data = { 'client_id' : client_id,
                               'client_secret' : client_secret } ) )
        session.commit( )

    @classmethod
    def get_spotify_credentials( cls ):
        """
        :returns: a :py:class:`dict` whose two keys and values are the ``client_id`` and the ``client_secret`` for the Spotify_ web API client in the SQLite3_ configuration database.
        :rtype: dict
        """
        val = session.query( PlexConfig ).filter(
            PlexConfig.service == 'spotify' ).first( )
        if val is None:
            raise ValueError( "ERROR, SPOTIFY WEB API CLIENT CREDENTIALS NOT FOUND OR SET" )
        return val.data

    @classmethod
    def get_spotify_session( cls ):
        """
        Returns the session token from a valid Spotify_ API account.
        :rtype: str
        """
        data = MusicInfo.get_spotify_credentials( )
        response = requests.post(
            "https://accounts.spotify.com/api/token",
            headers = { 'Content-Type' : 'application/x-www-form-urlencoded' },
            data = {
                'grant_type'    : 'client_credentials',
                'client_id'     : data['client_id'],
                'client_secret' : data['client_secret'] } )
        assert( response.ok )
        data_auth = response.json( )
        return data_auth[ 'access_token' ]

    #
    ## now get all the albums of this artist.
    ## musicbrainz does a "make functionality so general that easy use cases
    ## are much harder than expected" implementation.
    ##
    ## first, get all the release-groups of the artist
    @classmethod
    def get_albums_lowlevel( cls, ambid, do_all = False ):
        """
        Used by the constructor to get the collection of studio albums released by this artist.
        
        :param int ambid: the MusicBrainz_ artist ID.
        :param bool do_all: if ``True``, then return all the MusicBrainz_ album info provided. If ``False``, then do not include albums that have been classified as remixes or mixtapes. Default is ``False``.
        :returns: a :py:class:`list`, where each element of the list is low-level :py:mod:`musicbrainzngs` music collection information. The album information is a :py:class:`dict` with the following keys,
          
          * ``id`` is the MusicBrainz_ album ID.
          * ``type`` is the type of the release (for example,  ``Album`` s a studio released album).
          * ``title`` is the name of the release.
          * ``first-release-date`` is the release date, as a :py:class:`str`.
          * ``primary-type`` is the main type of the release.
        
          For example, for the artist Air_, whose MusicBrainz_ artist ID is ``"cb67438a-7f50-4f2b-a6f1-2bb2729fd538"``, an example first element in the list is,

          .. code-block:: python

             {'id': 'b0bf2b77-b8cf-32f6-8893-9741d757b400',
              'type': 'Album',
              'title': 'Moon Safari',
              'first-release-date': '1998-01-16',
              'primary-type': 'Album'}

        :rtype: list
        """
        rgdata = musicbrainzngs.get_artist_by_id(
            ambid, includes=[ 'release-groups' ],
            release_type=['album'] )['artist']['release-group-list']
        if do_all: return rgdata
        #
        def is_mixtape( elem ):
            if 'secondary-type-list' not in elem: return False
            if any(map(lambda typ: 'mixtape' in typ.lower( ) or 'remix' in typ.lower( ) or
                       'live' in typ.lower( ), elem['secondary-type-list'])):
                return True
            return False
        rgdata = list(filter(lambda elem: not is_mixtape( elem ), rgdata))
        return rgdata

    @classmethod
    def get_album_info( cls, album ):
        """
        :param dict album: a dictionary of low-level album info returned by :py:mod:`musicbrainzngs` associated with this studio album.
        :returns: a two-element :py:class:`tuple` if successful, otherwise returns ``None``. The first is the studio album name, and each second element is a :py:class:`dict` containing summary album info of that album. See the ``altrackdata`` dictionary in :py:class:`MusicInfo <howdy.music.music.MusicInfo>` to understand the description of summary album information.
        :rtype: tuple
        """
        time0 = time.time( )
        rgid = album['id']
        rgdate = album['first-release-date']
        rtitle = album['title']
        rgdate_date = None
        for fmt in ( '%Y-%m-%d', '%Y-%m', '%Y' ):
            try:
                rgdate_date = datetime.datetime.strptime(
                    rgdate, fmt ).date( )
                break
            except: pass
        if rgdate is None:
            print("Error, could not find correct release info for %s because no date defined." % rtitle )
            return None
        rdata = musicbrainzngs.get_release_group_by_id( rgid, includes=['releases'] )[
            'release-group']['release-list']
        try:
            release = list(filter(lambda dat: 'date' in dat and dat['date'] == rgdate, rdata ) )
            if len( release ) == 0:
                logging.debug("Error, could not find correct release info for %s." % rtitle )
                return None
            release = release[ 0 ]
        except Exception as e:
            logging.debug("Error, could not find correct release info for %s." % rtitle )
            return None
        rid = release['id']
        trackinfo = musicbrainzngs.get_release_by_id( rid, includes = ['recordings'] )[
            'release']['medium-list']
        try:
            image_datas = musicbrainzngs.get_image_list( rid )[ 'images' ]
            if len( image_datas ) == 0:
                album_url = ''
            else:
                image_data = image_datas[ 0 ]
                album_url = image_data[ 'image' ]
        except Exception as e:
            album_url = ''
        
        #
        ## collapse multiple discs into single disk with more tracknumbers
        track_counts = list(map(lambda cd_for_track: cd_for_track['track-count'], trackinfo))
        act_counts = numpy.concatenate([ [ 0, ], numpy.cumsum( track_counts ) ])
        albumdata = { 'release-date' : rgdate_date }
        albumdata[ 'album url' ] = album_url
        albumdata[ 'tracks' ] = { }
        alltracknos = set(range(1, 1 + act_counts[-1]))
        for idx, cd_for_track in enumerate( trackinfo ):
            assert( len( cd_for_track[ 'track-list' ]) == cd_for_track[ 'track-count' ] )
            for track in cd_for_track[ 'track-list' ]:
                try: number = int( track[ 'position' ] )
                except:
                    logging.debug( 'error, track = %s does not have defined position.' % track )
                    return None
                title = titlecase.titlecase( track[ 'recording' ][ 'title' ] )
                if 'length' in track[ 'recording' ]:
                    length = 1e-3 * int( track[ 'recording' ][ 'length' ] )
                else: length = None
                albumdata[ 'tracks' ][ act_counts[ idx ] + number ] = ( title, length )
        assert( set( albumdata[ 'tracks' ] ) == alltracknos )
        logging.debug( 'processed %s in %0.3f seconds.' % ( rtitle, time.time( ) - time0 ) )
        return titlecase.titlecase( rtitle ), albumdata
    
    def __init__( self, artist_name, artist_mbid = None, do_direct = False ):
        time0 = time.time( )
        #
        ## first get out artist MBID, called ambid, with score = 100
        adata = MusicInfo.get_artist_datas_LL( artist_name, min_score = 100, artist_mbid = artist_mbid, do_direct = do_direct )
        if len(adata) == 0:
            raise ValueError( 'Could not find artist = %s in MusicBrainz.' % artist_name )
        self.artist = adata[ 0 ]
        self.ambid = self.artist[ 'id' ]
        self.artist_name = artist_name
        logging.debug('found artist %s with artist mbid = %s.' % (
            artist_name, self.ambid ) )
        rgdata = MusicInfo.get_albums_lowlevel( self.ambid )
        albums = list( filter(lambda dat: dat['type'] == 'Album', rgdata ) )
        with multiprocessing.Pool( processes = multiprocessing.cpu_count( ) ) as pool:
            self.alltrackdata = dict( filter(None, 
                pool.map( MusicInfo.get_album_info, albums  ) ) )
        logging.debug( 'processed %d albums for %s in %0.3f seconds.' % (
            len( self.alltrackdata ), artist_name, time.time( ) - time0 ) )

    def get_music_metadatas_album( self, album_name, min_criterion_score = 95 ):
        """
        :param str album_name: a studio album released by this artist.
        :param int min_criterion_score: the minimum score to accept for a string similarity comparison between ``album_name`` and any studio album created by this artist. ``70`` :math:`\le` ``min_criterion_score`` :math:`\le` ``100``, and the default is ``95``. The :py:meth:`get_maximum_matchval <howdy.core.get_maximum_matchval>` performs the string comparison. If no album matches ``album_name``, then return album data for the album whose name is closest (while having a similarity score :math:`\ge` ``min_criterion_score``) to ``album_name`` is returned.
        :returns: a two-element :py:class:`tuple`, whose first element is a :py:class:`list` of summary information on tracks for this album, and whose second element is the string ``"SUCCESS"``. The elements in this list are ordered by first song track to last song track. An example first song for the `Moon Safari`_ album released by Air_ is,

          .. code-block:: python

             {'artist': 'Air',
              'album': 'Moon Safari',
              'year': 1998,
              'total tracks': 10,
              'song': 'La Femme D’argent',
              'tracknumber': 1,
              'album url': '',
              'duration': 429}

          If the album name has not been published by this artist, return a :py:class:`tuple` of format :py:meth:`return_error_raw <howdy.core.return_error_raw>`.

        :rtype: tuple
        """
        assert( min_criterion_score >= 70 and min_criterion_score <= 100 )
        aname = album_name
        #
        ## only if score is less than 95%
        if album_name not in self.alltrackdata:
            best_match_aname = max( self.alltrackdata, key = lambda a_name: get_maximum_matchval( a_name, album_name ) )
            score_best_match = get_maximum_matchval( album_name, album_name )
            logging.info( 'MUSICBRAINZ: best_match = "%s", score = %0.1f.' % ( best_match_aname, score_best_match ) )
            if score_best_match < min_criterion_score:
                return return_error_raw(
                    'Could not find album = %s for artist = %s with Musicbrainz. Best match is "%s" with score = %0.1f' % (
                        album_name, self.artist_name, best_match_aname, score_best_match ) )
            aname = best_match_aname
        album_info = self.alltrackdata[ aname ]
        album_data_dict = [ ]
        total_tracks = len( album_info[ 'tracks' ] )
        for trackno in sorted( album_info[ 'tracks' ] ):
            trackinfo = { 'artist' : self.artist_name,
                          'album' : album_name,
                          'year' : album_info[ 'release-date' ].year,
                          'total tracks' : total_tracks,
                          'song' : album_info[ 'tracks' ][ trackno ][ 0 ],
                          'tracknumber' : trackno,
                          'album url' : album_info[ 'album url' ]
            }
            if album_info[ 'tracks' ][ trackno ][ 1 ] is not None:
                trackinfo[ 'duration' ] = int( album_info[ 'tracks' ][ trackno ][ 1 ] )
            album_data_dict.append( trackinfo )
        return album_data_dict, 'SUCCESS'

    def get_album_image( self, album_name ):
        """
        :param str album_name: album_name.
        :returns: If successful, downloads the album image into a PNG_ file named "artist_name.album_name.png", and returns a two-element :py:class:`tuple`, whose first element is the PNG_ filename, and whose second element is the string ``"SUCCESS"``. If unsuccessful, then returns a :py:class:`tuple` of format :py:meth:`return_error_raw <howdy.core.return_error_raw>`.
        :rtype: tuple
        """
        if album_name not in self.alltrackdata:
            return return_error_raw(
                'Could not find album = %s for artist = %s with Musicbrainz.' % (
                    album_name, self.artist_name ) )
        album_info = self.alltrackdata[ album_name ]
        album_url = album_info[ 'album url' ]
        filename = '%s.%s.png' % ( self.artist_name, album_name.replace('/', '-' ) )
        img = Image.open( io.BytesIO( requests.get( album_url, verify = False ).content ) )
        img.save( filename, format = 'png' )
        os.chmod( filename, 0o644 )
        return filename, 'SUCCESS'

    def get_music_metadata( self, song_name, min_criterion_score = 85 ):
        """
        :param str song_name: name of the song.
        :param int min_criterion_score: the minimum score to accept for a string similarity comparison between ``song_name`` and any track created by this artist. ``70`` :math:`\le` ``min_criterion_score`` :math:`\le` ``100``, and the default is ``85``. The :py:meth:`get_maximum_matchval <howdy.core.get_maximum_matchval>` performs the string comparison. If no track matches ``song_name``, then track data for a track that is the closest match (while having a similarity score :math:`\ge` ``min_criterion_score``) to ``song_name`` is returned.
        :returns: if successful, a two element :py:class:`tuple`. First element is a :py:class:`dict` of information on the song, and the second element is the string ``"SUCCESS"``. For example, for the Air_ song `Kelly Watch the Stars`_ in `Moon Safari`_, the closest match is ``Kelly, Watch the Stars!``.

          .. code-block:: python
        
             {'album': 'Moon Safari',
              'artist': 'Air',
              'year': 1998,
              'tracknumber': 4,
              'total tracks': 10,
              'song': 'Kelly, Watch the Stars!',
              'duration': 225.746,
              'album url': 'http://...2-490838855977/21141679576.jpg'}

          If unsuccessful, then returns a :py:class:`tuple` of format :py:meth:`return_error_raw <howdy.core.return_error_raw>`.
        
        :rtype: tuple
        """
        assert( min_criterion_score >= 70 and min_criterion_score <= 100 )
        
        def is_track_in_album( album_name, song_name ):
            trackdata = self.alltrackdata[ album_name ][ 'tracks' ]
            matches = len(list(filter(lambda trkno: trackdata[ trkno ][ 0 ] == song_name,
                                      trackdata)))
            return matches > 0

        def best_song_match( song_name ):
            alltracks = set( chain.from_iterable(
                map(lambda album_name: set(
                    map(lambda trkno: self.alltrackdata[ album_name ][ 'tracks' ][ trkno ][ 0 ],
                        self.alltrackdata[ album_name ][ 'tracks' ] ) ),
                    self.alltrackdata ) ) )
            best_matches = list( filter(lambda song: get_maximum_matchval( song, song_name ) >= 
                                        min_criterion_score, alltracks ) )
            if len( best_matches ) == 0: return None
            return max( best_matches, key = lambda song: get_maximum_matchval( song, song_name ) )
            
        #
        ## find the single album in which the song is found
        album_matches = list(filter(lambda album_name: is_track_in_album( album_name, song_name ),
                                    self.alltrackdata ) )
        if len( album_matches ) == 0:
            best_match = best_song_match( song_name )
            if best_match is None:
                return return_error_raw( 'Could not find song = %s produced by artist = %s.' % (
                    song_name, self.artist_name ) )
            album_match = max(list(filter(
                lambda album_name: is_track_in_album( album_name, best_match ),
                                    self.alltrackdata ) ) )
        else:
            best_match = song_name
            album_match = max( album_matches )
        #
        ## now get all the info for this song
        albumdata = self.alltrackdata[ album_match ]
        trackdata = albumdata[ 'tracks' ]
        tracknumber = min(list(filter(
            lambda trkno: trackdata[ trkno ][ 0 ] == best_match,
            trackdata)))
        return {
            'album'  : album_match,
            'artist' : self.artist_name,
            'tracknumber' : tracknumber,
            'year' : albumdata[ 'release-date' ].year,
            'total tracks' : len( trackdata ),
            'song' : best_match,
            'duration' : trackdata[ tracknumber ][ 1 ],
            'album url' : albumdata[ 'album url' ] }, 'SUCCESS'

    def get_song_listing( self, album_name ):
        """
        :param str album_name: album_name.
        :returns: If successful, returns a two-element :py:class:`tuple`, whose first element is the list of songs ordered by track number, and whose second element is the string ``"SUCCESS"``. Each element in this list is a :py:class:`tuple` of song number and track number. For example, for `Moon Safari`_ by Air_,
        
          .. code-block:: python

              [("La Femme d'Argent", 1),
               ('Sexy Boy', 2),
               ('All I Need', 3),
               ('Kelly Watch the Stars', 4),
               ('Talisman', 5),
               ('Remember', 6),
               ('You Make It Easy', 7),
               ('Ce Matin-Là', 8),
               ('New Star in the Sky (Chanson Pour Solal)', 9),
               ('Le Voyage De Pénélope', 10)]

          If unsuccessful, then returns a :py:class:`tuple` of format :py:meth:`return_error_raw <howdy.core.return_error_raw>`.
        
        :rtype: tuple
        """
        if album_name not in self.alltrackdata:
            return return_error_raw(
                'Could not find album = %s for artist = %s with Musicbrainz.' % (
                    album_name, self.artist_name ) )
        data, status = self.get_music_metadatas_album( album_name )
        track_listing = sorted(map(lambda elem: ( elem[ 'song' ], elem[ 'tracknumber' ] ), data ),
                               key = lambda tup: tup[1] )
        return track_listing, 'SUCCESS'

    def print_format_album_names( self ):
        """
        Pretty-prints summary table of studio albums released by the artist, ordered by album release date. For example, for Air_,

        .. code-block:: console

           Air has 7 studio albums.

           Studio Album                         Year    # Tracks
           ---------------------------------  ------  ----------
           Moon Safari                          1998          10
           10 000 Hz Legend                     2001          12
           City Reading (Tre Storie Western)    2003          19
           Talkie Walkie                        2004          11
           Pocket Symphony                      2006          12
           Love 2                               2009          12
           Music for Museum                     2014           9
        """
        all_album_data = sorted(
            map(lambda album:
                ( album, self.alltrackdata[ album ]['release-date'].year,
                  len( self.alltrackdata[ album ][ 'tracks' ] ) ), self.alltrackdata ),
            key = lambda tup: tup[1] )
        print( '%s has %d studio albums.\n' % ( self.artist_name, len( all_album_data ) ) )
        print( '%s\n' % 
               tabulate.tabulate( all_album_data, headers = [ 'Studio Album', 'Year', '# Tracks' ] ) )
        

@contextmanager
def gmusicmanager( useMobileclient = False, verify = True, device_id = None ):
    """
    Returns a :py:class:`contextmanager <contextlib.contextmanager>` wrapped GmusicAPI_ manager used to perform operations on one's `Google Play Music`_ account.
    
    :param bool useMobileClient: optional argument. If ``True``, use the :py:class:`MobileClient <gmusicapi.MobileClient>` manager, otherwise use the :py:class:`Musicmanager <gmusicapi.MusicManager>` manager. Default is ``False``.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :param str device_id: optional argument. If defined, then attempt to use this MAC ID to register the music manager.
    
    .. seealso:: :py:meth:`get_gmusicmanager <howdy.music.music.get_gmusicmanager>`.

    .. _`Google Play Music`: https://play.google.com/music/listen
    """
    mmg = get_gmusicmanager( useMobileclient = useMobileclient, verify = verify,
                             device_id = device_id )
    try:
        yield mmg
    finally:
        mmg.logout( )

def gmusicmanager_fixlogin( mmg ):
    """
    Workaround to deal with following problem: cannot create an authorized GmusicAPI :py:class:`Mobileclient <gmusicapi.Mobileclient>` because the device ID automatically found is not one of the :py:class:`set` of authorized device IDs.

    :param Mobileclient mmg: the erroring out :py:class:`Mobileclient <gmusicapi.Mobileclient>` music manager.
    :raise ValueError: if the music manager has not errored out.
    :raise ValueError: if the music manager is not a :py:class:`Mobileclient <gmusicapi.Mobileclient>`.

    .. seealso:: :py:meth:`get_gmusicmanager <howdy.music.music.get_gmusicmanager>`.
    """
    import gmusicapi
    
    assert( isinstance( mmg, gmusicapi.Mobileclient ) ), "error, music manager object must be a Mobileclient"
    assert( len( mmg.error_device_ids ) != 0 ), "error, did not find the right device_id previously."
    credentials = oauth_get_google_credentials( )
    device_id = min( mmg.error_device_ids )
    mmg.logout( )
    mmg.oauth_login( oauth_credentials = credentials, device_id = device_id )

def get_gmusicmanager( useMobileclient = False, verify = True, device_id = None ):
    """
    Returns a GmusicAPI_ manager used to perform operations on one's `Google Play Music`_ account. If the Musicmanager is instantiated but cannot find the device (hence properly authorize for operation), then the attribute ``error_device_ids`` is a non-empty :py:class:`set` of valid device IDs.

    :param bool useMobileClient: optional argument. If ``True``, use the :py:class:`MobileClient <gmusicapi.MobileClient>` manager, otherwise use the :py:class:`Musicmanager <gmusicapi.MusicManager>` manager. Default is ``False``.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :param str device_id: optional argument. If defined, then attempt to use this MAC ID to register the music manager.

    :raise ValueError: if cannot instantiate the Musicmanager.
    :raise AssertionError: if cannot get machine's MAC id.

    .. seealso:: :py:meth:`gmusicmanager <howdy.music.music.gmusicmanager>`.
    """
    import gmusicapi
    
    
    #
    ## first copy this code from gmusic.mobileclient
    ## because base method to determine device id by gmusicapi fails when cannot be found
    def return_deviceid( replace_colons = True ):
        from uuid import getnode as getmac
        from gmusicapi.utils import utils
        try:
            mac_int = getmac( )
            if (mac_int >> 40) % 2:
                raise OSError("a valid MAC could not be determined."
                              " Provide an android_id (and be"
                              " sure to provide the same one on future runs).")
            device_id = utils.create_mac_string( mac_int )
            if replace_colons:
                return device_id.replace( ':', '' )
            else: return device_id
        except Exception:
            pass
        try:
            import netifaces
            valid_ifaces = list( filter(lambda iface: iface.lower( ) != 'lo',
                                        netifaces.interfaces( ) ) )
            if len( valid_ifaces ) == 0: return None
            valid_iface = max( valid_ifaces )
            iface_tuples =  netifaces.ifaddresses( valid_iface )[ netifaces.AF_LINK ]
            if len( iface_tuples ) == 0: return None
            hwaddr = max( iface_tuples )[ 'addr' ].upper( )
            if replace_colons:
                return hwaddr.replace(':', '')
            else: return hwaddr
        except Exception:
            return None

    if not useMobileclient:
        if device_id is None: device_id = return_deviceid( replace_colons = False )
        assert( device_id is not None ), "error, could not determine the local MAC id"
        mmg = gmusicapi.Musicmanager(
            debug_logging = False, verify_ssl = verify )
        credentials = core.oauthGetOauth2ClientGoogleCredentials( )
        if credentials is None:
            raise ValueError( "Error, do not have Google Music credentials." )
        mmg.login( oauth_credentials = credentials, uploader_id = device_id )
        mmg.error_device_ids = { }
    else:
        if device_id is None: device_id = return_deviceid( )
        assert( device_id is not None ), "error, could not determine the local MAC id"
        mmg = gmusicapi.Mobileclient(
            debug_logging = False, verify_ssl = verify )
        credentials = oauth_get_google_credentials( )
        if credentials is None:
            raise ValueError( "Error, do not have GMusicAPI Mobileclient credentials." )
        try:
            mmg.oauth_login( oauth_credentials = credentials, device_id = device_id )
            mmg.error_device_ids = { }
        except gmusicapi.exceptions.InvalidDeviceId as exc: # tack on some error messages
            mmg.error_device_ids = set( exc.valid_device_ids )
    return mmg

"""
Took stuff from http://unofficial-google-music-api.readthedocs.io/en/latest/usage.html#usage                                                                    
"""
def save_gmusic_creds( email, password ):
    """
    Pushes one's Google account email and password into the ``gmusic`` configuration stored in the SQLite3_ configuration database.
    
    :param str email: Google account email address.
    :param str password: Google account password.
    """
    query = session.query( PlexConfig ).filter( PlexConfig.service == 'gmusic' )
    val = query.first( )
    if val is not None:
        session.delete( val )
        session.commit( )
    newval = PlexConfig(
        service = 'gmusic',
        data = { 'email' : email.strip( ),
                 'password' : password.strip( ) } )
    session.add( newval )
    session.commit( )

def get_gmusic_all_songs( verify = True, device_id = None ):
    """
    Returns a :py:class:`dict` of all songs stored on one's `Google Play Music`_ account. Each key is an unique song ID, and each value is summary information for that song. Example element output looks like,

    .. code-block:: python

        {'kind': 'sj#track',
         'id': 'fe65be9b-5e0d-39f8-a104-34579cac7d25',
         'clientId': '0xjqU3q/jCIkKK+42LXx+A',
         'creationTimestamp': '1312046208050197',
         'lastModifiedTimestamp': '1385273200005040',
         'recentTimestamp': '1312050096197000',
         'deleted': False,
         'title': "Why Can't There Be Love (Pilooski Edit)",
         'artist': 'Pilooski',
         'composer': 'Hermon Weems',
         'album': 'Saint-Germain-Des-Pres Cafe (The Blue Edition)',
         'albumArtist': 'Saint-Germain-Des-Prés Café (Selected and mixed by Mr Scruff)',
         'year': 2010,
         'comment': '',
         'trackNumber': 15,
         'genre': 'Dance & DJ',
         'durationMillis': '180720',
         'beatsPerMinute': 0,
         'albumArtRef': [{'kind': 'sj#imageRef',
           'url': 'http://lh5.ggpht.com/Czw3aqGNeQdsXMy9EnaAoC92F3WZHvKO2iqRGyZouUodlJqTP3anpjxb7qdLTdsPae1evBD0'}],
         'playCount': 0,
         'totalTrackCount': 0,
         'discNumber': 0,
         'totalDiscCount': 0,
         'rating': '0',
         'estimatedSize': '5782883',
         'storeId': 'Tovfqdqypwu27btjcetswr464qe',
         'albumId': 'B4utisa64lnb5bja5hg3ym5efrm',
         'artistId': ['A5yefhy34gybvo5okv4hfychfia'],
         'nid': 'Tovfqdqypwu27btjcetswr464qe'}

    If cannot access the account, returns ``None``.
    
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :param str device_id: optional argument. If defined, then attempt to use this MAC ID to register the music manager.

    :raise ValueError: if cannot find and use the correct device ID.
    """
    with gmusicmanager( useMobileclient = True, verify = verify,
                        device_id = device_id ) as mmg:
        if len( mmg.error_device_ids ) != 0: # error condition
            raise ValueError("Error, could not return a collection of songs from the Google Play Music account. Please explicitly specify one of the device_ids = %s." % mmg.error_device_ids )
        allSongs = mmg.get_all_songs( )        
        allSongsDict = dict( map(lambda song: (
            song.get('id'),
            {
                "album":       song.get('album').encode('utf-8'),
                "artist":      song.get('artist').encode('utf-8'),
                "name":        song.get('title').encode('utf-8'),
                "trackNumber": song.get('trackNumber'),
                "playCount":   song.get('playCount')
            } ), allSongs ) )
        return allSongsDict

def upload_to_gmusic(filenames, verify = True):
    """
    Uploads a collection of music files to the Google Play Music account.
    
    :param list filenames: a list of candidate files to upload.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    """
    filenames_valid = list(filter(lambda fname: os.path.isfile(fname), set(filenames)))
    if len(filenames_valid) != 0:
        with gmusicmanager( useMobileclient = False, verify = verify ) as mmg:
            if len( mmg.error_device_ids ) != 0: gmusicmanager_fixlogin( mmg )
            mmg.upload(filenames_valid)

def download_best_song( artist_name, song_name, youtube = None,
                        verify = True):
    """
    If successful, downloads the most likely YouTube_ clip into an M4A_ file, whose name is ``"artist_name"."song_name".m4a``. Uses the LastFM_ API functionality, through :py:class:`HowdyLastFM <howdy.music.music.HowdyLastFM>`, to get the music metadata.

    :param str artist_name: the artist name.
    :param str song_name: name of the song.
    :param Resource youtube: optional aegument, a `googleapiclient Resource`_ object that allows for the access to the `YouTube Google API`_. If not defined, then instantiated with :py:meth:`get_youtube_service <howdy.music.music.get_youtube_service>`.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :returns: if successful, the file name of the downloaded M4A_ song (``"artist_name"."song_name".m4a``). If cannot find the song metadata, or cannot find YouTube_ clips for this song, then returns ``None``.
    """
    if youtube is not None:
        youtube = get_youtube_service( verify = verify )
    plastm = HowdyLastFM( verify = verify )
    data_dict, status = plastfm.get_music_metadata(
        song_name = song_name,
        artist_name = artist_name, all_data = True )
    if status != 'SUCCESS':
        return None
    artist_name = data_dict[ 'artist' ]
    song_name = data_dict[ 'song' ]
    name = '%s %s' % ( artist_name, song_name )
    videos = youtube_search( youtube, name, max_results = 10 )
    if len( videos ) == 0:
        return None
    _, youtubeURL = videos[0]
    filename = '%s.%s.m4a' % ( artist_name, '; '.join( map(lambda tok: tok.strip( ), song_name.split('/') ) ) )
    get_youtube_file( youtubeURL, filename )
    fill_m4a_metadata( filename, data_dict )
    return filename

            
def get_youtube_service( verify = True ):
    """
    Gets the `YouTube Google API`_ service from the `Google OAuth2`_ credentials stored in the SQLite3_ configuration database.

    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :returns: a `googleapiclient Resource`_ object that allows for the access to the `YouTube Google API`_.

    .. _`YouTube Google API`: https://developers.google.com/youtube/v3
    .. _`googleapiclient Resource`: http://googleapis.github.io/google-api-python-client/docs/epy/googleapiclient.discovery.Resource-class.html
    """
    # credentials = core.oauthGetGoogleCredentials( verify = verify )
    # http = httplib2.Http( disable_ssl_certificate_validation = not verify )
    credentials = core.oauthGetOauth2ClientGoogleCredentials( )
    if credentials is None:
        raise ValueError( "Error, could not build the YouTube service." )
    http_auth = credentials.authorize( httplib2.Http(
        disable_ssl_certificate_validation = not verify ) )
    youtube = build(  "youtube", "v3", http = http_auth,
                      cache_discovery = False )
    #youtube = build( "youtube", "v3", credentials = credentials,
    #                 cache_discovery = False ) 
    return youtube

def get_youtube_file( youtube_URL, outputfile, use_aria2c = True ):
    """
    Uses youtube-dl_ programmatically to download into an M4A_ file.

    :param str youtube_URL: a valid YouTube_ URL for the song clip.
    :param str outputfile: the M4A_ music file name.
    :param bool use_aria2c: use the aria2c_ downloader. *Implicitly* requires that aria2c_ exists on the server.

    .. _youtube-dl: https://ytdl-org.github.io/youtube-dl/index.html
    .. _YouTube: https://www.youtube.com
    .. _aria2c: https://aria2.github.io
    """
    import yt_dlp
    assert( os.path.basename( outputfile ).lower( ).endswith( '.m4a' ) )
    logging.info( 'URL: %s, outputfile: %s.' % (
        youtube_URL, outputfile ) )
    try:
        ydl_opts = {
            'format' : '140',
            'outtmpl' : outputfile }

        #
        ## these options come from https://www.reddit.com/r/youtubedl/comments/fx2ifj/comment/fms2ej6/?utm_source=share&utm_medium=web2x&context=3
        ## because come on why is youtube-dl so achingly slow?
        ## only if aria2c exists on this server
        ## also to get INFO logging level: https://aria2.github.io/manual/en/html/aria2c.html#cmdoption-log-level
        aria2c_exec = which('aria2c')
        if aria2c_exec is not None and use_aria2c:
            ydl_opts['external-downloader'] = 'aria2c'
            ydl_opts['external-downloader-args'] = "-j 16 -x 16 -s 16 -k 1M --log-level=info"
        with yt_dlp.YoutubeDL( ydl_opts ) as ydl:
            ydl.download([ youtube_URL ])
    except yt_dlp.DownloadError: # could not download the file to M4A format
        ffmpeg_exec = which( 'ffmpeg' )
        if ffmpeg_exec is None:
            raise ValueError("Error, no FFMPEG executable found." )
        with yt_dlp.YoutubeDL( ) as ydl:
            info = ydl.extract_info( youtube_URL, download = False )
            extension = info[ 'ext' ]
        ydl_opts = { 'outtmpl' : '%s.%s' % ( str( uuid.uuid4( ) ), extension ) }
        tmpfile = ydl_opts[ 'outtmpl' ]
        with yt_dlp.YoutubeDL( ydl_opts ) as ydl:
            ydl.download( [ youtube_URL ] )
            stdout_val = subprocess.check_output(
                [ ffmpeg_exec, '-i', tmpfile, '-vn',
                  '-strict', 'experimental', '-acodec',
                  'aac', '-ab', '128k', "file:%s" % outputfile ],
                stderr = subprocess.STDOUT )
            os.chmod( outputfile, 0o644 )
            os.remove( tmpfile )        
            
def youtube_search(youtube, query, max_results = 10):
    """
    Performs a string query to search through YouTube_ clips, and returns list of valid YouTube_ URLs.

    :param Resource youtube: a `googleapiclient Resource`_ object that allows for the access to the `YouTube Google API`_.
    :param str query: the string on which to search.
    :param int max_results: optional argument, the maximum number of YouTube_ clips to return. Must be :math:`\ge 1`. Default is ``10``.

    :returns: a :py:class:`list` of YouTube_ URLs of clips that satisfy the query.
    :rtype: list
    """
    assert( max_results >= 5 )
    search_response = youtube.search().list(
        q=query,
        order="relevance",
        type="video",
        part="id,snippet",
        #part="id",
        maxResults=50).execute()

    search_videos = list( map(lambda search_result:
                              search_result['id']['videoId'],
                              filter(lambda search_result: 'videoId' in search_result['id'],
                                     search_response.get('items', []) ) ) )
    # Merge video ids
    video_ids = ",".join(search_videos)
    if len( search_videos ) == 0:
        return

    # Call the videos.list method to retrieve details for each video.
    video_response = youtube.videos().list(
        id=video_ids,
        part='snippet, recordingDetails, contentDetails'
    ).execute()

    videos = []
    # Add each result to the list, and then display the list of matching videos.
    for video_result in video_response.get("items", [])[:max_results]:
        duration_string = video_result['contentDetails']['duration']
        try:
            logging.debug( 'YOUTUBE CLIP duration_string = %s.' % duration_string )
            dt_duration = parse_youtube_date( duration_string )
            dstring = format_youtube_date( dt_duration )
            videos.append(("%s (%s)" % ( video_result["snippet"]["title"], dstring ),
                           urljoin("https://youtu.be", video_result['id'] ) ) )
        except Exception as e:
            print( e )
            pass
    return videos

def push_spotify_song_id_to_file( spotify_id, filename ):
    _error_expired_token = 'The access token expired'
    if spotify_id.strip( ) == _error_expired_token:
        logging.debug( 'ACTUAL MESSAGE IS EXPIRED TOKEN. DOING NOTHING.' )
        return

    #
    ## final comments list has no SPOTIFY: things in it
    song_metadata_dict = get_m4a_metadata( filename )
    if 'comment' not in song_metadata_dict:
        comments = list(filter(lambda cmnt: not cmnt.startswith('SPOTIFY: '), [ ] ) )
    else:
        comments = list(filter(lambda cmnt: not cmnt.startswith('SPOTIFY: '), song_metadata_dict[ 'comment' ] ) )

    comments.append( 'SPOTIFY: %s' % spotify_id )

    mp4tags = mutagen.mp4.MP4( filename )
    mp4tags[ '\xa9cmt' ] = comments
    mp4tags.save( )
    
def get_spotify_song_id_filename( filename ):
    song_metadata_dict = get_m4a_metadata( filename )
    if 'comment' not in song_metadata_dict:
        logging.debug( 'ERROR, NO COMMENTS IN %s.' % os.path.abspath( filename ) )
        return None
    comments = list(filter(lambda cmnt: cmnt.startswith('SPOTIFY: '), song_metadata_dict[ 'comment' ] ) )
    if len( comments ) != 1:
        logging.debug( 'ERROR, NOT JUST ONE SPOTIFY: ENTRY IN COMMENTS IN %s.' % os.path.abspath( filename ) )
        return None

    spotify_id = re.sub('^SPOTIFY:', '', comments[0] ).strip( )
    return spotify_id
    

def get_spotify_song_id( spotify_access_token, song_metadata_dict, song_limit = 5, market = 'us' ):
    assert( song_limit > 0 )
    #
    def _get_track_query_string( song_metadata_dict ):
        assert( 'song' in song_metadata_dict )
        return 'track:%s' % song_metadata_dict[ 'song' ]
    def _get_artist_query_string( song_metadata_dict ):
        assert( 'artist' in song_metadata_dict )
        return 'artist:%s' % song_metadata_dict[ 'artist' ]
    def _get_year_query_string( song_metadata_dict ):
        assert( 'date' in song_metadata_dict )
        return 'year:%d' % song_metadata_dict[ 'date' ].year
    def _get_album_query_string( song_metadata_dict ):
        assert( 'album' in song_metadata_dict )
        return 'album:%s' % song_metadata_dict[ 'album' ]

    #
    ## now create a dictionary of song metadata keys (4) to above methods
    query_dict = {
        'song'   : _get_track_query_string,
        'artist' : _get_artist_query_string,
        'date'   : _get_year_query_string,
        'album'  : _get_album_query_string }
    
    def _get_info_track_elem( track_elem ):
        track_album = track_elem['album']['name']
        track_date = datetime.datetime.strptime( track_elem[ 'album' ][ 'release_date' ], '%Y-%m-%d' ).date( )
        track_name = track_elem[ 'name' ]
        track_artist = track_elem[ 'artists' ][ 0 ][ 'name' ]
        return {
            'song'   : track_name,
            'artist' : track_artist,
            'date'   : track_date,
            'album'  : track_album }
    
    def _get_spotify_query( song_dict, query_keys ):
        spotify_query = ' '.join(map(lambda key: query_dict[ key ]( song_dict ), query_keys ) )
        logging.debug( 'SPOTIFY QUERY FOR SONG = %s.' % spotify_query )
        return spotify_query

    def _get_comparative_score( track_elem ):
        query_keys = sorted(set( song_metadata_dict ) & set( query_dict ) )
        initial_query = _get_spotify_query( song_metadata_dict, query_keys )
        track_query = _get_spotify_query(
            _get_info_track_elem( track_elem ),
            query_keys )
        return partial_ratio( initial_query, track_query )
    #
    ## now essential keys in song_metadata_dict
    essential_keys = set([ 'song', 'artist' ] )
    assert( len( essential_keys - set( song_metadata_dict ) ) == 0 ) # must have AT LEAST these two
    #
    ## now the final query
    query_keys = sorted(set( song_metadata_dict ) & set( query_dict ) )
    spotify_query = _get_spotify_query( song_metadata_dict, query_keys )
    logging.debug( 'SPOTIFY QUERY FOR SONG = %s.' % spotify_query )
    #
    ## now get the track query
    resp_track = requests.get(
        "https://api.spotify.com/v1/search",
        headers = { 'Authorization' : 'Bearer %s' % spotify_access_token },
        params = {
            'q' : spotify_query,
            'type' : 'track',
            'market' : market,
            'limit'  : song_limit } )
    #
    ## check that we have a good response
    if not resp_track.ok:
        error_json = resp_track.json( )
        return error_json[ 'error' ][ 'message' ]
    #
    ## now get the best track
    data_track = resp_track.json( )
    best_elem = max( data_track['tracks']['items'], key = lambda track_elem: _get_comparative_score( track_elem ) )
    logging.debug( 'BEST SCORE TRACK_ELEM = %0.1f' % _get_comparative_score( best_elem ) )
    return best_elem['uri']
    
def plexapi_music_playlist_info( plex_playlist ):
    """
    This creates a :py:class:`Pandas DataFrame <pandas.DataFrame>` out of the :py:class:`PlexAPI Playlist <plexapi.playlist.Playlist>`. This DataFrame has the following columns:

    * ``filename``
    * ``added date``
    * ``song name``
    * ``artist``
    * ``track number``
    * ``album``
    * ``album number of tracks``
    * ``album year``

    This DataFrame is ordered by ``added date``.

    :param plex_playist: the :py:class:`PlexAPI Playlist <plexapi.playlist.Playlist>`, which must be an audio playlist.
    :returns: a :py:class:`Pandas DataFrame <pandas.DataFrame>` of useful track information for the playlist.
    :rtype: :py:class:`Pandas DataFrame <pandas.DataFrame>`
    """
    assert( plex_playlist.playlistType == 'audio' )
    time0 = time.perf_counter( )
    #
    def _get_info_playlist_item( item ):
        try:
            info = {
                'filename'               : max(item._data.iter('Part')).attrib['file'],
                'added date'             : item.addedAt,
                'song name'              : item.title,
                'artist'                 : item.artist( ).title,
                'track number'           : item.trackNumber,
                'album'                  : item.album( ).title,
                'album number of tracks' : max(alb.tracks(), key = lambda track: track.trackNumber ).trackNumber, # not perfect I know
                'album year'             : alb.year }
            if not os.path.isfile( info[ 'filename' ] )
                raise ValueError("ERROR, %s is not a valid file" % info[ 'filename' ] )
            return info
        except Exception as e:
            logging.error( "ERROR ON ITEM, REASON = %s." % str( e ) )
            return None
    #
    all_valid_tracks = sorted(
        filter( None, map( _get_info_playlist_item, plex_playlist.items( ) ),
        key = lambda entry: entry[ 'added date' ] ) )
    logging.info( 'FOUND %d / %d VALID TRACKS IN PLAYLIST = %s IN %0.3f SECONDS.' % (
        len( all_valid_tracks ), len( plex_playlist.items( ) ), time.perf_counter( ) - time0 ) )
    return all_valid_tracks
    


class HowdyLastFM( object ):
    """
    This object uses the LastFM_ API, through the higher level :py:mod:`musicbrainzngs` Python module, to get information on songs, albums, and artists. Where possible, this extracts additional song metadata using the MusicBrainz_ API.
    
    :param dict data: optional argument, containg the LastFM_ API data: ``api_key``, ``api_secret``, ``application_name``, and ``username``. See :numref:`The Gracenote and LastFM APIs` to understand how to set up the LastFM_ API credentials. If not given, then gets the LastFM_ API data from :py:meth:`HowdyLastFM.get_lastfm_credentials <howdy.music.music.HowdyLastFM.get_lastfm_credentials>`.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :var str api_key: the LastFM_ API key.
    :var str api_secret: the LastFM_ API secret.
    :var str application_name: the LastFM_ application name.
    :var str username: the LastFM_ API user name.
    :var str endpoint: the LastFM_ endpoint, here ``http://ws.audioscrobbler.com/2.0``.
    :var bool verify: whether to verify SSL connections.

    .. _LastFM: https://www.last.fm/api
    .. _MusicBrainz: https://musicbrainz.org/doc/Development/XML_Web_Service/Version_2
    """

    @classmethod
    def get_mb_album_year( cls, year_string ):
        """
        Returns a year of release given a MusicBrainz_ style date string, can be either of the form "2000-12-23" (YYYY-MM-DD)" or just four-digit year.

        :param str year_string: a MusicBrainz_ style date string, can be either of the form "2000-12-23" (YYYY-MM-DD) or just four-digit year.
        :return: the year corresponding to the release date. If date string is invalid, then returns ``None``.
        :rtype: int
        """
        try:
            album_year = datetime.datetime.strptime(
                year_string, '%Y-%m-%d' ).year
            return album_year
        except: pass

        try:
            album_year = datetime.datetime.strptime(
                year_string, '%Y' ).year
            return album_year
        except Exception as e:
            return None
        
    @classmethod
    def push_lastfm_credentials( cls, api_data ):
        """
        Pushes the LastFM_ API configuration into the SQLite3_ configuration database.
        
        :param dict api_data: the dictionary containing the LastFM_ API data: ``api_key``, ``api_secret``, ``application_name``, and ``username``.
        """
        assert( len(set(api_data) - set([ 'api_key', 'api_secret', 'application_name',
                                          'username' ]) ) == 0 )
        query = session.query( PlexConfig ).filter(
            PlexConfig.service == 'lastfm' )
        val = query.first( )
        if val is not None:
            session.delete( val )
            session.commit( )
        session.add(
            PlexConfig( service = 'lastfm',
                        data = { key : api_data[key] for key in
                                 ( 'api_key', 'api_secret', 'application_name', 'username' ) } ) )
        session.commit( )
    
    @classmethod
    def get_lastfm_credentials( cls ):
        """
        :returns: a :py:class:`dict` of LastFM_ API configuration information from the SQLite3_ configuration database: ``api_key``, ``api_secret``, ``application_name``, and ``username``.
        :rtype: dict
        
        :raise ValueError: if LastFM_ API credentials could not be found.
        """
        query = session.query( PlexConfig ).filter(
            PlexConfig.service == 'lastfm' )
        val = query.first( )
        if val is None:
            raise ValueError("ERROR, LASTFM CREDENTIALS NOT FOUND" )
        data = val.data
        return { key : data[key] for key in
                 ( 'api_key', 'api_secret', 'application_name', 'username' ) }
        
    @classmethod
    def get_album_url( cls, album_url_entries ):
        """
        Returns the album URL of the largest album image provided.
        
        :param list album_url_entries: a :py:class:`list` of album URL information. Each element is a :py:class:`dict` with two keys: `#text` is the URL, and `size` is a qualifier on the image size -- can be one of ``mega``, ``extralarge``, ``large``, ``medium``, ``small``, or `""` (no size given).
        
        :returns: images sizes are ordered this way -- ``mega``, ``extralarge``, ``large``, ``medium``, ``small``, and `""`. Returns the URL for the largest sized album image in this collection.
        
        :rtype: str
        """
        sorting_list_size = {            
            'mega' : 0, 'extralarge' : 1,
            'large' : 2, 'medium' : 3,
            'small' : 4, '' : 5 }
        sorted_entries = sorted(
            filter(lambda entry: 'size' in entry and
                   '#text' in entry and
                   entry['size'] in sorting_list_size, album_url_entries ),
            key = lambda entry: sorting_list_size[ entry['size'] ] )
        if len( sorted_entries ) == 0: return None
        logging.debug( 'entries: %s' % list(
            map(lambda entry: ( entry['#text'], entry['size'] ), sorted_entries ) ) )
        logging.debug( 'chosen entry: %s, %s' % ( sorted_entries[ 0 ][ '#text' ],
                                                  sorted_entries[ 0 ][ 'size' ] ) )
        return sorted_entries[ 0 ][ '#text' ]
    
    def __init__( self, data = None, verify = True ):
        if data is None: data = HowdyLastFM.get_lastfm_credentials( )
        self.api_key = data[ 'api_key' ]
        self.api_secret = data[ 'api_secret' ]
        self.application_name = data[ 'application_name' ]
        self.username = data[ 'username' ]
        self.endpoint = 'http://ws.audioscrobbler.com/2.0'
        self.verify = verify

    def get_collection_album_info( self, album_name ):
        """
        :param str album_name: the name of a compilation album (consisting of multiple artists).
        :returns: a two-element :py:class:`tuple`, whose first element is a :py:class:`dict` of summary information on tracks for this compilation album, and whose second element is the string ``"SUCCESS"``. This dictionary is a low level LastFM_ data structure. The example low level, nicely formatted JSON representation of this dictionary, for the compilation album, `The Politics of Photosynthesis`_, is located in :download:`lastfm_collection_data.json </_static/lastfm_collection_data.json>`. If unsuccessful, then returns a :py:class:`tuple` of format :py:meth:`return_error_raw <howdy.core.return_error_raw>`.
        
        :rtype: dict

        .. _`The Politics of Photosynthesis`: https://www.amazon.com/Politics-Photosynthesis-Tribute-Stereolab/dp/B0012BIPCG
        """
        response = requests.get( self.endpoint,
                                 params = { 'method' : 'album.search',
                                            'album' : album_name,
                                            'api_key' : self.api_key,
                                            'format' : 'json',
                                            'lang' : 'en' },
                                 verify = self.verify )
        data = response.json( )
        if 'error' in data:
            return return_error_raw(
                "ERROR: %s" % data['message'] )
        return data, 'SUCCESS'
        
    def get_album_info( self, artist_name, album_name ):
        """
        :param str artist_name: the artist name.
        :param str album_name: the studio album.
        
        :returns: a two-element :py:class:`tuple`, whose first element is a :py:class:`dict` of LastFM_ API low level information on the album, and whose second element is the string ``"SUCCESS"``. For example, for `Moon Safari`_ from Air_, we have, complicated JSON structure stored in :download:`HowdyLastFM get_album_info </_static/howdylastfm_getalbuminfo.json>`. If unsuccessful, then returns a :py:class:`tuple` of format :py:meth:`return_error_raw <howdy.core.return_error_raw>`.
        
        :rtype: tuple
        """
        response = requests.get(
            self.endpoint,
            params = { 'method' : 'album.getinfo',
                       'album' : album_name,
                       'artist' : artist_name,
                       'api_key' : self.api_key,
                       'format' : 'json',
                       'lang' : 'en' },
            verify = self.verify )
        data = response.json( )
        if 'error' in data:
            return return_error_raw( "ERROR: %s" % data['message'] )
        return data['album'], 'SUCCESS'
        
    def get_album_image( self, artist_name, album_name ):
        """
        :param str artist_name: the artist name.
        :param str album_name: album_name.
        :returns: If successful, downloads the album image into a PNG_ file named "artist_name.album_name.png", and returns a two-element :py:class:`tuple`, whose first element is the PNG_ filename, and whose second element is the string ``"SUCCESS"``. If unsuccessful, then returns a :py:class:`tuple` of format :py:meth:`return_error_raw <howdy.core.return_error_raw>`.
        :rtype: tuple
        """
        album, status = self.get_album_info( artist_name, album_name )
        if status != 'SUCCESS':
            return return_error_raw( status )
        if 'image' not in album:
            error_message = 'Could not find album art for album = %s for artist = %s.' % (
                album_name, artist_name )
            return return_error_raw( error_message )
        album_url = HowdyLastFM.get_album_url( album[ 'image' ] )
        if album_url is None or not validators.url( album_url ):
            error_message = "Could not find album art for album = %s for artist = %s, because of invalid album URL" % (
                album_name, artist_name )
            return return_error_raw( error_message )
        filename = '%s.%s.png' % ( artist_name, album_name.replace('/', '-' ) )

        img = Image.open( io.BytesIO( requests.get( album_url, verify = self.verify ).content ) )
        img.save( filename, format = 'png' )
        os.chmod( filename, 0o644 )
        return filename, 'SUCCESS'
        
    def get_song_listing( self, artist_name, album_name ):
        """
        :param str artist_name: the artist name.
        :param str album_name: album_name.
        :returns: If successful, returns a two-element :py:class:`tuple`, whose first element is the list of songs ordered by track number, and whose second element is the string ``"SUCCESS"``. Each element in this list is a :py:class:`tuple` of song number and track number. For example, for `Moon Safari`_ by Air_,

        .. code-block:: python

            [("La Femme d'Argent", 1),
             ('Sexy Boy', 2),
             ('All I Need', 3),
             ('Kelly Watch the Stars', 4),
             ('Talisman', 5),
             ('Remember', 6),
             ('You Make It Easy', 7),
             ('Ce Matin-Là', 8),
             ('New Star in the Sky (Chanson Pour Solal)', 9),
             ('Le Voyage De Pénélope', 10)]
        
        If unsuccessful, then returns a :py:class:`tuple` of format :py:meth:`return_error_raw <howdy.core.return_error_raw>`.
        
        :rtype: tuple
        """
        album, status = self.get_album_info( artist_name, album_name )
        if status != 'SUCCESS': return return_error_raw( status )
        track_listing = sorted(map(lambda track: ( titlecase.titlecase( track['name'] ),
                                                   int( track[ '@attr' ][ 'rank' ] ) ),
                                   album['tracks']['track'] ), key = lambda tup: tup[1] )
        return track_listing, 'SUCCESS'

    #
    ## note that lastfm does not provide a releasedate at all.
    ## see, e.g., https://github.com/pylast/pylast/issues/177.
    ## also, https://github.com/feross/last-fm/issues/2.
    ## documentation found here, https://www.last.fm/api/show/album.getInfo, is incorrect.
    def get_music_metadata( self, song_name, artist_name, all_data = False ):
        """
        Uses the MusicBrainz_ API to fill out as much metadata as possible for a given song. Before running this method, one should first set the MusicBrainz_ API header data with :py:meth:`MusicInfo.get_set_musicbrainz_useragent <howdy.music.music.MusicInfo.get_set_musicbrainz_useragent>`.
        
        :param str song_name: name of the song.
        :param str artist_name: name of the artist.
        :param bool all_data: optional argument. If ``False``, then perform a cursory search for metadata on the selected song. If ``True``, then perform a more careful search. Default is ``False``. Running with ``True`` can work if running with ``False`` does not produce a result.
        :returns: if successful, returns a two element :py:class:`tuple`. First element is a :py:class:`dict` of information on the song, and the second element is the string ``"SUCCESS"``. For example, for the Air_ song `Kelly Watch the Stars`_ in `Moon Safari`_. the closest match is ``Kelly, Watch the Stars!``.
        
          .. code-block:: python

             {'album': 'Moon Safari',
              'artist': 'Air',
              'year': 1998,
              'tracknumber': 4,
              'total tracks': 10,
              'song': 'Kelly, Watch the Stars!',
              'duration': 225.746,
              'album url': 
                 'https://lastfm.freetls.fastly.net/i/u/300x300/016....png'}

          If unsuccessful, then returns a :py:class:`tuple` of format :py:meth:`return_error_raw <howdy.core.return_error_raw>`.

        :rtype: tuple

        .. note::
        
           LastFM_ does not provide a release date at all. Furthermore, LastFM_ documentation shown here (https://www.last.fm/api/show/album.getInfo) is incorrect. See, e.g, :issue:`pylast/pylast#177` and :issue:`feross/last-fm#2`.

        .. _`Kelly Watch the Stars`: https://en.wikipedia.org/wiki/Kelly_Watch_the_Stars
        """
        response = requests.get( self.endpoint,
                                 params = { 'method' : 'track.getinfo',
                                            'artist' : artist_name,
                                            'track' : titlecase.titlecase( song_name ),
                                            'autocorrect' : 1,
                                            'api_key' : self.api_key,
                                            'format' : 'json',
                                            'lang' : 'en' },
                                 verify = self.verify )
        data = response.json( )
        if 'error' in data:
            return return_error_raw( "ERROR: %s" % data[ 'message' ] )
        track = data['track']
        logging.debug( track )
        #
        ## now see if we have an album with mbid, fill out ALL the metadata
        if 'mbid' in track[ 'album' ]:
            music_metadata = { }
            album_mbid = track[ 'album' ][ 'mbid' ]
            data = musicbrainzngs.get_release_by_id(
                album_mbid, includes = [ 'recordings', 'artists' ] )['release']
            music_metadata[ 'album' ] = data[ 'title' ]
            music_metadata[ 'artist' ] = data[ 'artist-credit' ][ 0 ][ 'artist' ][ 'name' ]
            if 'date' in data:
                album_year = HowdyLastFM.get_mb_album_year( data['date'] )
                if album_year is not None:
                    music_metadata[ 'year' ] = album_year
            #
            ## get position of track
            if '@attr' in track[ 'album' ] and 'position' in track[ 'album' ]['@attr']:
                tracknumber = int( track[ 'album' ][ '@attr' ][ 'position' ] )
                music_metadata[ 'tracknumber' ] = tracknumber
            else: tracknumber = None
            #
            ## now look for the track list
            medium_list = data['medium-list'][0]
            music_metadata[ 'total tracks' ] = medium_list[ 'track-count' ]
            track_list = medium_list['track-list']
            #
            ## now find tracknumber here
            if tracknumber is not None:
                act_track = list(filter(lambda trck: int( trck['position'] ) == tracknumber,
                                        track_list))
                if len( act_track ) == 0:
                    music_metadata[ 'duration' ] = float( track['duration'] ) * 1e-3
                    music_metadata[ 'song' ] = titlecase.titlecase( track[ 'name' ] )
                else:
                    act_track = act_track[ 0 ]
                    music_metadata[ 'song' ] = titlecase.titlecase( act_track[ 'recording' ][ 'title' ] )
                    music_metadata[ 'duration' ] = float( act_track[ 'recording' ][ 'length' ] ) * 1e-3
            else:
                music_metadata[ 'duration' ] = float( track['duration'] ) * 1e-3
                music_metadata[ 'song' ] = titlecase.titlecase( track[ 'name' ] )
                music_metadata[ 'tracknumber' ] = 1

            #
            ## if find the image
            if 'image' in track[ 'album' ]:
                album_url = HowdyLastFM.get_album_url( track[ 'album' ][ 'image' ] )
                if album_url is not None:
                    music_metadata[ 'album url' ] = album_url

            return music_metadata, 'SUCCESS'

        elif 'mbid' in track[ 'artist' ]:
            pass # not working now for reasons cannot debug
            music_metadata = { }
            artist_mbid = track[ 'artist' ][ 'mbid' ]
            mi = MusicInfo( artist_name, artist_mbid = artist_mbid )
            #
            ## now find song name in list of stuff
            alltracks = list(chain.from_iterable(map(lambda album: map(lambda trackno: (
                mi.alltrackdata[album]['tracks'][trackno][0], trackno, album ), mi.alltrackdata[album]['tracks'] ),
                                                     mi.alltrackdata.keys( ))))
            matches = list( filter( lambda tup: tup[0] == song_name, alltracks ) )
            if len( matches ) != 1: pass
            match = matches[ 0 ]
            trackno = match[ 1 ]
            album = match[ 2 ]
            music_metadata[ 'album' ] = album
            music_metadata[ 'artist' ] = mi.artist_name
            trackdata = mi.alltrackdata[ album ]
            music_metadata[ 'total tracks' ] = len( trackdata[ 'tracks' ] )
            music_metadata[ 'song' ] = match[ 0 ]
            music_metadata[ 'tracknumber' ] = trackno
            music_metadata[ 'year' ] = trackdata[ 'release-date' ].year
            music_metadata[ 'duration' ] = trackdata[ 'tracks' ][ trackno ][ 1 ]
            return music_metadata, 'SUCCESS'
            

        #
        ## alternate, could not get mbid stuff...
        if 'date' in track:
            album_year = HowdyLastFM.get_mb_album_year( track['date'] )
            music_metadata[ 'year' ] = album_year
        music_metadata = { 'artist' : track['artist']['name'],
                           'song' : titlecase.titlecase( track['name'] ),
                           'album' : track[ 'album' ][ 'title' ],
                           'duration' : float(track['duration']) * 1e-3 }
        if 'image' in track[ 'album' ]:
            album_url = HowdyLastFM.get_album_url( track[ 'album' ][ 'image' ] )
            if album_url is not None:
                music_metadata[ 'album url' ] = album_url
        if not all_data:
            return music_metadata, 'SUCCESS'
        #
        ## now if we want to get total number of tracks for this album, and track number for song
        track_listing, status = self.get_song_listing(
            artist_name = artist_name,
            album_name = track[ 'album' ][ 'title' ] )
        if track_listing is None:
            return music_metadata, 'SUCCESS'
        track_listing_dict = dict( track_listing )
        if titlecase.titlecase( song_name ) in track_listing_dict or song_name in track_listing_dict:
            music_metadata[ 'tracknumber' ] = track_listing_dict[
                titlecase.titlecase( song_name ) ]
            music_metadata[ 'total tracks' ] = len( track_listing_dict )
        else:
            music_metadata[ 'tracknumber' ] = 1
            music_metadata[ 'total tracks' ] = 1
        return music_metadata, 'SUCCESS'

    def get_music_metadatas_album( self, artist_name, album_name ):
        """
        :param str artist_name: the artist name.
        :param str album_name: the album name.
        :returns: a two-element :py:class:`tuple`, whose first element is a :py:class:`list` of summary information on tracks for this album, and whose second element is the string ``"SUCCESS"``. The elements in this list are ordered by first song track to last song track. An example first song for the `Moon Safari`_ album released by Air_ is,
        
          .. code-block:: python

              {'song': 'La Femme D’argent',
               'artist': 'Air',
               'tracknumber': 1,
               'total tracks': 10,
               'duration': 429.56,
               'album url': 
                  'https://lastfm.freetls.fastly.net/i/u/300x300/016b6....png',
               'album': 'Moon Safari',
               'year': 1998}

          If the album name has not been published by this artist, return a :py:class:`tuple` of format :py:meth:`return_error_raw <howdy.core.return_error_raw>`.

        :rtype: tuple
        """
        album, status = self.get_album_info( artist_name = artist_name,
                                             album_name = album_name )
        if status != 'SUCCESS':
            return return_error_raw( status )
        if len( album[ 'tracks' ][ 'track' ] ) == 0:
            return return_error_raw(
                "Error, could find no tracks for artist = %s, album = %s." % (
                    artist_name, album_name ) )
        if 'mbid' in album:
            album_mbid = album['mbid']
            data = musicbrainzngs.get_release_by_id(
                album_mbid, includes = [ 'recordings', 'artists' ] )['release']
            album_name = data['title']
            artist = data[ 'artist-credit' ][ 0 ][ 'artist' ][ 'name' ]
            if 'date' in data:
                album_year = HowdyLastFM.get_mb_album_year( data['date' ] )
            else: album_year is None
            #
            ## now look for the track list
            medium_list = data['medium-list'][0]
            total_tracks = medium_list[ 'track-count' ]
            track_list = medium_list['track-list']
            #
            ## image URL
            album_url = HowdyLastFM.get_album_url( album[ 'image' ] )
            #
            album_data_dict = sorted(map(lambda act_track:
                                         { 'song' : titlecase.titlecase( act_track[ 'recording' ][ 'title' ] ),
                                           'artist' : artist,
                                           'tracknumber' : int( act_track[ 'position' ] ),
                                           'total tracks' : total_tracks,
                                           'duration' : 1e-3 * float( act_track[ 'recording' ][ 'length' ] ),
                                           'album url' : album_url,
                                           'album' : album_name }, track_list ),
                                     key = lambda trck: trck['tracknumber'] )
            if album_year is not None:
                for datum in album_data_dict:
                    datum['year'] = album_year
            return album_data_dict, 'SUCCESS'
        #
        track_listing = sorted(map(lambda track: ( titlecase.titlecase( track['name'] ),
                                                   int( track[ '@attr' ][ 'rank' ] ),
                                                   float( track[ 'duration' ] ) ),
                                   album['tracks']['track'] ), key = lambda tup: tup[1] )
        album_data_dict = list( map(lambda title_num:
                                    { 'song' : titlecase.titlecase( title_num[ 0 ] ),
                                      'artist' : album[ 'artist' ],
                                      'tracknumber' : title_num[ 1 ],
                                      'total tracks' : len( track_listing ),
                                      'duration' : title_num[ 2 ],
                                      'album url' : HowdyLastFM.get_album_url( album[ 'image' ] ),
                                      'album' : album[ 'name' ] },
                                    track_listing ) )
        
        return album_data_dict, 'SUCCESS'
    
class HowdyMusic( object ):
    """
    This object uses the Gracenote_ API to get information on songs, albums, and artists. Uses :py:meth:`HowdyMusic.get_gracenote_credentials <howdy.music.music.HowdyMusic.get_gracenote_credentials>` to get the Gracenote_ API configuration data.

    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.

    :var str clientID: Gracenote_ API app client ID.
    :var str userID: Gracenote_ API app user ID.
    :var bool verify: whether to verify SSL connections.

    :raise ValueError: if cannot find the Gracenote_ API configuration information in the database.
    
    .. warning::

       As of October 20, 2019, this API may not be generally functional. A discussion is found on the `Pygn`_ Python Gracenote_ API implementation, :issue:`cweichen/pygn#14`.

    .. _Pygn: https://github.com/cweichen/pygn
    .. _Gracenote: https://developer.gracenote.com/web-api
    """
    
    @classmethod
    def push_gracenote_credentials( cls, client_ID, verify = True ):
        """
        Pushes the Gracenote_ API configuration into the SQLite3_ configuration database.
        
        :param str client_ID: the Gracenote_ API client ID.
        :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.

        :raise ValueError: if the ``client_ID`` is invalid, or cannot update the database.
        """
        try:
            userID = pygn.register( client_ID, verify = verify )
            query = session.query( PlexConfig ).filter(
                PlexConfig.service == 'gracenote' )
            val = query.first( )
            if val is not None:
                session.delete( val )
                session.commit( )
            session.add(
                PlexConfig( service = 'gracenote',
                            data = { 'clientID' : client_ID,
                                     'userID' : userID } ) )
            session.commit( )
        except:
            raise ValueError("Error, %s is invalid." % client_ID )

    @classmethod
    def get_gracenote_credentials( cls ):
        """
        :returns: a :py:class:`tuple` of Gracenote_ API clientID and userID from the SQLite3_ configuration database.

        :raise ValueError: if cannot find the Gracenote_API configuration information in the database.
        """
        query = session.query( PlexConfig ).filter(
            PlexConfig.service == 'gracenote' )
        val = query.first( )
        if val is None:
            raise ValueError("ERROR, GRACENOTE CREDENTIALS NOT FOUND" )
        data = val.data
        clientID = data['clientID']
        userID = data['userID']
        return clientID, userID
    
    def __init__( self, verify = True ):
        self.clientID, self.userID = HowdyMusic.get_gracenote_credentials( )
        self.verify = verify

    def get_album_image( self, artist_name, album_name ):
        """
        :param str artist_name: the artist name.
        :param str album_name: album_name.
        :returns: If successful, downloads the album image into a PNG_ file named "artist_name.album_name.png", and returns a two-element :py:class:`tuple`, whose first element is the PNG_ filename, and whose second element is the string ``"SUCCESS"``. If unsuccessful, then returns a :py:class:`tuple` of format :py:meth:`return_error_raw <howdy.core.return_error_raw>`.
        :rtype: tuple
        """
        metadata_album = pygn.search( clientID = self.clientID, userID = self.userID,
                                      album = album_name,
                                      artist = titlecase.titlecase( artist_name ),
                                      verify = self.verify )
        if 'album_art_url' not in metadata_album or len( metadata_album[ 'album_art_url' ].strip( ) ) == 0:
            return return_error_raw(
                'Could not find album = %s for artist = %s.' % (
                    album_name, titlecase.titlecase( artist_name ) ) )
        filename = '%s.%s.png' % ( artist_name, album_name.replace('/', '-') )
        img = Image.open( io.BytesIO( requests.get(
            metadata_album[ 'album_art_url' ], verify = self.verify ).content ) )
        img.save( filename, format = 'png' )
        os.chmod( filename, 0o644 )
        return filename, 'SUCCESS'
    
    def get_song_listing( self, artist_name, album_name ):
        """
        :param str artist_name: the artist name.
        :param str album_name: album_name.
        :returns: a :py:class:`list` of songs ordered by track number, and whose second element is the string ``"SUCCESS"``. Each element in this list is a :py:class:`tuple` of song number and track number. For example, for `Moon Safari`_ by Air_,
        
          .. code-block:: python

             [("La Femme d'Argent", 1),
              ('Sexy Boy', 2),
              ('All I Need', 3),
              ('Kelly Watch the Stars', 4),
              ('Talisman', 5),
              ('Remember', 6),
              ('You Make It Easy', 7),
              ('Ce Matin-Là', 8),
              ('New Star in the Sky (Chanson Pour Solal)', 9),
              ('Le Voyage De Pénélope', 10)]


        :rtype: list
        """
        metadata_album = pygn.search( clientID = self.clientID, userID = self.userID,
                                      album = album_name,
                                      artist = titlecase.titlecase( artist_name ), verify = self.verify )
        track_listing = sorted(map(lambda track: ( track['track_title'], int( track['track_number'])),
                                   metadata_album['tracks']), key = lambda title_num: title_num[1] )
        return track_listing

    def get_music_metadata_lowlevel( self, metadata_song, album_title = None ):
        """
        :param dict metadata_song: the low level :py:class:`dict` of Gracenote_API produced track information. Must have ``track__title``, ``track_number``, and ``album_artist_name`` keys.
        :param str album_title: optional argument, the candidate album from which the song came. If not defined, then ``ablum_title`` key must be set.
        :returns: if successful, returns a two element :py:class:`tuple`. First element is a :py:class:`dict` of information on the song, and the second element is the string ``"SUCCESS"``. This dictionary defines the following keys: ``song``, ``artist``, ``tracknumber``, ``total tracks``, ``year``, ``album url``, and ``album``. If unsuccessful, then returns a :py:class:`tuple` of format :py:meth:`return_error_raw <howdy.core.return_error_raw>`.

        :rtype: tuple
        """
        song_name = titlecase.titlecase( metadata_song[ 'track_title' ] )
        track_number = int( metadata_song[ 'track_number' ] )
        if album_title is None: album_title = metadata_song[ 'album_title' ]
        artist_name = metadata_song[ 'album_artist_name' ]
        metadata_album = pygn.search(clientID = self.clientID, userID = self.userID,
                                     artist = titlecase.titlecase( artist_name ),
                                     album = album_title, verify = self.verify )
        total_tracks = len( metadata_album['tracks'] )
        album_url = ''
        if 'album_art_url' in metadata_album:
            album_url = metadata_album[ 'album_art_url' ]
        try:
            album_year = int( metadata_album[ 'album_year' ] )
        except:
            album_year = 1900
        data_dict = { 'song' : titlecase.titlecase( song_name ),
                      'artist' : artist_name,
                      'tracknumber' : track_number,
                      'total tracks' : total_tracks,
                      'year' : album_year,
                      'album url' : album_url,
                      'album' : album_title }
        return data_dict, 'SUCCESS'

    def get_music_metadatas_album( self, artist_name, album_name ):
        """
        :param str artist_name: the artist name.
        :param str album_name: the album name.
        :returns: a two-element :py:class:`tuple`, whose first element is a :py:class:`list` of summary information on tracks for this album, and whose second element is the string ``"SUCCESS"``. The elements in this list are ordered by first song track to last song track. An example first song for the `Moon Safari`_ album released by Air_ is,

          .. code-block:: python

             {'song': 'La Femme D’argent',
              'artist': 'Air',
              'tracknumber': 1,
              'total tracks': 10,
              'duration': 429.56,
              'album url':
                 'https://lastfm.freetls.fastly.net/i/u/300x300/016b6....png',
              'album': 'Moon Safari',
              'year': 1998}

          If the album name has not been published by this artist, return a :py:class:`tuple` of format :py:meth:`return_error_raw <howdy.core.return_error_raw>`.

        :rtype: tuple
        """
        metadata_album = pygn.search( clientID = self.clientID, userID = self.userID,
                                      album = album_name,
                                      artist = artist_name, verify = self.verify )
        if titlecase.titlecase( album_name ) != \
           titlecase.titlecase( metadata_album[ 'album_title' ] ):
            return return_error_raw(
                'COULD NOT FIND ALBUM = %s FOR ARTIST = %s' % (
                    album_name, artist_name ) )
        album_url = ''
        if 'album_art_url' in metadata_album:
            album_url = metadata_album[ 'album_art_url' ]
        try:
            album_year = int( metadata_album[ 'album_year' ] )
        except:
            album_year = 1900
        total_tracks = len( metadata_album['tracks'] )
        track_listing = sorted(map(lambda track: ( track['track_title'],
                                                   int( track['track_number'] ) ),
                                   metadata_album['tracks']),
                               key = lambda title_num: title_num[1] )
        album_data_dict = sorted(map(lambda title_num:
                                     { 'song' : titlecase.titlecase( title_num[ 0 ] ),
                                       'artist' : artist_name,
                                       'tracknumber' : title_num[ 1 ],
                                       'total tracks' : total_tracks,
                                       'year' : album_year,
                                       'album url' : album_url,
                                       'album' : album_name },
                                     track_listing ), key = lambda tok: tok['tracknumber'])
        return album_data_dict, 'SUCCESS'

    def get_music_metadata( self, song_name, artist_name ):
        """
        :param str song_name: name of the song.
        :param str artist_name: name of the artist.
        :returns: if successful, returns a two element :py:class:`tuple`. First element is a :py:class:`dict` of information on the song, and the second element is the string ``"SUCCESS"``. For example, for the Air_ song `Kelly Watch the Stars`_ in `Moon Safari`_,

          .. code-block:: python
        
             {'album': 'Moon Safari',
              'artist': 'Air',
              'year': 1998,
              'tracknumber': 4,
              'total tracks': 10,
              'song': 'Kelly, Watch the Stars!',
              'duration': 225.746,
              'album url':
                 'https://lastfm.freetls.fastly.net/i/u/300x300/016b6b....png'}

          If unsuccessful, then returns a :py:class:`tuple` of format :py:meth:`return_error_raw <howdy.core.return_error_raw>`.

        :rtype: tuple
        """
        metadata_song = pygn.search( clientID = self.clientID, userID = self.userID,
                                     artist = artist_name,
                                     track = titlecase.titlecase( song_name ) )
        #
        ## now see if I can get the necessary metadata
        if 'album_artist_name' not in metadata_song:
            return return_error_raw( "ERROR, COULD NOT FIND ARTIST = %s" % artist_name )
        if metadata_song[ 'album_artist_name' ] != artist_name:
            return return_error_raw( "ERROR, COULD NOT FIND ARTIST = %s" % artist_name )
        #
        if 'track_title' not in metadata_song:
            return return_error_raw( 'ERROR, COULD NOT FIND SONG = %s FOR ARTIST = %s.' % (
                titlecase.titlecase( song_name ), artist_name ) )
        if titlecase.titlecase( metadata_song['track_title'] ) != \
           titlecase.titlecase( song_name ):
            return return_error_raw( "ERROR, COULD NOT FIND ARTIST = %s, SONG = %s." % (
                artist_name, titlecase.titlecase( song_name ) ) )
        #
        if 'album_title' not in metadata_song:
            return return_error_raw(
                "ERROR, COULD NOT FIND ALBUM FOR ARTIST = %s, SONG = %s." % (
                    artist_name, titlecase.titlecase( song_name ) ) )
        #
        if 'track_number' not in metadata_song:
            return return_error_raw(
                "ERROR, COULD NOT FIND TRACK NUMBER FOR ARTIST = %s, SONG = %s." % (
                    artist_name, titlecase.titlecase( song_name ) ) )
        #
        ##
        return self.get_music_metadata_lowlevel( metadata_song )
