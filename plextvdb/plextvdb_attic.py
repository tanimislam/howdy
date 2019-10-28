import requests, os, sys, time
import logging, datetime, fuzzywuzzy.fuzz
from dateutil.relativedelta import relativedelta
from imdb import IMDb

from plextmdb import tmdb_apiKey
from plextvdb import get_token, plextvdb

def get_series_omdb_id( series_name, apikey ):
    """
    Returns the most likely IMDB_ key, using the OMDB_ API, for a TV show.

    :param str series_name: the series name.
    :param str apikey: the OMDB_ API key.
    
    :returns: the IMDB_ key associated with ``series_name``.
    :rtype: str

    .. _OMDB: http://www.omdbapi.com
    """
    params = { 's' : series_name, 'type' : 'series', 'plot' : 'full', 'apikey' : apikey }
    response = requests.get( 'http://www.omdbapi.com',
                             params = params )
    if response.status_code != 200:
        return None
    data = response.json( )
    if 'Search' not in data:
        return None
    if 'totalResults' not in data:
        return None
    if data['totalResults'] == 0:
        return None
    items = list(
        filter(lambda item: 'Poster' in item.keys( ) and item['Poster'] != 'N/A' and 'imdbID' in item.keys( ),
               data['Search']) )
    if len( items ) == 0:
        return None
    return items[0]['imdbID']

def get_possible_omdb_ids( series_name, apikey ):
    """
    Returns a :py:class:`list` of basic information on TV shows from the OMDB_ API search of a TV show. Each element in the list is a :py:class:`tuple`: the first element is the IMDB_ series ID, and the second element is a :py:class:`list` of years during which the TV series has aired. For example, for `The Simpsons`_.

    .. code-block:: python
    
        >> get_possible_omdb_ids( 'The Simpsons', omdb_apikey )
        >> [ ( 'tt0096697', [ 1989, 1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019 ] ) ]

    If unsuccessful, then returns ``None``.

    :param str series_name: the series name.
    :param str apikey: the OMDB_ API key.
    
    :returns: a :py:class:`list` of IMDB_ based information on TV shows that match the series name. If unsuccessful, returns ``None``.
    :rtype: list
    """
    params = { 's' : series_name, 'type' : 'series', 'plot' : 'full', 'apikey' : apikey }
    response = requests.get( 'http://www.omdbapi.com', params = params )
    if response.status_code != 200:
        return None
    data = response.json( )
    if 'Search' not in data:
        return None
    if 'totalResults' not in data:
        return None
    if data['totalResults'] == 0:
        return None
    items = list(
        filter(lambda item: 'Poster' in item.keys( ) and item['Poster'] != 'N/A' and 'imdbID' in item.keys( ),
               data['Search']) )
    if len( items ) == 0:
        return None
    currentYear = datetime.datetime.now( ).year
    def get_range_years( item ):
        splitYears = item['Year'].split(u'\u2013')
        startYear = int( splitYears[ 0 ] )
        if len( splitYears[1] ) == 0:
            endYear = currentYear
        else:
            endYear = int( splitYears[ 1 ] )
        return list( range( startYear, endYear + 1 ) )
    return list( map( lambda item: ( item['imdbID'], get_range_years( item ) ), items ) )


#
## Does not show the specials for the TV series
def get_episodes_series_omdb( imdbID, apikey, fromDate = None ):
    """
    Returns a :py:class:`list` of episodes found using the OMDB_ API. Each element has the following keys,
    
    * ``Title`` is the episode name.
    * ``Released`` is the :py:class:`str` representation of the date it was aired.
    * ``Episode`` is the episode number in the season.
    * ``airedSeason`` is the season in which the episode was aired.
    * ``imdbID`` is the IMDB_ episode ID.
    * ``imdbRating`` is the episode rating (out of 10.0) on IMDB_.

    For example, for `The Simpsons`_,

    .. code-block:: python

        [{'Title': 'The Call of the Simpsons',
          'Released': '1990-02-18',
          'Episode': 7,
          'imdbRating': '7.9',
          'imdbID': 'tt0701228',
          'airedSeason': 1},
         {'Title': 'The Telltale Head',
          'Released': '1990-02-25',
          'Episode': 8,
          'imdbRating': '7.7',
          'imdbID': 'tt0756398',
          'airedSeason': 1},
         {'Title': 'Life on the Fast Lane',
          'Released': '1990-03-18',
          'Episode': 9,
          'imdbRating': '7.5',
          'imdbID': 'tt0701152',
          'airedSeason': 1},
         ...
        ]
    
    :param str imdbID: the IMDB_ ID of the TV show.
    :param str apiKey: the OMDB_ API key.
    
    :returns: a :py:class:`list` of IMDB_ episode information for the TV show.
    :rtype: list
    """
    response = requests.get( 'http://www.omdbapi.com',
                             params = { 'i' : imdbID, 'type' : 'series', 'plot' : 'full', 'apikey' : apikey } )
    if response.status_code != 200: return None
    data = response.json( )
    numSeasons = int( data[ 'totalSeasons' ] )
    currentDate = datetime.datetime.now( ).date( )
    sData = [ ]
    for season in range( 1, numSeasons + 1 ):
        params_season = { 'i' : imdbID, 'type' : 'series', 'plot' : 'full', 'Season' : season, 'apikey' : apikey }
        response_season = requests.get( 'http://omdbapi.com', params = params_season )
        if response_season.status_code != 200: continue
        data_season = response_season.json( )
        if 'Episodes' not in data_season: continue
        episodes_valid = [ ]
        for episode in data_season[ 'Episodes' ]:
            try:
                date = datetime.datetime.strptime( episode[ 'Released' ], '%Y-%m-%d' ).date( )
                if date >= currentDate:
                    continue
                if fromDate is not None:
                    if date < fromDate:
                        continue
            except:
                continue
            episode['airedSeason'] = season
            episode['Episode'] = int( episode[ 'Episode' ] )
            episodes_valid.append( episode )
        #
        ## get last episode
        if len( episodes_valid ) == 0: continue
        last_ep = max(episodes_valid, key = lambda episode: datetime.datetime.strptime( episode[ 'Released' ], '%Y-%m-%d' ).date( ) )['Episode']
        sData += list( filter(lambda episode: episode['Episode'] <= last_ep, episodes_valid) )
    return sData

def get_tot_epdict_omdb( showName, apikey, inYear = None ):
    """
     Returns a :py:class:`dict` of episodes found from the OMDB_ API. The top level dictionary's keys are the season numbers, and each value is the next-level dictionary of season information. The next level, season dictionary's keys are the episode number, and its values are the episode names. For example, for `The Simpsons`_ (here the collection of episodes is incomplete),
    
    .. code-block:: python
        
        {
         1: {7: 'The Call of the Simpsons',
          8: 'The Telltale Head',
          9: 'Life on the Fast Lane',
          10: "Homer's Night Out",
          11: 'The Crepes of Wrath',
          12: 'Krusty Gets Busted',
          13: 'Some Enchanted Evening'},
         2: {1: 'Bart Gets an F',
          2: 'Simpson and Delilah',
          3: 'Treehouse of Horror',
          4: 'Two Cars in Every Garage and Three Eyes on Every Fish',
          6: 'Dead Putting Society',
          12: 'The Way We Was',
          13: 'Homer vs. Lisa and the 8th Commandment',
          14: 'Principal Charming',
          15: 'Oh Brother, Where Art Thou?',
          16: "Bart's Dog Gets an F",
          17: 'Old Money',
          18: 'Brush with Greatness',
          19: "Lisa's Substitute",
          20: 'The War of the Simpsons',
          21: 'Three Men and a Comic Book',
          22: 'Blood Feud'},
         ...
        }

    If unsuccessful, then returns ``None``.

    :param str showName: the series name.
    :param str apikey: the OMDB_ API key.
    :param int inYear: optional argument. If given, then search for those TV shows whose episodes aired in ``inYear``.
    :returns: a :py:class:`dict` of episode information for that TV show.
    :rtype: dict

    .. seealso::
    
       * :py:meth:`get_tot_epdict_imdb <plextvdb.plextvdb_attic.get_tot_epdict_imdb>`.
       * :py:meth:`get_tot_epdict_tmdb <plextvdb.plextvdb_attic.get_tot_epdict_tmdb>`.
    """
    if inYear is None:
        imdbID = get_series_omdb_id( showName, apikey )
    else:
        valids = get_possible_omdb_ids( showName, apikey )
        if len(valids) == 1:
            imdbID = valid[0][0]
        else:
            valids = list( filter(lambda item: inYear in item[1], valids ) )
            if len(valids) == 0:
                print( 'Could not find %s in %d' % ( showName, inYear ) )
                return None
            imdbID = valids[0][0]
    eps = get_episodes_series_omdb( imdbID, apikey )
    tot_epdict = { }
    for episode in eps:
        seasnum = episode[ 'airedSeason' ]
        epno = episode[ 'Episode' ]
        title = episode[ 'Title' ]
        tot_epdict.setdefault( seasnum, { } )
        tot_epdict[seasnum][epno] = title
    return tot_epdict

def get_possible_tmdb_ids( series_name, firstAiredYear = None ):
    """
    Returns a :py:class:`list` of candidate TMDB_ TV shows given the series name. Each element in the list is a dictionary: the ``id`` is the TMDB_ series ID, and ``airedYear`` is the year in which the first episode aired. If nothing is found, returns ``None``. For example, for `The Simpsons`_,

    .. code-block:: python

        [{'id': 456, 'name': 'The Simpsons', 'airedYear': 1989},
         {'id': 73980, 'name': 'Da Suisa', 'airedYear': 2013}]

    :param str series_name: the series name.
    :param int firstAiredYear: optional argument. If provided, filter on TV shows that were first aired that year.
    :returns: a :py:class:`list` of candidate TMDB_ TV shows, otherwise ``None``.
    :rtype: list
    """
    params = { 'api_key' : tmdb_apiKey, 'query' : '+'.join( series_name.split( ) ) }
    if firstAiredYear is not None:
        params[ 'first_air_date_year' ] = firstAiredYear
    response = requests.get( 'https://api.themoviedb.org/3/search/tv',
                             params = params, verify = False )
    if response.status_code != 200:
        return None
    data = response.json( )
    total_pages = data[ 'total_pages' ]
    results = filter(lambda result: fuzzywuzzy.fuzz.ratio( result['name'], series_name ) >= 10.0,
                     data['results'] )
    results = sorted( results, key = lambda result: -fuzzywuzzy.fuzz.ratio( result['name'], series_name ) )
    if total_pages >= 2:
        for pageno in xrange(2, max( 5, total_pages + 1 ) ):
            params = { 'api_key' : tmdb_apiKey,
                       'query' : '+'.join( series_name.split( ) ),
                       'page' : pageno }
            if firstAiredYear is not None:
                params[ 'first_air_date_year' ] = firstAiredYear
            response = requests.get( 'https://api.themoviedb.org/3/search/tv',
                                     params = params, verify = False )
            if response.status_code != 200:
                continue
            data = response.json( )
            newresults = list(
                filter(lambda result: fuzzywuzzy.fuzz.ratio( result['title'], title ) >= 10.0,
                       data['results'] ) )
            if len( newresults ) > 0:
                results += sorted( newresults, key = lambda result: -fuzzywuzzy.fuzz.ratio( result['title'], title ) )
    if len( results ) == 0: return None
    return list(
        map(lambda result: { 'id' : result['id'], 'name' : result['name'],
                             'airedYear' : datetime.datetime.strptime( result['first_air_date'], '%Y-%m-%d' ).year },
            results ) )

def get_series_tmdb_id( series_name, firstAiredYear = None ):
    """
    Returns the first TMDB_ series ID for a TV show. Otherwise returns ``None`` if no TV series could be found.
    
    :param str series_name: the series name.
    :param int firstAiredYear: optional argument. If provided, filter on TV shows that were first aired that year.
    :returns: the TMDB_ series ID for that TV show.
    :rtype: int

    .. _TMDB: https://www.themoviedb.org/documentation/api?language=en-US
    """
    results = get_possible_tmdb_ids( series_name, firstAiredYear = firstAiredYear )
    if len( results ) == 0: return None
    return results[0]['id']

#
##Ignore specials (season 0) for now...
def get_episodes_series_tmdb( tmdbID, fromDate = None ):
    """
    Returns a :py:class:`list` of episodes returned by the TMDB_ API. Each element is a dictionary: ``name`` is the episode name, ``airedDate`` is the :py:class:`date <datetime.date>` the episode aired, ``season`` is the season it aired, and ``episode`` is the episode number in that season. For example, for for `The Simpsons`_,
    
    .. code-block:: python

       >> series_id = get_series_tmdb_id( 'The Simpsons' )
       >> episodes_tmdb = get_episodes_series_tmdb( series_id )
       >> [{'name': 'Simpsons Roasting on an Open Fire',
            'airedDate': datetime.date(1989, 12, 17),
            'season': 1,
            'episode': 1},
           {'name': 'Bart the Genius',
            'airedDate': datetime.date(1990, 1, 14),
            'season': 1,
            'episode': 2},
           {'name': "Homer's Odyssey",
            'airedDate': datetime.date(1990, 1, 21),
            'season': 1,
            'episode': 3},
           ...
          ]

    :param int tmdbID: the TMDB_ series ID.
    :param date fromDate: optional argument, of type :py:class:`date <datetime.date>`. If given, then only return episodes aired on or after this date.
    :returns: a :py:class:`list` of episoes returned by the TMDB_ database.
    :rtype: list

    .. _`The Simpsons`: https://en.wikipedia.org/wiki/The_Simpsons
    """
    response = requests.get( 'https://api.themoviedb.org/3/tv/%d' % tmdbID,
                             params = { 'api_key' : tmdb_apiKey }, verify = False )
    if response.status_code != 200:
        return None
    data = response.json( )
    currentDate = datetime.datetime.now( ).date( )
    sData = [ ]
    for season_elem in data[ 'seasons' ]:
        if season_elem['season_number'] == 0: continue
        season_number = season_elem['season_number']
        response_season = requests.get( 'https://api.themoviedb.org/3/tv/%d/season/%d' % ( tmdbID, season_number ),
                                        params = { 'api_key' : tmdb_apiKey }, verify = False )
        if response_season.status_code != 200: continue
        data_season = response_season.json( )
        for episode in data_season[ 'episodes' ]:
            try:
                date = datetime.datetime.strptime( episode['air_date'], '%Y-%m-%d' ).date( )
                if date >= currentDate:
                    continue
                if fromDate is not None:
                    if date < fromDate:
                        continue
                sData.append( { 'name' : episode['name'],
                                'airedDate' : date,
                                'season' : season_number,
                                'episode' : episode['episode_number'] } )
            except:
                continue
    return sData

def get_tot_epdict_tmdb( showName, firstAiredYear = None ):
    """
    Returns a :py:class:`dict` of episodes found from the TMDB_ API. The top level dictionary's keys are the season numbers, and each value is the next-level dictionary of season information. The next level, season dictionary's keys are the episode number, and its values are the episode names. For example, for `The Simpsons`_,

    .. code-block:: python
    
          {1: {1: 'Simpsons Roasting on an Open Fire',
           2: 'Bart the Genius',
           3: "Homer's Odyssey",
           4: "There's No Disgrace Like Home",
           5: 'Bart the General',
           6: 'Moaning Lisa',
           7: 'The Call of the Simpsons',
           8: 'The Telltale Head',
           9: 'Life on the Fast Lane',
           10: "Homer's Night Out",
           11: 'The Crepes of Wrath',
           12: 'Krusty Gets Busted',
           13: 'Some Enchanted Evening'},
           ...
          }
    
    If unsuccessful, then returns ``None``.

    :param str showName: the series name.
    :param int firstAiredYear: optional argument. If provided, filter on TV shows that were first aired that year.
    :returns: a :py:class:`dict` of episode information for that TV show.
    :rtype: dict

    .. seealso::
    
       * :py:meth:`get_tot_epdict_imdb <plextvdb.plextvdb_attic.get_tot_epdict_imdb>`.
       * :py:meth:`get_tot_epdict_omdb <plextvdb.plextvdb_attic.get_tot_epdict_omdb>`.
    """
    tmdbID = get_series_tmdb_id( showName, firstAiredYear = firstAiredYear )
    if tmdbID is None: return None
    eps = get_episodes_series_tmdb( tmdbID )
    tot_epdict = { }
    for episode in eps:
        seasnum = episode[ 'season' ]
        title = episode[ 'name' ]
        epno = episode[ 'episode' ]
        tot_epdict.setdefault( seasnum, { } )
        tot_epdict[ seasnum ][ epno ] = title
    return tot_epdict

def get_tot_epdict_singlewikipage(epURL, seasnums = 1, verify = True):
    """    
    Returns a dictionary of episodes from a Wikipedia_ URL for a TV show.

    :param str epURL: the Wikipedia_ URL for the TV show.
    :param int seasnums: the season number for which to get episodes.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: a :py:class:`dict` of episodes for this season. Each key is the episode number, and each value is the episode name.
    :rtype: dict

    .. warning::
      
       This may not reliably work at all anymore! This is very brittle and has not been used since 2015.

    .. _Wikipedia: https://en.wikipedia.org
    """
    import lxml.html, titlecase
    assert(seasnums >= 1)
    assert(isinstance(seasnums, int))
    #
    def is_epelem(elem):
        if elem.tag == 'span':
            if 'class' not in elem.keys(): return False
            if 'id' not in elem.keys(): return False
            if elem.get('class') != 'mw-headline': return False
            if 'Season' not in elem.get('id'): return False
            return True
        elif elem.tag == 'td':
            if 'class' not in elem.keys(): return False
            if 'style' not in elem.keys(): return False
            if elem.get('class') != 'summary': return False
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

def fix_missing_unnamed_episodes( seriesName, eps, verify = True, showFuture = False ):
    """
    This supposedly uses the TMDB_ API to find names for episodes that the TVDB_ API cannot find.
    
    .. warning:: As of |date|, I still don't understand the purpose behind this method. and no other methods call this it. I might remove this method altogether.
    """
    eps_copy = copy.deepcopy( eps )
    tmdb_id = plextmdb.get_tv_ids_by_series_name( seriesName, verify = verify )
    if len( tmdb_id ) == 0: return
    tmdb_id = tmdb_id[ 0 ]
    tmdb_tv_info = plextmdb.get_tv_info_for_series( tmdb_id, verify = verify )
    numeps_in_season = { }
    for season in tmdb_tv_info['seasons']:
        if season['season_number'] == 0: continue
        season_number = season['season_number']
        numeps = season['episode_count']
        
    #
    ## only fix the non-specials
    for episode in eps_copy:
        if episode['airedSeason'] == 0: continue

        
#
## Date must be within 4 weeks of now
def get_series_updated_fromdate( date, token, verify = True ):
    """
    a :py:class:`set` of TVDB_ series IDs of TV shows that have been updated *at least* four weeks fron now.
    
    :param date date: the :py:class:`date <datetime.date>` after which to look for updated TV shws.
    :param str token: the TVDB_ API access token.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: a :py:class:`set` of TVDB_ series IDs.
    :rtype: set
    """
    datetime_now = datetime.datetime.now( )
    assert( date + relativedelta(weeks=4) >= datetime_now.date( ) )
    dates_start = list(
        filter(lambda mydate: mydate < datetime_now.date( ),
               sorted(map(lambda idx: date + relativedelta(weeks=idx), range(5)))))
    print( dates_start )
    #
    ##
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % token }
    series_ids = [ ]
    for mydate in dates_start:
        dt_start = datetime.datetime( year = mydate.year,
                                      month = mydate.month,
                                      day = mydate.day )
        dt_end = min( dt_start + relativedelta(weeks=1), datetime_now )
        epochtime = int( time.mktime( dt_start.utctimetuple( ) ) )
        toTime = int( time.mktime( dt_end.utctimetuple( ) ) )
        response = requests.get( 'https://api.thetvdb.com/updated/query',
                                 params = { 'fromTime' : epochtime,
                                            'toTime' : toTime },
                                 headers = headers, verify = verify )
        if response.status_code != 200:
            continue
        series_ids += response.json( )['data']
    return sorted( set( map(lambda elem: elem['id'], series_ids ) ) )

def get_tot_epdict_imdb( showName, verify = True ):
    """
    Returns a summary nested :py:class:`dict` of episode information for a given TV show, using :py:class:`IMDb <imdb.IMDb>` class in the `IMDB Python Package`_.

    * The top level dictionary has keys that are the TV show's seasons. Each value is a second level dictionary of information about each season.

    * The second level dictionary has keys (for each season) that are the season's episodes. Each value is a :py:class:`tuple` of episode name and air date, as a :py:class:`date <datetime.date>`.

    An example of the structure of this dictionary can be found in :py:meth:`get_tot_epdict_tvdb <plextvdb.plextvdb.get_tot_epdict_tvdb>`.

    .. seealso::

       * :py:meth:`get_tot_epdict_tvdb <plextvdb.plextvdb.get_tot_epdict_tvdb>`.
       * :py:meth:`get_tot_epdict_omdb <plextvdb.plextvdb_attic.get_tot_epdict_omdb>`.
       * :py:meth:`get_tot_epdict_tmdb <plextvdb.plextvdb_attic.get_tot_epdict_tmdb>`.

    .. _`IMDB Python Package`: https://imdbpy.readthedocs.io/en/latest
    """
    token = get_token( verify = verify )
    tvdb_id = plextvdb.get_series_id( showName, token, verify = verify )
    if tvdb_id is None: return None
    imdbId = plextvdb.get_imdb_id( tvdb_id, token, verify = verify )
    if imdbId is None: return None
    #
    ## now run imdbpy
    time0 = time.time( )
    ia = IMDb( )
    imdbId = imdbId.replace('tt','').strip( )
    series = ia.get_movie( imdbId )
    ia.update( series, 'episodes' )
    logging.debug('took %0.3f seconds to get episodes for %s.' % (
        time.time( ) - time0, showName ) )
    tot_epdict = { }
    seasons = sorted( set(filter(lambda seasno: seasno != -1, series['episodes'].keys( ) ) ) )
    tot_epdict_tvdb = plextvdb.get_tot_epdict_tvdb( showName, verify = verify )
    for season in sorted( set( seasons ) & set( tot_epdict_tvdb ) ):
        tot_epdict.setdefault( season, { } )
        for epno in series['episodes'][season]:
            episode = series['episodes'][season][epno]
            title = episode[ 'title' ].strip( )
            try:
                firstAired_s = episode[ 'original air date' ]
                firstAired = datetime.datetime.strptime(
                    firstAired_s, '%d %b. %Y' ).date( )
            except:
                firstAired = tot_epdict_tvdb[ season ][ epno ][-1]
            tot_epdict[ season ][ epno ] = ( title, firstAired )
    return tot_epdict
