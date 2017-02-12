import threading, requests, fuzzywuzzy, plextmdb
from tpb import CATEGORIES, ORDERS
from bs4 import BeautifulSoup
from requests.compat import urljoin

def get_movie_torrent_rarbg( name, maxnum = 10 ):
    tmdbid = plextmdb.get_movie_tmdbids( name )
    if tmdbid is None:
        return None, 'ERROR, could not find %s in themoviedb.'
    apiurl = "http://torrentapi.org/pubapi_v2.php"
    response = requests.get(apiurl,
                            params={ "get_token": "get_token",
                                     "format": "json",
                                     "app_id": "sickrage2" } )
    if response.status_code != 200:
        status = 'ERROR, problem with rarbg.to'
        return None, status
    token = response.json( )[ 'token' ]
    params = { 'mode' : 'search', 'search_themoviedb' : tmdbid, 'token' : token,
               'response_type' : 'json', 'limit' : 100 }
    response = requests.get( apiurl, params = params )
    data = response.json( )
    if 'torrent_results' not in data:
        status = 'ERROR, RARBG.TO could not find any torrents for %s.' % name            
        return None, status
    data = data['torrent_results']
    actdata = map(lambda item: ( item['filename'], 1, 1, item['download'] ), data )
    return actdata, 'SUCCESS'
        
def get_movie_torrent_tpb( name, maxnum = 10, doAny = False ):
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

    surl = urljoin( 'https://thepiratebay.se', 's/' )
    if not doAny:
        cat = CATEGORIES.VIDEO.MOVIES
    else:
        cat = CATEGORIES.VIDEO.ALL
    search_params = { "q" : name, "type" : "search",
                      "orderby" : ORDERS.SIZE.DES, "page" : 0,
                      "category" : cat }
    response = requests.get( surl, params = search_params )
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

    html = BeautifulSoup( response.content, 'lxml' )
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
    except Exception as e:
        return None, 'FAILURE: ', e
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
    #print movies
    #if beforeYear is not None:
    #    movies = filter(lambda movie: int(movie['year']) <= beforeYear, movies )
    # alldata = { }
    # for actmov in movies:
    #     title = actmov['title']
    #     url = list(filter(lambda tor: 'quality' in tor and '3D' not in tor['quality'],
    #                       actmov['torrents']))[0]['url']
    #    alldata[ title ] = requests.get( url, verify = verify ).content
    return movies, 'SUCCESS'
