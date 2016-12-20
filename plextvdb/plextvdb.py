import requests, os, sys, json, re
import multiprocessing, datetime, time

_apiKey = '0B3F6D72213D71C8'
_usrKey = 'AEE839E62568BA63'
_usname = '***REMOVED***islam1978'

def get_token( verify = True ):
    data = { 'apikey' : _apiKey,
             'username' : _usname,
             'userkey' : _usrKey }
    with requests.Session( ) as s:
        s.headers = { 'Content-Type' : 'application/json' }
        response = s.post( 'https://api.thetvdb.com/login',
                           data = json.dumps( data ),
                           verify = verify )
        if response.status_code != 200:
            return None
        outdata = response.json( )
        return outdata[ 'token' ]

def refresh_token( token ):
    with requests.Session( ) as s:
        s.headers = { 'Content-Type' : 'application/json',
                      'Authorization' : 'Bearer %s' % token }
        response = s.get( 'https://api.thetvdb.com/refresh_token' )
        if response.status_code != 200:
            return None
        return response.json( )['token']

def get_series_id( series_name, token ):    
    with requests.Session( ) as s:
        params = { 'name' : series_name }
        s.headers = { 'Content-Type' : 'application/json',
                      'Authorization' : 'Bearer %s' % token }
        response = s.get( 'https://api.thetvdb.com/search/series',
                          params = params )
        if response.status_code != 200:
            return None
        data = response.json( )[ 'data' ]
        return data[0]['id']

def get_possible_ids( series_name, token ):
    with requests.Session( ) as s:
        params = { 'name' : series_name }
        s.headers = { 'Content-Type' : 'application/json',
                      'Authorization' : 'Bearer %s' % token }
        response = s.get( 'https://api.thetvdb.com/search/series',
                          params = params )
        if response.status_code != 200:
            return None
        data = response.json( )[ 'data' ]
        return map(lambda dat: dat['id'], data )

def get_episode_name( series_id, airedSeason, airedEpisode, token ):
    with requests.Session( ) as s:
        params = { 'page' : 1,
                   'airedSeason' : '%d' % airedSeason,
                   'airedEpisode' : '%d' % airedEpisode }
        s.headers = { 'Content-Type' : 'application/json',
                      'Authorization' : 'Bearer %s' % token }
        response = s.get( 'https://api.thetvdb.com/series/%d/episodes/query' % series_id,
                          params = params )
        if response.status_code != 200:
            return None
        data = max( response.json( )[ 'data' ] )
        return data[ 'episodeName' ]

def get_episodes_series( series_id, token, showSpecials = True, fromDate = None ):
    with requests.Session( ) as s:
        params = { 'page' : 1 }
        s.headers = { 'Content-Type' : 'application/json',
                      'Authorization' : 'Bearer %s' % token }
        response = s.get( 'https://api.thetvdb.com/series/%d/episodes' % series_id,
                          params = params )
        if response.status_code != 200:
            return None
        data = response.json( )
        links = data[ 'links' ]
        lastpage = links[ 'last' ]
        seriesdata = data[ 'data' ]
        for pageno in range( 2, lastpage + 1 ):
            response = s.get( 'https://api.thetvdb.com/series/%d/episodes' % series_id,
                              params = { 'page' : pageno } )
            data = response.json( )
            seriesdata += data[ 'data' ]
        currentDate = datetime.datetime.now( ).date( )
        sData = [ ]
        for episode in seriesdata:
            try:
                date = datetime.datetime.strptime( episode['firstAired'], '%Y-%m-%d' ).date( )
                if date >= currentDate:
                    continue
                if fromDate is not None:
                    if date < fromDate:
                        continue
            except Exception:
                continue
            if episode[ 'airedSeason' ] is None:
                continue
            if not showSpecials and episode[ 'airedSeason' ] == 0:
                continue
            sData.append( episode )
        return sData

"""
Format of the datestring is January 1, 2016
"""
def get_series_updated_fromdate( date, token ):
    try:
        dt = datetime.datetime(
            year = date.year,
            month = date.month,
            day = date.day )
        epochtime = int( time.mktime( dt.utctimetuple( ) ) )
    except Exception as e:
        print(e)
        return None
    #
    ##
    with requests.session( ) as s:
        s.headers = { 'Content-Type' : 'application/json',
                      'Authorization' : 'Bearer %s' % token }
        response = s.get( 'https://api.thetvdb.com/updated/query',
                          params = { 'fromTime' : epochtime })
        if response.status_code != 200:
            return None
        return response.json( )['data']

def _get_remaining_eps_perproc( input_tuple ):
    name, series_id, epsForShow, token, showSpecials, fromDate = input_tuple
    eps = get_episodes_series( series_id, token, showSpecials = showSpecials )
    tvdb_eps = set(map(lambda ep: ( ep['airedSeason'], ep['airedEpisodeNumber' ] ), eps ) )
    here_eps = set([ ( seasno, epno ) for seasno in epsForShow for
                     epno in epsForShow[ seasno ] ] )
    tuples_to_get = tvdb_eps - here_eps
    if len( tuples_to_get ) == 0:
        return None
    return name, sorted( tuples_to_get )

def _get_series_id_perproc( input_tuple ):
    show, token = input_tuple
    return show, get_series_id( show, token )
    
def get_remaining_episodes( tvdata, showSpecials = True, fromDate = None ):
    token = get_token( )
    pool = multiprocessing.Pool( processes = multiprocessing.cpu_count( ) )
    tvshow_id_map = dict( pool.map( _get_series_id_perproc,
                                    map(lambda show: ( show, token ), tvdata ) ) )
    if fromDate is not None:
        data = get_series_updated_fromdate( fromDate, token )
        series_ids = set( map(lambda tup: tup['id'], data ) )
        ids_tvshows = dict(map( lambda tup: ( tup[1], tup[0] ), tvshow_id_map.items( ) ) )
        updated_ids = set( ids_tvshows.keys( ) ) & series_ids
        tvshow_id_map = { ids_tvshows[ series_id ] : series_id for series_id in
                          updated_ids }
        print(len(tvshow_id_map ) )
    input_tuples = map(lambda name: ( name, tvshow_id_map[ name ], tvdata[ name ], token,
                                      showSpecials, fromDate ), tvshow_id_map )                       
    pool = multiprocessing.Pool( processes = multiprocessing.cpu_count( ) )
    toGet = dict( filter( None, pool.map( _get_remaining_eps_perproc, input_tuples ) ) )
    return toGet
                                
def get_tot_epdict_tvdb( showName ):
    token = get_token( )
    id = get_series_id( showName, token )
    eps = get_episodes_series( id, token )
    totseasons = max( map(lambda episode: int( episode['airedSeason' ] ), eps ) )
    tot_epdict = { }
    for episode in eps:
        seasnum = int( episode[ 'airedSeason' ] )
        if seasnum == 0: continue
        epno = episode[ 'airedEpisodeNumber' ]
        title = episode[ 'episodeName' ]
        tot_epdict.setdefault( seasnum, { } )
        tot_epdict[ seasnum ][ epno ] = title
    return tot_epdict

def get_tot_epdict_singlewikipage(epURL, seasnums = 1, verify = True):
    import lxml.html, titlecase
    assert(seasnums >= 1)
    assert(isinstance(seasnums, int))
    #
    def is_epelem(elem):
        if elem.tag == 'span':
            if 'class' not in elem.keys():
                return False
            if 'id' not in elem.keys():
                return False
            if elem.get('class') != 'mw-headline':
                return False
            if 'Season' not in elem.get('id'):
                return False
            return True
        elif elem.tag == 'td':
            if 'class' not in elem.keys():
                return False
            if 'style' not in elem.keys():
                return False
            if elem.get('class') != 'summary':
                return False
            return True
        return False
    #
    tree = lxml.html.fromstring(requests.get(epURL, verify=verify).content )    
    epelems = filter(is_epelem, tree.iter())
    #
    ## splitting by seasons
    idxof_seasons = list(zip(*filter(lambda tup: tup[1].tag == 'span',
                                     enumerate(epelems)))[0]) + \
        [ len(epelems) + 1, ]
    totseasons = len(idxof_seasons) - 1
    assert( seasnums <= totseasons )
    return { idx + 1 : titlecase.titlecase( epelem.text_content().replace('"','')) for
             (idx, epelem) in enumerate( epelems[idxof_seasons[seasnums-1]+1:idxof_seasons[seasnums]] ) }


def get_tv_torrent_torrentz( name, maxnum = 10 ):
    from bs4 import BeautifulSoup
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
    response = requests.get( url, params = search_params )
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
    import threading
    from tpb import CATEGORIES, ORDERS
    from bs4 import BeautifulSoup
    from requests.compat import urljoin
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
