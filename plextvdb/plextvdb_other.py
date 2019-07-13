import requests, os, sys, json, re
import logging, datetime, fuzzywuzzy.fuzz
from PIL import Image
from io import StringIO
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
    items = filter(lambda item: 'Poster' in item.keys( ) and item['Poster'] != 'N/A' and 'imdbID' in item.keys( ),
                   data['Search'])
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
                print 'Could not find %s in %d' % ( showName, inYear )
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
            newresults = filter(lambda result: fuzzywuzzy.fuzz.ratio( result['title'], title ) >= 10.0,
                                data['results'] )
            if len( newresults ) > 0:
                results += sorted( newresults, key = lambda result: -fuzzywuzzy.fuzz.ratio( result['title'], title ) )
    if len( results ) == 0: return None
    return map(lambda result: { 'id' : result['id'], 'name' : result['name'],
                                'airedYear' : datetime.datetime.strptime( result['first_air_date'], '%Y-%m-%d' ).year },
               results )

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
