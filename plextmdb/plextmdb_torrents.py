import threading, requests, fuzzywuzzy
from tpb import CATEGORIES, ORDERS
from bs4 import BeautifulSoup
from requests.compat import urljoin

def get_movie_torrent_tpb( name, maxnum = 10, doAny = False ):
    import threading
    surl = urljoin( 'https://thepiratebay.se', 's/' )
    if not doAny:
        cat = CATEGORIES.VIDEO.MOVIES
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
            #if not doAny:
            #    if 'x264' not in title.lower( ):
            #        continue
            #    if '720p' not in title.lower( ):
            #        continue
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
        except Exception:
            continue
    if len( items ) == 0:
        return None, 'FAILURE, NO MOVIES SATISFYING CRITERIA'
    items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
    items = items[:maxnum]
    return map(lambda item: ( item['title'], item[ 'seeders' ], item[ 'leechers' ], item[ 'link' ] ),
               items ), 'SUCCESS'

def get_movie_torrent_kickass( name, maxnum = 10 ):
    from KickassAPI import Search, Latest, User, CATEGORY, ORDER
    def get_size( lookup ):
        size_string = lookup.size
        if size_string.lower().endswith('mb'):
            return float( size_string.lower().split()[0] )
        elif size_string.lower().endswith('kb'):
            return float( size_string.lower().split()[0] ) / 1024
        elif size_string.lower().endswith('gb'):
            return float( size_string.lower().split()[0] ) * 1024
    try:
        lookups = sorted( filter(lambda lookup: '720p' in lookup.name and
                                 get_size( lookup ) >= 100.0 and
                                 lookup.torrent_link is not None,
                                 Search( name, category = CATEGORY.MOVIES ) ),
                          key = lambda lookup: get_size( lookup ) )[:maxnum]
        if len(lookups) == 0:
            return None, 'FAILURE'
    except Exception:
        return None, 'FAILURE'
    return map(lambda lookup: ( lookup.name, get_size( lookup ),
                                lookup.torrent_link ), lookups ), 'SUCCESS'
    
def get_movie_torrent( name, verify = True ):
    mainURL = 'https://yts.ag/api/v2/list_movies.json'
    params = { 'query_term' : name, 'order_by' : 'year' }
    response = requests.get( mainURL, params = params, verify = verify )
    if response.status_code != 200:
        return None, 'Error, could not use the movie service. Exiting...'
    data = response.json()['data']
    if 'movies' not in data or len(data['movies']) == 0:
        return None, "Could not find %s, exiting..." % name
    movies = data['movies']
    alldata = { }
    for actmov in movies:
        title = actmov['title']
        url = list(filter(lambda tor: 'quality' in tor and '3D' not in tor['quality'],
                          actmov['torrents']))[0]['url']
        alldata[ title ] = requests.get( url, verify = verify ).content
    return alldata, 'SUCCESS'
