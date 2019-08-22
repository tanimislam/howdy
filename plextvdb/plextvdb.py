import requests, os, sys, json, re, logging
import datetime, time, numpy, copy, calendar, shutil
import pathos.multiprocessing as multiprocessing
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Ellipse
from matplotlib.backends.backend_agg import FigureCanvasAgg
from itertools import chain
from functools import reduce
from dateutil.relativedelta import relativedelta
from fuzzywuzzy.fuzz import ratio

from plextvdb import get_token, plextvdb_torrents, ShowsToExclude
from plexcore import plexcore_rsync, splitall, session, return_error_raw
from plextmdb import plextmdb

class TVShow( object ):
    
    @classmethod
    def create_tvshow_dict( cls, tvdata, token = None, verify = True,
                            debug = False, num_threads = 16 ):
        time0 = time.time( )
        assert( num_threads > 0 )
        if token is None: token = get_token( verify = verify )
        def _create_tvshow( seriesName ):
            try: return ( seriesName,
                          TVShow( seriesName, tvdata[ seriesName ],
                                  token, verify = verify ) )
            except: return None
        with multiprocessing.Pool(
                processes = max( num_threads, multiprocessing.cpu_count( ) ) ) as pool:
            tvshow_dict = dict(filter(None, pool.map(_create_tvshow, sorted( tvdata[:60] ) ) ) )
            mystr = 'took %0.3f seconds to get a dictionary of %d / %d TV Shows.' % (
                time.time( ) - time0, len( tvshow_dict ), len( tvdata ) )
            logging.debug( mystr )
            if debug: print( mystr )
            return tvshow_dict
    
    @classmethod
    def _create_season( cls, input_tuple ):
        seriesName, seriesId, token, season, verify, eps = input_tuple
        return season, TVSeason( seriesName, seriesId, token, season, verify = verify,
                                 eps = eps )
    
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
        
    def __init__( self, seriesName, seriesInfo, token, verify = True,
                  showSpecials = False ):
        self.seriesId = get_series_id( seriesName, token, verify = verify )
        self.seriesName = seriesName
        if self.seriesId is None:
            raise ValueError("Error, could not find TV Show named %s." % seriesName )
        #
        ## check if status ended
        self.statusEnded = did_series_end( self.seriesId, token, verify = verify )
        if self.statusEnded is None:
            self.statusEnded = True # yes, show ended
            #raise ValueError("Error, could not find whether TV Show named %s ended or not." %
            #                 seriesName )
        #
        ## get Image URL and Image
        if seriesInfo['picurl'] is not None:
            self.imageURL = seriesInfo['picurl']
            self.isPlexImage = True
        else:
            self.imageURL, _ = get_series_image( self.seriesId, token, verify = verify )
            self.isPlexImage = False
        # self.img = TVShow._create_image( self.imageURL, verify = verify )

        #
        ## get series overview
        if seriesInfo['summary'] != '':
            self.overview = seriesInfo['summary']
        else:
            data, status = get_series_info( self.seriesId, token, verify = verify )
            self.overview = ''
            if status == 'SUCCESS' and 'overview' in data:
                self.overview = data[ 'overview' ]
        
        #
        ## get every season defined
        eps = get_episodes_series(
            self.seriesId, token, showSpecials = True,
            showFuture = False, verify = verify )
        if any(filter(lambda episode: episode['episodeName'] is None,
                      eps ) ):
            tmdb_id = get_tv_ids_by_series_name( seriesName, verify = verify )
            if len( tmdb_id ) == 0:
                raise ValueError("Error, could not find TV Show named %s." % seriesName )
            tmdb_id = tmdb_id[ 0 ]
            eps = plextmdb.get_episodes_series_tmdb( tmdb_id, verify = verify )
        allSeasons = sorted( set( map(lambda episode: int( episode['airedSeason' ] ), eps ) ) )
        #with multiprocessing.Pool( processes = multiprocessing.cpu_count( ) ) as pool:
        input_tuples = map(lambda seasno: (
            self.seriesName, self.seriesId, token, seasno, verify, eps ), allSeasons)
        self.seasonDict = dict(
            filter(lambda seasno_tvseason: len( seasno_tvseason[1].episodes ) != 0,
                   map( TVShow._create_season, input_tuples ) ) )
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
        if not showSpecials:
            seasons = seasons - set([0,])
        sData = list(chain.from_iterable(
            map(lambda seasno:
                map(lambda epno: ( seasno, epno ),
                    self.seasonDict[ seasno ].episodes.keys( ) ),
                seasons ) ) )
        if fromDate is not None:
            sData = filter(
                lambda seasno_epno:
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

class TVSeason( object ):
    def get_num_episodes( self ):
        return len( self.episodes )
    
    def get_max_date( self ):
        if self.get_num_episodes( ) == 0: return None            
        return max(map(lambda epelem: epelem['airedDate'],
                       filter(lambda epelem: 'airedDate' in epelem,
                              self.episodes.values( ) ) ) )

    def get_min_date( self ):
        if self.get_num_episodes( ) == 0: return None
        return min(map(lambda epelem: epelem['airedDate'],
                       filter(lambda epelem: 'airedDate' in epelem,
                              self.episodes.values( ) ) ) )
    
    def __init__( self, seriesName, seriesId, token, seasno, verify = True,
                  eps = None ):
        self.seriesName = seriesName
        self.seriesId = seriesId
        self.seasno = seasno
        #
        ## first get the image associated with this season
        self.imageURL, status = get_series_season_image(
            self.seriesId, self.seasno, token, verify = verify )
        self.img = None
        if status == 'SUCCESS':
            try:
                response = requests.get( self.imageURL )
                if response.status_code == 200:
                    self.img = PIL.Image.open( io.BytesIO( response.content ) )
            except: pass
        #
        ## now get the specific episodes for that season
        if eps is None:
            eps = get_episodes_series(
                self.seriesId, token, showSpecials = True,
                showFuture = False, verify = verify )
        epelems = list(
            filter(lambda episode: episode[ 'airedSeason' ] == self.seasno, eps ) )
        self.episodes = { }
        for epelem in epelems:
            datum = {
                'airedEpisodeNumber' : epelem[ 'airedEpisodeNumber' ],
                'airedSeason' : self.seasno,
                'title' : epelem[ 'episodeName' ].strip( )
            }
            try:
                firstAired_s = epelem[ 'firstAired' ]
                firstAired = datetime.datetime.strptime(
                    firstAired_s, '%Y-%m-%d' ).date( )
                datum[ 'airedDate' ] = firstAired
            except: pass
            if 'overview' in epelem: datum[ 'overview' ] = epelem[ 'overview' ]
            self.episodes[ epelem[ 'airedEpisodeNumber' ] ] = datum            
        maxep = max( self.episodes )
        minep = min( self.episodes )            


#
## method to get all the shows organized by date.
## 1)  key is date
## 2)  value is list of tuples
## 2a) each tuple is of type date, show name, season, episode number, episode title
def get_tvdata_ordered_by_date( tvdata ):
    def _get_tuple_list_season( show, seasno ):
        assert( show in tvdata )
        assert( seasno in tvdata[ show ]['seasons'] )
        seasons_info = tvdata[ show ][ 'seasons' ]
        episodes_dict = seasons_info[ seasno ]['episodes']
        return list( filter(
            lambda tup: tup[0].year > 1900,
            map(lambda epno: (
                episodes_dict[ epno ]['date aired'],
                show, seasno, epno,
                episodes_dict[ epno ][ 'title'] ), episodes_dict ) ) )
    def _get_tuple_list_show( show ):
        assert( show in tvdata )
        return list( chain.from_iterable(
            map(lambda seasno: _get_tuple_list_season( show, seasno ),
                tvdata[ show ]['seasons'] ) ) )
    tvdata_tuples = list( chain.from_iterable( 
        map(_get_tuple_list_show, tvdata ) ) )
    tvdata_date_dict = { }
    for tup in tvdata_tuples:
        tvdata_date_dict.setdefault( tup[0], [ ] ).append( tup[1:] )
    return tvdata_date_dict

def create_plot_year_tvdata( tvdata_date_dict, year = 2010,
                             shouldPlot = True, dirname = None ):
    calendar.setfirstweekday( 6 )
    def suncal( mon, year = 2010, current_date = None ):
        if current_date is None:
            return numpy.array( calendar.monthcalendar( year, mon ), dtype=int )
        cal = numpy.array( calendar.monthcalendar( year, mon ), dtype=int )
        for idx in range( cal.shape[0] ):
            for jdx in range(7):
                if cal[ idx, jdx ] == 0: continue
                cand_date = datetime.date( year, mon, cal[ idx, jdx ] )
                if cand_date >= current_date: cal[ idx, jdx ] = 0
        return cal
    
    fig = Figure( figsize = ( 8 * 3, 6 * 5 ) )
    days = [ 'SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT' ]
    firstcolors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
                   '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
                   '#bcbd22']
    current_date = datetime.datetime.now( ).date( )
    numdays = sum(list(map(lambda mon: len( numpy.where( suncal( mon, year, current_date = current_date ) > 0)[1] ),
                           range(1, 13 ))))
    numdays_eps = len(list(filter(lambda mydate: mydate.year == year, tvdata_date_dict)))
    if numdays_eps != 0:
        numeps = sum(list(map(lambda mydate: len( tvdata_date_dict[ mydate ] ),
                              filter(lambda mydate: mydate.year == year, tvdata_date_dict))))
        #
        ## now count the number of shows in these new episodes
        shownames = set(chain.from_iterable(
            map(lambda mydate: list(map(lambda tup: tup[0], tvdata_date_dict[ mydate ] ) ),
                filter(lambda mydate: mydate.year == year, tvdata_date_dict))))
    else:
        numeps = 0
        shownames = { }
        
    #
    ## these are the legend plots
    ax = fig.add_subplot(5,3,3)
    ax.axis('off')
    ax.set_xlim([0,1])
    ax.set_ylim([0,1])
    mystr = '\n'.join([
        '%d / %d days have new episodes' % (numdays_eps, numdays),
        '%d new episodes in' % numeps,
        '%d shows' % len( shownames ) ])
    ax.text(0.15, 0.25, mystr,
            fontdict = { 'fontsize' : 16, 'fontweight' : 'bold' },
            horizontalalignment = 'left', verticalalignment = 'center',
            color = 'black' )
    #
    ax = fig.add_subplot(5,3,2)
    ax.axis('off')
    ax.set_xlim([0,1])
    ax.set_ylim([0,1])
    ax.text(0.5, 0.25, '\n'.join([ '%d TV DATA' % year, 'EPISODE COUNTS' ]),
            fontdict = { 'fontsize' : 36, 'fontweight' : 'bold' },
            horizontalalignment = 'center', verticalalignment = 'center' )
    #
    ax = fig.add_subplot(5,3,1)
    ax.axis('off')
    ax.set_xlim([0,1])
    ax.set_ylim([0,1])
    ax.text( 0.5, 0.575, 'number of new episodes on a day',
             fontdict = { 'fontsize' : 20, 'fontweight' : 'bold' },
             horizontalalignment = 'center', verticalalignment = 'center' )
    for idx in range( 10 ):
        if idx == 0: color = 'white'
        else: color = firstcolors[ idx - 1 ]
        #
        ## numbers 0-9
        ax.add_patch( Rectangle(( 0.01 + 0.098 * idx, 0.35 ), 0.098, 0.098 * 1.5,
                                linewidth = 2, facecolor = 'white', edgecolor = 'black' ) )
        ax.add_patch( Rectangle(( 0.01 + 0.098 * idx, 0.35 ), 0.098, 0.098 * 1.5,
                                facecolor = color, edgecolor = None, alpha = 0.5 ) )
        #if idx != 9: mytxt = '%d' % idx
        #else: mytxt = '≥ %d' % idx
        mytxt = '%d' % idx
        ax.text( 0.01 + 0.098 * ( idx + 0.5 ), 0.35 + 0.098 * 0.75, mytxt,
                 fontdict = { 'fontsize' : 16, 'fontweight' : 'bold' },
                 horizontalalignment = 'center', verticalalignment = 'center' )
        #
        ## numbers 10-19
        ax.add_patch( Rectangle(( 0.01 + 0.098 * idx, 0.35 - 0.098 * 1.5 ), 0.098, 0.098 * 1.5,
                                linewidth = 2, facecolor = 'white', edgecolor = 'black' ) )
        ax.add_patch( Rectangle(( 0.01 + 0.098 * idx, 0.35 - 0.098 * 1.5 ), 0.098, 0.098 * 1.5,
                                facecolor = color, edgecolor = None, alpha = 0.5 ) )
        ax.add_patch( Ellipse(( 0.01 + 0.098 * (idx + 0.5), 0.35 - 0.098 * 0.75 ),
                              0.098 * 0.8, 0.098 * 1.5 * 0.8, linewidth = 3,
                              facecolor = (0.5, 0.5, 0.5, 0.0), edgecolor = 'red' ) )
        ax.text( 0.01 + 0.098 * ( idx + 0.5 ), 0.35 - 0.098 * 0.75, '%d' % ( idx + 10),
                 fontdict = { 'fontsize' : 16, 'fontweight' : 'bold' },
                 horizontalalignment = 'center', verticalalignment = 'center' )
        

    for mon in range(1, 13):
        validdates = list(filter(lambda mydate: mydate.year == year and
                                 mydate.month == mon, tvdata_date_dict ) )
        mondata = []
        if len(validdates) != 0:
            mondata = list(chain.from_iterable(
                map(lambda mydate: tvdata_date_dict[ mydate ],
                    validdates ) ) )
        cal = suncal( mon, year )
        ax = fig.add_subplot(5, 3, mon + 3 )
        ax.set_xlim([0,1])
        ax.set_ylim([0,1])
        ax.axis('off')
        for jdx in range(7):
            ax.text( 0.01 + 0.14 * (jdx + 0.5), 0.93, days[jdx],
                     fontdict = { 'fontsize' : 16, 'fontweight' : 'bold' },
                     horizontalalignment = 'center',
                     verticalalignment = 'center' )
        for idx in range(cal.shape[0]):
            for jdx in range(7):
                if cal[idx, jdx] == 0: continue
                cand_date = datetime.date( year, mon, cal[ idx, jdx ] )
                if cand_date in tvdata_date_dict:
                    count = min( 19, len( tvdata_date_dict[ cand_date ] ) )
                else: count = 0
                if count % 10 != 0: color = firstcolors[ count % 10 - 1 ]
                else: color = 'white'
                ax.add_patch( Rectangle( ( 0.01 + 0.14 * jdx,
                                           0.99 - 0.14 - 0.14 * (idx + 1) ),
                                         0.14, 0.14, linewidth = 2,
                                         facecolor = 'white', edgecolor = 'black' ) )
                if cand_date < current_date:
                    ax.add_patch( Rectangle( ( 0.01 + 0.14 * jdx,
                                               0.99 - 0.14 - 0.14 * (idx + 1) ),
                                             0.14, 0.14, linewidth = 2,
                                             facecolor = color, edgecolor = None, alpha = 0.5 ) )
                    if count >= 10:
                        ax.add_patch( Ellipse( ( 0.01 + 0.14 * ( jdx + 0.5 ),
                                                 0.99 - 0.14 - 0.14 * (idx + 0.5) ),
                                               0.14 * 0.8, 0.14 * 0.8, linewidth = 3,
                                               facecolor = ( 0.5, 0.5, 0.5, 0.0), edgecolor = 'red' ) )
                else:
                    ax.add_patch( Rectangle( ( 0.01 + 0.14 * jdx,
                                               0.99 - 0.14 - 0.14 * (idx + 1) ),
                                             0.14, 0.14, linewidth = 2,
                                             facecolor = 'yellow', edgecolor = None, alpha = 0.25 ) )
                ax.text( 0.01 + 0.14 * ( jdx + 0.5 ),
                         0.99 - 0.14 - 0.14 * ( idx + 0.5 ), '%d' % cal[idx, jdx],
                         fontdict = { 'fontsize' : 16, 'fontweight' : 'bold' },
                         horizontalalignment = 'center',
                         verticalalignment = 'center' )
        monname = datetime.datetime.strptime('%02d.%d' % ( mon, year ),
                                             '%m.%Y' ).strftime('%B').upper( )
        if len(mondata) != 0:
            numshows = len(set(map(lambda tup: tup[0], mondata)))
            monname = '%s (%d eps., %d shows)' % ( monname, len(mondata), numshows )
        ax.set_title( monname, fontsize = 18, fontweight = 'bold' )
    #
    ## plotting
    if shouldPlot:
        if dirname is not None: assert( os.path.isdir( dirname ) )
        else: dirname = os.getcwd( )
        canvas = FigureCanvasAgg(fig)
        canvas.print_figure(
            os.path.join( dirname, 'tvdata.%d.svgz' % year ),
            bbox_inches = 'tight' )
    return fig
    
def get_series_id( series_name, token, verify = True ):
    data_ids, status = get_possible_ids( series_name, token, verify = verify )
    if data_ids is None:
        print( 'PROBLEM WITH series %s' % series_name )
        print( 'error message: %s.' % status )
        return None
    data_matches = list(filter(lambda dat: dat['seriesName'] == series_name,
                               data_ids ) )
    #
    ## if not get any matches, choose best one
    if len( data_matches ) != 1:
        data_match = max( data_ids, key = lambda dat:
                          ratio( dat[ 'seriesName' ], series_name ) )
        return data_match[ 'id' ]
    return max( data_matches )[ 'id' ]

def get_possible_ids( series_name, token, verify = True ):
    params = { 'name' : series_name.replace("'", '') }
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % token }
    response = requests.get( 'https://api.thetvdb.com/search/series',
                             params = params, headers = headers,
                             verify = verify )
    if response.status_code == 200:
        data = response.json( )[ 'data' ]
        return list(map(lambda dat: {
            'id' : dat['id'], 'seriesName' : dat['seriesName'] }, data ) ), 'SUCCESS'
    
    
    
    # quick hack to get this to work
    ## was a problem with show AQUA TEEN HUNGER FORCE FOREVER
    params = { 'name' : ' '.join( series_name.replace("'", '').split()[:-1] ) }
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % token }
    response = requests.get( 'https://api.thetvdb.com/search/series',
                             params = params, headers = headers,
                             verify = verify )
    if response.status_code == 200:
        data = response.json( )[ 'data' ]
        return list(map(lambda dat: {
            'id' : dat['id'], 'seriesName' : dat['seriesName'] }, data ) ), 'SUCCESS'

    #
    ## still doesn't work, figure out the imdbId for this episode, using tmdb API
    tmdb_ids = plextmdb.get_tv_ids_by_series_name( series_name, verify = verify )
    imdb_ids = list(filter(None, map(lambda tmdb_id: plextmdb.get_tv_imdbid_by_id(
        tmdb_id, verify = verify ), tmdb_ids ) ) )
    if len( imdb_ids ) == 0:
        return return_error_raw( 'Error, could not find TMDB ids for %s.' % series_name )
    tot_data = [ ]
    for imdb_id in imdb_ids:
        response = requests.get( 'https://api.thetvdb.com/search/series',
                                 params = { 'imdbId' : imdb_id }, headers = headers,
                                 verify = verify )
        if response.status_code != 200: continue
        data = response.json( )[ 'data' ]
        for dat in data:
            tot_data.append( {
                'id' : dat[ 'id' ], 'seriesName' : dat[ 'seriesName' ] } )
    if len( tot_data ) != 0:
        return tot_data, 'SUCCESS'
    #
    return return_error_raw( 'Error, could not find series ids for %s.' % series_name )

def did_series_end( series_id, token, verify = True, date_now = None ):
    """
    Check on shows that have ended more than 365 days from the last day
    """
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % token }
    response = requests.get( 'https://api.thetvdb.com/series/%d' % series_id,
                             headers = headers, verify = verify )
    if response.status_code != 200: return None
    data = response.json( )['data']
    
    if data['status'] != 'Ended': return False
    #
    ## now check when the last date of the show was
    if date_now is None: date_now = datetime.datetime.now( ).date( )
    last_date = max(map(lambda epdata: datetime.datetime.strptime(
        epdata['firstAired'], '%Y-%m-%d' ).date( ),
                        get_episodes_series( series_id, token, verify = verify ) ) )
    td = date_now - last_date
    return td.days > 365

def get_imdb_id( series_id, token, verify = True ):
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % token }
    response = requests.get( 'https://api.thetvdb.com/series/%d' % series_id,
                             headers = headers, verify = verify )
    if response.status_code != 200: return None
    data = response.json( )['data']
    return data['imdbId']

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

def get_series_info( series_id, token, verify = True ):
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % token }
    response = requests.get( 'https://api.thetvdb.com/series/%d' % series_id,
                             headers = headers, verify = verify )
    if response.status_code != 200: return None, "COULD NOT ACCESS TV INFO SERIES"
    data = response.json( )[ 'data' ]
    return data, 'SUCCESS'
    

def get_series_image( series_id, token, verify = True ):
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % token }
    response = requests.get( 'https://api.thetvdb.com/series/%d/images/query/params' % series_id,
                             headers = headers, verify = verify )
    if response.status_code != 200: return None, "COULD NOT ACCESS IMAGE URL FOR SERIES"
    data = response.json( )['data']
    #
    ## first look for poster entries
    poster_ones = list(
        filter(lambda elem: 'keyType' in elem.keys() and elem['keyType'] == 'poster', data ) )
    if len( poster_ones ) != 0:
        poster_one = poster_ones[ 0 ]
        params = { 'keyType' : 'poster' }
        if 'resolution' in poster_one and len( poster_one['resolution'] ) != 0:
            params['resolution'] = poster_one['resolution'][0]
        response = requests.get( 'https://api.thetvdb.com/series/%d/images/query' % series_id,
                                 headers = headers, params = params, verify = verify )
        if response.status_code == 200:
            data = response.json( )['data']
            firstPoster = data[0]
            #assert( 'fileName' in firstPoster )
            if 'fileName' in firstPoster:
                return 'https://thetvdb.com/banners/%s' % firstPoster['fileName'], "SUCCESS"
    fanart_ones = list(
        filter(lambda elem: 'keyType' in elem.keys( ) and elem['keyType'] == 'fanart', data ) )
    if len( fanart_ones ) != 0:
        fanart_one = fanart_ones[ 0 ]
        params = { 'keyType' : 'fanart' }
        if 'resolution' in fanart_one and len( fanart_one['resolution'] ) != 0:
            params['resolution'] = fanart_one['resolution'][0]
        response = requests.get( 'https://api.thetvdb.com/series/%d/images/query' % series_id,
                                 headers = headers, params = params, verify = verify )
        if response.status_code == 200:
            data = response.json( )['data']
            firstFanart = data[0]
            if 'fileName' in firstFanart:
                return 'https://thetvdb.com/banners/%s' % firstFanart['fileName'], "SUCCESS"
    series_ones = list(
        filter(lambda elem: 'keyType' in elem.keys( ) and elem['keyType'] == 'series') )
    if len( series_ones ) != 0:
        series_one = series_ones[ 0 ]
        params = { 'keyType' : 'series' }
        if 'resolution' in series_one and len( series_one['resolution'] ) != 0:
            params['resolution'] = series_one['resolution'][0]
        response = requests.get( 'https://api.thetvdb.com/series/%d/images/query' % series_id,
                                 headers = headers, params = params, verify = verify )
        if response.status_code == 200:
            data = response.json( )['data']
            firstSeries = data[0]
            if 'fileName' in firstSeries:
                return 'https://thetvdb.com/banners/%s' % firstSeries['fileName'], "SUCCESS"
    return None, "COULD NOT DOWNLOAD SERIES INFO FOR SERIES_ID = %d" % series_id ## nothing happened

def get_series_season_image( series_id, airedSeason, token, verify = True ):
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % token }
    response = requests.get( 'https://api.thetvdb.com/series/%d/images/query/params' % series_id,
                             headers = headers, verify = verify )
    if response.status_code != 200:
        return None, "COULD NOT FIND IMAGES FOR SERIES_ID = %d" % series_id
    data = response.json( )['data']
    #
    ## look for season keytype
    season_ones = list( filter(lambda elem: 'keyType' in elem.keys( ) and
                               elem['keyType'] == 'season' and
                               'subKey' in elem and
                               '%d' % airedSeason in elem['subKey'], data ) )
    if len( season_ones ) == 0:
        return None, "COULD NOT FIND SEASON IMAGE FOR SERIES_ID = %d AND SEASON = %d" % (
            series_id, airedSeason )
    season_one = season_ones[ 0 ]
    #
    ## now get that image for season
    params = { 'keyType' : 'season', 'subKey' : '%d' % airedSeason }
    #if 'resolution' in season_one and len( season_one[ 'resolution' ] ) != 0:
    #    params[ 'resolution' ] = season_one[ 'resolution' ][ 0 ]
    response = requests.get( 'https://api.thetvdb.com/series/%d/images/query' % series_id,
                             headers = headers, params = params, verify = verify )
    if response.status_code != 200:
        return None, "COULD NOT GET PROPER IMAGE FROM VALID IMAGE QUERY FOR SERIES_ID = %d AND SEASON = %d" % (
            series_id, airedSeason )
    season_data = response.json( )['data'][ 0 ]
    if 'fileName' not in season_data:
        return None, "COULD NOT FIND APPROPRIATE IMAGE URL FROM VALID IMAGE QUERY FOR SERIES_ID = %d AND SEASON = %d" % (
            series_id, airedSeason )
    return 'https://thetvdb.com/banners/%s' % season_data[ 'fileName' ], "SUCCESS"

def fix_missing_unnamed_episodes( seriesName, eps, verify = True, showFuture = False ):
    from plextmdb import plextmdb
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


def get_episodes_series( series_id, token, showSpecials = True, fromDate = None,
                         verify = True, showFuture = False ):
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
        if response.status_code != 200: continue
        data = response.json( )
        seriesdata += data[ 'data' ]
    currentDate = datetime.datetime.now( ).date( )
    sData = [ ]
    logging.debug( 'get_episodes_series: %s' % seriesdata )
    for episode in seriesdata:
        try:
            date = datetime.datetime.strptime( episode['firstAired'], '%Y-%m-%d' ).date( )
            if date > currentDate and not showFuture:
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

    #
    ## now postprocess for all problematic shows, use tmdbId
    problem_eps = list(filter(lambda episode: episode['episodeName'] is None,
                              sData ) )
    
        
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

def get_path_data_on_tvshow( tvdata, tvshow ):
    assert( tvshow in tvdata )
    seasons_info = tvdata[ tvshow ][ 'seasons' ]
    num_cols = set( chain.from_iterable(
        map(lambda seasno: list(
            map(lambda epno: len(splitall( seasons_info[seasno]['episodes'][epno]['path'])),
                seasons_info[seasno]['episodes'])), seasons_info ) ) )
    #
    ## only consider tv shows with fixed number of columns
    if len( num_cols ) != 1: return None
    num_cols = max( num_cols )

    #
    ## now find those split directories with only a single value
    splits_with_len_1 = list(
        filter(lambda colno:
               len(set(chain.from_iterable(
                   map(lambda seasno: list(
                       map(lambda epno: splitall(
                           seasons_info[seasno]['episodes'][epno]['path'])[ colno ],
                           seasons_info[ seasno ]['episodes'])),
                       seasons_info )))) == 1, range(num_cols)))
    
    if sum(map(lambda seasno: len(seasons_info[seasno]['episodes']), seasons_info)) == 1: # only one episode
        ## just get the non-episode, non-season name
        splits_with_len_1.pop(-1)
        season = max( seasons_info )
        epno = max( seasons_info[ season ]['episodes'] )
        fullpath_split = os.path.dirname( seasons_info[ season ]['episodes'][ epno ]['path'] ).split('/')
        if 'Season' or 'Special' in fullpath_split[-1]:
            splits_with_len_1.pop(-1)
    
    prefix = os.path.join(
        *list(map(lambda colno:
                  max(set(chain.from_iterable(
                      map(lambda seasno: list(
                          map(lambda epno: splitall(
                              seasons_info[seasno]['episodes'][epno]['path'])[ colno ],
                              seasons_info[ seasno ]['episodes'])),
                          seasons_info)))), sorted(splits_with_len_1))))
    #
    ## average length in seconds of an episode
    avg_length_secs = numpy.average(
        list( chain.from_iterable(
            map(lambda seasno: list(
                map(lambda epno: seasons_info[seasno]['episodes'][epno]['duration'],
                    seasons_info[seasno]['episodes'])),
                seasons_info))))
    
    #
    ## now those extra paths that are not common, but peculiar to each season and episode
    ## must be 2 or 1 extra columns
    extra_season_ep_columns = sorted(set(range(num_cols)) - set(splits_with_len_1))
    assert( len( extra_season_ep_columns ) in (2,1)), "problem with %s" % tvshow
    assert( min( extra_season_ep_columns ) == max( splits_with_len_1 ) + 1 )
    #
    ## now get the main prefix for the file
    def get_main_file_name( basename ):
        toks = list(map(lambda tok: tok.strip( ), basename.split(' - ') ) )
        idx_match = -1
        for idx in range(len(toks)):
            if re.match('^s\d{1,}e\d{1,}', toks[idx].lower( ) ) is not None:
                idx_match = idx
                break
        assert( idx_match != -1 ), 'problem with %s' % basename
        return ' - '.join( toks[:idx_match] )
    main_file_name = set(chain.from_iterable(
        map(lambda seasno: list(
            map(lambda epno: get_main_file_name( os.path.basename(
                seasons_info[seasno]['episodes'][epno]['path'] ) ),
                seasons_info[ seasno ]['episodes'])), seasons_info)))
    assert(len(main_file_name) == 1), 'error with %s, main_file_names = %s' % ( tvshow, sorted(main_file_name) )
    main_file_name = max( main_file_name )
    season_prefix_dict = { }
    if len( extra_season_ep_columns ) == 1:
        season_col = max( splits_with_len_1 )
        season_dirs = [ ]
        for seasno in seasons_info:
            season_dirs += sorted(set(map(lambda epno: splitall(
                seasons_info[seasno]['episodes'][epno]['path'])[ season_col ],
                                          seasons_info[ seasno ]['episodes'] ) ) )
        season_dirs = set( season_dirs )
        assert( len( season_dirs ) == 1 ), 'problem with %s' % tvshow
        last_dir = max( season_dirs )
        if last_dir.startswith( 'Season' ):
            prefix, season_dir = os.path.split( prefix )
            season_prefix_dict = dict(map(
                lambda seasno: ( seasno, season_dir ), seasons_info ) )            
    # go through each season, assert that all eps in a given season are in a single directory    
    elif len( extra_season_ep_columns ) == 2:
        season_col = extra_season_ep_columns[ 0 ]
        for seasno in seasons_info:
            season_dir = set(map(lambda epno: splitall(
                seasons_info[seasno]['episodes'][epno]['path'])[ season_col ],
                                 seasons_info[ seasno ]['episodes'] ) )
            assert( len( season_dir ) == 1 ), 'problem with %s' % tvshow
            #if len( season_dir ) != 1:
            #    print( '%s, %d, %s' % ( tvshow, seasno, season_dir ) )
            #    return None
            season_prefix_dict[ seasno ] = max( season_dir )
    if len( season_prefix_dict ) != 0:
        min_inferred_length = min(map(lambda seasno: len( season_prefix_dict[ seasno ].split()[-1]),
                                      filter(lambda seasno: season_prefix_dict[ seasno ].startswith('Season'),
                                             season_prefix_dict)))
    else: min_inferred_length = 0
    max_num_eps = max(map(lambda seasno: len(seasons_info[seasno]['episodes']),
                          seasons_info))
    max_eps_len = max(2, int( numpy.log10( max_num_eps ) + 1 ) )
    return { 'prefix' : prefix,
             'showFileName' : main_file_name,
             'season_prefix_dict' : season_prefix_dict,
             'min_inferred_length': min_inferred_length,
             'episode_number_length' : max_eps_len,
             'avg_length_mins' : avg_length_secs // 60 }

def get_all_series_didend( tvdata, verify = True,
                           num_threads = 2 * multiprocessing.cpu_count( ),
                           tvdb_token = None ):
    time0 = time.time( )
    if tvdb_token is None: tvdb_token = get_token( verify = verify )
    with multiprocessing.Pool(
            processes = max(num_threads, multiprocessing.cpu_count( ) ) ) as pool:
        date_now = datetime.datetime.now( ).date( )
        tvshow_id_map = dict(filter(
            None, pool.map(lambda seriesName: (
                seriesName, get_series_id( seriesName, tvdb_token, verify = verify ) ),
                           tvdata ) ) )
        tvshows_notfound = set( tvdata ) - set( tvshow_id_map )
        tvid_didend_map = dict(filter(
            lambda tup: tup is not None,
            pool.map(lambda seriesName: (
                tvshow_id_map[ seriesName ],
                did_series_end( tvshow_id_map[ seriesName ], tvdb_token, verify = verify,
                                date_now = date_now ) ),
                     tvshow_id_map ) ) )
        didend_map = { seriesName : tvid_didend_map[ tvshow_id_map[ seriesName ] ] for
                       seriesName in tvshow_id_map }
        for seriesName in tvshows_notfound:
            didend_map[ seriesName ] = True
        logging.debug( 'processed %d series to check if they ended, in %0.3f seconds.' % (
            len( tvdata ), time.time( ) - time0 ) )
        return didend_map                                
    
def _get_remaining_eps_perproc( input_tuple ):
    time0 = time.time( )
    name = input_tuple[ 'name' ]
    series_id = input_tuple[ 'series_id' ]
    epsForShow = input_tuple[ 'epsForShow' ]
    token = input_tuple[ 'token' ]
    showSpecials = input_tuple[ 'showSpecials' ]
    fromDate = input_tuple[ 'fromDate' ]
    verify = input_tuple[ 'verify' ]
    showFuture = input_tuple[ 'showFuture' ]
    #
    ## only record those episodes that have an episodeName that is not None
    eps = list(
        filter(lambda ep: 'episodeName' in ep and ep['episodeName'] is not None,
               get_episodes_series( series_id, token, showSpecials = showSpecials, verify = verify,
                                    fromDate = fromDate, showFuture = showFuture ) ) )
    tvdb_eps = set(map(lambda ep: ( ep['airedSeason'], ep['airedEpisodeNumber' ] ), eps ) )
    tvdb_eps_dict = { ( ep['airedSeason'], ep['airedEpisodeNumber' ] ) :
                      ( ep['airedSeason'], ep['airedEpisodeNumber' ], ep['episodeName'] ) for ep in eps }
    here_eps = set([ ( seasno, epno ) for seasno in epsForShow for
                     epno in epsForShow[ seasno ][ 'episodes' ] ] )
    tuples_to_get = tvdb_eps - here_eps
    if len( tuples_to_get ) == 0: return None
    tuples_to_get_act = list(map(lambda tup: tvdb_eps_dict[ tup ], tuples_to_get ) )
    logging.debug( 'finished processing %s in %0.3f seconds.' % ( name, time.time( ) - time0 ) )
    return name, sorted( tuples_to_get_act, key = lambda tup: (tup[0], tup[1]))

def _get_series_id_perproc( input_tuple ):
    show = input_tuple[ 'show' ]
    token = input_tuple[ 'token' ]
    verify = input_tuple[ 'verify' ]
    doShowEnded = input_tuple[ 'doShowEnded' ]
    series_id = get_series_id( show, token, verify = verify )
    if series_id is None:
        logging.debug( 'something happened with show %s' % show )
        return None
    if not doShowEnded:
        didEnd = did_series_end( series_id, token, verify = verify )
        if didEnd is None or didEnd: return None
    return show, series_id
    
def get_remaining_episodes( tvdata, showSpecials = True, fromDate = None, verify = True,
                            doShowEnded = False, showsToExclude = None, showFuture = False,
                            num_threads = 2 * multiprocessing.cpu_count( ), token = None ):
    assert( num_threads >= 1 )
    if token is None: token = get_token( verify = verify )
    tvdata_copy = copy.deepcopy( tvdata )
    if showsToExclude is not None:
        showsExclude = set( showsToExclude ) & set( tvdata_copy.keys( ) )
        for show in showsExclude: tvdata_copy.pop( show )
    with multiprocessing.Pool( processes = max( num_threads, multiprocessing.cpu_count( ) ) ) as pool:
        input_tuples = list(
            map(lambda show: {
                'show' : show, 'token' : token, 'verify' : verify, 'doShowEnded' : doShowEnded },
                tvdata_copy ) )
        tvshow_id_map = dict(filter(
            None, pool.map( _get_series_id_perproc, input_tuples ) ) )
        
    #if fromDate is not None:
    #    series_ids = set( get_series_updated_fromdate( fromDate, token ) )
    #    print( 'series_ids = %s.' % series_ids )
    #    ids_tvshows = dict(map(lambda name_seriesId: ( name_seriesId[1], name_seriesId[0] ),
    #                           tvshow_id_map.items( ) ) )
    #    updated_ids = set( ids_tvshows.keys( ) ) & series_ids
    #    tvshow_id_map = dict(map(lambda series_id: ( ids_tvshows[ series_id ], series_id ), updated_ids ) )
    tvshows = sorted( set( tvshow_id_map ) )
    input_tuples = list(
        map(lambda name:
            { 'name' : name,
              'token' : token,
              'showSpecials' : showSpecials,
              'fromDate' : fromDate,
              'verify' : verify,
              'series_id' : tvshow_id_map[ name ],
              'showFuture' : showFuture,
              'epsForShow' : tvdata_copy[ name ][ 'seasons' ] }, tvshow_id_map ) )
    with multiprocessing.Pool(
            processes = max(num_threads, multiprocessing.cpu_count( ) ) ) as pool:
        toGet_sub = dict( filter(
            None, pool.map( _get_remaining_eps_perproc, input_tuples ) ) )
    #
    ## guard code for now -- only include those tv shows that have titles of new episodes to download
    tvshows_act = set(filter(lambda tvshow: len(list(
        filter(lambda epdata: epdata[-1] is not None, toGet_sub[ tvshow ] ) ) ) != 0, toGet_sub ) )
    tvdata_path_data = dict(filter(None, map(lambda tvshow: (
        tvshow, get_path_data_on_tvshow( tvdata, tvshow ) ), tvshows_act ) ) )
    toGet = dict(map(lambda tvshow: ( tvshow, {
        'episodes' : list(
            filter(lambda epdata: epdata[-1] is not None, toGet_sub[ tvshow ] ) ),
        'prefix' : tvdata_path_data[ tvshow ][ 'prefix' ],
        'showFileName' : tvdata_path_data[ tvshow ][ 'showFileName' ],
        'min_inferred_length' : tvdata_path_data[ tvshow ][ 'min_inferred_length' ],
        'season_prefix_dict' : tvdata_path_data[ tvshow ][ 'season_prefix_dict' ],
        'episode_number_length' : tvdata_path_data[ tvshow ][ 'episode_number_length' ],
        'avg_length_mins' : tvdata_path_data[ tvshow ][ 'avg_length_mins' ] } ),
                     sorted( tvshows_act ) ) )
    return toGet

def get_future_info_shows( tvdata, verify = True, showsToExclude = None, token = None,
                           fromDate = None, num_threads = 2 * multiprocessing.cpu_count( ) ):
    #
    ## first get all candidate tv shows
    tvdb_token = get_token( verify = verify )
    if fromDate is None: fromDate = datetime.datetime.now( ).date( )
    toGet_future_cands = get_remaining_episodes(
        tvdata, showSpecials = False, fromDate = fromDate,
        doShowEnded = False, showsToExclude = showsToExclude,
        token = token, showFuture = True, num_threads = num_threads )
    logging.info( 'tvdata size = %d, toGet_future_cands size = %d.' % (
        len( tvdata ), len( toGet_future_cands ) ) )
    #
    ## check that the new season in toGet_future_cands > last season
    shows_to_include = [ ]
    for show in toGet_future_cands:
        if len( toGet_future_cands[ show ][ 'episodes' ] ) == 0: continue
        min_next_season = min(map(lambda tup: tup[0], toGet_future_cands[ show ][ 'episodes' ] ) )
        max_season_have = max( tvdata[ show ][ 'seasons' ] )
        if min_next_season <= max_season_have: continue
        shows_to_include.append( ( show, max_season_have, min_next_season ) )

    logging.info( 'final %d set of shows that have new season: %s.' % (
        len( shows_to_include ), sorted(map(lambda tup: tup[0], shows_to_include ) ) ) )

    def get_new_season_start( input_tuple ):
        show, max_last_season, min_next_season, verify = input_tuple
        epdicts = get_tot_epdict_tvdb(
            show, verify = verify, token = tvdb_token, showFuture = True )
        def _get_min_date_season( epdicts, seasno ):
            return min(map(lambda epno: epdicts[ seasno ][ epno ][ -1 ], epdicts[seasno] ) )
        date_min = min(map(lambda seasno: _get_min_date_season( epdicts, seasno ),
                           filter(lambda sn: sn >= min_next_season, epdicts ) ) )
        return show, max_last_season, min_next_season, date_min

    with multiprocessing.Pool( processes = num_threads ) as pool:
        future_shows_dict = dict(
            map(lambda tup:
                ( tup[0], { 'max_last_season' : tup[1],
                            'min_next_season' : tup[2],
                            'start_date' : tup[3] } ),
                  pool.map(
                      get_new_season_start, map(lambda show_max_min: (
                          show_max_min[0], show_max_min[1], show_max_min[2], verify ), shows_to_include ) ) ) )
        logging.info( 'found detailed info on %d shows with a new season: %s.' % (
            len( future_shows_dict ), sorted( future_shows_dict ) ) )
        return future_shows_dict
    
def push_shows_to_exclude( tvdata, showsToExclude ):
    if len( tvdata ) == 0: return
    showsActExclude = set(showsToExclude) & set( tvdata.keys( ) ) # first get the union of shows to exclude
    if len( showsActExclude ) != 0:
        print('found %d shows to exclude from TV database.' % len( showsActExclude ) )
    showsToExcludeInDB = set( session.query( ShowsToExclude ).all( ) )
    notHere = set(showsToExcludeInDB) - set( tvdata )
    for show in notHere: session.delete( show )
    session.commit( )
    if len( notHere ) != 0:
        print( 'had to remove %d excluded shows from DB that were not in TV library.' % len( notHere ) )
    if len( showsActExclude ) == 0: return
    showsToExcludeInDB = set( session.query( ShowsToExclude ).all( ) )
    candShows = showsActExclude - showsToExcludeInDB
    if len( candShows ) != 0:
        print('adding %d extra shows to exclusion database.' % len( candShows ) )
    for show in candShows: session.add( ShowsToExclude( show = show ) )
    session.commit( )

def get_shows_to_exclude( tvdata = None ):
    showsToExcludeInDB = sorted( set( map(lambda val: val.show, session.query( ShowsToExclude ).all( ) ) ) )
    if tvdata is None: return showsToExcludeInDB
    if len( tvdata ) == 0: return [ ]
    # notHere = set(showsToExcludeInDB) - set( tvdata )
    # for show in notHere:
    #     session.delete( show )
    #     session.commit( )
    # if len( notHere ) != 0:
    #     print( 'had to remove %d excluded shows from DB that were not in TV library.' %
    #            len( notHere ) )
    # showsToExcludeInDB = sorted( set( showsToExcludeInDB ) & set( tvdata ) )
    return showsToExcludeInDB

def create_tvTorUnits( toGet, restrictMaxSize = True ):
    tv_torrent_gets = { }
    tv_torrent_gets.setdefault( 'nonewdirs', [] )
    tv_torrent_gets.setdefault( 'newdirs', {} )
    for tvshow in toGet:
        mydict = toGet[ tvshow ]
        showFileName = mydict[ 'showFileName' ]
        prefix = mydict[ 'prefix' ]
        min_inferred_length = mydict[ 'min_inferred_length' ]
        episode_number_length = mydict[ 'episode_number_length' ]
        avg_length_mins = mydict[ 'avg_length_mins']
        #
        ## calc minsize from avg_length_mins
        num_in_50 = int( avg_length_mins * 60.0 * 700 / 8.0 / 1024 / 50 + 1)
        minSize = 50 * num_in_50
        num_in_50 = int( avg_length_mins * 60.0 * 500 / 8.0 / 1024 / 50 + 1)
        minSize_x265 = 50 * num_in_50
        ##
        ## calc maxsize from avg_length_mins
        num_in_50 = int( avg_length_mins * 60.0 * 2000 / 8.0 / 1024 / 50 + 1 )
        maxSize = 50 * num_in_50
        num_in_50 = int( avg_length_mins * 60.0 * 1600 / 8.0 / 1024 / 50 + 1 )
        maxSize_x265 = 50 * num_in_50
        if not restrictMaxSize:
            maxSize *= 10
            maxSize_x265 *= 10
        #
        ## being too clever
        ## doing torTitle = showFileName.replace("'",'').replace(':','').replace('&', 'and').replace('/', '-')
        torTitle = reduce(lambda x,y: x.replace(y[0], y[1]),
                          zip([ ":", "&", "/" ], # do not replace apostrophe
                              [ '', '', 'and', ',' ]),
                          showFileName)
        for seasno, epno, title in mydict[ 'episodes' ]:
            actTitle = title.replace('/', ', ')
            candDir = os.path.join( prefix, 'Season %%%02dd' % min_inferred_length % seasno )
            fname = '%s - s%02de%s - %s' % ( showFileName, seasno, '%%%02dd' % episode_number_length % epno, actTitle )
            totFname = os.path.join( candDir, fname )
            torFname = '%s S%02dE%02d' % ( torTitle, seasno, epno )
            dat = { 'totFname' : totFname, 'torFname' : torFname,
                    'minSize' : minSize, 'maxSize' : maxSize,
                    'minSize_x265' : minSize_x265, 'maxSize_x265' : maxSize_x265,
                    'tvshow' : tvshow }
                
            if not os.path.isdir( candDir ):
                tv_torrent_gets[ 'newdirs' ].setdefault( candDir, [] )
                tv_torrent_gets[ 'newdirs' ][ candDir ].append( dat )
            else: tv_torrent_gets[ 'nonewdirs' ].append( dat )

    tvTorUnits = list(chain.from_iterable(
        [ tv_torrent_gets[ 'nonewdirs' ] ] +
        list(map(lambda newdir: tv_torrent_gets[ 'newdirs' ][ newdir ],
                 tv_torrent_gets[ 'newdirs' ] ) ) ) )
    return tvTorUnits, sorted( tv_torrent_gets[ 'newdirs' ].keys( ) )

def download_batched_tvtorrent_shows( tvTorUnits, newdirs = [ ], maxtime_in_secs = 240, num_iters = 10 ):
    time0 = time.time( )
    data = plexcore_rsync.get_credentials( )
    assert( data is not None ), "error, could not get rsync download settings."
    assert( maxtime_in_secs >= 60 ), "error, max time to download each torrent >= 60 seconds."
    assert( num_iters >= 1 ), "error, number of tries on different magnet links >= 1."
    print( 'started downloading %d episodes on %s' % (
        len( tvTorUnits ), datetime.datetime.now( ).strftime(
            '%B %d, %Y @ %I:%M:%S %p' ) ) )
        
    for newdir in filter(lambda nd: not os.path.isdir( nd ), newdirs ):
        os.mkdir( newdir )
    def worker_process_download_tvtorrent_perproc( tvTorUnit ):
        try:
            dat, status_dict = plextvdb_torrents.worker_process_download_tvtorrent(
                tvTorUnit, maxtime_in_secs = maxtime_in_secs, num_iters = num_iters,
                kill_if_fail = True )
            if dat is None: return tvTorUnit[ 'torFname' ] # could not download this
            tvTorUnitFin = copy.deepcopy( tvTorUnit )
            tvTorUnitFin['remoteFileName'] = dat
            suffix = dat.split('.')[-1].strip( )
            tvTorUnitFin[ 'totFname' ] = '%s.%s' % ( tvTorUnit[ 'totFname' ], suffix )
            return tvTorUnitFin
        except Exception as e:
            import traceback
            return 'filename = %s, error_message = %s, %s' % (
                tvTorUnit[ 'torFname' ], str( e ), traceback.print_tb( e.__traceback__ ) )
    #
    ## now create a pool to multiprocess collect those episodes
    with multiprocessing.Pool( processes = min(
            multiprocessing.cpu_count( ), len( tvTorUnits ) ) ) as pool:
        allTvTorUnits = list( pool.map(
            worker_process_download_tvtorrent_perproc, tvTorUnits ) )
    successfulTvTorUnits = list(filter(lambda tup: not isinstance( tup, str ),
                                       allTvTorUnits ) )
    could_not_download = list(filter(lambda tup: isinstance( tup, str ),
                                     allTvTorUnits ) )
    logging.info('successful TV Tor Units: %s.' % successfulTvTorUnits )
    logging.info('could not downloads: %s' % could_not_download )
    
    if len( could_not_download ) != 0:
        print( '\n'.join([
            'successfully processed %d / %d episodes in %0.3f seconds.' % (
                len( successfulTvTorUnits ), len( tvTorUnits ), time.time( ) - time0 ),
            'could not download %s.' % ', '.join( sorted( could_not_download ) ) ] ) )
    else:
        print( 'successfully processed %d / %d episodes in %0.3f seconds.' % (
            len( successfulTvTorUnits ), len( tvTorUnits ), time.time( ) - time0 ) )
        
    #
    ## now rsync those files over
    if len( successfulTvTorUnits ) == 0:
        print( 'processed from start to finish in %0.3f seconds.' % ( time.time( ) - time0 ) )
        return
    time1 = time.time( )
    suffixes = set(map(lambda tvTorUnit: tvTorUnit[ 'remoteFileName' ].split('.')[-1].strip( ),
                       successfulTvTorUnits ) )
    all_glob_strings = list(map(lambda suffix: '*.%s' % suffix, suffixes ) )
    for glob_string in all_glob_strings:
        plexcore_rsync.download_upload_files(
            glob_string, numtries = 100, debug_string = True )
    #
    ## now check all the files downloaded
    local_dir = data[ 'local_dir' ].strip( )
    def did_cleanly_download( tvTorUnit ):
        lfilename = os.path.join( local_dir, tvTorUnit[ 'remoteFileName' ] )
        if not os.path.isfile( lfilename ): return False
        # modification time
        mtime = os.path.getmtime( lfilename )
        dat = datetime.datetime.fromtimestamp( mtime ).date( )
        if dat.year == 1969: return False
        return True
    successfulTvTorUnits = list(filter( did_cleanly_download, successfulTvTorUnits ) )
    print( 'these %d / %d tv torrents cleanly downloaded in %0.3f seconds.' % (
        len( successfulTvTorUnits ), len( tvTorUnits ), time.time( ) - time1 ) )
    #
    ## now move those files that have successfully downloaded into their final destinations
    time2 = time.time( )
    for tvTorUnit in successfulTvTorUnits:
        shutil.move( os.path.join( local_dir, tvTorUnit[ 'remoteFileName' ] ),
                     tvTorUnit[ 'totFname' ] )
    print( 'these %d files moved to correct destinations in %0.3f seconds.' % (
        len( successfulTvTorUnits ), time.time( ) - time2 ) )
    print( 'processed from start to finish in %0.3f seconds.' % ( time.time( ) - time0 ) )

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

def get_tot_epdict_tvdb( showName, verify = True, showSpecials = False, showFuture = False, token = None ):
    if token is None: token = get_token( verify = verify )
    series_id = get_series_id( showName, token, verify = verify )
    eps = get_episodes_series( series_id, token, verify = verify, showFuture = showFuture )
    totseasons = max( map(lambda episode: int( episode['airedSeason' ] ), eps ) )
    tot_epdict = { }
    for episode in eps:
        seasnum = int( episode[ 'airedSeason' ] )
        if not showSpecials and seasnum == 0: continue
        epno = episode[ 'airedEpisodeNumber' ]
        title = episode[ 'episodeName' ]
        try:
            firstAired_s = episode[ 'firstAired' ]
            firstAired = datetime.datetime.strptime(
                firstAired_s, '%Y-%m-%d' ).date( )
        except:
            firstAired = datetime.datetime.strptime(
                '1900-01-01', '%Y-%m-%d' ).date( )
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
