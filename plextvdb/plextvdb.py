import requests, os, sys, json, re, logging
import multiprocessing, datetime, time
from functools import reduce
from PIL import Image
from io import StringIO
from dateutil.relativedelta import relativedelta
from fuzzywuzzy.fuzz import ratio
from . import get_token

def _create_season( input_tuple ):
    seriesName, seriesId, token, season, verify = input_tuple
    return season, TVSeason( seriesName, seriesId, token, season, verify = verify )

class TVSeason( object ):
    def get_num_episodes( self ):
        return len( self.episodes )
    
    def get_max_date( self ):
        if self.get_num_episodes( ) == 0: return None            
        return max(map(lambda epelem: epelem['airedDate'], self.episodes.values( ) ) )

    def get_min_date( self ):
        if self.get_num_episodes( ) == 0: return None
        return min(map(lambda epelem: epelem['airedDate'], self.episodes.values( ) ) )
        
    def _get_season_episodes( self, token, verify = True ):
        currentDate = datetime.datetime.now( ).date( )
        headers = { 'Content-Type' : 'application/json',
                    'Authorization' : 'Bearer %s' % token }
        params = { 'airedSeason' : self.seasno, 'page' : 1 }
        response = requests.get( 'https://api.thetvdb.com/series/%d/episodes/query' % self.seriesId,
                                 headers = headers, params = params, verify = verify )
        if response.status_code != 200:
            raise ValueError("Error, could find no episodes for season %02d in series %s." %
                             ( self.seasno, self.seriesName ) )
        data = response.json( )['data']
        links = response.json( )['links']
        lastpage = links[ 'last' ]
        seriesdata = data
        for pageno in range( 2, lastpage + 1 ):
            params = {  'airedSeason' : self.seasno, 'page' : pageno }
            response = requests.get( 'https://api.thetvdb.com/series/%d/episodes/query' % self.seriesId,
                                     headers = headers, params = params, verify = verify )                                     
            if response.status_code != 200:
                continue
            seriesdata += response.json( )['data']
        sData = { }
        for episode in seriesdata:
            try:
                 date = datetime.datetime.strptime( episode['firstAired'], '%Y-%m-%d' ).date( )
                 if date > currentDate:
                     continue
            except Exception:
                continue
            airedDate = datetime.datetime.strptime( episode['firstAired'], '%Y-%m-%d' ).date( )
            epno = int( episode[ 'airedEpisodeNumber' ] )
            name = episode[ 'episodeName' ]
            overview = episode[ 'overview' ]
            sData[ epno ] = { 'name' : name,
                              'overview' : overview,
                              'airedDate': airedDate }
        return sData        
    
    def _get_season_image( self, token, verify = True ):
        headers = { 'Content-Type' : 'application/json',
                    'Authorization' : 'Bearer %s' % token }
        response = requests.get( 'https://api.thetvdb.com/series/%d/images/query/params' % self.seriesId,
                                 headers = headers, verify = verify )
        if response.status_code != 200:
            return None
        data = response.json( )['data']
        #
        ## look for season keytype
        season_ones = filter(lambda elem: 'keyType' in elem.keys( ) and elem['keyType'] == 'season', data )
        if len( season_ones ) == 0:
            return None
        season_one = season_ones[ 0 ]
        if 'subKey' not in season_one:
            return None
        #
        ## now look to see if season in subkey
        if '%d' % self.seasno not in season_one['subKey']:
            return None
        #
        ## now get that image for season
        params = { 'keyType' : 'season', 'subKey' : '%d' % self.seasno }
        if 'resolution' in season_one.keys( ) and len( season_one[ 'resolution' ] ) != 0:
            params[ 'resolution' ] = season_one[ 'resolution' ][ 0 ]
        response = requests.get( 'https://api.thetvdb.com/series/%d/images/query' % self.seriesId,
                                 headers = headers, params = params, verify = verify )
        if response.status_code != 200:
            return None
        data = response.json( )['data']
        firstSeason = data[ 0 ]
        assert( 'fileName' in firstSeason )
        return 'https://thetvdb.com/banners/%s' % firstSeason[ 'fileName' ]        
    
    def __init__( self, seriesName, seriesId, token, seasno, verify = True ):
        self.seriesName = seriesName
        self.seriesId = seriesId
        self.seasno = seasno
        #
        ## first get the image associated with this season
        self.imageURL = self._get_season_image( token, verify = verify )
        self.img = None
        if self.imageURL is not None:
            response = requests.get( self.imageURL )
            if response.status_code == 200:
                self.img = Image.open( StringIO( response.content ) )

        #
        ## now get the specific episodes for that season
        self.episodes = self._get_season_episodes( token )

class TVShow( object ):
    def _get_series_seasons( self, token, verify = True ):
        headers = { 'Content-Type' : 'application/json',
                    'Authorization' : 'Bearer %s' % token }
        response = requests.get( 'https://api.thetvdb.com/series/%d/episodes/summary' % self.seriesId,
                                 headers = headers, verify = verify )
        if response.status_code != 200:
            return None
        data = response.json( )['data']
        if 'airedSeasons' not in data:
            return None
        return sorted( map(lambda tok: int(tok), data['airedSeasons'] ) )
        
    def _get_series_image( self, token, verify = True ):
        headers = { 'Content-Type' : 'application/json',
                    'Authorization' : 'Bearer %s' % token }
        response = requests.get( 'https://api.thetvdb.com/series/%d/images/query/params' % self.seriesId,
                                 headers = headers, verify = verify )
        if response.status_code != 200:
            return None
        data = response.json( )['data']
        #
        ## first look for poster entries
        poster_ones = filter(lambda elem: 'keyType' in elem.keys() and elem['keyType'] == 'poster', data )
        if len( poster_ones ) != 0:
            poster_one = poster_ones[ 0 ]
            params = { 'keyType' : 'poster' }
            if 'resolution' in poster_one and len( poster_one['resolution'] ) != 0:
                params['resolution'] = poster_one['resolution'][0]
            response = requests.get( 'https://api.thetvdb.com/series/%d/images/query' % self.seriesId,
                                     headers = headers, params = params, verify = verify )
            if response.status_code == 200:
                data = response.json( )['data']
                firstPoster = data[0]
                assert( 'fileName' in firstPoster )
                return 'https://thetvdb.com/banners/%s' % firstPoster['fileName']
        fanart_ones = filter(lambda elem: 'keyType' in elem.keys( ) and
                             elem['keyType'] == 'fanart', data )
        if len( fanart_ones ) != 0:
            fanart_one = fanart_ones[ 0 ]
            params = { 'keyType' : 'fanart' }
            if 'resolution' in fanart_one and len( fanart_one['resolution'] ) != 0:
                params['resolution'] = fanart_one['resolution'][0]
            response = requests.get( 'https://api.thetvdb.com/series/%d/images/query' % self.seriesId,
                                     headers = headers, params = params, verify = verify )
            if response.status_code == 200:
                data = response.json( )['data']
                firstFanart = data[0]
                assert( 'fileName' in firstFanart )
                return 'https://thetvdb.com/banners/%s' % firstFanart['fileName']
        series_ones = filter(lambda elem: 'keyType' in elem.keys( ) and
                             elem['keyType'] == 'series')
        if len( series_ones ) != 0:
            series_one = series_ones[ 0 ]
            params = { 'keyType' : 'series' }
            if 'resolution' in series_one and len( series_one['resolution'] ) != 0:
                params['resolution'] = series_one['resolution'][0]
            response = requests.get( 'https://api.thetvdb.com/series/%d/images/query' % self.seriesId,
                                     headers = headers, params = params, verify = verify )
            if response.status_code == 200:
                data = response.json( )['data']
                firstSeries = data[0]
                assert( 'fileName' in firstSeries )
                return 'https://thetvdb.com/banners/%s' % firstSeries['fileName']
        return None ## nothing happened
        
    def __init__( self, seriesName, token, verify = True ):
        self.seriesId = get_series_id( seriesName, token, verify = verify )
        self.seriesName = seriesName
        if self.seriesId is None:
            raise ValueError("Error, could not find TV Show named %s." % seriesName )
        #
        ## check if status ended
        self.statusEnded = did_series_end( self.seriesId, token, verify = verify )
        if self.statusEnded is None:
             raise ValueError("Error, could not find whether TV Show named %s ended or not." %
                              seriesName )
        #
        ## get Image URL and Image
        self.imageURL = self._get_series_image( token )
        self.img = None
        if self.imageURL is not None:
            response = requests.get( self.imageURL )
            if response.status_code == 200: 
                self.img = Image.open( StringIO( response.content ) )
        #
        ## get every season defined
        allSeasons = self._get_series_seasons( token )
        pool = multiprocessing.Pool( processes = multiprocessing.cpu_count( ) )
        input_tuples = map(lambda seasno: (
            self.seriesName, self.seriesId, token, seasno, verify ),
                           allSeasons)
        self.seasonDict = dict( filter(lambda seasno_tvseason: len( seasno_tvseason[1].episodes ) != 0,
                                       pool.map( _create_season, input_tuples ) ) )
        self.startDate = min(filter(None, map(lambda tvseason: tvseason.get_min_date( ),
                                              self.seasonDict.values( ) ) ) )
        self.endDate = max(filter(None, map(lambda tvseason: tvseason.get_max_date( ),
                                            self.seasonDict.values( ) ) ) )

    def get_episode_name( self, airedSeason, airedEpisode ):
        if airedSeason not in self.seasonDict:
            raise ValueError("Error, season %d not a valid season." % airedSeason )
        if airedEpisode not in self.seasonDict[ airedSeason ].episodes:
            raise ValueError("Error, episode %d in season %d not a valid episode number." % (
                airedEpisode, airedSeason ) )
        epStruct = self.seasonDict[ airedSeason ].episode[ airedEpisode ]
        return ( epStruct['name'], epStruct['airedDate'] )

    def get_episodes_series( self, showSpecials = True, fromDate = None ):
        seasons = set( self.seasonDict.keys( ) )
        print('all seasons: %s' % seasons )
        if not showSpecials:
            seasons = seasons - set([0,])
        sData = reduce(lambda x,y: x+y,
                       map(lambda seasno:
                           map(lambda epno: ( seasno, epno ),
                               self.seasonDict[ seasno ].episodes.keys( ) ),
                           seasons ) )
        if fromDate is not None:
            sData = filter(lambda seasno_epno:
                           self.seasonDict[ seasno_epno[0] ].episodes[ seasno_epno[1] ][ 'airedDate' ] >=
                           fromDate, sData )
        return sData

    def get_tot_epdict_tvdb( self ):
        tot_epdict = { }
        seasons = set( self.seasonDict.keys( ) ) - set([0,])
        for seasno in sorted(seasons):
            tot_epdict.setdefault( seasno, {} )
            for epno in sorted(self.seasonDict[ seasno ].episodes):
                epStruct = self.seasonDict[ seasno ].episodes[ epno ]
                title = epStruct[ 'name' ]
                airedDate = epStruct[ 'airedDate' ]
                tot_epdict[ seasno ][ epno ] = ( title, airedDate )
        return tot_epdict

#
## method to get all the shows organized by date.
## 1)  key is date
## 2)  value is list of tuples
## 2a) each tuple is of type date, show name, season, episode number, episode title
def get_tvdata_ordered_by_date( tvdata, year = 2010 ):
    def _get_tuple_list_season( show, seasno ):
        assert( show in tvdata )
        assert( seasno in tvdata[ show ] )
        episodes_dict = tvdata[ show ][ seasno ]
        return list( filter(lambda tup: tup[0].year > 1900,
                            map(lambda epno: (
                                episodes_dict[ epno ][ 1 ], show,
                                seasno, epno,
                                episodes_dict[ epno ][ 0 ] ), episodes_dict ) ) )
    def _get_tuple_list_show( show ):
        assert( show in tvdata )
        return reduce(lambda x,y: x+y, list( map(lambda seasno: _get_tuple_list_season( show, seasno ),
                                           tvdata[ show ] ) ) )
    tvdata_tuples = reduce(lambda x,y: x+y, list( map(lambda show: _get_tuple_list_show( show ), tvdata) ) )
    tvdata_date_dict = { }
    for tup in tvdata_tuples:
        tvdata_date_dict.setdefault( tup[0], [ ] ).append( tup[1:] )
    return tvdata_date_dict

def create_plot_year_tvdata( tvdata_date_dict, year = 2010 ):
    calendar.setfirstweekday( 6 )
    def suncal( mon, year = 2010 ):
        return numpy.array( calendar.monthcalendar( year, mon ), dtype=int )
    
    fig = pylab.figure( figsize = ( 8 * 3, 6 * 5 ) )
    days = [ 'SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT' ]
    firstcolors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
                   '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
                   '#bcbd22']
    numdays = sum(list(map(lambda mon: len( numpy.where( suncal( mon, year ) > 0)[1] ),
                           range(1, 13 ))))
    numdays_eps = len(list(filter(lambda mydate: mydate.year == year, tvdata_date_dict)))
    numeps = sum(list(map(lambda mydate: len( tvdata_date_dict[ mydate ] ),
                          filter(lambda mydate: mydate.year == year, tvdata_date_dict))))
    #
    ## now count the number of shows in these new episodes
    shownames = set(reduce(lambda x,y: x+y,
                           list( map(lambda mydate: list(map(lambda tup: tup[0], tvdata_date_dict[ mydate ] ) ),
                                     filter(lambda mydate: mydate.year == year, tvdata_date_dict)))))
    
    #
    ## these are the legend plots
    ax = fig.add_subplot(5,3,3)
    pylab.axis('off')
    ax.set_xlim([0,1])
    ax.set_ylim([0,1])
    mystr = '\n'.join([
        '%d / %d days have new episodes' % (numdays_eps, numdays),
        '%d new episodes in' % numeps,
        '%d shows' % len( shownames ) ])
    ax.text(0.15, 0.5, mystr,
            fontdict = { 'fontsize' : 16, 'fontweight' : 'bold' },
            horizontalalignment = 'left', verticalalignment = 'center',
            color = 'black' )
    #
    ax = fig.add_subplot(5,3,2)
    pylab.axis('off')
    ax.set_xlim([0,1])
    ax.set_ylim([0,1])
    ax.text(0.5,0.5, '\n'.join([ '%d TV DATA' % year, 'EPISODE COUNTS' ]),
            fontdict = { 'fontsize' : 24, 'fontweight' : 'bold' },
            horizontalalignment = 'center', verticalalignment = 'center' )
    #
    ax = fig.add_subplot(5,3,1)
    pylab.axis('off')
    ax.set_xlim([0,1])
    ax.set_ylim([0,1])
    ax.text( 0.5, 0.75, 'number of new episodes on a day',
             fontdict = { 'fontsize' : 14, 'fontweight' : 'bold' },
             horizontalalignment = 'center', verticalalignment = 'center' )
    for idx in range( 10 ):
        ax.add_patch( Rectangle(( 0.01 + 0.098 * idx, 0.5 ), 0.098, 0.098 * 1.5,
                                linewidth = 2, facecolor = 'white', edgecolor = 'black' ) )
        if idx == 0: color = 'white'
        else: color = firstcolors[ idx - 1 ]
        ax.add_patch( Rectangle(( 0.01 + 0.098 * idx, 0.5 ), 0.098, 0.098 * 1.5,
                                facecolor = color, edgecolor = None, alpha = 0.5 ) )
        if idx != 9: mytxt = '%d' % idx
        else: mytxt = '≥ %d' % idx
        ax.text( 0.01 + 0.098 * ( idx + 0.5 ), 0.5 + 0.098 * 0.75, mytxt,
                 fontdict = { 'fontsize' : 14, 'fontweight' : 'bold' },
                 horizontalalignment = 'center', verticalalignment = 'center' )
    
    for mon in range(1, 13):
        cal = suncal( mon, year )
        ax = fig.add_subplot(5, 3, mon + 3 )
        ax.set_xlim([0,1])
        ax.set_ylim([0,1])
        pylab.axis('off')
        for jdx in range(7):
            ax.text( 0.01 + 0.14 * (jdx + 0.5), 0.93, days[jdx],
                     fontdict = { 'fontsize' : 14, 'fontweight' : 'bold' },
                     horizontalalignment = 'center',
                     verticalalignment = 'center' )
        for idx in range(cal.shape[0]):
            for jdx in range(7):
                if cal[idx, jdx] == 0: continue
                cand_date = datetime.date( year, mon, cal[ idx, jdx ] )
                if cand_date in tvdata_date_dict:
                    count = min( 9, len( tvdata_date_dict[ cand_date ] ) )
                    color = firstcolors[ count - 1 ]
                else: color = 'white'
                ax.add_patch( Rectangle( ( 0.01 + 0.14 * jdx,
                                           0.99 - 0.14 - 0.14 * (idx + 1) ),
                                         0.14, 0.14, linewidth = 2,
                                         facecolor = 'white', edgecolor = 'black' ) )
                ax.add_patch( Rectangle( ( 0.01 + 0.14 * jdx,
                                           0.99 - 0.14 - 0.14 * (idx + 1) ),
                                         0.14, 0.14, linewidth = 2,
                                         facecolor = color, edgecolor = None, alpha = 0.5 ) )
                ax.text( 0.01 + 0.14 * ( jdx + 0.5 ),
                         0.99 - 0.14 - 0.14 * ( idx + 0.5 ), '%d' % cal[idx, jdx],
                         fontdict = { 'fontsize' : 14, 'fontweight' : 'bold' },
                         horizontalalignment = 'center',
                         verticalalignment = 'center' )
        monname = datetime.datetime.strptime('%02d.%d' % ( mon, year ),
                                             '%m.%Y' ).strftime('%B').upper( )
        ax.set_title( monname, fontsize = 14, fontweight = 'bold' )
    fig.savefig( 'tvdata.%d.svgz' % year, bbox_inches = 'tight' )
    pylab.close( )
    
def get_series_id( series_name, token, verify = True ):
    data_ids = get_possible_ids( series_name, token, verify = verify )
    if data_ids is None:
        print( 'PROBLEM WITH series %s' % series_name )
        return None
    data_matches = list(filter(lambda dat: dat['seriesName'] == series_name,
                               data_ids ) )
    #
    ## if not get any matches, choose best one
    if len( data_matches ) == 0:
        data_match = max( data_ids, key = lambda dat:
                          ratio( dat[ 'seriesName' ], series_name ) )
        return data_match[ 'id' ]
    if len( data_matches ) != 1: return None
    return max( data_matches )[ 'id' ]

def get_possible_ids( series_name, token, verify = True ):
    params = { 'name' : series_name.replace("'", '') }
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % token }
    response = requests.get( 'https://api.thetvdb.com/search/series',
                             params = params, headers = headers,
                             verify = verify )
    if response.status_code != 200: # quick hack to get this to work
        # was a problem with show AQUA TEEN HUNGER FORCE FOREVER
        params = { 'name' : ' '.join( series_name.replace("'", '').split()[:-1] ) }
        headers = { 'Content-Type' : 'application/json',
                    'Authorization' : 'Bearer %s' % token }
        response = requests.get( 'https://api.thetvdb.com/search/series',
                                 params = params, headers = headers,
                                 verify = verify )
        if response.status_code != 200: return None
    data = response.json( )[ 'data' ]
    return list(map(lambda dat: {
        'id' : dat['id'], 'seriesName' : dat['seriesName'] }, data ) )

def did_series_end( series_id, token, verify = True ):
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % token }
    response = requests.get( 'https://api.thetvdb.com/series/%d' % series_id,
                             headers = headers, verify = verify )
    if response.status_code != 200: return None
    data = response.json( )['data']
    return data['status'] == 'Ended'

def get_episode_id( series_id, airedSeason, airedEpisode, token, verify = True ):
    params = { 'page' : 1,
               'airedSeason' : '%d' % airedSeason,
               'airedEpisode' : '%d' % airedEpisode }
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % token }
    response = requests.get( 'https://api.thetvdb.com/series/%d/episodes/query' % series_id,
                             params = params, headers = headers, verify = verify )
    if response.status_code != 200: return None
    data = max( response.json( )[ 'data' ] )
    return data[ 'id' ]

def get_episode_name( series_id, airedSeason, airedEpisode, token, verify = True ):
    params = { 'page' : 1,
               'airedSeason' : '%d' % airedSeason,
               'airedEpisode' : '%d' % airedEpisode }
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % token }
    response = requests.get( 'https://api.thetvdb.com/series/%d/episodes/query' % series_id,
                             params = params, headers = headers, verify = verify )
    if response.status_code != 200: return None
    data = max( response.json( )[ 'data' ] )
    try:
        firstAired_s = data[ 'firstAired' ]
        firstAired = datetime.datetime.strptime( firstAired_s,
                                                 '%Y-%m-%d' ).date( )
    except:
        firstAired = datetime.datetime.strptime( '1900-01-01',
                                                 '%Y-%m-%d' ).date( )
    
    return ( data[ 'episodeName' ], firstAired )

def get_episodes_series( series_id, token, showSpecials = True, fromDate = None, verify = True ):
    params = { 'page' : 1 }
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % token }
    response = requests.get( 'https://api.thetvdb.com/series/%d/episodes' % series_id,
                             params = params, headers = headers, verify = verify )
    if response.status_code != 200: return None
    data = response.json( )
    links = data[ 'links' ]
    lastpage = links[ 'last' ]
    seriesdata = data[ 'data' ]
    for pageno in range( 2, lastpage + 1 ):
        response = requests.get( 'https://api.thetvdb.com/series/%d/episodes' % series_id,
                                 params = { 'page' : pageno }, headers = headers,
                                 verify = verify )
        data = response.json( )
        seriesdata += data[ 'data' ]
    currentDate = datetime.datetime.now( ).date( )
    sData = [ ]
    logging.debug( 'GET_EPISODES_SERIES: %s' % seriesdata )
    for episode in seriesdata:
        try:
            date = datetime.datetime.strptime( episode['firstAired'], '%Y-%m-%d' ).date( )
            if date > currentDate:
                continue
            if fromDate is not None:
                if date < fromDate:
                    continue
        except Exception:
            continue
        if episode[ 'airedSeason' ] is None:
            continue
        if episode[ 'airedEpisodeNumber' ] is None:
            continue
        if not showSpecials and episode[ 'airedSeason' ] == 0:
            continue
        if episode[ 'airedEpisodeNumber' ] == 0:
            continue
        sData.append( episode )
    return sData

"""
Date must be within 4 weeks of now
"""
def get_series_updated_fromdate( date, token, verify = True ):
    assert( date + relativedelta(weeks=4) >= datetime.datetime.now( ).date( ) )
    datetime_now = datetime.datetime.now( )
    dates_start = filter(lambda mydate: mydate < datetime_now.date( ),
                         sorted(map(lambda idx: date + relativedelta(weeks=idx), range(5))))
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

def _get_remaining_eps_perproc( input_tuple ):
    #name, epsForShow, token, showSpecials, fromDate, verify, doShowEnded = input_tuple
    name, series_id, epsForShow, token, showSpecials, fromDate, verify = input_tuple
    eps = get_episodes_series( series_id, token, showSpecials = showSpecials, verify = verify,
                               fromDate = fromDate )
    tvdb_eps = set(map(lambda ep: ( ep['airedSeason'], ep['airedEpisodeNumber' ] ), eps ) )
    #tvshow = TVShow( name, token, verify = verify )
    #if not doShowEnded and tvshow.statusEnded:
    #    return None
    #tvdb_eps = set(tvshow.get_episodes_series( showSpecials = showSpecials, fromDate = fromDate ) )
    here_eps = set([ ( seasno, epno ) for seasno in epsForShow for
                     epno in epsForShow[ seasno ] ] )
    tuples_to_get = tvdb_eps - here_eps
    if len( tuples_to_get ) == 0:
        return None
    return name, sorted( tuples_to_get )

def _get_series_id_perproc( input_tuple ):
    show, token, verify, doShowEnded = input_tuple
    series_id = get_series_id( show, token, verify = verify )
    if series_id is None:
        print( 'SOMETHING HAPPENED WITH SHOW %s' % show )
        return None
    if not doShowEnded:
        didEnd = did_series_end( series_id, token, verify = verify )
        if didEnd is None: return None
        if didEnd: return None
    return show, series_id
    
def get_remaining_episodes( tvdata, showSpecials = True, fromDate = None, verify = True,
                            doShowEnded = False ):
    token = get_token( verify = verify )
    pool = multiprocessing.Pool( processes = multiprocessing.cpu_count( ) )
    tvshow_id_map = dict( filter(lambda tup: tup is not None, 
                                 pool.map( _get_series_id_perproc,
                                           map(lambda show: ( show, token, verify, doShowEnded ), tvdata ) ) ) )
    if fromDate is not None:
        series_ids = set( get_series_updated_fromdate( fromDate, token ) )
        ids_tvshows = dict(map(lambda name_seriesId: ( name_seriesId[1], name_seriesId[0] ), tvshow_id_map.items( ) ) )
        updated_ids = set( ids_tvshows.keys( ) ) & series_ids
        tvshow_id_map = { ids_tvshows[ series_id ] : series_id for series_id in
                          updated_ids }
    tvshows = sorted( set( tvshow_id_map.keys( ) ) )
    input_tuples = map(lambda name: ( name, tvshow_id_map[ name ], tvdata[ name ], token,
                                      showSpecials, fromDate, verify ), tvshow_id_map )
    pool = multiprocessing.Pool( processes = multiprocessing.cpu_count( ) )
    toGet = dict( filter( lambda tup: tup is not None,
                          pool.map( _get_remaining_eps_perproc,
                                    input_tuples ) ) )
    return toGet
                                
def get_tot_epdict_tvdb( showName, verify = True, showSpecials = False ):
    token = get_token( verify = verify )
    id = get_series_id( showName, token, verify = verify )
    eps = get_episodes_series( id, token, verify = verify )
    totseasons = max( map(lambda episode: int( episode['airedSeason' ] ), eps ) )
    tot_epdict = { }
    for episode in eps:
        seasnum = int( episode[ 'airedSeason' ] )
        if not showSpecials and seasnum == 0: continue
        epno = episode[ 'airedEpisodeNumber' ]
        title = episode[ 'episodeName' ]
        try:
            firstAired_s = episode[ 'firstAired' ]
            firstAired = datetime.datetime.strptime( firstAired_s,
                                                     '%Y-%m-%d' ).date( )
        except:
            firstAired = datetime.datetime.strptime('1900-01-01',
                                                    '%Y-%m-%d' ).date( )
        tot_epdict.setdefault( seasnum, { } )
        tot_epdict[ seasnum ][ epno ] = ( title, firstAired )
    return tot_epdict

def get_tot_epdict_singlewikipage(epURL, seasnums = 1, verify = True):
    import lxml.html, titlecase
    assert(seasnums >= 1)
    assert(isinstance(seasnums, int))
    #
    def is_epelem(elem):
        if elem.tag == 'span':
            if 'class' not in elem.keys():
                return False
            if 'id' not in elem.keys():
                return False
            if elem.get('class') != 'mw-headline':
                return False
            if 'Season' not in elem.get('id'):
                return False
            return True
        elif elem.tag == 'td':
            if 'class' not in elem.keys():
                return False
            if 'style' not in elem.keys():
                return False
            if elem.get('class') != 'summary':
                return False
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
