#!/usr/bin/env python2

import requests, fuzzywuzzy, re, codecs
from requests.compat import urljoin
from optparse import OptionParser
from KickassAPI import Search, Latest, User, CATEGORY, ORDER
from tpb import CATEGORIES, ORDERS
from bs4 import BeautifulSoup

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
        print('Error, could not use the movie service. Exiting...')
        return
    
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
        print('Error, could find no torrents with name %s' % name)
        return
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
            
            item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': ''}
            items.append(item)
        except Exception as e:
            continue
    if len( items ) == 0:
        print('Could not find %s, exiting...' % name)
        return
    items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
    items = items[:maxnum]
    if len( items ) != 1:
        sortdict = { idx + 1 : item for ( idx, item ) in enumerate(items) }
        bs = codecs.encode( 'Choose movie:\n%s\n' %
                            '\n'.join(map(lambda idx: '%d: %s (%d SE, %d LE)' % ( idx, sortdict[ idx ][ 'title' ],
                                                                                  sortdict[ idx ][ 'seeders' ],
                                                                                  sortdict[ idx ][ 'leechers' ]),
                                          sorted( sortdict ) ) ), 'utf-8' )
        iidx = raw_input( bs )
        try:
            iidx = int( iidx.strip( ) )
            if iidx not in sortdict:
                print('Error, need to choose one of the movie names. Exiting...')
                return
            magnet_link = sortdict[ iidx ][ 'link' ]
            actmov = sortdict[ iidx ][ 'title' ]
        except Exception:
            print('Error, did not give a valid integer value. Exiting...')
            return
    else:
        actmov = max( items )[ 'title' ]
        magnet_link = max( items )[ 'link' ]

    print('Chosen movie %s' % actmov )
    print('magnet link: %s' % magnet_link )

def get_movie_torrent_kickass( name, maxnum = 10, doAny = False ):
    assert( maxnum >= 5 )
    def get_size( lookup ):
        size_string = lookup.size
        if size_string.lower().endswith('mb'):
            return float( size_string.lower().split()[0] )
        elif size_string.lower().endswith('kb'):
            return float( size_string.lower().split()[0] ) / 1024
        elif size_string.lower().endswith('gb'):
            return float( size_string.lower().split()[0] ) * 1024
    if not doAny:
        lookups = sorted( filter(lambda lookup: '720p' in lookup.name and
                                 get_size( lookup ) >= 100.0 and
                                 lookup.torrent_link is not None,
                                 Search( name, category = CATEGORY.MOVIES ) ),
                          key = lambda lookup: get_size( lookup ) )[:maxnum]
    else:
        lookups = sorted( filter(lambda lookup: get_size( lookup ) >= 100.0 and
                                 lookup.torrent_link is not None,
                                 Search( name, category = CATEGORY.MOVIES ) ),
                          key = lambda lookup: get_size( lookup ) )[:maxnum]
    if len( lookups ) == 0:
        print('Could not find %s, exiting...' % name)
        return
    if len( lookups ) != 1:
        sortdict = { idx + 1 : ( lookup.name, get_size( lookup ),
                                 lookup.torrent_link ) for (idx, lookup) in
                     enumerate( lookups ) }
        iidx = raw_input( 'Choose movie:\n%s\n' %
                          '\n'.join('%d: %s, %0.2f MB' % ( idx, sortdict[ idx ][ 0 ],
                                                           sortdict[ idx ][ 1 ]) for
                                    idx in sorted( sortdict ) ) )
        try:
            iidx = int( iidx.strip( ) )
            if iidx not in sortdict:
                print('Error, need to choose one of the movie names. Exiting...')
                return
            torrent_page = sortdict[ iidx ][ -1 ]
            actmov = sortdict[ iidx ][ 0 ]
        except Exception:
            print('Error, did not give an integer value. Exiting...')
            return
    else:
        torrent_page = max( lookups ).torrent_link
        actmov = max( lookups ).name
    #
    print('Chosen movie %s' % actmov )
    splitstuff = map(lambda tok: tok.lower(), actmov.split( ) )
    html = BeautifulSoup( requests.get( torrent_page ).content, 'lxml' )
    mag_links = filter(lambda elem: 'href' in elem.attrs and 
                       elem['href'].startswith( 'magnet:' ) and
                       any([ tok in elem['href'] for tok in splitstuff ]),
                       tree.find_all( 'a' ) )
    if len( mag_links )  == 0:
        print('Error, could not find any magnet links for %s.' % name )
        return
    mag_link = max( mag_links )[ 'href' ]
    print 'magnet link: %s' % mag_link
    
def get_movie_torrent( name, verify = True, raiseError = False ):
    mainURL = 'https://yts.ag/api/v2/list_movies.json'
    params = { 'query_term' : name, 'order_by' : 'year' }
    response = requests.get( mainURL, params = params, verify = verify )
    if response.status_code != 200:
        if raiseError:
            raise ValueError("Error, could not use the movie service. Exiting...")
        print('Error, could not use the movie service. Exiting...')
        return
    data = response.json()['data']
    if 'movies' not in data or len(data['movies']) == 0:
        if raiseError:
            raise ValueError("Could not find %s, exiting..." % name )
        print('Could not find %s, exiting...' % name)
        return
    movies = data['movies']
    if len(movies) != 1:
        movdict = { mov['title'] : mov for mov in movies }
        sortdict = { idx + 1 : title for (idx, title) in
                     enumerate( sorted( movdict.keys( ) ) ) }
        iidx = raw_input( 'choose movie: %s\n' % '\n'.join([
            '%d: %s' % ( idx, sortdict[idx] ) for idx in
            sorted( sortdict.keys( ) ) ]) )
        try:
            iidx = int( iidx.strip( ) )
            if iidx not in sortdict:
                print('Error, need to choose one of the movie names. Exiting...')
                return
            actmov = movdict[ sortdict[ iidx ] ]
        except Exception:
            print('Error, did not give an integer value. Exiting...')
            return
    else:
        def valid_movie( mov ):
            if 'quality' not in mov:
                return True
            if '3D' in mov['quality']:
                return False
            return True
        actmov = max( data['movies'] )
    print('Chosen movie %s' % actmov['title'])
    url = list(filter(lambda tor: 'quality' in tor and '3D' not in tor['quality'],
                      actmov['torrents']))[0]['url']
    resp = requests.get( url, verify = verify )
    with open( '%s.torrent' % '_'.join( actmov['title'].split() ), 'wb') as openfile:
        openfile.write( resp.content )

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('--name', dest='name', type=str, action='store',
                      help = 'Name of the movie file to get.')
    parser.add_option('--maxnum', dest='maxnum', type=int, action='store', default = 10,
                      help = 'Maximum number of torrents to look through. Default is 10.')
    parser.add_option('--any', dest='do_any', action='store_true', default = False,
                      help = 'If chosen, make no filter on movie format.')
    opts, args = parser.parse_args( )
    assert( opts.name is not None )
    # verify = not opts.do_noverify
    try:
        get_movie_torrent( opts.name, verify = True, raiseError = True )
    except ValueError:
        get_movie_torrent_tpb( opts.name, doAny = opts.do_any, maxnum = opts.maxnum )
