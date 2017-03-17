import requests, os, sys, json, re, logging, datetime
from PIL import Image
from cStringIO import StringIO
from dateutil.relativedelta import relativedelta

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
