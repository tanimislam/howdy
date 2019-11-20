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
    """
    A convenience object that stores TV show information for a TV show. This provides a higher level object oriented implementation of the lower level pure method implementation of manipulating TV show data.

    :param str seriesName: the series name.
    :param dict seriesInfo: the subdictionary of the Plex_ TV library information returned by :py:meth:`get_library_data <plexcore.plexcore.get_library_data>` associated with ``seriesName``. If ``tvdata`` is the Plex_ TV library information, then ``seriesInfo = tvdata[ seriesName ]``.
    :param str token: the TVDB_ API access token.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :Param bool showSpecials: optional argument. If ``True``, then also collect information on TV specials associated with this TV show. Default is ``False``.

    :var int seriesId:  the TVDB_ series ID.
    :var str seriesName: the series name,
    :var bool statusEnded: whether the series has ended.
    :var str imageURL: the URL of the TV series.
    :var bool isPlexImage: ``True`` if the URL came from the Plex_ server, ``False`` if it came from TVDB_.
    :var str overview: summary of the TV series.
    :var dict seasonDict: a :py:class:`dict`, whose keys are the season numbers and whose values are the :py:class:`TVSeason <plextvdb.plextvdb.TVSeason>` associated with that season of the series.
    :var date startDate: the first :py:class:`date <datetime.date>` aired date for the series.
    :var date lastDate: the last :py:class:`date <datetime.date>` aired date for the series.

    :raises ValueError: if cannot find the TV show with this name, or otherwise cannot construct this object.
    """
    
    @classmethod
    def create_tvshow_dict( cls, tvdata, token = None, verify = True,
                            debug = False, num_threads = 2 * multiprocessing.cpu_count( ) ):
        """
        :param dict tvdata: the Plex_ TV library information returned by :py:meth:`get_library_data <plexcore.plexcore.get_library_data>`.
        :param str token: optional argument. The TVDB_ API access token.
        :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
        :param debug False: optional argument. If ``True``, run with :py:const:`DEBUG <logging.DEBUG>` :py:mod:`logging` mode. Default is ``False``.
        :param int num_threads: the number of threads over which to parallelize this calculation. The default is *twice* the number of cores on the CPU.

        :returns: a :py:class:`dict`, whose keys are the TV show names and whose values are the :py:class:`TVShow <plextvdb.plextvdb.TVSeason>` associated with that TV show.
        :rtype: dict
        """
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
            tvshow_dict = dict(filter(None, pool.map(_create_tvshow, sorted( tvdata )[:60] ) ) )
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
        """
        :param int airedSeason: the season number.
        :param int airedEpisode: episode number.
        :returns: a :py:class:`tuple`, of episode name and aired date (of type :py:class:`date <datetime.date>`), associated with that episode.
        :rtype: tuple

        :raises ValueError: if cannot find the episode aired at the season and episode number.
        """
        if airedSeason not in self.seasonDict:
            raise ValueError("Error, season %d not a valid season." % airedSeason )
        if airedEpisode not in self.seasonDict[ airedSeason ].episodes:
            raise ValueError("Error, episode %d in season %d not a valid episode number." % (
                airedEpisode, airedSeason ) )
        epStruct = self.seasonDict[ airedSeason ].episodes[ airedEpisode ]
        return ( epStruct['title'], epStruct['airedDate'] )

    def get_episodes_series( self, showSpecials = True, fromDate = None ):
        """
        :param bool showSpecials: optional argument. If ``True`` then include the TV specials. Default is ``True``.
        :param date fromDate: optional argument of type :py:class:`date <datetime.date>`. If provided, only include the episodes aired on or after this date.
        :returns: a :py:class:`list` of :py:class:`tuples`. Each tuple is of type ``( SEASON NUMBER, EPISODE NUMBER IN SEASON )``. Specials have a season number of ``0``.
        :type: list
        """
        seasons = set( self.seasonDict.keys( ) )
        if not showSpecials:
            seasons = seasons - set([0,])
        sData = list(chain.from_iterable(
            map(lambda seasno:
                map(lambda epno: ( seasno, epno ),
                    self.seasonDict[ seasno ].episodes.keys( ) ),
                seasons ) ) )
        if fromDate is not None:
            sData = list(filter(
                lambda seasno_epno:
                self.seasonDict[ seasno_epno[0] ].episodes[ seasno_epno[1] ][ 'airedDate' ] >=
                fromDate, sData ) )
        return sData

    def get_tot_epdict_tvdb( self ):
        """
        :returns: a summary nested :py:class:`dict` of episode information for a given TV show.

        * The top level dictionary has keys that are the TV show's seasons. Each value is a second level dictionary of information about each season.

        * The second level dictionary has keys (for each season) that are the season's episodes. Each value is a :py:class:`tuple` of episode name and air date, as a :py:class:`date <datetime.date>`.

        An example of the output format is described in the pure method :py:meth:`get_tot_epdict_tvdb <plextvdb.plextvdb.get_tot_epdict_tvdb>`.

        :rtype: dict

        .. seealso:: :py:meth:`get_tot_epdict_tvdb <plextvdb.plextvdb.get_tot_epdict_tvdb>`
        """
        tot_epdict = { }
        seasons = set( self.seasonDict.keys( ) ) - set([0,])
        for seasno in sorted(seasons):
            tot_epdict.setdefault( seasno, {} )
            for epno in sorted(self.seasonDict[ seasno ].episodes):
                epStruct = self.seasonDict[ seasno ].episodes[ epno ]
                title = epStruct[ 'title' ]
                airedDate = epStruct[ 'airedDate' ]
                tot_epdict[ seasno ][ epno ] = ( title, airedDate )
        return tot_epdict

class TVSeason( object ):
    """
    A convenience object that stores season information for a TV show. This provides a higher level object oriented implementation of the lower level pure method implementation of manipulating TV show data.

    :param str seriesName: the series name.
    :param int seriesId: the TVDB_ series ID.
    :param str token: the TVDB_ API access token.
    :param int seasno: the season number. If this is a TV special, then this should be ``0``.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :param list eps: optional argument. The :py:class:`list` of TV shows returned by the TVDB_ API, and whose format is described in :py:meth:`get_episodes_series <plextvdb.plextvdb.get_episodes_series>`.

    :var str seriesName: the series name.
    :var int seriesId: the TVDB_ series ID.
    :var int seasno: the season number. If this is a TV special, then the season number is ``0``.
    :var str imageURL: the TVDB_ URL of the season poster.
    :var Image img: the :py:class:`Image <PIL.Image.Image>` object associated with this season poster, if found. Otherwise ``None``.
    :var dict episodes: a :py:class:`dict` of episode data. Each key is the episode number. Each value is a :py:class:`dict` of TVDB_ summary of that episode.

          * ``airedEpisodeNumber`` is the episode number in the season.
          * ``airedSeason`` is the season.
          * ``airedDate`` is the :py:class:`date <datetime.date>` on which the episode aired.
          * ``overview`` is the summary of the episode.
    """
    
    def get_num_episodes( self ):
        """
        :returns: the total number of episodes for this season.
        :rtype: int
        """
        return len( self.episodes )
    
    def get_max_date( self ):
        """
        :returns: the last :py:class:`date <datetime.date>` of episodes aired this season.
        :rtype: :py:class:`date <datetime.date>`
        """
        if self.get_num_episodes( ) == 0: return None            
        return max(map(lambda epelem: epelem['airedDate'],
                       filter(lambda epelem: 'airedDate' in epelem,
                              self.episodes.values( ) ) ) )

    def get_min_date( self ):
        """
        :returns: the first :py:class:`date <datetime.date>` of episodes aired this season.
        :rtype: :py:class:`date <datetime.date>`
        """
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
    """
    This *flattens* the TV data, stored as a nested :py:class:`dict` (see documentation in :py:meth:`get_library_data <plexcore.plexcore.get_library_data>` that focuses on the format of the dictionary for TV libraries) into a dictionary whose keys are the :py:class:`date <datetime.date>` at which episodes have been aired, and whose values are the :py:class:`list` of episodes aired on that date. Each element of that list is a :py:class:`tuple` representing a given episode: ``( SHOW, SEASON #, EPISODE #, EPISODE TITLE )``.

    For example, let ``tvdata`` represent the Plex_ TV library information  collected with :py:meth:`get_library_data <plexcore.plexcore.get_library_data>`. Then here are the episodes on the Plex_ server aired on the *last* date.

    .. code-block:: python

        >> tvdata_flatten = get_tvdata_ordered_by_date( tvdata )
        >> last_date = max( tvdata_flatten )
        >> datetime.date(2019, 10, 21)
        >> tvdata_flatten[ last_date ]
        >> [('Robot Chicken', 10, 7, 'Snoopy Camino Lindo in: Quick and Dirty Squirrel Shot'), ('Robot Chicken', 10, 8, "Molly Lucero in: Your Friend's Boob"), ('The Deuce', 3, 7, "That's a Wrap"), ('Travel Man: 48 Hours in...', 10, 1, 'Dubrovnik')]


    :param dict tvdata: the Plex_ TV library information returned by :py:meth:`get_library_data <plexcore.plexcore.get_library_data>`.
    :returns: a :py:class:`dict` of episodes. Each key is the date a list of episodes aired. The value is the list of episodes.
    :rtype: dict

    .. seealso:: :py:meth:`create_plot_year_tvdata <plextvdb.plextvdb.create_plot_year_tvdata>`
    """
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
    """
    Creates a calendar eye chart of episodes aired during a given calendar year. This either creates an SVGZ_ file, or shows the chart on the screen. An example chart is shown in :numref:`plex_tvdb_cli_figures_plots_tvdata_2000`.
    
    :param dict tvdata_date_dict: the :py:class:`dictionary <dict>` of Plex_ TV library episodes, organized by date aired.
    :param int year: the calendar year for which to create an eye chart of episodes aired.
    :param bool shouldPlot: if ``True``, then crate an SVGZ_ file named ``tvdata.YEAR.svgz``. Otherwise plot this eye chart on the screen.
    :parm str dirname: the directory into which a file should be created (only applicable when ``shouldPlot = True``). If ``None``, then defaults to current working directory. If not ``None``, then must be a valid directory.

    .. _SVGZ: https://en.wikipedia.org/wiki/Scalable_Vector_Graphics#Compression
    """
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
    """
    Returns the TVDB_ series ID given its series name. If no candidate is found, returns ``None``.

    :param str series_name: the series name for which to search.
    :param str token: the TVDB_ API access token.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.

    :returns: the :py:class:`int` TVDB_ series ID for a series if found, otherwise ``None``.
    :rtype: str
    """
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

def get_possible_ids( series_name, tvdb_token, verify = True ):
    """
    Returns a :py:class:`tuple` of candidate TV shows from the TVDB_ database that match a series name, and status string. If matches could not be found, returns an error :py:class:`tuple` returned by :py:meth:`return_error_raw <plexcore.return_error_raw>` -- first element is ``None``, second element is :py:class:`str` error message.

    The form of the candidate TV shows is a list of dictionaries. Each dictionary is a candidate TV show: the ``'id'`` key is the :py:class:`int` TVDB_ series ID, and the ``'seriesName'`` key is the :py:class:`str` series name. For example, for `The Simpsons`_

    .. code-block:: bash

       >> candidate_series, _ = get_possible_ids( 'The Simpsons', tvdb_token )
       >> [{'id': 71663, 'seriesName': 'The Simpsons'}, {'id': 76580, 'seriesName': "Paul Merton in Galton & Simpson's..."}, {'id': 153221, 'seriesName': "Jessica Simpson's The Price of Beauty"}]
    
    :param str series_name: the series over which to search on the TVDB_ database.
    :param str tvdb_token: the TVDB_ API access token.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.

    :returns: a :py:class:`tuple` of candidate TVDB_ series that match ``series_name``, and the :py:class:`str` ``'SUCCESS'``. Otherwise an error tuple returned by :py:meth:`return_error_raw <plexcore.return_error_raw>`.
    :rtype: tuple

    .. _`The Simpsons`: https://en.wikipedia.org/wiki/The_Simpsons
    """
    params = { 'name' : series_name.replace("'", '') }
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % tvdb_token }
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
                'Authorization' : 'Bearer %s' % tvdb_token }
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
        response = requests.get(
            'https://api.thetvdb.com/search/series',
            params = { 'imdbId' : imdb_id }, headers = headers, verify = verify )
        if response.status_code != 200: continue
        data = response.json( )[ 'data' ]
        for dat in data:
            tot_data.append( {
                'id' : dat[ 'id' ], 'seriesName' : dat[ 'seriesName' ] } )
    if len( tot_data ) != 0:
        return tot_data, 'SUCCESS'
    #
    return return_error_raw( 'Error, could not find series ids for %s.' % series_name )

def did_series_end( series_id, tvdb_token, verify = True, date_now = None ):
    """
    Check on shows that have ended more than 365 days from the last day.
    
    :param int series_id: the TVDB_ database series ID.
    :param str tvdb_token: the TVDB_ API access token.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :param date date_now: an optional specific last :py:class:`date <datetime.date>` to describe when a show was deemed to have ended. That is, if a show has not aired any episodes more than 365 days before ``date_now``, then define the show as ended. By default, ``date_now`` is the current date.

    :returns: ``True`` if the show is "ended," otherwise ``False``.
    :rtype: bool
    """
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % tvdb_token }
    response = requests.get( 'https://api.thetvdb.com/series/%d' % series_id,
                             headers = headers, verify = verify )
    if response.status_code != 200: return None
    try:
        data = response.json( )['data']
        
        if data['status'] != 'Ended': return False
        #
        ## now check when the last date of the show was
        if date_now is None: date_now = datetime.datetime.now( ).date( )
        last_date = max(map(lambda epdata: datetime.datetime.strptime(
            epdata['firstAired'], '%Y-%m-%d' ).date( ),
                            get_episodes_series( series_id, tvdb_token, verify = verify ) ) )
        td = date_now - last_date
        return td.days > 365
    except:
        raise ValueError("Error, no JSON in the response for show with TVDB ID = %d." % series_id )

def get_imdb_id( series_id, tvdb_token, verify = True ):
    """
    Returns the IMDb_ string ID given a TVDB_ series ID, otherwise return ``None`` if show's IMDb_ ID cannot be found.

    :param int series_id: the TVDB_ database series ID.
    :param str tvdb_token: the TVDB_ API access token.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: the :py:class:`str` IMDb_ ID of the TV show if found, otherwise ``None``.
    :rtype: str
    
    .. _IMDb: https://en.wikipedia.org/wiki/IMDb
    """
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % tvdb_token }
    response = requests.get( 'https://api.thetvdb.com/series/%d' % series_id,
                             headers = headers, verify = verify )
    logging.debug( 'STATUS CODE OF get_imdb_id( %d, %s, %s ) = %d.' % (
        series_id, tvdb_token, verify, response.status_code ) )
    if response.status_code != 200: return None
    data = response.json( )['data']
    return data['imdbId']

def get_episode_id( series_id, airedSeason, airedEpisode, tvdb_token, verify = True ):
    """
    Returns the TVDB_ :py:class:`int` episode ID of an episode, given its TVDB_ series ID, season, and episode number. If cannot be found, then returns ``None``.

    :param int series_id: the TVDB_ database series ID.
    :param int airedSeason: the season number of the episode.
    :param int airedEpisode: the aired episode number, in the season.
    :param str tvdb_token: the TVDB_ API access token.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :returns: the :py:class:`int` TVDB_ episode ID if found, otherwise ``None``.
    :rtype: int
    """
    params = { 'page' : 1,
               'airedSeason' : '%d' % airedSeason,
               'airedEpisode' : '%d' % airedEpisode }
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % tvdb_token }
    response = requests.get( 'https://api.thetvdb.com/series/%d/episodes/query' % series_id,
                             params = params, headers = headers, verify = verify )
    if response.status_code != 200: return None
    data = max( response.json( )[ 'data' ] )
    return data[ 'id' ]

def get_episode_name( series_id, airedSeason, airedEpisode, tvdb_token, verify = True ):
    """
    Returns the episode given its TVDB_ series ID, season number, and episode number. If cannot be found, then returns ``None``.

    :param int series_id: the TVDB_ database series ID.
    :param int airedSeason: the season number of the episode.
    :param int airedEpisode: the aired episode number, in the season.
    :param str tvdb_token: the TVDB_ API access token.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.

    :returns: the :py:class:`str` episode name.
    :rtype: str
    """
    params = { 'page' : 1,
               'airedSeason' : '%d' % airedSeason,
               'airedEpisode' : '%d' % airedEpisode }
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % tvdb_token }
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

def get_series_info( series_id, tvdb_token, verify = True ):
    """
    Returns a :py:class:`tuple` of TVDB_ summary information AND the string "SUCCESS" for a given Tv show, otherwise returns an error :py:class:`tuple` given by :py:meth:`return_error_raw <plexcore.return_error_raw>`. For example, here is the summary information returned for `The Simpsons`_.
    
    .. code-block:: python
    
        >> series_id = get_series_id( 'The Simpsons', tvdb_token )
        >> series_info, _ = get_series_info( series_id, tvdb_token )
        >> {'id': 71663,
            'seriesName': 'The Simpsons',
            'aliases': [],
            'banner': 'graphical/71663-g13.jpg',
            'seriesId': '146',
            'status': 'Continuing',
            'firstAired': '1989-12-17',
            'network': 'FOX',
            'networkId': '',
            'runtime': '25',
            'genre': ['Animation', 'Comedy'],
            'overview': 'Set in Springfield, the average American town, the show focuses on the antics and everyday adventures of the Simpson family; Homer, Marge, Bart, Lisa and Maggie, as well as a virtual cast of thousands. Since the beginning, the series has been a pop culture icon, attracting hundreds of celebrities to guest star. The show has also made name for itself in its fearless satirical take on politics, media and American life in general.',
            'lastUpdated': 1571687688,
            'airsDayOfWeek': 'Sunday',
            'airsTime': '8:00 PM',
            'rating': 'TV-PG',
            'imdbId': 'tt0096697',
            'zap2itId': 'EP00018693',
            'added': '',
            'addedBy': None,
            'siteRating': 8.9,
            'siteRatingCount': 847,
            'slug': 'the-simpsons'}

    :param int series_id: the TVDB_ database series ID.
    :param str tvdb_token: the TVDB_ API access token.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.

    :returns: a :py:class:`tuple` of candidate TV show info, and the :py:class:`str` ``'SUCCESS'``. Otherwise an error tuple returned by :py:meth:`return_error_raw <plexcore.return_error_raw>`.
    :rtype: tuple
    """
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % tvdb_token }
    response = requests.get( 'https://api.thetvdb.com/series/%d' % series_id,
                             headers = headers, verify = verify )
    if response.status_code != 200: return return_error_raw( "COULD NOT ACCESS TV INFO SERIES" )
    data = response.json( )[ 'data' ]
    return data, 'SUCCESS'

def get_series_image( series_id, tvdb_token, verify = True ):
    """
    Returns a :py:class:`tuple` of the TVDB_ URL of the TV show's poster AND the string "SUCCESS", if found. Otherwise returns an error :py:class:`tuple` given by :py:meth:`return_error_raw <plexcore.return_error_raw>`. For example, here is the TVDB_ poster URL for `The Simpsons`_.
    
    .. code-block:: python

        >> series_id = get_series_id( 'The Simpsons', tvdb_token )
        >> series_image, _ = get_series_image( series_id, tvdb_token )
        >> 'https://thetvdb.com/banners/posters/71663-1.jpg'

    :param int series_id: the TVDB_ database series ID.
    :param str tvdb_token: the TVDB_ API access token.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.

    :returns: a :py:class:`tuple` of TV show poster URL, and the :py:class:`str` ``'SUCCESS'``. Otherwise an error tuple returned by :py:meth:`return_error_raw <plexcore.return_error_raw>`.
    :rtype: tuple

    .. seealso:: :py:meth:`get_series_season_image <plextvdb.plextvdb.get_series_season_image>`
    """
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % tvdb_token }
    response = requests.get( 'https://api.thetvdb.com/series/%d/images/query/params' % series_id,
                             headers = headers, verify = verify )
    if response.status_code != 200: return return_error_raw( "COULD NOT ACCESS IMAGE URL FOR SERIES" )
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
    #
    ## then look for fan art ones
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

    #
    ## finally look for fan art ones
    series_ones = list(
        filter(lambda elem: 'keyType' in elem.keys( ) and elem['keyType'] == 'series', data ) )
    logging.info( 'number of series: %d.' % len( series_ones ) )
    if len( series_ones ) != 0:
        series_one = series_ones[ 0 ]
        params = { 'keyType' : 'series' }
        if 'resolution' in series_one and len( series_one['resolution'] ) != 0:
            params['resolution'] = series_one['resolution'][0]
        response = requests.get( 'https://api.thetvdb.com/series/%d/images/query' % series_id,
                                 headers = headers, params = params, verify = verify )
        logging.info( 'response status code = %s. params = %s.' % (
            response.status_code, params ) )
        if response.status_code == 200:
            data = response.json( )['data']
            firstSeries = data[0]
            if 'fileName' in firstSeries:
                return 'https://thetvdb.com/banners/%s' % firstSeries['fileName'], "SUCCESS"
    #
    ## nothing happened
    return return_error_raw( "COULD NOT DOWNLOAD SERIES INFO FOR SERIES_ID = %d" % series_id )

def get_series_season_image( series_id, airedSeason, tvdb_token, verify = True ):
    """
    Returns a :py:class:`tuple` of the TVDB_ URL of the TV show's SEASON poster AND the string "SUCCESS", if found. Otherwise returns an error :py:class:`tuple` given by :py:meth:`return_error_raw <plexcore.return_error_raw>`. For example, here is the TVDB_ season poster URL for `The Simpsons, season 10`_.
    
    .. code-block:: python

        >> series_id = get_series_id( 'The Simpsons', tvdb_token )
        >> season_image, _ = get_series_image( series_id, 10, tvdb_token )
        >> 'https://thetvdb.com/banners/seasons/146-10.jpg'

    :param int series_id: the TVDB_ database series ID.
    :param int airedSeason: the season number of the episode.
    :param str tvdb_token: the TVDB_ API access token.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.

    :returns: a :py:class:`tuple` of TV show SEASON poster URL, and the :py:class:`str` ``'SUCCESS'``. Otherwise an error tuple returned by :py:meth:`return_error_raw <plexcore.return_error_raw>`.
    :rtype: tuple

    .. seealso:: :py:meth:`get_series_image <plextvdb.plextvdb.get_series_image>`

    .. _`The Simpsons, season 10`: https://en.wikipedia.org/wiki/The_Simpsons_(season_10)
    """
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % tvdb_token }
    response = requests.get( 'https://api.thetvdb.com/series/%d/images/query/params' % series_id,
                             headers = headers, verify = verify )
    if response.status_code != 200:
        return return_error_raw( "COULD NOT FIND IMAGES FOR SERIES_ID = %d" % series_id )
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
        return return_error_raw(
            "COULD NOT GET PROPER IMAGE FROM VALID IMAGE QUERY FOR SERIES_ID = %d AND SEASON = %d" % (
                series_id, airedSeason ) )
    season_data = response.json( )['data'][ 0 ]
    if 'fileName' not in season_data:
        return return_error_raw(
            "COULD NOT FIND APPROPRIATE IMAGE URL FROM VALID IMAGE QUERY FOR SERIES_ID = %d AND SEASON = %d" % (
                series_id, airedSeason ) )
    return 'https://thetvdb.com/banners/%s' % season_data[ 'fileName' ], "SUCCESS"

def get_episodes_series( series_id, tvdb_token, showSpecials = True, fromDate = None,
                         verify = True, showFuture = False ):
    """
    Returns a large and comprehensive :py:class:`list` of TVDB_ episode info on a given TV show. Example TVDB_ show data for `The Simpsons`_, represented as a JSON file, is located in :download:`tvdb_simpsons_info.json </_static/tvdb_simpsons_info.json>`. Each element of the list is an episode, and the list is ordered from earliest aired episode to latest aired episode.
    
    :param int series_id: the TVDB_ database series ID.
    
    :param str tvdb_token: the TVDB_ API access token.
    
    :param bool showSpecials: if ``True``, also include episode info for TV specials for that given series. Default is ``True``.
    
    :param date fromDate: optional first :py:class:`date <datetime.date>` after which to collect TVDB_ episode information. If not defined, then include information on all episodes from the first one aired.
    
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :param bool showFuture: optional argument, if ``True`` then also include information on episodes that have not yet aired.
    
    :returns: the :py:class:`list` of unified TVDB_ information on a TV show. See :download:`tvdb_simpsons_info.json </_static/tvdb_simpsons_info.json>`.
    :rtype: list

    .. _TVDB: https://api.thetvdb.com/swagger
    """
    params = { 'page' : 1 }
    headers = { 'Content-Type' : 'application/json',
                'Authorization' : 'Bearer %s' % tvdb_token }
    response = requests.get( 'https://api.thetvdb.com/series/%d/episodes' % series_id,
                             params = params, headers = headers, verify = verify )
    if response.status_code != 200:
        logging.debug( 'could not get episodes for series_id = %d.' % series_id )
        return None
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

def get_path_data_on_tvshow( tvdata, tvshow ):
    """
    This method is used by the :ref:`get_plextvdb_batch.py` tool that can automatically download new episodes. This returns a summary :py:class:`dict` of information on a TV show stored in the Plex_ server (see documentation in :py:meth:`get_library_data <plexcore.plexcore.get_library_data>` that focuses on the format of the dictionary for TV libraries). For example, here is the summary information on `The Simpsons`_ given in the ``tvdata``, the dictionary representation of TV library data. ``$LIBRARY_DIR`` is the TV library's location on the Plex_ server.

    .. code-block:: python
        
        >> simpsons_summary = get_path_data_on_tvshow( tvdata, 'The Simpsons' )
        >> {'prefix': '$LIBRARY_DIR/The Simpsons',
            'showFileName': 'The Simpsons',
            'season_prefix_dict': {1: 'Season 01',
              2: 'Season 02',
              3: 'Season 03',
              4: 'Season 04',
              5: 'Season 05',
              6: 'Season 06',
              7: 'Season 07',
              8: 'Season 08',
              9: 'Season 09',
              10: 'Season 10',
              11: 'Season 11',
              12: 'Season 12',
              13: 'Season 13',
              14: 'Season 14',
              15: 'Season 15',
              16: 'Season 16',
              17: 'Season 17',
              18: 'Season 18',
              19: 'Season 19',
              20: 'Season 20',
              21: 'Season 21',
              22: 'Season 22',
              23: 'Season 23',
              24: 'Season 24',
              25: 'Season 25',
              26: 'Season 26',
              27: 'Season 27',
              28: 'Season 28',
              29: 'Season 29',
              30: 'Season 30',
              31: 'Season 31'},
            'min_inferred_length': 2,
            'episode_number_length': 2,
            'avg_length_mins': 22.0}
    
    Here is a guide to the keys:
    
    * ``prefix`` is the root directory in which the episodes of the TV show live.
    * ``showFilename`` is the prefix of all episodes of this TV show. Here for instance, a new Simpsons episode, say S31E06, would start with ``"The Simpsons - s31e06 - ..."``.
    * ``season_prefix_dict`` is a dictionary of sub-directories, by *season*, in which the episodes live. For example, season 1 episodes live in ``"$LIBRARY_DIR/The Simpsons/Season 01"``.
    * ``min_inferred_length`` refers to the padding of season number. This :py:class:`integer <int>` must be :math:`\ge 1`. Here ``min_inferred_length = 2``, so seasons are numbered as ``"Season 01"``.
    * ``episode_number_length`` is the formatting on each episode number. Two means that episode numbers for this TV show are formatted as ``01-99``. This becomes important for TV shows in which there are 100 or more episodes in a season, such as `The Adventures of Rocky and Bullwinkle and Friends`_.
    * ``avg_length_mins`` is the average episode length, in minutes.

    :param dict tvdata: the Plex_ TV library information returned by :py:meth:`get_library_data <plexcore.plexcore.get_library_data>`.
    :param str tvshow: the TV show's name.

    :returns: the summary :py:class:`dict` for the TV show on this Plex_ server's TV library. If ``tvshow`` is not found, then returns ``None``.
    :rtype: dict

    .. _`The Adventures of Rocky and Bullwinkle and Friends`: https://en.wikipedia.org/wiki/The_Adventures_of_Rocky_and_Bullwinkle_and_Friends
    """
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

def get_all_series_didend(
        tvdata, verify = True,
        num_threads = 2 * multiprocessing.cpu_count( ),
        tvdb_token = None ):
    """
    Returns a :py:class:`dict` on which TV shows on the Plex_ server have ended. Each key is the TV show, and its value is whether the show ended or not. Here is its format.

    .. code-block:: python

        {
          '11.22.63': True,
          'Fargo': False,
          'Night Court': True,
          'Two and a Half Men': True,
          '24': True,
          ...
        }

    :param dict tvdata: the Plex_ TV library information returned by :py:meth:`get_library_data <plexcore.plexcore.get_library_data>`.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :param int num_threads: the number of threads over which to parallelize this calculation. The default is *twice* the number of cores on the CPU.
    :param str tvdb_token: optional TVDB_ API access token. If ``None``, then gets the TVDB_ API access token with :py:meth:`get_token <plextvdb.get_token>`.
    
    :returns: the :py:class:`dict` of TV shows on the Plex_ server and whether each has ended or not.
    :type: dict
    """
    time0 = time.time( )
    if tvdb_token is None: tvdb_token = get_token( verify = verify )
    with multiprocessing.Pool(
            processes = max(num_threads, multiprocessing.cpu_count( ) ) ) as pool:
        date_now = datetime.datetime.now( ).date( )
        tvshow_id_list = list(map(lambda seriesName: ( seriesName, tvdata[ seriesName ][ 'tvdbid' ] ),
                                  filter(lambda seriesName: 'tvdbid' in tvdata[ seriesName ], tvdata ) ) )
        tvshow_id_list_2 = list(filter(
            None, pool.map(lambda seriesName: (
                seriesName, get_series_id( seriesName, tvdb_token, verify = verify ) ),
                           filter(lambda seriesName: 'tvdbid' not in tvdata[ seriesName ], tvdata ) ) ) )
        tvshow_id_map = dict( tvshow_id_list + tvshow_id_list_2 )
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
    mustHaveTitle = input_tuple[ 'mustHaveTitle' ]
    #
    ## only record those episodes that have an episodeName that is not None
    if mustHaveTitle:
        eps = list(
            filter(lambda ep: 'episodeName' in ep and ep['episodeName'] is not None,
                   get_episodes_series( series_id, token, showSpecials = showSpecials, verify = verify,
                                        fromDate = fromDate, showFuture = showFuture ) ) )
    else:
        eps = get_episodes_series( series_id, token, showSpecials = showSpecials, verify = verify,
                                   fromDate = fromDate, showFuture = showFuture )
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
    try:
        if 'tvdbid' not in input_tuple:
            series_id = get_series_id( show, token, verify = verify )
        else: series_id = input_tuple[ 'tvdbid' ]
        if series_id is None:
            logging.info( 'something happened with show %s' % show )
            return None
        if not doShowEnded:
            didEnd = did_series_end( series_id, token, verify = verify )
            if didEnd is None or didEnd: return None
        return show, series_id
    except Exception as e:
        print( 'problem getting %s, error = %s.' % ( show, str( e ) ) )
        return None
    
def get_remaining_episodes(
        tvdata, showSpecials = True, fromDate = None, verify = True,
        doShowEnded = False, showsToExclude = None, showFuture = False,
        num_threads = 2 * multiprocessing.cpu_count( ), token = None,
        mustHaveTitle = True ):
    """
    Returns a :py:class:`dict` of episodes missing from the Plex_ TV library for the TV shows that are in it. Each key in the dictionary is the TV show with missing episodes. The value is another dictionary. Here are their keys and values,
    
    * ``episodes`` returns a :py:class:`list` of :py:class:`tuple`s of missing episodes. Each tuple is of the form ``( SEASON #, EPISODE #, EPISODE NAME )``.
    * the remaining keys -- ``prefix``, ``showFilename``, ``min_inferred_length``, ``season_prefix_dict``, ``episode_number_length``, ``avg_length_mins`` -- and their values have the same meaning as the summary Plex_ TV library returned by :py:meth:`get_path_data_on_tvshow <plextvdb.plextvdb.get_path_data_on_tvshow>`.

    Here is some example output. ``$LIBRARY_DIR`` is the TV library's location on the Plex_ server, and `The Great British Bake Off`_ is a British reality TV show on baking.

    .. code-block:: python

       {'The Great British Bake Off': {'episodes': [(5, 12, 'Masterclass 2'),
       (5, 13, 'Class of 2013'),
       (5, 14, 'Masterclass 3'),
       (5, 15, 'Masterclass 4'),
       (7, 11, 'Class of 2015'),
       (10, 1, 'Cake Week'),
       (10, 2, 'Biscuit Week'),
       (10, 3, 'Bread Week'),
       (10, 4, 'Dairy Week'),
       (10, 5, 'The Roaring Twenties'),
       (10, 6, 'Dessert Week'),
       (10, 7, 'Festival Week'),
       (10, 8, 'Pastry Week')],
      'prefix': '$LIBRARY_DIR/The Great British Bake Off',
      'showFileName': 'The Great British Bake Off',
      'min_inferred_length': 1,
      'season_prefix_dict': {0: 'Specials',
       1: 'Season 1',
       2: 'Season 2',
       3: 'Season 3',
       4: 'Season 4',
       5: 'Season 5',
       6: 'Season 6',
       7: 'Season 7',
       8: 'Season 8',
       9: 'Season 9'},
      'episode_number_length': 2,
      'avg_length_mins': 52.0}}
    
    :param dict tvdata: the Plex_ TV library information returned by :py:meth:`get_library_data <plexcore.plexcore.get_library_data>`.
    :param bool showSpecials: if ``True``, also include episode info for TV specials for that given series. Default is ``True``.
    :param date fromDate: optional start :py:class:`date <datetime.date>` from which to search for new episodes. That is, if defined then only look for missing episodes aired on or after this date. If not defined, then look for *any* aired episode missing from this Plex_ TV library.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :param bool doShowEnded: if ``True``, then also look for missing episodes from shows that have ended. Default is ``False``.
    :param list showsToExclude: the list of TV shows on the Plex_ server to ignore. Default is to not ignore any TV show.
    :param bool showFuture: if ``True``, then also include missing episodes that have not aired yet. Default is ``False``.
    :param int num_threads: the number of threads over which to parallelize this calculation. The default is *twice* the number of cores on the CPU.
    :param str token: optional TVDB_ API access token. If ``None``, then gets the TVDB_ API access token with :py:meth:`get_token <plextvdb.get_token>`.
    :param bool mustHaveTitle: sometimes new episodes are registered in TVDB_ but without titles. Functionality to download missing episodes to the Plex_ server (see, e.g., :ref:`get_plextvdb_batch.py`) fails if the episode does not have a name. If ``True``, then ignore new episodes that do not have titles. Default is ``True``.
    
    :returns: a :py:class:`dict` of missing episodes by TV show on the Plex_ server.
    :rtype: dict

    .. seealso::

       * :py:meth:`get_path_data_on_tvshow <plextvdb.plextvdb.get_path_data_on_tvshow>`.
       * :ref:`get_plextvdb_batch.py`.

    .. _`The Great British Bake Off`: https://en.wikipedia.org/wiki/The_Great_British_Bake_Off
    """
    assert( num_threads >= 1 )
    if token is None: token = get_token( verify = verify )
    tvdata_copy = copy.deepcopy( tvdata )
    if showsToExclude is not None:
        showsExclude = set( showsToExclude ) & set( tvdata_copy.keys( ) )
        for show in showsExclude: tvdata_copy.pop( show )
    with multiprocessing.Pool( processes = max( num_threads, multiprocessing.cpu_count( ) ) ) as pool:
        input_tuples = list(
            map(lambda show: {
                'show' : show, 'token' : token, 'verify' : verify, 'doShowEnded' : doShowEnded,
                'tvdbid' : tvdata_copy[ show ][ 'tvdbid' ] },
                filter(lambda show: 'tvdbid' in tvdata_copy[ show ], tvdata_copy ) ) )
        input_tuples_2 = list(
            map(lambda show: {
                'show' : show, 'token' : token, 'verify' : verify, 'doShowEnded' : doShowEnded },
                filter(lambda show: 'tvdbid' not in tvdata_copy[ show ], tvdata_copy ) ) )
        tvshow_id_map = dict(filter(
            None, pool.map( _get_series_id_perproc, input_tuples + input_tuples_2 ) ) )
        
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
              'mustHaveTitle' : mustHaveTitle,
              'epsForShow' : tvdata_copy[ name ][ 'seasons' ] }, tvshow_id_map ) )
    with multiprocessing.Pool(
            processes = max(num_threads, multiprocessing.cpu_count( ) ) ) as pool:
        toGet_sub = dict( filter(
            None, pool.map( _get_remaining_eps_perproc, input_tuples ) ) )
    #
    ## guard code for now -- only include those tv shows that have titles of new episodes to download
    if mustHaveTitle:
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
    else:
        tvshows_act = set(filter(lambda tvshow: len( toGet_sub[ tvshow ] ) != 0, toGet_sub ) )
        tvdata_path_data = dict(filter(None, map(lambda tvshow: (
            tvshow, get_path_data_on_tvshow( tvdata, tvshow ) ), tvshows_act ) ) )
        toGet = dict(map(lambda tvshow: ( tvshow, {
            'episodes' : toGet_sub[ tvshow ],
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
    """
    Returns a :py:class:`dict` on which TV shows on the Plex_ server have a new season to start. Each key is a TV show in the Plex_ library. Each value is another dictionary: ``max_last_season`` is the latest season of the TV show, ``min_next_season`` is the next season to be aired, and ``start_date`` is the first :py:class:`date <datetime.date>` that a new episode will air.

    An example output of this method is shown here,
    
    .. code-block:: python

        {'American Crime Story': {'max_last_season': 2,
          'min_next_season': 3,
          'start_date': datetime.date(2020, 9, 27)},
         'BoJack Horseman': {'max_last_season': 5,
          'min_next_season': 6,
          'start_date': datetime.date(2019, 10, 25)},
         'Homeland': {'max_last_season': 7,
          'min_next_season': 8,
          'start_date': datetime.date(2020, 2, 9)},
          ...
        }
    
    :param dict tvdata: the Plex_ TV library information returned by :py:meth:`get_library_data <plexcore.plexcore.get_library_data>`.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :param list showsToExclude: the list of TV shows on the Plex_ server to ignore. Default is to not ignore any TV show.
    :param str token: optional TVDB_ API access token. If ``None``, then gets the TVDB_ API access token with :py:meth:`get_token <plextvdb.get_token>`.
    :param date fromDate: optional start :py:class:`date <datetime.date>` *after* which to search for new episodes. That is, if defined then only look for future episodes aired on or after this date. If not defined, then look for *any* aired episode to be aired after the current date.
    :param int num_threads: the number of threads over which to parallelize this calculation. The default is *twice* the number of cores on the CPU.
    
    :returns: a :py:class:`dict` of TV shows that will start airing new episodes.
    :rtype: dict

    .. seealso:: :ref:`plex_tvdb_futureshows.py`
    """
    #
    ## first get all candidate tv shows
    if token is None: token = get_token( verify = verify )
    if fromDate is None: fromDate = datetime.datetime.now( ).date( )
    toGet_future_cands = get_remaining_episodes(
        tvdata, showSpecials = False, fromDate = fromDate,
        doShowEnded = False, showsToExclude = showsToExclude,
        mustHaveTitle = False, token = token, showFuture = True,
        num_threads = num_threads, verify = verify )
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
            show, verify = verify, token = token, showFuture = True )
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
    """
    Adds a list of new shows to exclude from analysis or update in the Plex_ TV library. This updates the ``showstoexclude`` table in the SQLite3_ configuration database with new shows. The shows in the list must exist in the Plex_ server.

    :param dict tvdata: the Plex_ TV library information returned by :py:meth:`get_library_data <plexcore.plexcore.get_library_data>`.
    :param list showsToExclude: the list of TV shows on the Plex_ server to ignore. Default is to not ignore any TV show.

    .. seealso:: :py:meth:`get_shows_to_exclude <plextvdb.plextvdb.get_shows_to_exclude>`
    """
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
    """
    Returns the list of shows in the Plex_ library that are ignored from analysis or update. This queries the ``showstoexclude`` table in the SQLite3_ configuration database.

    :param dict tvdata: Optional Plex_ TV library information, returned by :py:meth:`get_library_data <plexcore.plexcore.get_library_data>`, to query. If not defined, then return the list of excluded TV shows found in the relevant table. If defined, returns an intersection of shows found in the table with TV shows in the Plex_ library.

    :returns: a :py:class:`list` of TV shows to ignore.
    :rtype: list

    .. seealso:: :py:meth:`push_shows_to_exclude <plextvdb.plextvdb.push_shows_to_exclude>`
    """
    showsToExcludeInDB = sorted( set( map(lambda val: val.show,
                                          session.query( ShowsToExclude ).all( ) ) ) )
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

def create_tvTorUnits( toGet, restrictMaxSize = True, restrictMinSize = True,
                       do_raw = False ):
    """
    Used by, e.g., :ref:`get_plextvdb_batch.py`, to download missing episodes on the Plex_ TV library. This returns a :py:class:`tuple` of a :py:class:`list` of missing episodes to (torrent) download from the remote Deluge_ torrent server, and a :py:class:`list` of new directories to create, given a set of missing episode information, ``toGet``, as produced by :py:meth:`get_remaining_episodes <plextvdb.plextvdb.get_remaining_episodes>`. ``$LIBRARY_DIR`` is the TV library's location on the Plex_ server.

    * The first element of the tuple is a list of missing episodes to download using the remote Deluge_ server (see :numref:`Seedhost Services Setup` on the server's setup). Each element in the list consists of summary information, as a dictionary, that describes those TV Magnet links to download. Here are the keys.
      
      * ``totFname`` is the destination prefix (without file extension) of the episode on the Plex_ server.
      * ``torFname`` is the search string to give to the Jackett_ server (see :numref:`The Jackett Server` on the Jackett_ server's setup) to search for and download this episode.
      * ``minSize`` is the minimum size, in MB, of the H264_ encoded MP4 or MKV episode file to search for.
      * ``minSize_x265`` is the minimum size, in MB, of the `H265/HEVC`_ encoded MP4 or MKV episode file to search for. By defsault this is smaller than ``minSize``.
      * ``maxSize`` is the maximum size, in MB, of the H264_ encoded MP4 or MKV episode file to search for.
      * ``maxSize_x265`` is the maximum size, in MB, of the `H265/HEVC`_ encoded MP4 or MKV episode file to search for. By defsault this is smaller than ``maxSize``.
      * ``tvshow`` is the name of the TV show to which this missing episode belongs.
      * ``do_raw`` is a :py:class:`boolean <bool>` flag. If ``True``, then search for this missing episode through the Jackett_ server using available IMDb_ information. If ``False``, then do a raw text search on ``torFname`` to find episode Magnet links.

      For example, here is a representation of a missing episode that will be fed to the Deluge_ server for download.

      .. code-block:: python

           {
            'totFname': '$LIBRARY_DIR/The Great British Bake Off/Season 5/The Great British Bake Off - s05e12 - Masterclass 2',
             'torFname': 'The Great British Bake Off S05E12',
             'minSize': 300,
             'maxSize': 800,
             'minSize_x265': 200,
             'maxSize_x265': 650,
             'tvshow': 'The Great British Bake Off',
             'do_raw': False
           }

    * The second element is a :py:class:`list` of new directories to create for missing episodes. In this example, there are new episodes for season 10 of `The Great British Bake Off`_, but no season 10 directory.

      .. code-block:: python

            [ '$LIBRARY_DIR/The Great British Bake Off/Season 10' ]

    :param dict toGet: a :py:class:`dict` of missing episodes by TV show on the Plex_ server, of the format returned by :py:meth:`get_remaining_episodes <plextvdb.plextvdb.get_remaining_episodes>`.
    :param bool restrictMaxSize: if ``True``, then restrict the *maximum* size of H264_ or `H265/HEVC`_ videos to search for on the Jackett_ server. Default is ``True``.
    :param bool restrictMinSize: if ``True``, then restrict the *minimum* size of H264_ or `H265/HEVC`_ videos to search for on the Jackett_ server. Default is ``True``.
    :param bool do_raw: if ``False``, then search for Magnet links of missing episodes using their IMDb_ information. If ``True``, then search using the raw string. Default is ``False``.

    :returns: a :py:class:`tuple` of two elements. The first element is a :py:class:`list` of missing episodes to search on the Jackett_ server. The second element is a :py:class:`list` of new directories to create for the TV library.
    :rtype: tuple
    
    .. seealso::
    
       * :ref:`get_plextvdb_batch.py`.
       * :py:meth:`get_remaining_episodes <plextvdb.plextvdb.get_remaining_episodes>`.
       * :py:meth:`download_batched_tvtorrent_shows <plextvdb.plextvdb.download_batched_tvtorrent_shows>`.
       * :py:meth:`worker_process_download_tvtorrent <plextvdb.plextvdb_torrents.worker_process_download_tvtorrent>`.
    
    .. _Deluge: https://en.wikipedia.org/wiki/Deluge_(software)
    .. _Jackett: https://github.com/Jackett/Jackett
    .. _H264: https://en.wikipedia.org/wiki/Advanced_Video_Coding
    .. _`H265/HEVC`: https://en.wikipedia.org/wiki/High_Efficiency_Video_Coding
    """
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
        if not restrictMinSize:
            minSize /= 10
            minSize_x265 /= 10
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
                    'tvshow' : tvshow,
                    'do_raw' : do_raw }
                
            if not os.path.isdir( candDir ):
                tv_torrent_gets[ 'newdirs' ].setdefault( candDir, [] )
                tv_torrent_gets[ 'newdirs' ][ candDir ].append( dat )
            else: tv_torrent_gets[ 'nonewdirs' ].append( dat )

    tvTorUnits = list(chain.from_iterable(
        [ tv_torrent_gets[ 'nonewdirs' ] ] +
        list(map(lambda newdir: tv_torrent_gets[ 'newdirs' ][ newdir ],
                 tv_torrent_gets[ 'newdirs' ] ) ) ) )
    return tvTorUnits, sorted( tv_torrent_gets[ 'newdirs' ].keys( ) )

def download_batched_tvtorrent_shows( tvTorUnits, newdirs = [ ], maxtime_in_secs = 240, num_iters = 10,
                                      do_raw = False ):
    """
    Engine backend code, used by :ref:`get_plextvdb_batch.py`, that  searches for Magnet links for missing episodes on the Jackett_ server, downloads the Magnet links using the Deluge_ server, and finally copies the downloaded missing episodes to the appropriate locations in the Plex_ TV library. This expects the :py:class:`tuple` input returned by :py:meth:`create_tvTorUnits <plextvdb.plextvdb.create_tvTorUnits>` to run.

    :param list tvTorUnits: the :py:class:`list` of missing episodes to search on the Jackett_ server. This is the first element of the :py:class:`tuple` returned by :py:meth:`create_tvTorUnits <plextvdb.plextvdb.create_tvTorUnits>`.
    :param list newdirs: the :py:class:`list` of new directories to create for the TV library. This is the second element of the :py:class:`tuple` returned by :py:meth:`create_tvTorUnits <plextvdb.plextvdb.create_tvTorUnits>`.
    :param int maxtime_in_secs: optional argument, the maximum time to wait for a Magnet link found by the Jackett_ server to fully download through the Deluge_ server. Must be :math:`\ge 60` seconds. Default is 240 seconds.
    :param int num_iters: optional argument, the maximum number of Magnet links to try and fully download before giving up. The list of Magnet links to try for each missing episode is ordered from *most* seeders + leechers to *least*. Must be :math:`\ge 1`. Default is 10.
    :param bool do_raw: if ``False``, then search for Magnet links of missing episodes using their IMDb_ information. If ``True``, then search using the raw string. Default is ``False``.

    .. seealso::
    
       * :ref:`get_plextvdb_batch.py`.
       * :py:meth:`get_remaining_episodes <plextvdb.plextvdb.get_remaining_episodes>`.
       * :py:meth:`create_tvTorUnits <plextvdb.plextvdb.create_tvTorUnits>`.
       * :py:meth:`worker_process_download_tvtorrent <plextvdb.plextvdb_torrents.worker_process_download_tvtorrent>`.
    """
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
    
def get_tot_epdict_tvdb(
        showName, verify = True, showSpecials = False,
        showFuture = False, token = None ):
    """
    Returns a summary nested :py:class:`dict` of episode information for a given TV show.

    * The top level dictionary has keys that are the TV show's seasons. Each value is a second level dictionary of information about each season.

    * The second level dictionary has keys (for each season) that are the season's episodes. Each value is a :py:class:`tuple` of episode name and air date, as a :py:class:`date <datetime.date>`.

    An example for `The Simpsons`_ is shown below,

    .. code-block:: python

        {1 : {1: ('Simpsons Roasting on an Open Fire', datetime.date(1989, 12, 17)),
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
        2: {1: ('Bart Gets an F', datetime.date(1990, 10, 11)),
          2: ('Simpson and Delilah', datetime.date(1990, 10, 18)),
          3: ('Treehouse of Horror', datetime.date(1990, 10, 24)),
          4: ('Two Cars in Every Garage and Three Eyes on Every Fish', datetime.date(1990, 11, 1)),
          5: ("Dancin' Homer", datetime.date(1990, 11, 8)),
          6: ('Dead Putting Society', datetime.date(1990, 11, 15)),
          7: ('Bart vs. Thanksgiving', datetime.date(1990, 11, 22)),
          8: ('Bart the Daredevil', datetime.date(1990, 12, 6)),
          9: ('Itchy & Scratchy & Marge', datetime.date(1990, 12, 20)),
          10: ('Bart Gets Hit by a Car', datetime.date(1991, 1, 10)),
          11: ('One Fish, Two Fish, Blowfish, Blue Fish', datetime.date(1991, 1, 24)),
          12: ('The Way We Was', datetime.date(1991, 1, 31)),
          13: ('Homer vs. Lisa and the Eighth Commandment', datetime.date(1991, 2, 7)),
          14: ('Principal Charming', datetime.date(1991, 2, 14)),
          15: ('Oh Brother, Where Art Thou?', datetime.date(1991, 2, 21)),
          16: ("Bart's Dog Gets an F", datetime.date(1991, 3, 7)),
          17: ('Old Money', datetime.date(1991, 3, 28)),
          18: ('Brush With Greatness', datetime.date(1991, 4, 11)),
          19: ("Lisa's Substitute", datetime.date(1991, 4, 25)),
          20: ('The War of the Simpsons', datetime.date(1991, 5, 2)),
          21: ('Three Men and a Comic Book', datetime.date(1991, 5, 9)),
          22: ('Blood Feud', datetime.date(1991, 8, 11))},
          ...
        }

    :param str showName: the TV show's name.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :param bool showSpecials: if ``True``, then also include TV specials. These specials will appear in a season ``0`` in this dictionary.
    :param bool showFuture: optional argument, if ``True`` then also include information on episodes that have not yet aired.
    
    :returns: a :py:class:`dict` of TV show episodes that the TVDB_ database has found.
    :rtype: dict
    """
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
