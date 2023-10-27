import requests, re, threading, cfscrape, logging
import os, time, numpy, logging, datetime, pickle, gzip
from itertools import chain
from requests.compat import urljoin
from multiprocessing import Process, Manager
from pathos.multiprocessing import Pool
from bs4 import BeautifulSoup
from torf import Magnet
#
from howdy.core import core_deluge, get_formatted_size, get_maximum_matchval, return_error_raw, core
from howdy.core import PlexExcludedTrackerStubs, session

def get_trackers_to_exclude( ):
    """
    Returns the :py:class:`set` of `torrent tracker stubs <torrent_tracker_>`_ to exclude from the reconstruction of magnet_ links.

    .. _torrent_tracker: https://en.wikipedia.org/wiki/BitTorrent_tracker
    .. _magnet: https://en.wikipedia.org/wiki/Magnet_URI_scheme
    """
    tracker_stubs_to_exclude = sorted(set(map(
        lambda val: val.trackerstub.strip( ).lower( ), session.query( PlexExcludedTrackerStubs ).all( ) ) ) )
    return tracker_stubs_to_exclude

def push_trackers_to_exclude( tracker_stubs ):
    """
    Adds a collection of *new* `torrent tracker stubs <torrent_tracker_>`_ to the :py:class:`PlexExcludedTrackerStubs <howdy.core.PlexExcludedTrackerStubs>` database.

    :param list tracker_stubs: the collection of `torrent tracker stubs <torrent_tracker_>`_ to add to the database.
    """
    set_tracker_stubs = set(map(lambda tracker_stub: tracker_stub.strip( ).lower( ), tracker_stubs ) )
    tracker_stubs_left = set_tracker_stubs - set( get_trackers_to_exclude( ) )
    logging.debug( 'input trackers: %s, actual trackers to add: %s.' % (
        tracker_stubs, tracker_stubs_left ) )
    if len( tracker_stubs_left ) == 0: return
    #
    ## now add those tracker stubs
    for tracker_stub in tracker_stubs_left:
        session.add( PlexExcludedTrackerStubs( trackerstub = tracker_stub ) )
    session.commit( )

def remove_trackers_to_exclude( tracker_stubs ):
    """
    Removes a collection of candidate `torrent tracker stubs <torrent_tracker_>`_ to the :py:class:`PlexExcludedTrackerStubs <howdy.core.PlexExcludedTrackerStubs>` database.

    :param list tracker_stubs: the collection of `torrent tracker stubs <torrent_tracker_>`_ to remove from the database.
    """
    set_tracker_stubs = set(map(lambda tracker_stub: tracker_stub.strip( ).lower( ), tracker_stubs ) )
    tracker_stubs_rem = set_tracker_stubs & set( get_trackers_to_exclude( ) )
    logging.debug( 'input trackers: %s, actual trackers to remove: %s.' % (
        tracker_stubs, tracker_stubs_rem ) )
    if len( tracker_stubs_rem ) == 0: return
    #
    ## now delete those tracker stubs
    for row in session.query( PlexExcludedTrackerStubs ).all( ):
        if row.trackerstub not in tracker_stubs_rem: continue
        session.delete( row )
    session.commit( )
    
def deconfuse_magnet_link( magnet_string, excluded_tracker_stubs = get_trackers_to_exclude( ) ):
    """
    First functional implementation that *returns* a magnet_ string given a :py:class:`list` of `torrent tracker`_ stubs to ignore. ``stealth.si`` -- I am looking at you!

    If one has an *invalid* magnet_string, then return ``None``.

    :param str magnet_string: the initial magnet string.
    :param list excluded_tracker_stubs: the :py:class:`list` of `torrent tracker`_ stubs to ignore. Default is :py:meth:`get_trackers_to_exclude <howdy.core.core_torrents.get_trackers_to_exclude>`.
    :returns a :py:class:`str` of a magnet_ string with the problematic `torrent tracker`_ stubs in ``excluded_tracker_stubs`` removed. If ``magnet_string`` is not a valid magnet_ string, return ``None``.
    :rtype: str

    .. _magnet: https://en.wikipedia.org/wiki/Magnet_URI_scheme
    .. _`torrent tracker`: https://en.wikipedia.org/wiki/BitTorrent_tracker
    """
    try:
        m = Magnet.from_string( magnet_string )
        #
        ## if NO excluded tracker stubs, just return initial valid magnet string
        if len( excluded_tracker_stubs ) == 0: return str( m )
        #
        tr_sub = list( m.tr )
        for tracker_stub in set( excluded_tracker_stubs ):
            tr_sub = list(filter(lambda elem: tracker_stub not in elem, tr_sub ) )
        m.tr = tr_sub
        return str( m )
    except Exception as e:
        logging.error( str( e ) )
        return None

def get_book_torrent_jackett( name, maxnum = 10, keywords = [ ], verify = True ):
    """
    Returns a :py:class:`tuple` of candidate book Magnet links found using the main Jackett_ torrent searching service and the string ``"SUCCESS"``, if successful.

    :param str name: the book to search for.
    :param int maxnum: optional argumeent, the maximum number of magnet links to return. Default is 10. Must be :math:`\ge 5`.
    :param list keywords: optional argument. If not empty, the title of the candidate element must have at least one of the keywords in ``keywords``.
    :param bool verify:  optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: if successful, then returns a two member :py:class:`tuple` the first member is a :py:class:`list` of elements that match the searched episode, ordered from *most* seeds and leechers to least. The second element is the string ``"SUCCESS"``. The keys in each element of the list are,
       
      * ``title`` is the name of the candidate book to download, and in parentheses the size of the candidate in MB or GB.
      * ``rawtitle`` also the name of the candidate episode to download.
      * ``seeders`` is the number of seeds for this Magnet link.
      * ``leechers`` is the number of leeches for this Magnet link.
      * ``link`` is the Magnet URI link.
      * ``torrent_size`` is the size of this torrent in Megabytes.
    
    If this is unsuccessful, then returns an error :py:class:`tuple` of the form returned by :py:meth:`return_error_raw <howdy.core.return_error_raw>`.
    
    :rtype: tuple

    .. _Jackett: https://github.com/Jackett/Jackett
    """
    import validators
    assert( maxnum >= 5 )
    data = core.get_jackett_credentials( )
    if data is None:
        return return_error_raw('FAILURE, COULD NOT GET JACKETT SERVER CREDENTIALS')
    url, apikey = data
    if not url.endswith( '/' ): url = '%s/' % url
    endpoint = 'api/v2.0/indexers/all/results/torznab/api'
    name_split = name.split()
    last_tok = name_split[-1].lower( )
    status = re.match('^s[0-9]{2}e[0-9]{2}',
                      last_tok )
    
    def _return_params( name ):
        params = { 'apikey' : apikey, 'q' : name, 'cat' : '7020' }
        return params

    logging.info( 'URL ENDPOINT: %s, PARAMS = %s.' % (
        urljoin( url, endpoint ), { 'apikey' : apikey, 'q' : name, 'cat' : '7020' } ) )
    response = requests.get(
        urljoin( url, endpoint ),
        params = { 'apikey' : apikey, 'q' : name, 'cat' : '7020' },
        verify = verify ) # tv shows
    if response.status_code != 200:
        return return_error_raw( 'FAILURE, PROBLEM WITH JACKETT SERVER ACCESSIBLE AT %s.' % url )
    html = BeautifulSoup( response.content, 'html.parser' )
    if len( html.find_all('item') ) == 0:
        return return_error_raw( 'FAILURE, NO BOOKS SATISFYING CRITERIA FOR GETTING %s' % name )
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
        h2 = BeautifulSoup( resp2.content, 'html.parser' )
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
    if len( keywords ) != 0:
        items = list(filter(lambda item: any(map(lambda tok: tok.lower( ) in item['rawtitle'].lower( ), keywords ) ) and
                            not any(map(lambda tok: tok.lower( ) in item['rawtitle'].lower( ), keywords_exc ) ) and
                            all(map(lambda tok: tok.lower( ) in item['rawtitle'].lower( ), must_have ) ),
                            items ) )
    if len( items ) == 0:
        return return_error_raw( 'FAILURE, NO BOOKS SATISFYING CRITERIA FOR GETTING %s' % name )
        
    return items[:maxnum], 'SUCCESS'
