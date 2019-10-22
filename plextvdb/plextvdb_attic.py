import requests, os, sys
import logging, datetime, fuzzywuzzy.fuzz
from dateutil.relativedelta import relativedelta

from plextmdb import tmdb_apiKey

def get_series_omdb_id( series_name ):
    params = { 's' : series_name, 'type' : 'series', 'plot' : 'full' }
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

def get_possible_omdb_ids( series_name ):
    params = { 's' : series_name, 'type' : 'series', 'plot' : 'full' }
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
    items = filter(lambda item: 'Poster' in item.keys( ) and item['Poster'] != 'N/A' and 'imdbID' in item.keys( ),
                   data['Search'])
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
        return range( startYear, endYear + 1 )
    return map( lambda item: ( item['imdbID'], get_range_years( item ) ), items )

"""
Does not show the specials for the TV series
"""
def get_episodes_series_omdb( imdbID, fromDate = None ):
    response = requests.get( 'http://www.omdbapi.com',
                             params = { 'i' : imdbID, 'type' : 'series', 'plot' : 'full' } )
    if response.status_code != 200: return None
    data = response.json( )
    numSeasons = int( data[ 'totalSeasons' ] )
    currentDate = datetime.datetime.now( ).date( )
    sData = [ ]
    for season in xrange( 1, numSeasons + 1 ):
        params_season = { 'i' : imdbID, 'type' : 'series', 'plot' : 'full', 'Season' : season }
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
        sData += filter(lambda episode: episode['Episode'] <= last_ep, episodes_valid)
    return sData

def get_tot_epdict_omdb( showName, inYear = None ):
    if inYear is None:
        imdbID = get_series_omdb_id( showName )
    else:
        valids = get_possible_omdb_ids( showName )
        if len(valids) == 1:
            imdbID = valid[0][0]
        else:
            valids = filter(lambda item: inYear in item[1], valids )
            if len(valids) == 0:
                print( 'Could not find %s in %d' % ( showName, inYear ) )
                return None
            imdbID = valids[0][0]
    eps = get_episodes_series_omdb( imdbID )
    tot_epdict = { }
    for episode in eps:
        seasnum = episode[ 'airedSeason' ]
        epno = episode[ 'Episode' ]
        title = episode[ 'Title' ]
        tot_epdict.setdefault( seasnum, { } )
        tot_epdict[seasnum][epno] = title
    return tot_epdict

def get_possible_tmdb_ids( series_name, firstAiredYear = None ):
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
    results = get_possible_tmdb_ids( series_name, firstAiredYear = firstAiredYear )
    if len( results ) == 0: return None
    return results[0]['id']

"""
Ignore specials (season 0) for now...
"""
def get_episodes_series_tmdb( tmdbID, fromDate = None ):
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

        
"""
Date must be within 4 weeks of now
"""
def get_series_updated_fromdate( date, token, verify = True ):
    """
    
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
    from imdb import IMDb
    token = get_token( verify = verify )
    id = get_series_id( showName, token, verify = verify )
    if id is None: return None
    imdbId = get_imdb_id( id, token, verify = verify )
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
    tot_epdict_tvdb = get_tot_epdict_tvdb( showName, verify = verify )
    for season in seasons:
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
