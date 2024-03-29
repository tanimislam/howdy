import requests, os, sys, time, json, titlecase, re, copy
import logging, datetime, rapidfuzz.fuzz
from dateutil.relativedelta import relativedelta
from pathos.multiprocessing import Pool, cpu_count
from imdb import Cinemagoer
#
from howdy.core import session
from howdy.movie import tmdb_apiKey, movie
from howdy.tv import get_token, tv, TMDBShowIds

def get_series_omdb_id( series_name, apikey ):
    """
    Returns the most likely IMDB_ key, using the OMDB_ API, for a TV show.

    :param str series_name: the series name.
    :param str apikey: the OMDB_ API key.
    
    :returns: the IMDB_ key associated with ``series_name``.
    :rtype: str

    .. _OMDB: http://www.omdbapi.com
    .. _TMDB: https://www.themoviedb.org/documentation/api?language=en-US
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
    return items[0]['imdbID']

def get_possible_omdb_ids( series_name, apikey ):
    """
    Returns a :py:class:`list` of basic information on TV shows from the OMDB_ API search of a TV show. Each element in the list is a :py:class:`tuple`: the first element is the IMDB_ series ID, and the second element is a :py:class:`list` of years during which the TV series has aired.

    :param str series_name: the series name.
    :param str apikey: the OMDB_ API key.
    
    :returns: a :py:class:`list` of IMDB_ based information on TV shows that match the series name. For example, for `The Simpsons`_.

      .. code-block:: python

         >> get_possible_omdb_ids( 'The Simpsons', omdb_apikey )
         >> [ ( 'tt0096697', [ 1989, 1990, 1991, 1992, 1993, 1994, 1995,
                               1996, 1997, 1998, 1999, 2000, 2001, 2002,
                               2003, 2004, 2005, 2006, 2007, 2008, 2009,
                               2010, 2011, 2012, 2013, 2014, 2015, 2016,
                               2017, 2018, 2019 ] ) ]

      If unsuccessful, returns ``None``. 
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
     Returns a :py:class:`dict` of episodes found from the OMDB_ API. The top level dictionary's keys are the season numbers, and each value is the next-level dictionary of season information. The next level, season dictionary's keys are the episode number, and its values are the episode names.

    :param str showName: the series name.
    :param str apikey: the OMDB_ API key.
    :param int inYear: optional argument. If given, then search for those TV shows whose episodes aired in ``inYear``.
    :returns: a :py:class:`dict` of episode information for that TV show. For example, for `The Simpsons`_ (here the collection of episodes is incomplete),
    
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
    :rtype: dict

    .. seealso::
    
       * :py:meth:`get_tot_epdict_imdb <howdy.tv.tv_attic.get_tot_epdict_imdb>`.
       * :py:meth:`get_tot_epdict_tmdb <howdy.tv.tv_attic.get_tot_epdict_tmdb>`.
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

def get_possible_tmdb_ids( series_name, firstAiredYear = None, minmatch = 10.0 ):
    """
    Returns a :py:class:`list` of candidate TMDB_ TV shows given the series name. Each element in the list is a dictionary: the ``id`` is the TMDB_ series ID, and ``airedYear`` is the year in which the first episode aired.

    :param str series_name: the series name.
    :param int firstAiredYear: optional argument. If provided, filter on TV shows that were first aired that year.
    :param float minmatch: minimum value of the ratio match. Must be :math:`> 0` and :math:`\le 100.0`. Default is 10.0.
    :returns: a :py:class:`list` of candidate TMDB_ TV shows, otherwise ``None``. For example, for `The Simpsons`_,

      .. code-block:: python

         [{'id': 456, 'name': 'The Simpsons', 'airedYear': 1989},
          {'id': 73980, 'name': 'Da Suisa', 'airedYear': 2013}]
          
    :rtype: list
    """
    assert( minmatch > 0 )
    assert( minmatch <= 100.0 )
    params = { 'api_key' : tmdb_apiKey, 'query' : '+'.join( series_name.split( ) ) }
    if firstAiredYear is not None:
        params[ 'first_air_date_year' ] = firstAiredYear
    response = requests.get( 'https://api.themoviedb.org/3/search/tv',
                             params = params, verify = False )
    if response.status_code != 200:
        return None
    data = response.json( )
    total_pages = data[ 'total_pages' ]
    results = filter(lambda result: rapidfuzz.fuzz.ratio( result['name'], series_name ) >= minmatch,
                     data['results'] )
    results = sorted( results, key = lambda result: -rapidfuzz.fuzz.ratio( result['name'], series_name ) )
    if total_pages >= 2:
        for pageno in range(2, max( 5, total_pages + 1 ) ):
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
                filter(lambda result: rapidfuzz.fuzz.ratio( result['name'], series_name ) >= minmatch,
                       data['results'] ) )
            if len( newresults ) > 0:
                results += sorted( newresults, key = lambda result: -rapidfuzz.fuzz.ratio( result['name'], series_name ) )
    if len( results ) == 0: return None
    def get_candidate_show( result ):
        try:
            entry = { 'id' : result['id'], 'name' : result['name'],
                      'airedYear' : datetime.datetime.strptime( result['first_air_date'], '%Y-%m-%d' ).year }
            return entry
        except: return None
    return list(filter(None, map(get_candidate_show, results ) ) )


def did_series_end_tmdb( series_id, date_now = None ):
    """
    Check on shows that have ended more than 365 days from the last day.
    
    :param int series_id: the TMDB_ database series ID.
    :param date date_now: an optional specific last :py:class:`date <datetime.date>` to describe when a show was deemed to have ended. That is, if a show has not aired any episodes more than 365 days before ``date_now``, then define the show as ended. By default, ``date_now`` is the current date.

    :returns: ``True`` if the show is "ended," otherwise ``False``.
    :rtype: bool

    :raise ValueError: if we get a 200 response, but the response does not contain JSON data.
    """
    response = requests.get( 'https://api.themoviedb.org/3/tv/%d' % series_id,
                             params = { 'api_key' : tmdb_apiKey }, verify = False )
    if response.status_code != 200:
        logging.debug( 'was not able to get series info. status_code = %d. series_id = %d.' % (
            response.status_code, series_id ) )
        return None
    try:
        data = response.json( )
        if data['status'] == 'Ended': return True

        #
        ## now check when the last date of the show was
        if date_now is None: date_now = datetime.datetime.now( ).date( )
        last_date = max(
            map(lambda epdata: epdata['airedDate'],
                get_episodes_series_tmdb( series_id, showSpecials = False ) ) )
        td = date_now - last_date
        return td.days > 365
    except:
        raise ValueError("Error, no JSON in the response for show with TMDB ID = %d." % series_id )


def fix_show_tmdbid( show, firstAiredYear ):
    """
    This fixes the database of TV shows with TMDB_ ids when wrong. DOCUMENTATION TO FOLLOW.

    :param str show: name of the TV show in the ``tmdbshowids`` database.
    :param int firstAiredYear: the year in which the show aired.
    """
    result = session.query( TMDBShowIds ).filter( TMDBShowIds.show == show ).first( )
    if result is None:
        logging.error("Error, could not find %s in the TMDB show ids database." )
        return
    tmdb_show_id = get_series_tmdb_id( show, firstAiredYear = firstAiredYear, minmatch = 10.0 )
    if tmdb_show_id is None:
        logging.error("Error, could not find a tmdb id for the show = %s with candidate first year = %d." % (
            show, firstAiredYear ) )
        return
    session.delete( result )
    session.add( TMDBShowIds( show = show, tmdbid = tmdb_show_id ) )
    session.commit( )
    
def populate_out_tmdbshowids_and_fix( tvdata ):
    """
    This fills out the database of TV show names with the TMDB_ ids. DOCUMENTATION TO FOLLOW.
    
    :param dict tvdata: the dictionary of TV shows to their attributes.
    :returns: a modified ``tvdata`` dictionary that contains all the TMDB_ ids it could find. For each TV show it finds, it fills in the ``tmdbid`` key associated with it.
    :rtype: dict
    """
    #
    ## first get ALL the current mappings of TV shows with tmdb ids
    tvshows_with_tmdbids =    dict(map(lambda tvshow: ( tvshow, tvdata[tvshow]['tmdbid'] ), filter(lambda tvshow: 'tmdbid' in tvdata[tvshow], tvdata)))
    tvshows_without_tmdbids = set(filter(lambda tvshow: 'tmdbid' not in tvdata[ tvshow ], tvdata ) )
    #
    ## now find those shows for which I can find a TMDB ID
    def get_tvshow_tmdbid( tvshow ):
        tmdb_id = get_series_tmdb_id( tvshow )
        if tmdb_id is None: return None
        return ( tvshow, tmdb_id )
    with Pool( processes = 2 * cpu_count( ) ) as pool:
        tmdbid_dict = dict(filter(None, pool.map(get_tvshow_tmdbid, tvshows_without_tmdbids)))
    #
    ## now find the TV shows remaining
    tvshows_remaining = set(  tvshows_without_tmdbids ) - set( tmdbid_dict )
    #
    ## first, those TV shows with years in parentheses they end on...
    def get_firstaired_year( tvshow ):
        if not re.findall('\)$', tvshow.strip( ) ): return None
        lastelem = tvshow.split()[-1].strip( )
        if not re.findall('^\(', lastelem ): return None
        try:
            return int( lastelem[1:-1])
        except:
            return None
    tvshows_years_parentheses = set(filter(lambda tvshow: get_firstaired_year( tvshow ) is not None, tvshows_remaining ) )
    tvshows_years_parentheses_dict = dict(map(lambda tvshow: ( tvshow, { 'name' : ' '.join( tvshow.strip( ).split()[:-1] ),
                                                                         'year' : get_firstaired_year( tvshow ) } ),
                                              tvshows_years_parentheses))
    def get_tvshow_year( tvshow, name, firstAiredYear ):
        tmdb_id = get_series_tmdb_id( name, firstAiredYear = firstAiredYear )
        if tmdb_id is None: return None
        return ( tvshow, tmdb_id )
    with Pool( processes = 2 * cpu_count( ) ) as pool:
        tmdb_id_dict2 = dict(filter(None, pool.map(lambda tvshow: get_tvshow_year(
            tvshow, ' '.join( tvshow.strip( ).split( )[:-1] ), get_firstaired_year( tvshow ) ), tvshows_years_parentheses ) ) )
        for tvshow in tmdb_id_dict2:
            tmdbid_dict[ tvshow ] = tmdb_id_dict2[ tvshow ]
    #
    ## now find the TV shows remaining
    tvshows_remaining = set( tvshows_without_tmdbids ) - set( tmdbid_dict )
    def get_tvshow_low( tvshow ):
        lastelem = tvshow.strip( ).split()[-1]
        tvshow_act = tvshow
        if lastelem.startswith('(') and lastelem.endswith(')'):
            tvshow_act = ' '.join( tvshow.strip().split()[:-1] )
        tmdb_id = get_series_tmdb_id( tvshow_act, minmatch = 10.0 )
        if tmdb_id is None: return None
        return (tvshow, tmdb_id )
    with Pool( processes = 2 * cpu_count( ) ) as pool:
        tmdb_id_dict2 = dict(filter(None, pool.map(get_tvshow_low, tvshows_remaining)))
        for tvshow in tmdb_id_dict2:
            tmdbid_dict[ tvshow ] = tmdb_id_dict2[ tvshow ]
    #
    ## final collection of remaining TV shows which we cannot identify
    tvshows_remaining = set( tvshows_without_tmdbids ) - set( tmdbid_dict )
    logging.info( 'these %d TV shows remaining: %s.' % ( len( tvshows_remaining ), sorted( tvshows_remaining ) ) )
    #
    ## now perform operations on tvdata
    tvdata_copy = copy.deepcopy( tvdata )
    for tvshow in tmdbid_dict:
        tvdata_copy[ tvshow ][ 'tmdbid' ] = tmdbid_dict[ tvshow ]
    #
    ## now create the tmdbid_dict from where we have MORE tmdbids from tv shows
    tmdb_dict = dict(map(lambda tvshow: ( tvshow, tvdata_copy[ tvshow ][ 'tmdbid' ] ),
                         filter(lambda tvshow: 'tmdbid' in tvdata_copy[ tvshow ], tvdata_copy ) ) )
    #
    ## now find all the rows in the ``tmdbshowids`` database, make a dict of them
    tmdb_dict_db = dict(map(lambda val: ( val.show, val.tmdbid ), session.query( TMDBShowIds ) ) )
    #
    ## find the entries to get rid of...
    ## and get rid of them
    tvshows_to_delete_from_database = set( tmdb_dict_db ) - set( tmdb_dict )
    result = session.query( TMDBShowIds ).filter( TMDBShowIds.show.in_(list(tvshows_to_delete_from_database)))
    for tmdbshowid in result:
        session.delete( tmdbshowid )
    session.commit( )
    for tvshow in tvshows_to_delete_from_database:
        tmdb_dict_db.pop( tvshow )
    #
    ## now find the entries to change or add
    entries_to_change_in_db = set( tmdb_dict.items( ) ) - set( tmdb_dict_db.items( ) )
    #
    ## find those tvshows already in the db, and get rid of them
    tvshows_already_in_db = set(map(lambda tup: tup[0], entries_to_change_in_db ) ) & set(
        map(lambda tmdbshowid: tmdbshowid.show, session.query( TMDBShowIds ) ) )
    result = session.query( TMDBShowIds ).filter( TMDBShowIds.show.in_(list( tvshows_already_in_db)))
    for tmdbshowid in result:
        session.delete( tmdbshowid )
    session.commit( )
    #
    ## finally, create entries to change in db by adding them back to the db
    for show, tmdbid in entries_to_change_in_db:
        session.add( TMDBShowIds( show = show, tmdbid = tmdbid ) )
    session.commit( )
    #
    ## return copy of tvdata with all possible tmdbids filled out
    return tvdata_copy

def get_series_tmdb_id( series_name, firstAiredYear = None, minmatch = 50.0 ):
    """
    Returns the first TMDB_ series ID for a TV show. Otherwise returns ``None`` if no TV series could be found.
    
    :param str series_name: the series name.
    :param int firstAiredYear: optional argument. If provided, filter on TV shows that were first aired that year.
    :param float minmatch: the minimal matching of the series name. Default is 50.0.
    :returns: the TMDB_ series ID for that TV show.
    :rtype: int

    """
    results = get_possible_tmdb_ids( series_name, firstAiredYear = firstAiredYear, minmatch = minmatch )
    if results is None: return None
    if len( results ) == 0: return None
    return results[0]['id']

#
##Ignore specials (season 0) for now...
def get_episodes_series_tmdb( tmdbID, fromDate = None, showSpecials = False, showFuture = False ):
    """
    Returns a :py:class:`list` of episodes returned by the TMDB_ API. Each element is a dictionary: ``name`` is the episode name, ``airedDate`` is the :py:class:`date <datetime.date>` the episode aired, ``season`` is the season it aired, and ``episode`` is the episode number in that season.

    :param int tmdbID: the TMDB_ series ID.
    :param date fromDate: optional argument, of type :py:class:`date <datetime.date>`. If given, then only return episodes aired *after* this date.
    :param bool showSpecials: if ``True``, then also include TV specials. These specials will appear in a season ``0`` in this dictionary.
    :param bool showFuture: optional argument, if ``True`` then also include information on episodes that have not yet aired.
    :returns: a :py:class:`list` of episoes returned by the TMDB_ database. For example, for `The Simpsons`_,
    
      .. code-block:: python

         >> series_id = get_series_tmdb_id( 'The Simpsons' )
         >> episodes_tmdb = get_episodes_series_tmdb( series_id )
         >> [{'episodeName': 'Simpsons Roasting on an Open Fire',
              'airedDate': datetime.date(1989, 12, 17),
              'airedSeason': 1,
              'airedEpisodeNumber': 1},
             {'episodeName': 'Bart the Genius',
              'airedDate': datetime.date(1990, 1, 14),
              'airedSeason': 1,
              'airedEpisodeNumber': 2},
             {'episodeName': "Homer's Odyssey",
              'airedDate': datetime.date(1990, 1, 21),
              'airedSeason': 1,
              'airedEpisodeNumber': 3},
             ...
            ]
          
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
        if season_elem['season_number'] == 0 and not showSpecials: continue
        season_number = season_elem['season_number']
        response_season = requests.get( 'https://api.themoviedb.org/3/tv/%d/season/%d' % ( tmdbID, season_number ),
                                        params = { 'api_key' : tmdb_apiKey }, verify = False )
        if response_season.status_code != 200: continue
        data_season = response_season.json( )
        for episode in data_season[ 'episodes' ]:
            try:
                date = datetime.datetime.strptime( episode['air_date'], '%Y-%m-%d' ).date( )
                if date > currentDate and not showFuture:
                    continue
                if fromDate is not None:
                    if date < fromDate:
                        continue
                sData.append( { 'episodeName' : episode['name'],
                                'airedDate' : date,
                                'airedSeason' : season_number,
                                'airedEpisodeNumber' : episode['episode_number'] } )
            except:
                continue
    return sData

def get_tot_epdict_tmdb( showName, firstAiredYear = None, showSpecials = False, showFuture = False, minmatch = 50.0 ):
    """
    Returns a :py:class:`dict` of episodes found from the TMDB_ API. The top level dictionary's keys are the season numbers, and each value is the next-level dictionary of season information. The next level, season dictionary's keys are the episode number, and its values are a two-element :tuple: of episode names and aired dates (as a :py:class:`date <datetime.date>` object). This two level dictionary has the same format as the output from :py:meth:`get_tot_epdict_tvdb <howdy.tv.tv.get_tot_epdict_tvdb>`.

    :param str showName: the series name.
    :param int firstAiredYear: optional argument. If provided, filter on TV shows that were first aired that year.
    :param bool showSpecials: if ``True``, then also include TV specials. These specials will appear in a season ``0`` in this dictionary.
    :param bool showFuture: optional argument, if ``True`` then also include information on episodes that have not yet aired.
    :param float minmatch: the minimal matching of the series name. Default is 50.0.
    :returns: a :py:class:`dict` of episode information for that TV show. For example, for `The Simpsons`_,
    
      .. code-block:: python

         {1: {1: ('Simpsons Roasting on an Open Fire',
                  datetime.date(1989, 12, 17)),
           2: ('Bart the Genius', datetime.date(1990, 1, 14)),
           3: ("Homer's Odyssey", datetime.date(1990, 1, 21)),
           4: ("There's No Disgrace Like Home", datetime.date(1990, 1, 28)),
           5: ('Bart the General', datetime.date(1990, 2, 4)),
           6: ('Moaning Lisa', datetime.date(1990, 2, 11)),
           7: ('The Call of the Simpsons', datetime.date(1990, 2, 18)),
           8: ('The Telltale Head', datetime.date(1990, 2, 25)),
           9: ('Life on the Fast Lane', datetime.date(1990, 3, 18)),
           10: ("Homer's Night Out", datetime.date(1990, 3, 25)),
           11: ('The Crepes of Wrath', datetime.date(1990, 4, 15)),
           12: ('Krusty Gets Busted', datetime.date(1990, 4, 29)),
           13: ('Some Enchanted Evening', datetime.date(1990, 5, 13))},
           ...
         }
         
      If unsuccessful, then returns ``None``.
       
    :rtype: dict

    .. seealso::
    
       * :py:meth:`get_tot_epdict_tvdb <howdy.tv.tv.get_tot_epdict_tvdb>`.
       * :py:meth:`get_tot_epdict_imdb <howdy.tv.tv_attic.get_tot_epdict_imdb>`.
       * :py:meth:`get_tot_epdict_omdb <howdy.tv.tv_attic.get_tot_epdict_omdb>`.
    """
    tmdbID = get_series_tmdb_id( showName, firstAiredYear = firstAiredYear, minmatch = minmatch )
    if tmdbID is None: return None
    eps = get_episodes_series_tmdb( tmdbID, showSpecials = showSpecials, showFuture = showFuture )
    tot_epdict = { }
    for episode in eps:
        seasnum = episode[ 'airedSeason' ]
        title = episode[ 'episodeName' ]
        epno = episode[ 'airedEpisodeNumber' ]
        airedDate = episode[ 'airedDate' ]
        tot_epdict.setdefault( seasnum, { } )
        tot_epdict[ seasnum ][ epno ] = ( title, airedDate )
    return tot_epdict

def get_tot_epdict_singlewikipage(epURL, seasnums = 1, verify = True):
    """    
    Returns a dictionary of episodes from a Wikipedia_ URL for a TV show.

    :param str epURL: the Wikipedia_ URL for the TV show.
    :param int seasnums: the season number for which to get episodes.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: a :py:class:`dict` of episodes for this season. Each key is the episode number, and each value is the episode name.
    :rtype: dict

    .. deprecated:: 1.0
      
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
    
    .. deprecated:: 1.0
    
       I have not understood the purpose behind this method in years. No other methods call this it. I might remove this method altogether.
    """
    eps_copy = copy.deepcopy( eps )
    tmdb_id = movie.get_tv_ids_by_series_name( seriesName, verify = verify )
    if len( tmdb_id ) == 0: return
    tmdb_id = tmdb_id[ 0 ]
    tmdb_tv_info = movie.get_tv_info_for_series( tmdb_id, verify = verify )
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

def get_tot_epdict_imdb( showName, firstAiredYear = None ):
    """
    Returns a summary nested :py:class:`dict` of episode information for a given TV show, using :py:class:`Cinemagoer <imdb.Cinemagoer>` class in the `Cinemagoer Python Package`_.

    * The top level dictionary has keys that are the TV show's seasons. Each value is a second level dictionary of information about each season.

    * The second level dictionary has keys (for each season) that are the season's episodes. Each value is a :py:class:`tuple` of episode name and air date, as a :py:class:`date <datetime.date>`.

    An example of the structure of this dictionary can be found in :py:meth:`get_tot_epdict_tvdb <howdy.tv.tv.get_tot_epdict_tvdb>`.

    :param str showName: the series name.
    :param int firstAiredYear: optional argument. If provided, filter on TV shows that were first aired that year.

    :returns: a summary nested :py:class:`dict` of episode information for a given TV show.
    :rtype: dict

    .. seealso::

       * :py:meth:`get_tot_epdict_tvdb <howdy.tv.tv.get_tot_epdict_tvdb>`.
       * :py:meth:`get_tot_epdict_omdb <howdy.tv.tv_attic.get_tot_epdict_omdb>`.
       * :py:meth:`get_tot_epdict_tmdb <howdy.tv.tv_attic.get_tot_epdict_tmdb>`.

    .. _`Cinemagoer Python Package`: https://cinemagoer.readthedocs.io/en/latest
    """
    time0 = time.perf_counter( )
    ia = Cinemagoer( )
    cand_series = list(filter(lambda entry: entry.data['kind'] == 'tv series', ia.search_movie( showName ) ) )
    if len( cand_series ) == 0: return None # cannot find showName
    if firstAiredYear is None:
        series = cand_series[ 0 ]
    else:
        cand_series = list(filter(lambda entry: entry.data['year'] == firstAiredYear, cand_series))
        if len( cand_series ) == 0: return None # cannot find showName
        series = cand_series[ 0 ]
    #
    ia.update( series, 'episodes' )
    logging.debug('took %0.3f seconds to get episodes for %s.' % (
        time.perf_counter( ) - time0, showName ) )
    tot_epdict = { }
    seasons = sorted( set(filter(lambda seasno: seasno != -1, series['episodes'].keys( ) ) ) )
    for season in seasons:
        tot_epdict.setdefault( season, { } )
        for epno in series['episodes'][season]:
            episode = series['episodes'][season][epno]
            title = episode[ 'title' ].strip( )
            firstAired = None
            try:
                firstAired_s = episode[ 'original air date' ]
                firstAired = datetime.datetime.strptime(
                    firstAired_s, '%d %b. %Y' ).date( )
            except:
                pass
            if firstAired is None:
                try:
                    firstAired_s = episode[ 'original air date' ]
                    firstAired = datetime.datetime.strptime( firstAired_s, '%Y' ).date( )
                except:
                    firstAired = datetime.datetime.strptime( '1900', '%Y' ).date( )
            #firstAired = tot_epdict_tvdb[ season ][ epno ][-1]
            tot_epdict[ season ][ epno ] = ( title, firstAired )
    return tot_epdict
