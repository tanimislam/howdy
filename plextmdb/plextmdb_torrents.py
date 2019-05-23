import threading, requests, fuzzywuzzy, re, os, time, logging
from tpb import CATEGORIES, ORDERS
from bs4 import BeautifulSoup
from requests.compat import urljoin
from plexcore.plexcore import get_maximum_matchval, get_jackett_credentials
from plexcore import plexcore
from . import plextmdb

def _return_error_raw( msg ): return None, msg

def get_movie_torrent_jackett( name, maxnum = 10, verify = True ):
    time0 = time.time( )
    import validators
    data = get_jackett_credentials( )
    if data is None:
        return _return_error_raw('failure, could not get jackett server credentials')
    url, apikey = data
    endpoint = 'api/v2.0/indexers/all/results/torznab/api'
    response = requests.get( urljoin( url, endpoint ), verify = verify,
                             params = { 'apikey' : apikey, 'q' : name } ) # movies, no category filtering
    if response.status_code != 200:
        return _return_error_raw(
            ' '.join([ 'failure, problem with jackett server accessible at %s.' % url,
                       'Error code = %d. Error data = %s.' % (
                           response.status_code, response.content ) ] ) )
    logging.info( 'processed jackett torrents for %s in %0.3f seconds.' % (
        name, time.time( ) - time0 ) )
    html = BeautifulSoup( response.content, 'lxml' )
    if len( html.find_all('item') ) == 0:
        return _return_error_raw(
            'failure, no tv shows or series satisfying criteria for getting %s.' % name )
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
                                     filter(lambda elem: 'href' in elem.attrs and
                                            'magnet' in elem['href'], h2.find_all('a'))))
        if len( valid_magnet_links ) == 0: return None
        return max( valid_magnet_links )

    for item in html('item'):
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
            myitem[ 'title' ] = '%s (%0.1f MiB)' % ( title, torrent_size )
        myitem[ 'torrent_size' ] = torrent_size
        items.append( myitem )
    if len( items ) == 0:
        return _return_error_raw( 'FAILURE, NO TV SHOWS OR SERIES SATISFYING CRITERIA FOR GETTING %s' % name )
    return items[:maxnum], 'SUCCESS'

def get_movie_torrent_zooqle( name, maxnum = 10 ):
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
    response = requests.get( fullurl )
    if response.status_code != 200:
        return None, 'ERROR, COULD NOT FIND ZOOQLE TORRENTS FOR %s' % candname
    myxml = BeautifulSoup( response.content, 'lxml' )
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
            plexcore.get_formatted_size( get_num_forelem( elem, 'contentlength' ) ) ),
        'seeders' : get_num_forelem( elem, 'seeds' ),
        'leechers' : get_num_forelem( elem, 'peers' ),
        'link' : _get_magnet_link( get_infohash( elem ),
                                   max( elem.find_all('title' ) ).get_text( ) ) },
                       cand_items ) )
    if len( items_toshow ) == 0:
        return None, 'ERROR, COULD NOT FIND ZOOQLE TORRENTS FOR %s' % candname
    return sorted( items_toshow, key = lambda item: -item['seeders'] - item['leechers'] )[:maxnum], 'SUCCESS'

def get_movie_torrent_rarbg( name, maxnum = 10 ):
    tmdbid = plextmdb.get_movie_tmdbids( name )
    if tmdbid is None:
        return None, 'ERROR, could not find %s in themoviedb.' % name
    #
    ## got app_id and apiurl from https://www.rubydoc.info/github/epistrephein/rarbg/master/RARBG/API
    apiurl = "https://torrentapi.org/pubapi_v2.php"
    response = requests.get(apiurl,
                            params={ "get_token": "get_token",
                                     "format": "json",
                                     "app_id": "rarbg-rubygem" } )
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
    response = requests.get( apiurl, params = params )
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
            return '%s (%s)' % ( elem['title'], plexcore.get_formatted_size( elem[ 'size' ] ) )
        return '%s ()' % elem['title']
    actdata = list( map(lambda elem: { 'title' : get_title( elem ),
                                       'seeders' : get_num_seeders( elem ),
                                       'leechers' : get_num_leechers( elem ),
                                       'link' : elem['download'] }, data ) ) 
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

    surl = urljoin( 'https://thepiratebay3.org', 's/' )
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
    return list( map(lambda item: {
        'title' : item['title'],
        'seeders' : item[ 'seeders' ],
        'leechers' : item[ 'leechers' ],
        'link' : item[ 'link' ] }, items ) ), 'SUCCESS'

def get_movie_torrent_kickass( name, maxnum = 10 ):
    from KickassAPI import Search, Latest, User, CATEGORY, ORDER
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
