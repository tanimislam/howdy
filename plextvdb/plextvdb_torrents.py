import requests, re, threading, plextvdb
from bs4 import BeautifulSoup
from tpb import CATEGORIES, ORDERS
from requests.compat import urljoin
from plexemail.plexemail import get_formatted_size

def get_tv_torrent_zooqle( name, maxnum = 10 ):
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
    response = requests.get( fullurl )
    if response.status_code != 200:
        return None, 'ERROR, COULD NOT FIND ZOOQLE TORRENTS FOR %s' % candname
    myxml = BeautifulSoup( response.content, 'lxml' )
    cand_items = filter(lambda elem: len( elem.find_all('title' ) ) >= 1 and
                        len( elem.find_all('torrent:infohash' ) ) >= 1 and
                        len( elem.find_all('torrent:seeds' ) ) >= 1 and
                        len( elem.find_all('torrent:peers' ) ) >= 1 and
                        len( elem.find_all('torrent:contentlength' ) ) >= 1,
                        myxml.find_all('item'))
    items_toshow = map(lambda elem: { 'title' : '%s (%s)' % ( max( elem.find_all('title' ) ).get_text( ),
                                                              get_formatted_size( int( max( elem.find_all('torrent:contentlength')).get_text( ) ) ) ),
                                      'seeders' : int( max( elem.find_all('torrent:seeds') ).get_text( ) ),
                                      'leechers' : int( max( elem.find_all('torrent:peers' ) ).get_text( ) ),
                                      'link' : _get_magnet_link( max( elem.find_all('torrent:infohash' ) ).get_text( ).lower( ),
                                                                 max( elem.find_all('title' ) ).get_text( ) ) },
                       cand_items )
    if len( items_toshow ) == 0:
        return None, 'ERROR, COULD NOT FIND ZOOQLE TORRENTS FOR %s' % candname
    return sorted( items_toshow, key = lambda item: -item['seeders'] - item['leechers'] )[:maxnum], 'SUCCESS'

def get_tv_torrent_rarbg( name, maxnum = 10, verify = True ):
    candidate_seriesname = ' '.join( name.strip().split()[:-1] )
    epstring = name.strip().split()[-1].upper()
    if not epstring[0] == 'S':
        status = 'Error, first string must be an s or S.'
        return None, status
    epstring = epstring[1:]
    splitseaseps = epstring.split('E')[:2]
    if len( splitseaseps ) != 2:
        status = 'Error, string must have a SEASON and EPISODE part.'
        return None, status
    try:
        seasno = int( splitseaseps[0] )
    except:
        status = 'Error, invalid season number.'
        return None, status
    try:
        epno = int( splitseaseps[1] )
    except:
        status = 'Error, invalid episode number.'
        return None, status
    
    tvdb_token = plextvdb.get_token( verify = verify )
    series_id = plextvdb.get_series_id( candidate_seriesname, tvdb_token,
                                        verify = verify )
    if series_id is None:
        series_ids = plextvdb.get_possible_ids( candidate_seriesname,
                                                tvdb_token, verify = verify )
        if series_ids is None or len( series_ids ) == 0:
            status = 'ERROR, PLEXTVDB could find no candidate series that match %s' % \
                     candidate_seriesname
            return None, status
        series_id = series_ids[ 0 ]
    apiurl = "http://torrentapi.org/pubapi_v2.php"
    response = requests.get(apiurl,
                            params={ "get_token": "get_token",
                                     "format": "json",
                                     "app_id": "sickrage2" }, verify = verify )
    if response.status_code != 200:
        status = 'ERROR, problem with rarbg.to'
        return None, status
    token = response.json( )[ 'token' ]
    params = { 'mode' : 'search', 'search_tvdb' : series_id, 'token' : token,
               'response_type' : 'json', 'search_string' : 'E'.join( splitseaseps ), 'limit' : 100 }
    response = requests.get( apiurl, params = params, verify = verify )
    data = response.json( )
    if 'torrent_results' not in data:
        status = 'ERROR, RARBG.TO could not find any torrents for %s %s.' % (
            candidate_seriesname, 'E'.join( splitseaseps ) )
        return None, status
    data = data['torrent_results']
    filtered_data = filter(lambda elem: 'E'.join( splitseaseps ) in elem['filename'] and
                           '720p' in elem['filename'] and 'HDTV' in elem['filename'], data )
    if len( filtered_data ) == 0:
        filtered_data = filter(lambda elem: 'E'.join( splitseaseps ) in elem['filename'], data )
    filtered_data = filtered_data[:maxnum]
    if len( filtered_data ) == 0:
        status = 'ERROR, RARBG.TO could not find any torrents for %s %s.' % (
            candidate_seriesname, 'E'.join( splitseaseps ) )
        return None, status
    items = map(lambda elem: { 'title' : elem['filename'], 'link' : elem['download'],
                               'seeders' : 1, 'leechers' : 1 }, filtered_data )
    return items, 'SUCCESS'

def get_tv_torrent_torrentz( name, maxnum = 10, verify = True ):
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
    response = requests.get( url, params = search_params, verify = verify )
    if response.status_code != 200:
        return None, 'FAILURE, request for %s did not work.' % name
    if not response.content.startswith('<?xml'):
        return None, 'ERROR, request content is not a valid XML block.'
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
        item = {'title': title, 'link': download_url, 'seeders': seeders,
                'leechers': leechers }
        items.append(item)
    if len( items ) == 0:
        return None, 'FAILURE, NO TV SHOWS OR SERIES SATISFYING CRITERIA'
    items.sort(key=lambda d: try_int(d.get('seeders', 0)) +
               try_int(d.get('leechers')), reverse=True)
    items = items[:maxnum]
    return map(lambda item: ( item['title'], item[ 'seeders' ], item[ 'leechers' ], item[ 'link' ] ),
               items ), 'SUCCESS'
    
def get_tv_torrent_tpb( name, maxnum = 10, doAny = False ):
    surl = urljoin( 'https://thepiratebay.se', 's/' )
    if not doAny:
        cat = CATEGORIES.VIDEO.TV_SHOWS
    else:
        cat = CATEGORIES.VIDEO.ALL
    search_params = { "q" : name, "type" : "search",
                      "orderby" : ORDERS.SIZE.DES, "page" : 0,
                      "category" : cat }

    response_arr = [ None, ]
    def fill_response( response_arr ):
        response_arr[ 0 ] = requests.get( surl, params = search_params )

    e = threading.Event( )
    t = threading.Thread( target = fill_response, args = ( response_arr, ) )
    t.start( )
    t.join( 30 )
    e.set( )
    t.join( )
    response = max( response_arr )
    if response is None:
        return None, 'FAILURE TIMED OUT'
    #response = requests.get( surl, params = search_params )
    if response.status_code != 200:
        return None, 'FAILURE STATUS CODE = %d' % response.status_code
        
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
        return None, 'FAILURE, NO MOVIES INITIALLY'
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
            
            # Convert size after all possible skip scenarios
            #torrent_size = cells[labels.index("Name")].find(class_="detDesc").get_text(strip=True).split(", ")[1]
            #torrent_size = re.sub(r"Size ([\d.]+).+([KMGT]iB)", r"\1 \2", torrent_size)
            #size = convert_size(torrent_size, units = ["B", "KB", "MB", "GB", "TB", "PB"]) or -1            
            #item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': ''}
            item = {'title': title, 'link': download_url, 'seeders': seeders, 'leechers': leechers }
            items.append(item)
        except Exception as e:
            print(e)
            continue
    if len( items ) == 0:
        return None, 'FAILURE, NO TV SHOWS OR SERIES SATISFYING CRITERIA'
    items.sort(key=lambda d: try_int(d.get('seeders', 0)) +
               try_int(d.get('leechers')), reverse=True)
    items = items[:maxnum]
    return map(lambda item: ( item['title'], item[ 'seeders' ], item[ 'leechers' ], item[ 'link' ] ),
               items ), 'SUCCESS'

def get_tv_torrent_best( name, maxnum = 10 ):
    items = [ ]
    assert( maxnum >= 5 )
    its, status = get_tv_torrent_tpb( name, maxnum = maxnum )
    if status == 'SUCCESS':
        print( len(its) )
        items = [ { 'title' : item[0], 'seeders' : item[1], 'leechers' : item[2], 'link' : item[3] } for
                  item in its ]
    its, status = get_tv_torrent_torrentz( name, maxnum = maxnum )
    print( status )
    if status == 'SUCCESS':
        items+= [ { 'title' : item[0], 'seeders' : item[1], 'leechers' : item[2], 'link' : item[3] } for
                  item in its ]
    print( 'LENGTH OF ALL ITEMS = %d' % len( items ) )
    if len( items ) == 0:
        print( "Error, could not find anything with name = %s" % name )
        return None, None # could find nothing
    item = max( items, key = lambda item: item['seeders'] + item['leechers'] )
    return item['title'], item[ 'link' ]
