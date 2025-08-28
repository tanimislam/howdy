import threading, requests, rapidfuzz, os, sys
import re, time, logging, validators
from tpb import CATEGORIES, ORDERS
from bs4 import BeautifulSoup
from urllib.parse import urljoin
#
from howdy.core import get_maximum_matchval, get_formatted_size, return_error_raw, core
from howdy.movie import movie

def get_movie_torrent_jackett( name, maxnum = 10, verify = True, doRaw = False, tmdb_id = None ):
    r"""
    Returns a :py:class:`tuple` of candidate movie Magnet links found using the main Jackett_ torrent searching service and the string ``"SUCCESS"``, if successful.

    :param str name: the movie string on which to search.
    :param int maxnum: optional argumeent, the maximum number of magnet links to return. Default is 10. Must be :math:`\ge 5`.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :param bool doRaw: optional argument. If ``True``, uses the IMDb_ information to search for the movie. Otherwise, uses the full string in ``name`` to search for the movie.
    :param int tmdb_id: optional argument. If defined, use this TMDB_ movie ID to search for magnet links.
    
    :returns: if successful, then returns a two member :py:class:`tuple` the first member is a :py:class:`list` of elements that match the searched movie, ordered from *most* seeds and leechers to least. The second element is the string ``"SUCCESS"``. The keys in each element of the list are,
       
      * ``title`` is the name of the candidate movie to download, and in parentheses the size of the candidate in MB or GB.
      * ``rawtitle`` is *only* the name of the candidate movie to download.
      * ``seeders`` is the number of seeds for this Magnet link.
      * ``leechers`` is the number of leeches for this Magnet link.
      * ``link`` is the Magnet URI link.
      * ``torrent_size`` is the size of this torrent in GB.
    
    If this is unsuccessful, then returns an error :py:class:`tuple` of the form returned by :py:meth:`return_error_raw <howdy.core.return_error_raw>`.
    
    :rtype: tuple
    
    .. _Jackett: https://github.com/Jackett/Jackett
    """
    time0 = time.time( )
    data = core.get_jackett_credentials( )
    if data is None:
        return return_error_raw('failure, could not get jackett server credentials')
    url, apikey = data
    endpoint = 'api/v2.0/indexers/all/results/torznab/api'
    popName = False
    if tmdb_id is not None: popName = True        
    def _return_params( name, popName, tmdb_id ):
        params = { 'apikey' : apikey, 'cat' : 2000 }
        if tmdb_id is not None:
            imdb_id = movie.get_imdbid_from_id( tmdb_id, verify = verify )
            params[ 'imdbid' ] = imdb_id
            return params
        elif doRaw:
            params['q'] = name
            return params

        tmdb_id = movie.get_movie_tmdbids( name, verify = verify )
        #if tmdb_id is None or doRaw and not popName:
        #    params['q'] = name
        #    return params
        #
        ## check that the name matches
        movie_name = movie.get_movie_info(
            tmdb_id, verify = verify )['title'].lower( ).strip( )
        if movie_name != name.lower( ).strip( ):
            params['q'] = name
            return params
        imdb_id = movie.get_imdbid_from_id(
            tmdb_id, verify = verify )
        if imdb_id is None:
            params['q'] = name
            return params
        params['imdbid'] = imdb_id
        return params

    params = _return_params( name, popName, tmdb_id )
    if popName and 'q' in params: params.pop( 'q' )
    logging.info( 'params: %s, mainURL = %s' % (
        params, urljoin( url, endpoint ) ) )                                                 
    response = requests.get(
        urljoin( url, endpoint ), verify = verify,
        params = params )
    if response.status_code != 200:
        return return_error_raw(
            ' '.join([ 'failure, problem with jackett server accessible at %s.' % url,
                       'Error code = %d. Error data = %s.' % (
                           response.status_code, response.text ) ] ) )
    logging.info( 'processed jackett torrents for %s in %0.3f seconds.' % (
        name, time.time( ) - time0 ) )
    html = BeautifulSoup( response.text, 'html.parser' )
    if len( html.find_all('item') ) == 0:
        return return_error_raw(
            'failure, could not find movie %s with jackett.' % name )
    items = [ ]
    
    def _get_magnet_url( item ):
        try:
           magnet_url = item.find( 'torznab:attr', { 'name' : 'magneturl' } )
           if magnet_url is not None and 'magnet' in magnet_url['value']:
              return magnet_url['value']
           #
           ## not found it here, must go into URL
           url2 = item.find('guid')
           if url2 is None: return None
           url2 = url2.text
           if not validators.url( url2 ): return None
           resp2 = requests.get( url2, verify = verify )
           if resp2.status_code != 200: return None
           h2 = BeautifulSoup( resp2.text, 'html.parser' )
           valid_magnet_links = set(map(lambda elem: elem['href'],
                                        filter(lambda elem: 'href' in elem.attrs and
                                               'magnet' in elem['href'], h2.find_all('a'))))
           if len( valid_magnet_links ) == 0: return None
           return max( valid_magnet_links )
        except: return None

    for item in html.find_all('item'):
        title = item.find('title')
        if title is None: continue
        title = title.text
        torrent_size = item.find('size')
        if torrent_size is not None:
            torrent_size = float( torrent_size.text ) / 1024**2
        seeders = item.find( 'torznab:attr', { 'name' : 'seeders' } )
        if seeders is None: seeders = -1
        else: seeders = int( seeders[ 'value' ] )
        leechers = item.find( 'torznab:attr', { 'name' : 'peers' } )
        if leechers is None: leechers = -1
        else: leechers = int( leechers[ 'value' ] )
        #
        ## now do one of two things to get the magnet URL
        magnet_url = _get_magnet_url( item )
        if magnet_url is None: continue
        myitem = {
            'raw_title' : title,
            'title' : title,
            'seeders' : seeders,
            'leechers' : leechers,
            'link' : magnet_url }
        if torrent_size is not None:
            myitem[ 'title' ] = '%s (%s)' % (
                title, get_formatted_size( torrent_size * 1024**2 ) )
            myitem[ 'torrent_size' ] = torrent_size
        items.append( myitem )
    if len( items ) == 0:
        return return_error_raw(
            'FAILURE, JACKETT CANNOT FIND %s' % name )
    return items[:maxnum], 'SUCCESS'

def get_movie_torrent_eztv_io( name, maxnum = 10, verify = True, tmdb_id = None ):
    r"""
    Returns a :py:class:`tuple` of candidate movie Magnet links found using the `EZTV.IO`_ torrent service and the string ``"SUCCESS"``, if successful.

    :param str name: the movie on which to search.
    :param int maxnum: optional argument, the maximum number of magnet links to return. Default is 10. Must be :math:`\ge 5`.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :param str tmdb_id: optional argument. The TMDB_ ID of the movie.
    
    :returns: if successful, then returns a two member :py:class:`tuple` the first member is a :py:class:`list` of elements that match the searched movie, ordered from *most* seeds and leechers to least. The second element is the string ``"SUCCESS"``. The keys in each element of the list are,
       
      * ``title`` is the name of the candidate movie to download, and in parentheses is the size of the download in MB or GB.
      * ``rawtitle`` is *only* the name of the candidate movie to download.
      * ``seeders`` is the number of seeds for this Magnet link.
      * ``leechers`` is the number of leeches for this Magnet link.
      * ``link`` is the Magnet URI link.
      * ``torrent_size`` is the size of this torrent in MB.
    
    If this is unsuccessful, then returns an error :py:class:`tuple` of the form returned by :py:meth:`return_error_raw <howdy.core.return_error_raw>`.
    
    :rtype: tuple

    .. warning:: As of |date|, cannot get it to work when giving it valid movie searches, such as ``"Star Trek Beyond"``. See :numref:`table_working_movietorrents`.
    
    .. _`EZTV.IO`: https://eztv.io
    .. _`Star Trek Beyond`: https://en.wikipedia.org/wiki/Star_Trek_Beyond
    """
    assert( maxnum >= 5 )
    if tmdb_id is None:
        tmdb_id = movie.get_movie_tmdbids( name, verify = verify )
    if tmdb_id is None:
        return return_error_raw( 'FAILURE, COULD NOT FIND IMDB ID FOR %s.' % name )
    #
    ## check that the name matches
    movie_name = movie.get_movie_info( tmdb_id, verify = verify )['title'].lower( ).strip( )
    if movie_name != name.lower( ).strip( ):
        return return_error_raw( 'FAILURE, COULD NOT FIND IMDB ID FOR %s.' % name )
    imdb_id = movie.get_imdbid_from_id( tmdb_id, verify = verify )
    if imdb_id is None:
        return return_error_raw( 'FAILURE, COULD NOT FIND IMDB ID FOR %s.' % name )
    response = requests.get( 'https://eztv.io/api/get-torrents',
                             params = { 'imdb_id' : int( imdb_id.replace('t','')),
                                        'limit' : 100, 'page' : 0 },
                             verify = verify )
    if response.status_code != 200:
        return return_error_raw(
            'ERROR, COULD NOT FIND ANY TORRENTS FOR %s IN EZTV.IO' % name )
    alldat = response.json( )
    if alldat['torrents_count'] == 0:
        return return_error_raw(
            'ERROR, COULD NOT FIND ANY TORRENTS FOR %s IN EZTV.IO' % name )
    all_torrents = alldat[ 'torrents' ]
    for pageno in range( 1, 101 ):
        if alldat[ 'torrents_count' ] < 100: break
        response = requests.get( 'https://eztv.io/api/get-torrents',
                             params = { 'imdb_id' : int( imdb_id.replace('t','')),
                                        'limit' : 100, 'page' : pageno },
                             verify = verify )
        if response.status_code != 200: break
        alldat = response.json( )
        if alldat['torrents_count'] == 0: break
        all_torrents += alldat[ 'torrents' ]
    all_torrents_mine = all_torrents[:maxnum]
    if len( all_torrents_mine ) == 0:
        return return_error_raw(
            'ERROR, COULD NOT FIND %s IN EZTV.IO' % name )
    return list(
        map(lambda tor: {
            'raw_title' : tor[ 'title' ],
            'title' : '%s (%s)' % (
                tor[ 'title' ], get_formatted_size( tor['size_bytes'] ) ),
            'seeders' : int( tor[ 'seeds' ] ),
            'leechers' : int( tor[ 'peers' ] ),
            'link' : tor[ 'magnet_url' ],
            'torrent_size' : float( tor[ 'size_bytes'] ) / 1024**2 },
            all_torrents_mine ) ), 'SUCCESS'
    

def get_movie_torrent_zooqle( name, maxnum = 10, verify = True ):
    r"""
    Returns a :py:class:`tuple` of candidate movie Magnet links found using the Zooqle_ torrent service and the string ``"SUCCESS"``, if successful.

    :param str name: the movie string on which to search.
    :param int maxnum: optional argument, the maximum number of magnet links to return. Default is 100. Must be :math:`\ge 5`.
    :param bool verify:  optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: if successful, then returns a two member :py:class:`tuple` the first member is a :py:class:`list` of elements that match the searched movie, ordered from *most* seeds and leechers to least. The second element is the string ``"SUCCESS"``. The keys in each element of the list are,

      * ``title`` is the name of the candidate movie to download, and in parentheses is the size of the download in MB or GB.
      * ``rawtitle`` is *only* the name of the candidate movie to download.
      * ``seeders`` is the number of seeds for this Magnet link.
      * ``leechers`` is the number of leeches for this Magnet link.
      * ``link`` is the Magnet URI link.
      * ``torrent_size`` is the size of this torrent in MB.
    
    If this is unsuccessful, then returns an error :py:class:`tuple` of the form returned by :py:meth:`return_error_raw <howdy.core.return_error_raw>`.
    
    :rtype: tuple
    
    .. _Zooqle: https://zooqle.com
    """
    assert( maxnum >= 5 )
    names_of_trackers = map(lambda tracker: tracker.replace(':', '%3A').replace('/', '%2F'), [
        'udp://tracker.opentrackr.org:1337/announce',
        'udp://open.demonii.com:1337',
        'udp://tracker.pomf.se:80/announce',
        'udp://torrent.gresille.org:80/announce',
        'udp://11.rarbg.com/announce',
        'udp://11.rarbg.com:80/announce',
        'udp://open.demonii.com:1337/announce',
        'udp://tracker.openbittorrent.com:80',
        'http://tracker.ex.ua:80/announce',
        'http://tracker.ex.ua/announce',
        'http://bt.careland.com.cn:6969/announce',
        'udp://glotorrents.pw:6969/announce'
    ])
    tracklist = ''.join(map(lambda tracker: '&tr=%s' % tracker, names_of_trackers ) )
    def _get_magnet_link( info_hash, title ):
        download_url = "magnet:?xt=urn:btih:" + info_hash + "&dn=" + '+'.join(title.split()) + tracklist
        return download_url
    candname = re.sub("'", '', name )
    url = 'https://zooqle.com/search'
    params = { 'q' : '+'.join( candname.split() + [ 'category%3AMovie', ] ),
               'fmt' : 'rss' }
    paramurl = '?' + '&'.join(map(lambda tok: '%s=%s' % ( tok, params[ tok ] ), params ) )                                  
    fullurl = urljoin( url, paramurl )
    response = requests.get( fullurl, verify = verify )
    if response.status_code != 200:
        return return_error_raw( 'ERROR, COULD NOT FIND ZOOQLE TORRENTS FOR %s' % candname )
    myxml = BeautifulSoup( response.text, 'html.parser' )
    def is_valid_elem( elem ):
        names = set(map(lambda elm: elm.name, elem.find_all( ) ) )
        return len( names & set([ 'torrent:infohash',
                                  'torrent:seeds',
                                  'torrent:peers',
                                  'torrent:contentlength' ]) ) == 4
    
    cand_items = list( filter(lambda elem: len( elem.find_all('title' ) ) >= 1 and
                              is_valid_elem( elem ) and
                              get_maximum_matchval( max( elem.find_all('title' ) ).get_text( ), candname ) >= 80,
                              myxml.find_all('item') ) )
    def get_num_forelem( elem, name ):
        valid_elm = list(filter(lambda elm: elm.name == 'torrent:%s' % name, elem ) )
        if len( valid_elm ) == 0: return None
        valid_elm = valid_elm[ 0 ]
        return int( valid_elm.get_text( ) )
    def get_infohash( elem ):
        valid_elm = list(filter(lambda elm: elm.name == 'torrent:infohash', elem ) )
        if len( valid_elm ) == 0: return None
        valid_elm = valid_elm[ 0 ]
        return valid_elm.get_text( ).lower( )
    
    items_toshow = list( map(lambda elem: {
        'title' : '%s (%s)' % (
            max( elem.find_all('title' ) ).get_text( ),
            get_formatted_size( get_num_forelem( elem, 'contentlength' ) ) ),
        'raw_title' : max( elem.find_all('title' ) ).get_text( ),
        'seeders' : get_num_forelem( elem, 'seeds' ),
        'leechers' : get_num_forelem( elem, 'peers' ),
        'link' : _get_magnet_link( get_infohash( elem ),
                                   max( elem.find_all('title' ) ).get_text( ) ),
        'torrent_size' : float( get_num_forelem( elem, 'contentlength' ) * 1.0 / 1024**2 ) },
                             cand_items ) )
    if len( items_toshow ) == 0:
        return return_error_raw( 'ERROR, COULD NOT FIND ZOOQLE TORRENTS FOR %s' % candname )
    return sorted( items_toshow, key = lambda item: -item['seeders'] - item['leechers'] )[:maxnum], 'SUCCESS'

def get_movie_torrent_rarbg( name, maxnum = 10, verify = True ):
    r"""
    Returns a :py:class:`tuple` of candidate movie Magnet links found using the RARBG_ torrent service and the string ``"SUCCESS"``, if successful.

    :param str name: the movie string on which to search.
    :param int maxnum: optional argument, the maximum number of magnet links to return. Default is 10. Must be :math:`\ge 5`.
    :param bool verify:  optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: if successful, then returns a two member :py:class:`tuple` the first member is a :py:class:`list` of elements that match the searched movie, ordered from *most* seeds and leechers to least. The second element is the string ``"SUCCESS"``. The keys in each element of the list are,

      * ``title`` is *only* the name of the candidate movie to download.
      * ``seeders`` is the number of seeds for this Magnet link.
      * ``leechers`` is the number of leeches for this Magnet link.
      * ``link`` is the Magnet URI link.
    
    If this is unsuccessful, then returns an error :py:class:`tuple` of the form returned by :py:meth:`return_error_raw <howdy.core.return_error_raw>`.
    
    :rtype: tuple
    
    .. warning:: As of |date|, cannot get it to work when giving it valid movie searches, such as ``"Star Trek Beyond"``. See :numref:`table_working_movietorrents`.
    
    .. _RARBG: https://en.wikipedia.org/wiki/RARBG    
    """
    assert( maxnum >= 5 )
    tmdbid = movie.get_movie_tmdbids( name )
    if tmdbid is None:
        return None, 'ERROR, could not find %s in themoviedb.' % name
    #
    ## got app_id and apiurl from https://www.rubydoc.info/github/epistrephein/rarbg/master/RARBG/API
    apiurl = "https://torrentapi.org/pubapi_v2.php"
    response = requests.get(apiurl,
                            params={ "get_token": "get_token",
                                     "format": "json",
                                     "app_id": "rarbg-rubygem" }, verify = verify )
    if response.status_code != 200:
        status = '. '.join([ 'ERROR, problem with rarbg.to: %d' % response.status_code,
                             'Unable to connect to provider.' ])
        return None, status
    token = response.json( )[ 'token' ]
    params = { 'mode' : 'search', 'search_themoviedb' : tmdbid, 'token' : token,
               'format' : 'json_extended', 'app_id' : 'rarbg-rubygem', 'limit' : 100,
               'category' : 'movies' }
    #
    ## wait 4 seconds
    ## this is a diamond hard limit for RARBG
    time.sleep( 4.0 )
    response = requests.get( apiurl, params = params, verify = verify )
    if response.status_code != 200:
        status = '. '.join([ 'ERROR, problem with rarbg.to: %d' % response.status_code,
                             'Unable to connect to provider.' ])
        return None, status
    data = response.json( )
    if 'torrent_results' not in data:
        status = 'ERROR, RARBG.TO could not find any torrents for %s.' % name            
        return None, status
    data = data['torrent_results']
    def get_num_seeders( elem ):
        if 'seeders' in elem: return elem['seeders']
        return 1
    def get_num_leechers( elem ):
        if 'leechers' in elem: return elem['leechers']
        return 1
    def get_title( elem ):
        if 'size' in elem:
            return '%s (%s)' % ( elem['title'], get_formatted_size( elem[ 'size' ] ) )
        return '%s ()' % elem['title']
    actdata = list( map(lambda elem: { 'title' : get_title( elem ),
                                       'seeders' : get_num_seeders( elem ),
                                       'leechers' : get_num_leechers( elem ),
                                       'link' : elem['download'] }, data ) ) 
    return actdata, 'SUCCESS'
        
def get_movie_torrent_tpb( name, maxnum = 10, doAny = False, verify = True ):
    r"""
    Returns a :py:class:`tuple` of candidate movie Magnet links found using the `The Pirate Bay`_ torrent service and the string ``"SUCCESS"``, if successful.

    :param str name: the movie string on which to search.
    :param int maxnum: optional argument, the maximum number of magnet links to return. Default is 100. Must be :math:`\ge 5`.
    :param bool doAny: optional argument. If ``True``, then only search through TV shows. Otherwise, search through all media.
    :param bool verify:  optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: if successful, then returns a two member :py:class:`tuple` the first member is a :py:class:`list` of elements that match the searched movie, ordered from *most* seeds and leechers to least. The second element is the string ``"SUCCESS"``. The keys in each element of the list are,

      * ``title`` is *only* the name of the candidate movie to download.
      * ``seeders`` is the number of seeds for this Magnet link.
      * ``leechers`` is the number of leeches for this Magnet link.
      * ``link`` is the Magnet URI link.
      * ``torrent_size`` is the size of this torrent in bytes.
    
    If this is unsuccessful, then returns an error :py:class:`tuple` of the form returned by :py:meth:`return_error_raw <howdy.core.return_error_raw>`.
    
    :rtype: tuple

    .. warning:: As of |date|, cannot get it to work when giving it valid movie searches, such as ``"Star Trek Beyond"``. See :numref:`table_working_movietorrents`.
    
    .. _`The Pirate Bay`: https://en.wikipedia.org/wiki/The_Pirate_Bay
    """
    assert( maxnum >= 5 )
    def convert_size(size, default=None, use_decimal=False, **kwargs):
        """
        Convert a file size into the number of bytes
        
        :param size: to be converted
        :param default: value to return if conversion fails
        :param use_decimal: use decimal instead of binary prefixes (e.g. kilo = 1000 instead of 1024)
        
        :keyword sep: Separator between size and units, default is space
        :keyword units: A list of (uppercase) unit names in ascending order.
        Default units: ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        
        :keyword default_units: Default unit if none is given,
        default is lowest unit on the scale, e.g. bytes

        :returns: the number of bytes, the default value, or 0
        """
        result = None
        
        try:
            sep = kwargs.pop('sep', ' ')
            scale = kwargs.pop('units', ['B', 'KB', 'MB', 'GB', 'TB', 'PB'])
            default_units = kwargs.pop('default_units', scale[0])
            
            if sep:
                size_tuple = size.strip().split(sep)
                scalar, units = size_tuple[0], size_tuple[1:]
                units = units[0].upper() if units else default_units
            else:
                regex_scalar = re.search(r'([\d. ]+)', size, re.I)
                scalar = regex_scalar.group() if regex_scalar else -1
                units = size.strip(scalar) if scalar != -1 else 'B'

            scalar = float(scalar)
            scalar *= (1024 if not use_decimal else 1000) ** scale.index(units)
            
            result = scalar
            
            # TODO: Make sure fallback methods obey default units
        except AttributeError:
            result = size if size is not None else default

        except ValueError:
            result = default

        finally:
            try:
                if result != default:
                    result = long(result)
                    result = max(result, 0)
            except (TypeError, ValueError):
                pass

        return result

    surl = urljoin( 'https://thepiratebay.org', 's/' )
    if not doAny:
        cat = CATEGORIES.VIDEO.MOVIES
    else:
        cat = CATEGORIES.VIDEO.ALL
    search_params = { "q" : name, "type" : "search",
                      "orderby" : ORDERS.SIZE.DES, "page" : 0,
                      "category" : cat }
    response = requests.get( surl, params = search_params, verify = verify )
    if response.status_code != 200:
        return None, 'Error, could not use the movie service. Exiting...'
    
    def process_column_header(th):
        result = ""
        if th.a:
            result = th.a.get_text(strip=True)
        if not result:
            result = th.get_text(strip=True)
        return result

    def try_int(candidate, default_value=0):
        """
        Try to convert ``candidate`` to int, or return the ``default_value``.
        
        :param candidate: The value to convert to int
        :param default_value: The value to return if the conversion fails
        :return: ``candidate`` as int, or ``default_value`` if the conversion fails
        """
        
        try:
            return int(candidate)
        except (ValueError, TypeError):
            return default_value

    html = BeautifulSoup( response.text, 'html.parser' )
    torrent_table = html.find("table", id="searchResult")
    torrent_rows = torrent_table("tr") if torrent_table else []
    if len( torrent_rows ) < 2:
        return None, 'Error, could find no torrents with name %s' % name
    labels = list(map(lambda label: process_column_header(label),
                      torrent_rows[0]("th") ) )
    items = []
    for result in torrent_rows[1:]:
        try:
            cells = result('td')
            
            title = result.find(class_='detName').get_text(strip = True )
            if not doAny:
                if 'x264' not in title.lower( ):
                    continue
                if '720p' not in title.lower( ):
                    continue
            download_url = result.find(title='Download this torrent using magnet')['href']
            if 'magnet:?' not in download_url:
                continue
            if not all([ title, download_url ]):
                continue
            seeders = try_int(cells[labels.index("SE")].get_text(strip=True))
            leechers = try_int(cells[labels.index("LE")].get_text(strip=True))
            
            # Convert size after all possible skip scenarios
            torrent_size = cells[labels.index("Name")].find(class_="detDesc").get_text(strip=True).split(", ")[1]
            torrent_size = re.sub(r"Size ([\d.]+).+([KMGT]iB)", r"\1 \2", torrent_size)
            size = convert_size(torrent_size, units = ["B", "KB", "MB", "GB", "TB", "PB"]) or -1
            
            item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders,
                    'leechers': leechers, 'hash': ''}
            items.append(item)
        except Exception as e:
            continue
    if len( items ) == 0:
        return None, 'FAILURE, NO MOVIES SATISFYING CRITERIA'
    items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
    items = items[:maxnum]
    return list( map(lambda item: {
        'title' : item['title'],
        'seeders' : item[ 'seeders' ],
        'leechers' : item[ 'leechers' ],
        'link' : item[ 'link' ],
        'torrent_size' : item[ 'size' ] }, items ) ), 'SUCCESS'

def get_movie_torrent_kickass( name, maxnum = 10, verify = True ):
    r"""
    Returns a :py:class:`tuple` of candidate movie Magnet links found using the KickAssTorrents_ torrent service and the string ``"SUCCESS"``, if successful.

    :param str name: the movie string on which to search.
    :param int maxnum: optional argument, the maximum number of magnet links to return. Default is 10. Must be :math:`\ge 5`.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: if successful, then returns a two member :py:class:`tuple` the first member is a :py:class:`list` of elements that match the searched movie, ordered from *most* seeds and leechers to least. The second element is the string ``"SUCCESS"``. The keys in each element of the list are,

      * ``title`` is *only* the name of the candidate movie to download.
      * ``seeders`` is the number of seeds for this Magnet link.
      * ``leechers`` is the number of leeches for this Magnet link.
      * ``link`` is the Magnet URI link.
    
    If this is unsuccessful, then returns an error :py:class:`tuple` of the form returned by :py:meth:`return_error_raw <howdy.core.return_error_raw>`.
    
    :rtype: tuple
    
    .. warning:: As of |date|, cannot get it to work when giving it valid movie searches, such as ``"Star Trek Beyond"``. See :numref:`table_working_movietorrents`.
    
    .. _KickassTorrents: https://en.wikipedia.org/wiki/KickassTorrents
    """
    from KickassAPI import Search, Latest, User, CATEGORY, ORDER
    assert( maxnum >= 5 )
    names_of_trackers = map(lambda tracker: tracker.replace(':', '%3A').replace('/', '%2F'), [
        'http://mgtracker.org:2710/announce',
        'http://tracker.internetwarriors.net:1337/announce',
        'http://37.19.5.139:6969/announce',
        'http://37.19.5.155:6881/announce',
        'http://p4p.arenabg.ch:1337/announce',
        'udp://tracker.zer0day.to:1337/announce',
        'udp://tracker.coppersurfer.tk:6969/announce',
        'http://109.121.134.121:1337/announce',
        'udp://tracker.opentrackr.org:1337/announce',
        'http://5.79.83.193:2710/announce',
        'udp://p4p.arenabg.com:1337/announce',
        'udp://explodie.org:6969/announce',
        'http://tracker.sktorrent.net:6969/announce',
        'udp://tracker.leechers-paradise.org:6969/announce',
        'http://mgtracker.org:6969/announce',
        'http://tracker.opentrackr.org:1337/announce',
        'http://p4p.arenabg.com:1337/announce',
        'udp://9.rarbg.com:2710/announce',
        'http://tracker.mg64.net:6881/announce',
        'http://explodie.org:6969/announce' ] )
    tracklist = ''.join(map(lambda tracker: '&tr=%s' % tracker, names_of_trackers ) )
    def get_size( lookup ):
        size_string = lookup.size
        if size_string.lower().endswith('mib'):
            return float( size_string.lower().split()[0] )
        elif size_string.lower().endswith('kib'):
            return float( size_string.lower().split()[0] ) / 1024
        elif size_string.lower().endswith('gib'):
            return float( size_string.lower().split()[0] ) * 1024
        else: return 0.0
    try:
        lookups = sorted( filter(lambda lookup: #'720p' in lookup.name and
                                 # get_size( lookup ) >= 100.0 and
                                 get_maximum_matchval( lookup.name, name ) >= 90 and
                                 lookup.torrent_link is not None,
                                 Search( name, category = CATEGORY.MOVIES ) ),
                          key = lambda lookup: get_size( lookup ) )[:maxnum]
        if len(lookups) == 0: return None, 'FAILURE, COULD FIND NOTHING THAT MATCHES %s' % name
    except Exception as e:
        return None, 'FAILURE: %s' % e

    def create_magnet_link( lookup ):
        info_hash = os.path.basename( lookup.torrent_link ).lower( )
        download_url = ''.join([ "magnet:?xt=urn:btih:%s" % info_hash,
                                 "&dn=%s" % '+'.join( lookup.name.split( ) ),
                                 tracklist ])
        return download_url

    items_toshow = list( map(lambda lookup: {
        'title' : '%s (%s)' % ( lookup.name, lookup.size ),
        'seeders' : -1,
        'leechers' : -1,
        'link' : create_magnet_link( lookup ) }, lookups ) )
    
    return items_toshow, 'SUCCESS'
    
def get_movie_torrent( name, verify = True ):
    """
    Returns a :py:class:`tuple` of candidate movie found using `Torrent files <torrent file_>`_ using the `YTS API`_ torrent service and the string ``"SUCCESS"``, if successful.
    
    :param str name: the movie string on which to search.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :returns: if successful, then returns a two member :py:class:`tuple` the first member is a :py:class:`list` of `Torrent files <torrent file_>`_ that match the searched movie, ordered from *earliest* to *latest* year of release. The second element is the string ``"SUCCESS"``. If this is unsuccessful, then returns an error :py:class:`tuple` of the form returned by :py:meth:`return_error_raw <howdy.core.return_error_raw>`.
    :rtype: tuple
    
    .. _`YTS API`: https://yts.ag/api
    .. _`torrent file`: https://en.wikipedia.org/wiki/Torrent_file
    """
    mainURL = 'https://yts.ag/api/v2/list_movies.json'
    params = { 'query_term' : name, 'order_by' : 'year' }
    response = requests.get( mainURL, params = params, verify = verify )
    if response.status_code != 200:
        return return_error_raw( 'Error, could not use the movie service. Exiting...' )
    data = response.json()['data']
    if 'movies' not in data or len(data['movies']) == 0:
        return return_error_raw( "Could not find %s, exiting..." % name )
    movies = data['movies']
    return movies, 'SUCCESS'
