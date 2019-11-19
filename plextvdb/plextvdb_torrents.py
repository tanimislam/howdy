import requests, re, threading, cfscrape
import os, time, numpy, logging, datetime, pickle, gzip
from bs4 import BeautifulSoup
from tpb import CATEGORIES, ORDERS
from itertools import chain
from requests.compat import urljoin
from multiprocessing import Process, Manager
from pathos.multiprocessing import Pool

from plexcore import plexcore_deluge, get_formatted_size, get_maximum_matchval, return_error_raw
from plexcore.plexcore import get_jackett_credentials
from plextvdb import get_token, plextvdb

_num_to_quit = 10

def return_error_couldnotfind( name ):
    """
    Returns a :py:class:`tuple` error message in the format of :py:meth:`return_error_raw <plexcore.return_error_raw>`, but with the message ``"Failure, could not find any tv shows with search term <name>"``, where ``<name>`` is the episode torrent that could not be found.

    :param str name: the episode torrent to be searched.
    
    :returns: a :py:class:`tuple` of format :py:meth:`return_error_raw <plexcore.return_error_raw>`, with the error message, ``"Failure, could not find any tv shows with search term <name>"``.
    :rtype: str
    
    .. seealso:: :py:meth:`return_error_raw <plexcore.return_error_raw>`
    """
    return return_error_raw(
        'Failure, could not find any tv shows with search term %s.' % name )


def get_tv_torrent_eztv_io( name, maxnum = 10, verify = True, series_name = None,
                            minsizes = None, maxsizes = None ):
    """
    Returns a :py:class:`tuple` of candidate episode Magnet links found using the `EZTV.IO`_ torrent service and the string ``"SUCCESS"``, if successful.

    :param str name: the episode string on which to search.
    :param int maxnum: optional argument, the maximum number of magnet links to return. Default is 10. Must be :math:`\ge 5`.
    :param bool verify:  optional argument, whether to verify SSL connections. Default is ``True``.
    :param str series_name: optional argument, the TV show for this episode.
    :param list minsizes: optional :py:class:`list` or :py:class:`tuple` of size at least 2. Here is its meaning if it is not ``None``:

        * if its size is 1, then the minimum size of H264_ and `H265/HEVC`_ encoded videos, in MB, is ``minsizes[ 0 ]``.
        * if its size is :math:`\ge 2`, then the minimum size of H264_ encoded video, in MB, is ``minsizes[ 0 ]``. The minimum size of `H265/HEVC`_ encoded video, in MB, is ``minsizes[ 1 ]``.

    :param list maxsizes: optional :py:class:`list` or :py:class:`tuple` of size at least 2. Here is its meaning if it is not ``None``:

        * if its size is 1, then the maximum size of H264_ and `H265/HEVC`_ encoded videos, in MB, is ``maxsizes[ 0 ]``.
        * if its size is :math:`\ge 2`, then the maximum size of H264_ encoded video, in MB, is ``maxsizes[ 0 ]``. The maximum size of `H265/HEVC`_ encoded video, in MB, is ``maxsizes[ 1 ]``.

    :returns: if successful, then returns a two member :py:class:`tuple` the first member is a :py:class:`list` of elements that match the searched episode, ordered from *most* seeds and leechers to least. The second element is the string ``"SUCCESS"``. The keys in each element of the list are,
       
      * ``title`` is the name of the candidate episode to download.
      * ``rawtitle`` is also the name of the candidate episode to download.
      * ``seeders`` is the number of seeds for this Magnet link.
      * ``leechers`` is the number of leeches for this Magnet link.
      * ``link`` is the Magnet URI link.
      * ``torrent_size`` is the size of this torrent in bytes.
      * ``pubdate`` is the :py:class:`date <datetime.date>` at which the magnet link was publshed and put online.
    
    If this is unsuccessful, then returns an error :py:class:`tuple` of the form returned by :py:meth:`return_error_raw <plexcore.return_error_raw>`.
    
    :rtype: tuple
    
    .. _`EZTV.IO`: https://eztv.io
    .. _H264: https://en.wikipedia.org/wiki/Advanced_Video_Coding
    .. _`H265/HEVC`: https://en.wikipedia.org/wiki/High_Efficiency_Video_Coding
    """
    assert( maxnum >= 5 )
    name_split = name.split()
    last_tok = name_split[-1]
    status = re.match('^s[0-9]{2}e[0-9]{2}',
                      last_tok.lower( ) )
    if status is None:
        return return_error_raw(
            'ERROR, LAST TOKEN %s IS NOT SEASON-EPISODE TOKEN.' % last_tok )
    if series_name is None: series_name = ' '.join( name_split[:-1] )
    tvdb_token = get_token( verify = verify )
    if tvdb_token is None:
        return return_error_raw(
            'ERROR, COULD NOT ACCESS API.THETVDB.COM' )
    series_id = plextvdb.get_series_id( series_name, tvdb_token, verify = verify )
    if series_id is None:
        return return_error_raw(
            'ERROR, COULD NOT FIND SERIES %s.' % series_name )
    imdb_id = plextvdb.get_imdb_id( series_id, tvdb_token, verify = verify )
    if imdb_id is None or len( imdb_id.strip( ) ) == 0:
        return return_error_raw(
            'ERROR, COULD NOT FIND IMDB ID FOR SERIES %s. IMDB ID COULD NOT BE FOUND.' % series_name )
    response = requests.get( 'https://eztv.io/api/get-torrents',
                             params = {
                                 'imdb_id' : int( imdb_id.replace('t','')),
                                 'limit' : 100, 'page' : 0 },
                             verify = verify )
    if response.status_code != 200:
        return return_error_raw(
            'ERROR, COULD NOT FIND ANY TORRENTS FOR %s IN EZTV.IO. Status code = %d' % (
                name, response.status_code ) )
    alldat = response.json( )
    if alldat['torrents_count'] == 0:
        return return_error_raw(
            'ERROR, COULD NOT FIND ANY TORRENTS FOR %s IN EZTV.IO. No magnet links found.' % name )
    all_torrents = alldat[ 'torrents' ]
    for pageno in range( 1, 101 ):
        if alldat[ 'torrents_count' ] < 100: break
        response = requests.get( 'https://eztv.io/api/get-torrents',
                             params = { 'imdb_id' : int( imdb_id.replace('t','')),
                                        'limit' : 100, 'page' : pageno },
                             verify = verify )
        if response.status_code != 200: break
        alldat = response.json( )
        if 'torrents' not in alldat: break
        if alldat['torrents_count'] == 0: break
        logging.debug( 'EZTV.IO: %s, %d, %s.' % ( name, pageno, alldat.keys( ) ) )
        all_torrents += alldat[ 'torrents' ]
    #
    ## now filter on those torrents that have sXXeYY in them
    all_torrents_mine = list(filter(
        lambda tor: last_tok.lower( ) in tor['title'].lower( ), all_torrents ) )

    logging.debug( 'MAGNET LINKS FOUND: %s.' % all_torrents_mine )

    #
    ## now perform the filtering
    def _filter_minmax_size( minSize, minSize_x265, maxSize, maxSize_x265, item ):
        if minSize is not None and 'x265' not in item['title'].lower( ) and int( item['size_bytes'] ) <= minSize*1024**2:
            return False
        if minSize_x265 is not None and 'x265' in item['title'].lower( ) and int( item['size_bytes'] ) <= minSize_x265*1024**2:
            return False
        if maxSize is not None and 'x265' not in item['title'].lower( ) and int( item['size_bytes'] ) >= maxSize*1024**2:
            return False
        if maxSize_x265 is not None and 'x265' in item['title'].lower( ) and int( item['size_bytes'] ) >= maxSize_x265*1024**2:
            return False
        return True
    
    ## now perform the filtering
    if any(map(lambda tok: tok is not None, [ minsizes, maxsizes ])):
        minsize = None
        minsize_x265 = None
        maxsize = None
        maxsize_x265 = None
        if minsizes is not None:
            if len( minsizes ) >= 2: minsize, minsize_x265 = minsizes[:2]
            else: minsize, minsize_x265 = 2 * [ minsizes[0] ]
        if maxsizes is not None:
            if len( maxsizes ) >= 2: maxsize, maxsize_x265 = maxsizes[:2]
            else: maxsize, maxsize_x265 = 2 * [ maxsizes[0] ]
        all_torrents_mine = list(filter(lambda item: _filter_minmax_size(
            minsize, minsize_x265, maxsize, maxsize_x265, item ),
                                        all_torrents_mine ) )
                  
    all_torrents_mine = all_torrents_mine[:maxnum]
    if len( all_torrents_mine ) == 0:
        return return_error_raw(
            'ERROR, COULD NOT FIND %s IN EZTV.IO' % name )
    return list(
        map(lambda tor: {
            'title' : tor[ 'title' ],
            'rawtitle' : tor[ 'title' ],
            'seeders' : int( tor[ 'seeds' ] ),
            'leechers' : int( tor[ 'peers' ] ),
            'link' : tor[ 'magnet_url' ],
            'torrent_size' : int( tor[ 'size_bytes' ] ) / 1024.0**2, # size in MB
            'pubdate' : datetime.datetime.fromtimestamp(
                int( tor['date_released_unix'] ) ).date( ) },
            all_torrents_mine ) ), 'SUCCESS'

def get_tv_torrent_zooqle( name, maxnum = 100, verify = True ):
    """
    Returns a :py:class:`tuple` of candidate episode Magnet links found using the Zooqle_ torrent service and the string ``"SUCCESS"``, if successful.

    :param str name: the episode string on which to search.
    :param int maxnum: optional argument, the maximum number of magnet links to return. Default is 100. Must be :math:`\ge 5`.
    :param bool verify:  optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: if successful, then returns a two member :py:class:`tuple` the first member is a :py:class:`list` of elements that match the searched episode, ordered from *most* seeds and leechers to least. The second element is the string ``"SUCCESS"``. The keys in each element of the list are,

      * ``title`` is *only* the name of the candidate episode to download.
      * ``seeders`` is the number of seeds for this Magnet link.
      * ``leechers`` is the number of leeches for this Magnet link.
      * ``link`` is the Magnet URI link.
      * ``torrent_size`` is the size of this torrent in bytes.
    
    If this is unsuccessful, then returns an error :py:class:`tuple` of the form returned by :py:meth:`return_error_raw <plexcore.return_error_raw>`.
    
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
    params = { 'q' : '+'.join( candname.split() + [ 'category%3ATV', ] ),
               'fmt' : 'rss' }
    paramurl = '?' + '&'.join(map(lambda tok: '%s=%s' % ( tok, params[ tok ] ),
                                  params ) )
    fullurl = urljoin( url, paramurl )
    response = requests.get( fullurl, verify = verify )
    if response.status_code != 200:
        return return_error_raw(
            'ERROR, COULD NOT FIND ZOOQLE TORRENTS FOR %s' % candname)
    myxml = BeautifulSoup( response.content, 'lxml' )
    def is_valid_elem( elem ):
        names = set(map(lambda elm: elm.name, elem.find_all( ) ) )
        return len( names & set([ 'torrent:infohash',
                                  'torrent:seeds',
                                  'torrent:peers',
                                  'torrent:contentlength' ]) ) == 4
    cand_items = filter(lambda elem: len( elem.find_all('title' ) ) >= 1 and
                        is_valid_elem( elem ) and
                        get_maximum_matchval(
                            max( elem.find_all('title' ) ).get_text( ), candname ) >= 80,
                        myxml.find_all('item'))
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
        'title' : max( elem.find_all('title' ) ).get_text( ),
        'seeders' : get_num_forelem( elem, 'seeds' ),
        'leechers' : get_num_forelem( elem, 'peers' ),
        'link' : _get_magnet_link(
            get_infohash( elem ),
            max( elem.find_all('title' ) ).get_text( ) ),
        'torrent_size' : float(
            get_num_forelem( elem, 'contentlength' ) * 1.0 / 1024**2 ) },
                             cand_items ) )
    if len( items_toshow ) == 0:
        return return_error_raw(
            'ERROR, COULD NOT FIND ZOOQLE TORRENTS FOR %s' % candname )
    items = sorted( items_toshow, key = lambda item: -item['seeders'] - item['leechers'] )[:maxnum]
    return items, 'SUCCESS'

def get_tv_torrent_rarbg( name, maxnum = 10, verify = True ):
    """
    Returns a :py:class:`tuple` of candidate episode Magnet links found using the RARBG_ torrent service and the string ``"SUCCESS"``, if successful.

    :param str name: the episode string on which to search.
    :param int maxnum: optional argument, the maximum number of magnet links to return. Default is 10. Must be :math:`\ge 5`.
    :param bool verify:  optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: if successful, then returns a two member :py:class:`tuple` the first member is a :py:class:`list` of elements that match the searched episode, ordered from *most* seeds and leechers to least. The second element is the string ``"SUCCESS"``. The keys in each element of the list are,

      * ``title`` is *only* the name of the candidate episode to download.
      * ``seeders`` is the number of seeds for this Magnet link.
      * ``leechers`` is the number of leeches for this Magnet link.
      * ``link`` is the Magnet URI link.
    
    If this is unsuccessful, then returns an error :py:class:`tuple` of the form returned by :py:meth:`return_error_raw <plexcore.return_error_raw>`.
    
    :rtype: tuple
    
    .. warning:: cannot get it to work as of |date|. Cannot get it to work when giving it valid episode searches, such as ``"The Simpsons S31E01"``. See :numref:`table_working_tvtorrents`.
    
    .. _RARBG: https://en.wikipedia.org/wiki/RARBG    
    """
    from .plextvdb import get_token, get_series_id, get_possible_ids
    assert( maxnum >= 5 )
    candidate_seriesname = ' '.join( name.strip().split()[:-1] )
    epstring = name.strip().split()[-1].upper()
    if not epstring[0] == 'S':
        return return_error_raw( 'Error, first string must be an s or S.' )
    epstring = epstring[1:]
    splitseaseps = epstring.split('E')[:2]
    if len( splitseaseps ) != 2:
        return return_error_raw( 'Error, string must have a SEASON and EPISODE part.' )
    try:
        seasno = int( splitseaseps[0] )
    except:
        return return_error_raw( 'Error, invalid season number.' )
    try:
        epno = int( splitseaseps[1] )
    except:
        return return_error_raw( 'Error, invalid episode number.' )
    
    tvdb_token = get_token( verify = verify )
    series_id = get_series_id( candidate_seriesname, tvdb_token,
                               verify = verify )
    if series_id is None:
        series_ids = get_possible_ids( candidate_seriesname,
                                       tvdb_token, verify = verify )
        if series_ids is None or len( series_ids ) == 0:
            return return_error_raw(
                'ERROR, PLEXTVDB could find no candidate series that match %s' %
                candidate_seriesname )
        series_id = series_ids[ 0 ]
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
        return return_error_raw( status )
    token = response.json( )[ 'token' ]
    params = { 'mode' : 'search', 'search_tvdb' : series_id, 'token' : token,
               'format' : 'json_extended', 'category' : 'tv', 'app_id' : 'rarbg-rubygem',
               'search_string' : 'E'.join( splitseaseps ), 'limit' : 100 }
    #
    ## wait 4 seconds
    ## this is a diamond hard limit for RARBG
    time.sleep( 4.0 )
    response = requests.get( apiurl, params = params, verify = verify )
    if response.status_code != 200:
        status = '. '.join([ 'ERROR, problem with rarbg.to: %d' % response.status_code,
                             'Unable to connect to provider.' ])
        return return_error_raw( status )
    data = response.json( )
    if 'torrent_results' not in data:
        status = '\n'.join([ 'ERROR, RARBG.TO could not find any torrents for %s %s.' %
                             ( candidate_seriesname, 'E'.join( splitseaseps ) ),
                             'data = %s' % data ])
        return return_error_raw( status )
    data = list( filter(lambda elem: 'title' in elem, data['torrent_results']) )
    filtered_data = list( filter(lambda elem: 'E'.join( splitseaseps ) in elem['title'] and
                                 '720p' in elem['title'] and 'HDTV' in elem['title'], data ) )
    if len( filtered_data ) == 0:
        filtered_data = list( filter(lambda elem: 'E'.join( splitseaseps ) in elem['title'], data ) )
    filtered_data = list(filtered_data)[:maxnum]
    if len( filtered_data ) == 0:
        status = 'ERROR, RARBG.TO could not find any torrents for %s %s.' % (
            candidate_seriesname, 'E'.join( splitseaseps ) )
        return return_error_raw( status )
    def get_num_seeders( elem ):
        if 'seeders' in elem: return elem['seeders']
        return 1
    def get_num_leechers( elem ):
        if 'leechers' in elem: return elem['leechers']
        return 1
    items = list( map(lambda elem: { 'title' : elem['title'], 'link' : elem['download'],
                                     'seeders' : get_num_seeders( elem ),
                                     'leechers' : get_num_leechers( elem ) },
                filtered_data ) )
    return items, 'SUCCESS'

def get_tv_torrent_torrentz( name, maxnum = 10, verify = True ):
    """
    Returns a :py:class:`tuple` of candidate episode Magnet links found using the Torrentz_ torrent service and the string ``"SUCCESS"``, if successful.

    :param str name: the episode string on which to search.
    :param int maxnum: optional argument, the maximum number of magnet links to return. Default is 10. Must be :math:`\ge 5`.
    :param bool verify:  optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: if successful, then returns a two member :py:class:`tuple` the first member is a :py:class:`list` of elements that match the searched episode, ordered from *most* seeds and leechers to least. The second element is the string ``"SUCCESS"``. The keys in each element of the list are,
       
      * ``title`` is the name of the candidate episode to download.
      * ``seeders`` is the number of seeds for this Magnet link.
      * ``leechers`` is the number of leeches for this Magnet link.
      * ``link`` is the Magnet URI link.
    
    If this is unsuccessful, then returns an error :py:class:`tuple` of the form returned by :py:meth:`return_error_raw <plexcore.return_error_raw>`.
    
    :rtype: tuple

    .. warning:: cannot get it to work as of |date|. Cannot get it to work when giving it valid episode searches, such as ``"The Simpsons S31E01"``. See :numref:`table_working_tvtorrents`.
    
    .. _Torrentz: https://en.wikipedia.org/wiki/Torrentz
    """
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
    #
    def try_int( candidate, default_value=0):
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
    def _split_description(description):
        match = re.findall(r'[0-9]+', description)
        return int(match[0]) * 1024 ** 2, int(match[1]), int(match[2])
    #
    url = 'https://torrentz2.eu/feed'
    search_params = {'f': name }
    scraper = cfscrape.create_scraper( )
    response = scraper.get( url, params = search_params, verify = verify )
    if response.status_code != 200:
        return return_error_raw( 'FAILURE, request for %s did not work.' % name )
    if not response.content.startswith(b'<?xml'):
        return return_error_raw( 'ERROR, request content is not a valid XML block.' )
    html = BeautifulSoup( response.content, 'lxml' )
    items = []
    for item in html('item'):
        if item.category and 'tv' not in item.category.get_text(strip=True).lower():
            continue
        title = item.title.get_text(strip=True)
        t_hash = item.guid.get_text(strip=True).rsplit('/', 1)[-1]
        if not all([title, t_hash]):
            continue
        download_url = "magnet:?xt=urn:btih:" + t_hash + "&dn=" + '+'.join(title.split()) + tracklist
        torrent_size, seeders, leechers = _split_description(item.find('description').text)
        if get_maximum_matchval( title, name ) < 80: continue
        myitem = {'title': title, 'link': download_url, 'seeders': seeders,
                  'leechers': leechers }
        items.append(myitem)
    if len( items ) == 0:
        return return_error_raw(
            'Failure, no tv shows or series satisfying criteria for getting %s.' % name)
    items.sort(key=lambda d: try_int(d.get('seeders', 0)) +
               try_int(d.get('leechers')), reverse=True)
    items = items[:maxnum]
    return items, 'SUCCESS'

def get_tv_torrent_jackett( name, maxnum = 10, minsizes = None, maxsizes = None, keywords = [ ],
                            keywords_exc = [ ], must_have = [ ], verify = True, series_name = None,
                            raw = False ):
    """
    Returns a :py:class:`tuple` of candidate episode Magnet links found using the main Jackett_ torrent searching service and the string ``"SUCCESS"``, if successful.

    :param str name: the episode string on which to search.
    :param int maxnum: optional argumeent, the maximum number of magnet links to return. Default is 10. Must be :math:`\ge 5`.
    :param list minsizes: optional :py:class:`list` or :py:class:`tuple` of size at least 2. Here is its meaning if it is not ``None``:

        * if its size is 1, then the minimum size of H264_ and `H265/HEVC`_ encoded videos, in MB, is ``minsizes[ 0 ]``.
        * if its size is :math:`\ge 2`, then the minimum size of H264_ encoded video, in MB, is ``minsizes[ 0 ]``. The minimum size of `H265/HEVC`_ encoded video, in MB, is ``minsizes[ 1 ]``.

    :param list maxsizes: optional :py:class:`list` or :py:class:`tuple` of size at least 2. Here is its meaning if it is not ``None``:

        * if its size is 1, then the maximum size of H264_ and `H265/HEVC`_ encoded videos, in MB, is ``maxsizes[ 0 ]``.
        * if its size is :math:`\ge 2`, then the maximum size of H264_ encoded video, in MB, is ``maxsizes[ 0 ]``. The maximum size of `H265/HEVC`_ encoded video, in MB, is ``maxsizes[ 1 ]``.

    :param list keywords: optional argument. If not empty, the title of the candidate element must have at least one of the keywords in ``keywords``.
    :param list kewods_exc: optional argument. If not empty, then reject candidate element if title has any keyword in ``keywords_exc``.
    :param list must_have: optional argument. If not empty, then title of the candidate element must have *all* the keywords in ``must_have``.    
    :param bool verify:  optional argument, whether to verify SSL connections. Default is ``True``.
    :param str series_name: optional argument. the TV show for this episode.
    :param bool raw: if ``True``, uses the IMDb_ information to search for the episode. Otherwise, uses the full string in ``name`` to search for the episode.
    
    :returns: if successful, then returns a two member :py:class:`tuple` the first member is a :py:class:`list` of elements that match the searched episode, ordered from *most* seeds and leechers to least. The second element is the string ``"SUCCESS"``. The keys in each element of the list are,
       
      * ``title`` is the name of the candidate episode to download, and in parentheses the size of the candidate in MB or GB.
      * ``rawtitle`` also the name of the candidate episode to download.
      * ``seeders`` is the number of seeds for this Magnet link.
      * ``leechers`` is the number of leeches for this Magnet link.
      * ``link`` is the Magnet URI link.
      * ``torrent_size`` is the size of this torrent in bytes.
    
    If this is unsuccessful, then returns an error :py:class:`tuple` of the form returned by :py:meth:`return_error_raw <plexcore.return_error_raw>`.
    
    :rtype: tuple

    .. warning:: cannot get it to work as of |date|. Cannot get it to work when giving it valid episode searches, such as ``"The Simpsons S31E01"``. See :numref:`table_working_tvtorrents`.
    
    .. _Jackett: https://github.com/Jackett/Jackett
    """
    import validators
    assert( maxnum >= 5 )
    data = get_jackett_credentials( )
    if data is None:
        return return_error_raw('FAILURE, COULD NOT GET JACKETT SERVER CREDENTIALS')
    url, apikey = data
    if not url.endswith( '/' ): url = '%s/' % url
    endpoint = 'api/v2.0/indexers/all/results/torznab/api'
    tvdb_token = get_token( verify = verify )
    logging.debug( '%s: tvdb_token is None? %s.' % ( name, tvdb_token is None ) )
    name_split = name.split()
    last_tok = name_split[-1].lower( )
    status = re.match('^s[0-9]{2}e[0-9]{2}',
                      last_tok )
    
    def _return_params( name ):
        params = { 'apikey' : apikey, 'q' : name, 'cat' : '5000' }
        if raw: return params
        if tvdb_token is None: return params
        if series_name is None:
            if status is None: sname = name
            else: sname = ' '.join( name_split[:-1] )
        else: sname = series_name
        series_id = plextvdb.get_series_id( sname, tvdb_token, verify = verify )
        if series_id is None: return params
        imdb_id = plextvdb.get_imdb_id( series_id, tvdb_token, verify = verify )
        if imdb_id is None: return params
        params[ 'imdbid' ] = imdb_id
        return params

    logging.info( 'URL ENDPOINT: %s, PARAMS = %s.' % (
        urljoin( url, endpoint ), _return_params( name ) ) )
    response = requests.get(
        urljoin( url, endpoint ),
        params = _return_params( name ), verify = verify ) # tv shows
    if response.status_code != 200:
        return return_error_raw( 'FAILURE, PROBLEM WITH JACKETT SERVER ACCESSIBLE AT %s.' % url )
    html = BeautifulSoup( response.content, 'lxml' )
    if len( html.find_all('item') ) == 0:
        return return_error_raw( 'FAILURE, NO TV SHOWS OR SERIES SATISFYING CRITERIA FOR GETTING %s' % name )
    items = [ ]
    
    def _get_magnet_url( item ):
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
        h2 = BeautifulSoup( resp2.content, 'lxml' )
        valid_magnet_links = set(map(lambda elem: elem['href'],
                                     filter(lambda elem: 'href' in elem.attrs and 'magnet' in elem['href'],
                                            h2.find_all('a'))))
        if len( valid_magnet_links ) == 0: return None
        return max( valid_magnet_links )

    if status is None: last_tok = None
    for item in html('item'):
        title = item.find('title')
        if title is None: continue
        title = title.text
        #
        ## now check if the sXXeYY in name
        if last_tok is not None:
            if last_tok not in title.lower( ): continue
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
        myitem = { 'title' : title,
                   'rawtitle' : title,
                   'seeders' : seeders,
                   'leechers' : leechers,
                   'link' : magnet_url }
        if torrent_size is not None:
            myitem[ 'title' ] = '%s (%0.1f MiB)' % ( title, torrent_size )
            myitem[ 'torrent_size' ] = torrent_size
        pubdate_elem = item.find( 'pubdate' )
        if pubdate_elem is not None:
            try:
                pubdate_s = pubdate_elem.get_text( ).split(',')[-1].strip( )
                pubdate_s = ' '.join( pubdate_s.split()[:3] )
                pubdate = datetime.datetime.strptime(
                    pubdate_s, '%d %B %Y' ).date( )
                myitem[ 'pubdate' ] = pubdate
            except: pass
        items.append( myitem )

    items = sorted(items, key = lambda elem: elem['seeders'] + elem['leechers' ] )[::-1]
    #
    ## now perform the filtering
    def _filter_minmax_size( minSize, minSize_x265, maxSize, maxSize_x265, item ):
        if minSize is not None and 'x265' not in item['rawtitle'].lower( ) and item['torrent_size'] <= minSize:
            return False
        if minSize_x265 is not None and 'x265' in item['rawtitle'].lower( ) and item['torrent_size'] <= minSize_x265:
            return False
        if maxSize is not None and 'x265' not in item['rawtitle'].lower( ) and item['torrent_size'] >= maxSize:
            return False
        if maxSize_x265 is not None and 'x265' in item['rawtitle'].lower( ) and item['torrent_size'] >= minSize_x265:
            return False
        return True
    
    if any(map(lambda tok: tok is not None, [ minsizes, maxsizes ])):
        items = list(filter(lambda item: 'torrent_size' in item, items ))
        minsize = None
        minsize_x265 = None
        maxsize = None
        maxsize_x265 = None
        if minsizes is not None:
            if len( minsizes ) >= 2: minsize, minsize_x265 = minsizes[:2]
            else: minsize, minsize_x265 = 2 * [ minsizes[0] ]
        if maxsizes is not None:
            if len( maxsizes ) >= 2: maxsize, maxsize_x265 = maxsizes[:2]
            else: maxsize, maxsize_x265 = 2 * [ maxsizes[0] ]
        items = list(filter(lambda item: _filter_minmax_size(
            minsize, minsize_x265, maxsize, maxsize_x265, item ), items ) )
    if len( keywords ) != 0:
        items = list(filter(lambda item: any(map(lambda tok: tok.lower( ) in item['rawtitle'].lower( ), keywords ) ) and
                            not any(map(lambda tok: tok.lower( ) in item['rawtitle'].lower( ), keywords_exc ) ) and
                            all(map(lambda tok: tok.lower( ) in item['rawtitle'].lower( ), must_have ) ),
                            items ) )
    if len( items ) == 0:
        return return_error_raw( 'FAILURE, NO TV SHOWS OR SERIES SATISFYING CRITERIA FOR GETTING %s' % name )
        
    return items[:maxnum], 'SUCCESS'

def get_tv_torrent_kickass( name, maxnum = 10, verify = True ):
    """
    Returns a :py:class:`tuple` of candidate episode Magnet links found using the KickAssTorrents_ torrent service and the string ``"SUCCESS"``, if successful.

    :param str name: the episode string on which to search.
    :param int maxnum: optional argument, the maximum number of magnet links to return. Default is 10. Must be :math:`\ge 5`.
    :param bool verify:  optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: if successful, then returns a two member :py:class:`tuple` the first member is a :py:class:`list` of elements that match the searched episode, ordered from *most* seeds and leechers to least. The second element is the string ``"SUCCESS"``. The keys in each element of the list are,

      * ``title`` is *only* the name of the candidate episode to download.
      * ``seeders`` is the number of seeds for this Magnet link.
      * ``leechers`` is the number of leeches for this Magnet link.
      * ``link`` is the Magnet URI link.
    
    If this is unsuccessful, then returns an error :py:class:`tuple` of the form returned by :py:meth:`return_error_raw <plexcore.return_error_raw>`.
    
    :rtype: tuple
    
    .. warning:: cannot get it to work as of |date|. Cannot get it to work when giving it valid episode searches, such as ``"The Simpsons S31E01"``. See :numref:`table_working_tvtorrents`.
    
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
        lookups = [ ]
        data = Search( name, category = CATEGORY.TV )
        for page in range(1, min( 11, 1 + int( data.url.max_page ) ) ):
            data.url.set_page( page )
            lookups += list( filter(lambda lookup: get_maximum_matchval( lookup.name, name ) >= 90 and
                                lookup.torrent_link is not None, data.list( ) ) )
        lookups = sorted( lookups, key = lambda lookup: get_maximum_matchval( lookup.name, name ) )[:maxnum]
        #lookups = sorted( filter(lambda lookup: #'720p' in lookup.name and
        #                         # get_size( lookup ) >= 100.0 and
        #                         get_maximum_matchval( lookup.name, name ) >= 90 and
        #                         lookup.torrent_link is not None,
        #                         Search( name, category = CATEGORY.TV ) ),
        #                  key = lambda lookup: get_size( lookup ) )[:maxnum]
        if len(lookups) == 0: return return_error_raw(
                'FAILURE, COULD FIND NOTHING THAT MATCHES %s' % name )
    except Exception as e:
        return return_error_raw( 'FAILURE: %s' % e )

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

def get_tv_torrent_tpb( name, maxnum = 10, doAny = False, verify = True ):
    """
    Returns a :py:class:`tuple` of candidate episode Magnet links found using the `The Pirate Bay`_ torrent service and the string ``"SUCCESS"``, if successful.

    :param str name: the episode string on which to search.
    :param int maxnum: optional argument, the maximum number of magnet links to return. Default is 100. Must be :math:`\ge 5`.
    :param bool doAny: optional argument. If ``True``, then only search through TV shows. Otherwise, search through all media.
    :param bool verify:  optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: if successful, then returns a two member :py:class:`tuple` the first member is a :py:class:`list` of elements that match the searched episode, ordered from *most* seeds and leechers to least. The second element is the string ``"SUCCESS"``. The keys in each element of the list are,

      * ``title`` is *only* the name of the candidate episode to download.
      * ``seeders`` is the number of seeds for this Magnet link.
      * ``leechers`` is the number of leeches for this Magnet link.
      * ``link`` is the Magnet URI link.
      * ``torrent_size`` is the size of this torrent in bytes.
    
    If this is unsuccessful, then returns an error :py:class:`tuple` of the form returned by :py:meth:`return_error_raw <plexcore.return_error_raw>`.
    
    :rtype: tuple

    .. warning:: cannot get it to work as of |date|. Cannot get it to work when giving it valid episode searches, such as ``"The Simpsons S31E01"``. See :numref:`table_working_tvtorrents`.
    
    .. _`The Pirate Bay`: https://en.wikipedia.org/wiki/The_Pirate_Bay
    """
    
    #surl = urljoin( 'https://thepiratebay3.org', 's/' )
    surl = 'https://thepiratebay.org'
    assert( maxnum >= 5 )
    if not doAny:
        cat = CATEGORIES.VIDEO.TV_SHOWS
    else:
        cat = CATEGORIES.VIDEO.ALL
    search_params = { "q" : name, "type" : "search",
                      "orderby" : ORDERS.SIZE.DES, "page" : 0,
                      "category" : cat }

    response_arr = [ None, ]
    def fill_response( response_arr ):
        response_arr[ 0 ] = requests.get(
            surl, params = search_params, verify = verify )

    e = threading.Event( )
    t = threading.Thread( target = fill_response, args = ( response_arr, ) )
    t.start( )
    t.join( 30 )
    e.set( )
    t.join( )
    response = max( response_arr )
    if response is None: return return_error_raw( 'FAILURE TIMED OUT' )
    if response.status_code != 200:
        return return_error_raw( 'FAILURE STATUS CODE = %d' % response.status_code )
        
    def process_column_header(th):
        if th.a:
            return th.a.get_text(strip=True)
        if not result:
            return th.get_text(strip=True)

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

    html = BeautifulSoup( response.content, 'lxml' )
    torrent_table = html.find("table", id="searchResult")
    torrent_rows = torrent_table("tr") if torrent_table else []
    if len( torrent_rows ) < 2:
        return return_error_couldnotfind( name )
    labels = list(map(lambda label: process_column_header(label),
                      torrent_rows[0]("th") ) )
    items = []
    for result in torrent_rows[1:]:
        try:
            cells = result('td')
            
            title = result.find(class_='detName').get_text(strip = True )
            download_url = result.find(title='Download this torrent using magnet')['href']
            if 'magnet:?' not in download_url:
                continue
            if not all([ title, download_url ]):
                continue
            seeders = try_int(cells[labels.index("SE")].get_text(strip=True))
            leechers = try_int(cells[labels.index("LE")].get_text(strip=True))
            #
            ## Convert size after all possible skip scenarios
            torrent_size = cells[labels.index("Name")].find(class_="detDesc").get_text(strip=True).split(", ")[1]
            torrent_size = re.sub(r"Size ([\d.]+).+([KMGT]iB)", r"\1 \2", torrent_size)
            #size = convert_size(torrent_size, units = ["B", "KB", "MB", "GB", "TB", "PB"]) or -1
            size = torrent_size
            item = { 'title': title,
                     'link': download_url,
                     'torrent_size': size,
                     'seeders': seeders,
                     'leechers': leechers }
            #item = {'title': title, 'link': download_url, 'seeders': seeders, 'leechers': leechers }
            items.append(item)
        except Exception as e:
            print( str( e ) )
            continue
    if len( items ) == 0:
        return return_error_couldnotfind( name )
    items.sort(key=lambda d: try_int(d.get('seeders', 0)) +
               try_int(d.get('leechers')), reverse=True)
    return items[:maxnum], 'SUCCESS'

def _finish_and_clean_working_tvtorrent_download( totFname, client, torrentId, tor_info ):
    from fabric import Connection
    media_file = max(tor_info[b'files'], key = lambda elem: elem[b'size'] )
    file_name = os.path.join( 'downloads', media_file[b'path'].decode('utf-8') )
    suffix = os.path.basename( file_name ).split('.')[-1].strip( )
    new_file = os.path.join( 'downloads', '%s.%s' % ( os.path.basename( totFname ), suffix ) )
    uname = client.username
    password = client.password
    host = client.host    
    with Connection( host, user = uname, connect_kwargs =
                     { 'password' : password } ) as conn:
        if 'key_filename' in conn.connect_kwargs:
            conn.connect_kwargs.pop( 'key_filename' )
        #
        ## first copy the file from src to destination
        cmd = 'cp "%s" "%s"' % ( file_name, new_file )
        try: r = conn.run( cmd, hide = True )
        except: return return_error_raw(
                'ERROR, could not properly run %s.' % cmd )
        cmd = 'chmod 644 "%s"' % new_file
        try: r = conn.run( cmd, hide = True )
        except: return return_error_raw(
                'ERROR, could not properly run %s.' % cmd )
        #
        ## if ends in mp4
        if suffix == 'mp4':
            cmd = '~/.local/bin/mp4tags -s "" "%s"' % new_file
            try: r = conn.run( cmd, hide = True )
            except: return return_error_raw(
                    'Error, could not properly run %s.' % cmd )
            #
            ## check for some ENGLISH srt files. If found, then do the following
            # 1) locate the SRT file with name ENGLISH in it
            # 2) if found, then convert file to mkv. Delete old file.
            # 3) mkvmerge out into a 'defaultXXXX.mkv', then copy over 'defaultXXXX.mkv' to new new file
            # 4) remove the temporary 'defaultXXXX.mkv' file
            
        #
        ## now delete the deluge connection
        plexcore_deluge.deluge_remove_torrent( client, [ torrentId ], remove_data = True )
        return '%s.%s' % ( os.path.basename( totFname ), suffix ), 'SUCCESS'

def _create_status_dict( status, status_message, time0 ):
    assert( status in ('SUCCESS', 'FAILURE' ) )
    return {
        'status' : status,
        'message' : status_message,
        'time' : time.time( ) - time0
    }
    
def _worker_process_tvtorrents( client, data, torFileName, totFname,
                                maxtime_in_secs, num_iters, kill_if_fail ):
    time0 = time.time( )
    failing_reasons = [ ]
    numiters, rem = divmod( maxtime_in_secs, 30 )
    if rem != 0: numiters += 1

    def kill_failing( torrentId ):
        if not kill_if_fail: return
        plexcore_deluge.deluge_remove_torrent( client, [ torrentId ], remove_data = kill_if_fail )

    
    def process_single_iteration( data, idx ):
        mag_link = data[ idx ]['link']
        #
        ## download the top magnet link
        torrentId = plexcore_deluge.deluge_add_magnet_file( client, mag_link )
        if torrentId is None:
            return None, _create_status_dict(
                'FAILURE',
                'could not add idx = %s, magnet_link = %s, for candidate = %s' % (
                    idx, mag_link, torFileName ), time0 )
        time00 = time.time( )
        progresses = [ ]
        for jdx in range( numiters ):
            time.sleep( 30 )
            torrent_info = plexcore_deluge.deluge_get_torrents_info( client )
            if torrentId not in torrent_info:
                kill_failing( torrentId )
                return None, _create_status_dict( 'FAILURE', 'ERROR, COULD NOT GET IDX = %d, TORRENT ID = %s.' % (
                    idx, torrentId.decode('utf-8').lower()[:6] ), time00 )
            tor_info = torrent_info[ torrentId ]
            status = tor_info[ b'state'].decode('utf-8').upper( )
            progress = tor_info[ b'progress']
            print( 'after %0.3f seconds, attempt #%d, for %s: status = %s, progress = %0.1f%%' % (
                time.time( ) - time00, idx + 1, torFileName, status, progress ) )
            progresses.append( progress )
            # quit after too many no-progress iterations?
            if len( progresses ) > _num_to_quit and numpy.allclose( progresses, [ 0.0 ] * len( progresses ) ):
                kill_failing( torrentId )
                return None, _create_status_dict(
                    'FAILURE',
                    'attempt #%d, magnet_link = %s, for candidate = %s, is probably not downloading' % (
                        idx, mag_link, torFileName ), time00 )
            if status in ( 'SEEDING', 'PAUSED' ): # now let's be ambitious and create the new file
                fullFname, status = _finish_and_clean_working_tvtorrent_download(
                    totFname, client, torrentId, tor_info )
                if status != 'SUCCESS':
                    kill_failing( torrentId )
                    return None, _create_status_dict( 'FAILURE', status, time0 )
                return fullFname, _create_status_dict(
                    'SUCCESS',
                    'attempt #%d successfully downloaded %s' % (
                        idx + 1, torFileName ), time00 )
        #
        ## did not finish in time
        kill_failing( torrentId )
        return None, _create_status_dict(
            'FAILURE',
            'failed to download idx = %d, %s after %0.3f seconds' % (
                idx, torFileName, time.time( ) - time00 ), time00 )
    for idx in range( min( len( data ), num_iters ) ):
        dat, status_dict = process_single_iteration( data, idx )
        if dat is not None:
            return dat, status_dict
        failing_reasons.append( status_dict[ 'message' ] )
    #
    ## final failing condition
    return None, _create_status_dict( 'FAILURE','\n'.join( failing_reasons ), time0 )
    
def worker_process_download_tvtorrent(
        tvTorUnit, client = None, maxtime_in_secs = 14400, 
        num_iters = 1, kill_if_fail = False ):
    """
    Used by, e.g., :ref:`get_plextvdb_batch.py`, to download missing episodes on the Plex_ TV library. Attempts to use the Deluge_ server, specified in :numref:`Seedhost Services Setup`, to download an episode. If successful then uploads the finished episode from the remote SSH server to the Plex_ server and local directory, specified in :numref:`Local and Remote (Seedhost) SSH Setup`.

    :param dict tvTorUnit: a :py:class:`dict` representing a summarized magnet link searching operation on an episode. The format and meaning of this data structure is described in :py:meth:`create_tvTorUnits <plextvdb.plextvdb.create_tvTorUnits>`.
    :param DelugeRPC client: optional argument, the `DelugeRPCClient <Deluge RPC client_>`_ object that at a low level uses the Deluge_ server to download the Magnet link at the remote SSH server. If ``None``, then this client is created using :py:meth:`get_deluge_client <plexcore.plexcore_deluge.get_deluge_client>`.
    :param int maxtime_in_secs: optional argument, the maximum time to wait for a Magnet link found by the Jackett_ server to fully download through the Deluge_ server. Must be :math:`\ge 60` seconds. Default is 14400 seconds.
    :param int num_iters: optional argument, the maximum number of Magnet links to try and fully download before giving up. The list of Magnet links to try for each missing episode is ordered from *most* seeders + leechers to *least*. Must be :math:`\ge 1`. Default is 1.
    :param bool kill_if_fail: optional argument. If ``True``, then on failing operation kill the torrent download on the Deluge_ server and delete any files associated with it. If ``False``, then keep the torrent download on failure.

    :returns: If successful, creates a two element :py:class:`tuple`: the first element is the base name of the episode that is uploaded to the Plex_ server, and the second element is a status :py:class:`dictionary <dict>` with three keys.

       * the ``status`` is ``"SUCCESS"``.
       * the ``message`` describes the final status of the operation.
       * the ``time`` tells how long, in seconds, the successful operation took.

       If unsuccessful, returns a failing tuple: the first element is ``None``, and the the second element is a status :py:class:`dictionary <dict>` with three keys.
    
       * the ``status`` is ``"FAILURE"``.
       * the ``message`` describes the illuminating reason as to how this operation failed.
       * the ``time`` tells how long, in seconds, the failing operation took.

    :rtype: tuple
    
    .. seealso::
       
        * :ref:`get_plextvdb_batch.py`.
        * :py:meth:`get_remaining_episodes <plextvdb.plextvdb.get_remaining_episodes>`.
        * :py:meth:`create_tvTorUnits <plextvdb.plextvdb.create_tvTorUnits>`.
        * :py:meth:`download_batched_tvtorrent_shows <plextvdb.plextvdb.download_batched_tvtorrent_shows>`.

    .. _`Deluge RPC client`: https://github.com/JohnDoee/deluge-client
    .. _Deluge: https://en.wikipedia.org/wiki/Deluge_(software)
    """
    
    time0 = time.time( )
        
    assert( maxtime_in_secs > 0 )
    #
    if client is None:
        client, status = plexcore_deluge.get_deluge_client( )
        if client is None:
            return None, _create_status_dict(
                'FAILURE', 'cannot create or run a valid deluge RPC client.', time0 )
    #
    ## now get list of torrents, choose "top" one
    def _process_jackett_items( tvTorUnit, shared_list ):
        t0 = time.time( )
        torFileName = tvTorUnit[ 'torFname' ]
        totFname = tvTorUnit[ 'totFname' ]
        minSize = tvTorUnit[ 'minSize' ]
        maxSize = tvTorUnit[ 'maxSize' ]
        minSize_x265 = tvTorUnit[ 'minSize_x265' ]
        maxSize_x265 = tvTorUnit[ 'maxSize_x265' ]
        series_name = tvTorUnit[ 'tvshow' ]
        mustHaveString = torFileName.split( )[ -1 ]
        do_raw = tvTorUnit[ 'do_raw' ]
        logging.info( 'jackett start: %s, %s, %s' % (
            torFileName, mustHaveString, series_name ) )
        #
        data, status = get_tv_torrent_jackett(
            torFileName, maxnum = 100, keywords = [ 'x264', 'x265', '720p' ],
            minsizes = [ minSize, minSize_x265 ],
            maxsizes = [ maxSize, maxSize_x265 ],
            keywords_exc = [ 'xvid' ], raw = do_raw,
            must_have = [ mustHaveString ] )
        if status != 'SUCCESS':
            shared_list.append( ( 'jackett', _create_status_dict( 'FAILURE', status, t0 ), 'FAILURE' ) )
            return
        logging.info( 'successfully processed jackett on %s in %0.3f seconds.' % (
            torFileName, time.time( ) - t0 ) )
        shared_list.append( ( 'jackett', data, 'SUCCESS' ) )
    #
    def _process_eztv_io_items( tvTorUnit, shared_list ):
        t0 = time.time( )
        torFileName = tvTorUnit[ 'torFname' ]
        totFname = tvTorUnit[ 'totFname' ]
        minSize = tvTorUnit[ 'minSize' ]
        maxSize = tvTorUnit[ 'maxSize' ]
        minSize_x265 = tvTorUnit[ 'minSize_x265' ]
        maxSize_x265 = tvTorUnit[ 'maxSize_x265' ]
        series_name = tvTorUnit[ 'tvshow' ]
        mustHaveString = torFileName.split( )[ -1 ]
        logging.info( 'eztv.io start: %s' % torFileName )
        #
        data, status = get_tv_torrent_eztv_io(
            torFileName, maxnum = 100, series_name = series_name,
            minsizes = [ minSize, minSize_x265],
            maxsizes = [ maxSize, maxSize_x265] )
        if status != 'SUCCESS':
            shared_list.append(
                ( 'eztv.io', _create_status_dict( 'FAILURE', status, time0 ), 'FAILURE' ) )
            return
        data_filt = list(filter(
            lambda elem: any(map(lambda tok: tok in elem['title'].lower( ),
                                 ( 'x264', 'x265', '720p' ) ) ) and
            'xvid' not in elem['title'].lower( ), data ) )
        if len( data_filt ) == 0:
            shared_list.append(
                ( 'eztv.io', _create_status_dict(
                    'FAILURE', 'ERROR, COULD NOT FIND %s IN EZTV.IO.' % torFileName, t0 ), 'FAILURE' ) )
            return
        logging.info( 'successfully processed eztv.io on %s in %0.3f seconds.' % (
            torFileName, time.time( ) - t0 ) )
        shared_list.append( ( 'eztv.io', data_filt, 'SUCCESS' ) )
    #
    def _process_zooqle_items( tvTorUnit, shared_list ):
        t0 = time.time( )
        torFileName = tvTorUnit[ 'torFname' ]
        totFname = tvTorUnit[ 'totFname' ]
        minSize = tvTorUnit[ 'minSize' ]
        maxSize = tvTorUnit[ 'maxSize' ]
        minSize_x265 = tvTorUnit[ 'minSize_x265' ]
        maxSize_x265 = tvTorUnit[ 'maxSize_x265' ]
        series_name = tvTorUnit[ 'tvshow' ]
        mustHaveString = torFileName.split( )[ -1 ]
        logging.info( 'zooqle start: %s' % torFileName )
        #
        data, status = get_tv_torrent_zooqle( torFileName, maxnum = 100 )
        if status != 'SUCCESS':
            shared_list.append( ( 'zooqle', _create_status_dict( 'FAILURE', status, t0 ), 'FAILURE' ) )
            return
        data_filt = list(filter(
            lambda elem: any(map(lambda tok: tok in elem['title'].lower( ),
                                 ( 'x264', 'x265', '720p' ) ) ) and
            'xvid' not in elem['title'].lower( ) and
            elem['torrent_size'] >= minSize*1e6 and
            elem['torrent_size'] <= maxSize*1e6, data ) )
        if len( data_filt ) == 0:
            shared_list.append(
                ( 'zooqle', _create_status_dict(
                    'FAILURE', 'ERROR, COULD NOT FIND %s IN ZOOQLE.' % torFileName, t0 ), 'FAILURE' ) )
        logging.info( 'successfully processed zooqle on %s in %0.3f seconds.' % (
            torFileName, time.time( ) - t0 ) )
        shared_list.append( ( 'zooqle', data_filt, 'SUCCESS' ) )

    m = Manager( )
    shared_list = m.list( )
    jobs = [ ]
    for targ in ( _process_jackett_items, _process_eztv_io_items, _process_zooqle_items ):
        job = Process( target = targ, args = ( tvTorUnit, shared_list ) )
        job.daemon = False
        jobs.append( job )
        job.start( )
    for job in jobs: job.join( )
    for job in jobs: job.close( )
    #shared_list = list(map(
    #    lambda proc: proc( tvTorUnit ),
    #    ( _process_jackett_items, _process_eztv_io_items, _process_zooqle_items ) ) )
    error_tup = list(map(
        lambda dat: ( dat[0], dat[1] ), filter(lambda dat: dat[-1] == 'FAILURE', shared_list ) ) )
    data = list( chain.from_iterable( map(lambda dat: dat[1],
                                          filter(lambda dat: dat[-1] == 'SUCCESS', shared_list ) ) ) )
    #
    ## status of downloaded elements
    torFileName = tvTorUnit[ 'torFname' ]
    totFname = tvTorUnit[ 'totFname' ]
    if len( data ) == 0:
        return None, dict( error_tup )
    print( 'got %d candidates for %s in %0.3f seconds.' % (
        len(data), torFileName, time.time( ) - time0 ) )
    #
    ## wrapped away in another method
    return _worker_process_tvtorrents(
        client, data, torFileName, totFname,
        maxtime_in_secs, num_iters, kill_if_fail )
