from PyQt4.QtGui import *
from PyQt4.QtCore import *
import os, sys, numpy, glob, datetime
import logging, requests, time, io, PIL.Image
import pathos.multiprocessing as multiprocessing
from bs4 import BeautifulSoup
from functools import reduce
from . import plextvdb, mainDir, get_token, plextvdb_season_gui
from plexcore import plexcore
from plextmdb import plextmdb

class TVShow( object ):
    
    @classmethod
    def create_tvshow_dict( cls, tvdata, token = None, verify = True,
                            debug = False ):
        time0 = time.time( )
        if token is None: token = get_token( verify = verify )
        def _create_tvshow( seriesName ):
            try: return ( seriesName, TVShow( seriesName, tvdata[ seriesName ],
                                              token, verify = verify ) )
            except: return None
        with multiprocessing.Pool(
                processes = max( 32, multiprocessing.cpu_count( ) ) ) as pool:
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
        
    def __init__( self, seriesName, seriesInfo, token, verify = True ):
        self.seriesId = plextvdb.get_series_id( seriesName, token, verify = verify )
        self.seriesName = seriesName
        if self.seriesId is None:
            raise ValueError("Error, could not find TV Show named %s." % seriesName )
        #
        ## check if status ended
        self.statusEnded = plextvdb.did_series_end( self.seriesId, token, verify = verify )
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
            self.imageURL, _ = plextvdb.get_series_image( self.seriesId, token, verify = verify )
            self.isPlexImage = False
        # self.img = TVShow._create_image( self.imageURL, verify = verify )

        #
        ## get series overview
        if seriesInfo['summary'] != '':
            self.overview = seriesInfo['summary']
        else:
            data, status = plextvdb.get_series_info( self.seriesId, token, verify = verify )
            self.overview = ''
            if status == 'SUCCESS' and 'overview' in data:
                self.overview = data[ 'overview' ]
        
        #
        ## get every season defined
        eps = plextvdb.get_episodes_series(
            self.seriesId, token, showSpecials = True,
            showFuture = False, verify = verify )
        if any(filter(lambda episode: episode['episodeName'] is None,
                      eps ) ):
            tmdb_id = plextmdb.get_tv_ids_by_series_name( seriesName, verify = verify )
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
        self.imageURL, status = plextvdb.get_series_season_image(
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
            eps = plextvdb.get_episodes_series(
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

class CustomDialog( QDialog ):
    def __init__( self, parent ):
        super( CustomDialog, self ).__init__( parent )
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        self.textArea = QTextEdit( )
        self.textArea.setReadOnly( True )
        myLayout.addWidget( self.textArea )
        self.parsedHTML = BeautifulSoup("""
        <html>
        <body>
        </body>
        </html>""", 'lxml' )
        self.textArea.setHtml( self.parsedHTML.prettify( ) )
        self.setFixedWidth( 250 )
        self.setFixedHeight( 300 )
        self.show( )

    def addText( self, text ):
        body_elem = self.parsedHTML.find_all('body')[0]
        txt_tag = self.parsedHTML.new_tag("p")
        txt_tag.string = text
        body_elem.append( txt_tag )
        self.textArea.setHtml( self.parsedHTML.prettify( ) )

        
class TVDBGUI( QDialog ):
    mySignal = pyqtSignal( list )
    tvSeriesSendList = pyqtSignal( list )
    tvSeriesRefreshRows = pyqtSignal( list )

    @classmethod
    def getShowSummary( cls, seriesName, tvshow_dict, tvdata_on_plex, missing_eps ):
        tvshow = tvshow_dict[ seriesName ]
        tvshow_plex = tvdata_on_plex[ seriesName ]
        overview = tvshow.overview.strip( )
        num_total = sum(list(
            map(lambda seasno: len( tvshow_plex[ seasno ] ),
                set( tvshow_plex ) - set([0]) ) ) )
        num_missing = len( missing_eps[ seriesName ] )
        if tvshow.statusEnded: show_status = "Show has ended"
        else: show_status = "Show is still ongoing"
        minDate = min(
            map(lambda seasno: min(
                map(lambda epno: tvshow_plex[ seasno ][epno]['date aired' ],
                    tvshow_plex[ seasno ] ) ), set( tvshow_plex ) - set([0])))
        maxDate = max(
            map(lambda seasno: max(
                map(lambda epno: tvshow_plex[ seasno ][epno]['date aired' ],
                    tvshow_plex[ seasno ] ) ), set( tvshow_plex ) - set([0])))
        
        html = BeautifulSoup("""
        <html>
        <p>Summary for %s.</p>
        <p>%s.</p>
        <p>%02d episodes, %02d missing.</p>
        <p>First episode aired on %s.</p>
        <p>Last episode aired on %s.</p>
        <p>
        </html>""" % ( seriesName, show_status,
                       num_total, num_missing,
                       minDate.strftime( '%B %d, %Y' ),
                       maxDate.strftime( '%B %d, %Y' ) ), 'lxml' )
        body_elem = html.find_all('body')[0]
        if len( overview ) != 0:
            summary_tag = html.new_tag("p")
            summary_tag.string = overview
            body_elem.append( summary_tag )
        average_duration_in_secs = numpy.array(
            reduce(lambda x,y: x+y,
                   list(map(lambda seasno: list(
                       map(lambda epno: tvshow_plex[ seasno ][ epno ][ 'duration' ],
                           tvshow_plex[ seasno ] ) ), tvshow_plex ) ) ) ).mean( )
        average_size_in_bytes = numpy.array(
            reduce(lambda x,y: x+y,
                   list(map(lambda seasno: list(
                       map(lambda epno: tvshow_plex[ seasno ][ epno ][ 'size' ],
                           tvshow_plex[ seasno ] ) ), tvshow_plex ) ) ) ).mean( )
        dur_tag = html.new_tag( "p" )
        dur_tag.string = "average duration of %02d episodes: %s." % (
            num_total, plexcore.get_formatted_duration( average_duration_in_secs ) )
        siz_tag = html.new_tag( "p" )
        siz_tag.string = "average size of %02d episodes: %s." % (
            num_total, plexcore.get_formatted_size( average_size_in_bytes ) )
        body_elem.append( dur_tag )
        body_elem.append( siz_tag )
        return html.prettify( )

    @classmethod
    def getSummaryImg( cls, imageURL, verify = True ):
        if imageURL is None: return None
        try:
            response = requests.get( imageURL, verify = verify )
            if response.status_code != 200: return None
            return response.content
        except: return None

    def screenGrab( self ):
        fname = str( QFileDialog.getSaveFileName(
            self, 'Save Screenshot',
            os.path.expanduser( '~' ),
            filter = '*.png' ) )
        if len( os.path.basename( fname.strip( ) ) ) == 0:
            return
        if not fname.lower( ).endswith( '.png' ):
            fname = fname + '.png'
        qpm = QPixmap.grabWidget( self )
        qpm.save( fname )

    def processTVShow( self, seriesName ):
        assert( seriesName in self.tvshow_dict )
        assert( seriesName in self.tvdata_on_plex )
        if seriesName not in self.summaryShowInfo:
            self.summaryShowInfo[ seriesName ] = TVDBGUI.getShowSummary(
                seriesName, self.tvshow_dict, self.tvdata_on_plex,
                self.missing_eps )
            
        if seriesName not in self.showImages:
            self.showImages[ seriesName ] = TVDBGUI.getSummaryImg(
                self.tvshow_dict[ seriesName ].imageURL, verify = self.verify )

        showSummary = self.summaryShowInfo[ seriesName ]
        showImg = self.showImages[ seriesName ]
        #
        ## now put this into summary image on left, summary info on right
        if showImg is not None:
            qpm = QPixmap.fromImage( QImage.fromData( showImg ) )
            qpm = qpm.scaledToWidth( 200 )
            self.summaryShowImage.setPixmap( qpm )
        else: self.summaryShowImage.setPixmap( )
        self.summaryShowInfoArea.setHtml( showSummary )
        
                                
    def __init__( self, token, fullURL, tvdata_on_plex = None,
                  tvshow_dict = None, verify = True ):
        super( TVDBGUI, self ).__init__( )
        time0 = time.time( )
        #cdg = CustomDialog( self )
        dtnow = datetime.datetime.now( )
        mytxt = '0, started loading in data on %s.' % (
            datetime.datetime.now( ).strftime( '%B %d, %Y @ %I:%M:%S %p' ) )
        #cdg.addText( mytxt )
        print( mytxt )
        libraries_dict = plexcore.get_libraries( fullURL = fullURL, token = token )
        if not any(map(lambda value: 'TV' in value, libraries_dict.values( ) ) ):
            raise ValueError( 'Error, could not find TV shows.' )
        self.key = max(map(lambda key: 'TV' in libraries_dict[ key ], libraries_dict ) )
        mytxt = '1, found TV library in %0.3f seconds.' % ( time.time( ) - time0 )
        #cdg.addText( mytxt )
        print( mytxt )
        if tvdata_on_plex is None:
            tvdata_on_plex = plexcore._get_library_data_show(
                self.key, fullURL = fullURL, token = token )
        if tvdata_on_plex is None:
            raise ValueError( 'Error, could not find TV shows on the server.' )
        self.tvdata_on_plex = tvdata_on_plex
        mytxt = '2, loaded TV data from Plex server in %0.3f seconds.' % (
            time.time( ) - time0 )
        #cdg.addText( mytxt )
        print( mytxt )
        #
        showsToExclude = plextvdb.get_shows_to_exclude( tvdata_on_plex )
        if tvshow_dict is None:
            tvshow_dict = TVShow.create_tvshow_dict(
                self.tvdata_on_plex, verify = verify )
        self.tvshow_dict = tvshow_dict
        mytxt = '3, loaded TV data from TVDB and TMDB in %0.3f seconds.' % (
            time.time( ) - time0 )
        #cdg.addText( mytxt )
        print( mytxt )
        mytxt = '4, finished loading in all data on %s.' % (
            datetime.datetime.now( ).strftime( '%B %d, %Y @ %I:%M:%S %p' ) )
        #cdg.addText( mytxt )
        print( mytxt )
        #cdg.close( )
        #
        ## now do the did_end and missing_eps
        self.did_end = { }
        self.missing_eps = { }
        for seriesName in self.tvdata_on_plex:
            if seriesName not in self.tvshow_dict:
                self.did_end[ seriesName ] = True
                self.missing_eps[ seriesName ] = [ ]
                continue
            tvshow = self.tvshow_dict[ seriesName ]                
            self.did_end[ seriesName ] = tvshow.statusEnded
            if seriesName in showsToExclude:
                self.missing_eps[ seriesName ] = [ ]
                continue
            missing_eps = reduce(lambda x,y: x+y,
                map(lambda seasno: list(map(lambda epno: ( seasno, epno ),
                    set( tvshow.seasonDict[ seasno ].episodes ) -
                                            set( self.tvdata_on_plex[ seriesName ][ seasno ] ) ) ),
                    set( tvshow.seasonDict ) & set( self.tvdata_on_plex[ seriesName ] ) - set([0]) ) )
            self.missing_eps[ seriesName ] = missing_eps
                                  
        #
        self.verify = verify
        #
        print('TVDBGUI: took %0.3f seconds to get tvdata_on_plex' %
              ( time.time( ) - time0 ) )
        self.instantiatedTVShows = { }
        self.dt = datetime.datetime.now( ).date( )
        self.filterOnTVShows = QLineEdit( '' )
        self.setWindowTitle( 'The List of TV Shows on the Plex Server' )
        self.showImages = { }
        self.summaryShowInfo = { }
        #
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        self.refreshButton = QPushButton( "REFRESH TV SHOWS" )
        #
        self.tm = TVDBTableModel( self )
        self.tv = TVDBTableView( self )
        self.tm.fillOutCalculation( )
        topWidget = QWidget( )
        topLayout = QGridLayout( )
        topWidget.setLayout( topLayout )
        topLayout.addWidget( QLabel( 'TV SHOW FILTER' ), 0, 0, 1, 1 )
        topLayout.addWidget( self.filterOnTVShows, 0, 1, 1, 3 )
        topLayout.addWidget( self.refreshButton, 0, 4, 1, 3 )
        myLayout.addWidget( self.tv )
        myLayout.addWidget( topWidget )
        #
        botWidget = QWidget( )
        botLayout = QHBoxLayout( )
        botWidget.setLayout( botLayout )
        self.summaryShowImage = QLabel( )
        self.summaryShowImage.setFixedWidth( 200 )
        botLayout.addWidget( self.summaryShowImage )
        self.summaryShowInfoArea = QTextEdit( )
        self.summaryShowInfoArea.setReadOnly( True )
        botLayout.addWidget( self.summaryShowInfoArea )
        myLayout.addWidget( botWidget )
        #
        ## set size, make sure not resizable
        self.setStyleSheet("""
        QWidget {
        font-family: Consolas;
        font-size: %d;
        }""" % ( int( 11 * 1.0 ) ) )
        self.setFixedWidth( self.tv.frameGeometry( ).width( ) * 1.05 )
        self.setFixedHeight( 800 )
        #
        ## connect actions
        self.filterOnTVShows.textChanged.connect( self.tm.setFilterString )
        self.refreshButton.clicked.connect( self.refreshTVShows ) ## don't do this yet
        #
        ## global actions
        quitAction = QAction( self )
        quitAction.setShortcuts( [ 'Ctrl+Q', 'Esc' ] )
        quitAction.triggered.connect( sys.exit )
        self.addAction( quitAction )
        #
        printAction = QAction( self )
        printAction.setShortcut( 'Shift+Ctrl+P' )
        printAction.triggered.connect( self.screenGrab )
        self.addAction( printAction )
        #
        # self.setSize( 800, 800 )
        self.show( )

    def refreshTVShows( self, doLocal = True ):
        time0 = time.time( )
        fullURL, token = plexcore.checkServerCredentials(
            doLocal = doLocal )
        if token is None:
            logging.debug("ERROR, COULD NOT GET NEW TOKEN.")
            return
        self.tvdata_on_plex = plexcore._get_library_data_show(
            self.key, fullURL = fullURL, token = token )
        self.tvshows_dict = TVShow.create_tvshow_dict(
            self.tvdata_on_plex, verify = self.verify )
        self.did_end = { }
        self.missing_eps = { }
        for seriesName in self.tvdata_on_plex:
            if seriesName not in self.tvshow_dict:
                self.did_end[ seriesName ] = True
                self.missing_eps[ seriesName ] = [ ]
                continue
            tvshow = self.tvshow_dict[ seriesName ]                
            self.did_end[ seriesName ] = tvshow.statusEnded
            if seriesName in showsToExclude:
                self.missing_eps[ seriesName ] = [ ]
                continue
            missing_eps = reduce(lambda x,y: x+y,
                map(lambda seasno: list(map(lambda epno: ( seasno, epno ),
                    set( tvshow.seasonDict[ seasno ].episodes ) -
                                            set( self.tvdata_on_plex[ seriesName ][ seasno ] ) ) ),
                    set( tvshow.seasonDict ) & set( self.tvdata_on_plex[ seriesName ] ) - set([0]) ) )
            self.missing_eps[ seriesName ] = missing_eps
        self.tm.fillOutCalculation( )
        logging.debug( 'refreshed all TV shows in %0.3f seconds.' % (
            time.time( ) - time0 ) )

class TVDBTableView( QTableView ):
    def __init__( self, parent ):
        super( TVDBTableView, self ).__init__( parent )
        self.parent = parent
        self.proxy = TVDBQSortFilterProxyModel( self, self.parent.tm )
        self.setModel( self.proxy )
        self.selectionModel( ).currentRowChanged.connect(
            self.processCurrentRow )
        #
        self.setShowGrid( True )
        self.verticalHeader( ).setResizeMode( QHeaderView.Fixed )
        self.horizontalHeader( ).setResizeMode( QHeaderView.Fixed )
        self.setSelectionBehavior( QAbstractItemView.SelectRows )
        self.setSelectionMode( QAbstractItemView.SingleSelection ) # single row        
        self.setSortingEnabled( True )
        #
        self.setColumnWidth(0, 210 )
        self.setColumnWidth(1, 120 )
        self.setColumnWidth(2, 120 )
        self.setColumnWidth(3, 120 )
        self.setColumnWidth(4, 120 )
        self.setColumnWidth(5, 120 )
        self.setFixedWidth( 1.05 * ( 210 * 1 + 120 * 5 ) )
        toBotAction = QAction( self )
        toBotAction.setShortcut( 'End' )
        toBotAction.triggered.connect( self.scrollToBottom )
        self.addAction( toBotAction )
        #
        toTopAction = QAction( self )
        toTopAction.setShortcut( 'Home' )
        toTopAction.triggered.connect( self.scrollToTop )
        self.addAction( toTopAction )
        #
        ## now do the same thing for contextMenuEvent with action
        popupAction = QAction( self )
        popupAction.setShortcut( 'Ctrl+Shift+S' )
        popupAction.triggered.connect( self.popupTVSeries )
        self.addAction( popupAction )

    def contextMenuEvent( self, event ):
        menu = QMenu( self )
        infoAction = QAction( 'Information', menu )
        infoAction.triggered.connect( self.popupTVSeries )
        menu.addAction( infoAction )
        menu.popup( QCursor.pos( ) )

    def popupTVSeries( self ):
        index_valid_proxy = max(filter(lambda index: index.column( ) == 0,
                                       self.selectionModel().selectedIndexes( ) ) )
        index_valid = self.proxy.mapToSource( index_valid_proxy )
        self.parent.tm.infoOnTVSeriesAtRow( index_valid.row( ) )

    def processCurrentRow( self, newIndex, oldIndex = None ):
        row_valid = self.proxy.mapToSource( newIndex ).row( )
        #
        ## episode data emit this row here
        self.parent.tm.emitRowSelected.emit( row_valid )

class TVDBQSortFilterProxyModel( QSortFilterProxyModel ):
    def __init__( self, parent, model ):
        super( TVDBQSortFilterProxyModel, self ).__init__( parent )
        self.setSourceModel( model )
        model.emitFilterChanged.connect( self.filterChanged )

    def sort( self, ncol, order ):
        self.sourceModel( ).sort( ncol, order )

    def filterAcceptsRow( self, rowNumber, sourceParent ):
        return self.sourceModel( ).filterRow( rowNumber )

class TVDBTableModel( QAbstractTableModel ):
    _headers = [ "TV Series", "Start Date", "Last Date",
                 "Seasons", "Episodes", "Missing" ]
    emitFilterChanged = pyqtSignal( )
    emitRowSelected = pyqtSignal( int )
    
    def __init__( self, parent = None ):
        super( TVDBTableModel, self ).__init__( parent )
        self.parent = parent # is the GUI that contains all the data
        self.actualTVSeriesData = [ ]
        self.sortColumn = 0
        self.filterStatus = 0 # 0, show everything; 1, show only tv series w/missing eps
        self.filterRegexp = QRegExp(
            '.', Qt.CaseInsensitive, QRegExp.RegExp )
        self.emitRowSelected.connect( self.summaryOnTVShowAtRow )
        self.fillOutCalculation( )

    def infoOnTVSeriesAtRow( self, actualRow ):
        seriesData = self.actualTVSeriesData[ actualRow ]
        seriesName = seriesData[ 'seriesName' ]
        self.parent.setEnabled( False )
        if seriesName not in self.parent.instantiatedTVShows:
            self.parent.instantiatedTVShows[ seriesName ] = TVDBShowGUI(
                seriesName, self.parent.tvdata_on_plex,
                self.parent.tvshow_dict, parent = self.parent,
                verify = self.parent.verify )
        tvdbsi = self.parent.instantiatedTVShows[ seriesName ]
        tvdbsi.setEnabled( True )
        result = tvdbsi.exec_( )
        self.parent.setEnabled( True )

    def summaryOnTVShowAtRow( self, actualRow ):
        self.parent.processTVShow(
            self.actualTVSeriesData[
                actualRow ][ 'seriesName' ] )

    def filterRow( self, rowNumber ):
        data = self.actualTVSeriesData[ rowNumber ]        
        if self.filterStatus == 0:
            return self.filterRegexp.indexIn( data[ 'seriesName' ] ) != -1
        elif self.filterStatus == 1:
            missing = data[ 'numMissing' ]
            return len( missing ) > 0
        else: return False
            
    def setFilterStatus( self, filterStatus ):
        self.filterStatus = filterStatus
        self.sort( 0, Qt.AscendingOrder )
        self.emitFilterChanged.emit( )
        
    def setFilterString( self, text ):
        mytext = str( text ).strip( )
        if len( mytext ) == 0:
            mytext = '.'
        self.filterRegexp = QRegExp(
            mytext, Qt.CaseInsensitive, QRegExp.RegExp )
        self.emitFilterChanged.emit( )
        
    def rowCount( self, parent ):
        return len( self.actualTVSeriesData )

    def columnCount( self, parent ):
        return 6

    def headerData( self, col, orientation, role ):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[ col ]
        return None

    def fillOutCalculation( self ):
        #
        ## now put in the actual data.
        self.actualTVSeriesData = [ ]
        for seriesName in sorted( self.parent.tvdata_on_plex ):
            startDate = min( map(
                lambda seasno: min(
                    map(lambda epno: self.parent.tvdata_on_plex[ seriesName ][ seasno ][ epno ][ 'date aired' ],
                        self.parent.tvdata_on_plex[ seriesName ][ seasno ] ) ),
                self.parent.tvdata_on_plex[ seriesName ] ) )
            endDate = max( map(
                lambda seasno: max(
                    map(lambda epno: self.parent.tvdata_on_plex[ seriesName ][ seasno ][ epno ][ 'date aired' ],
                        self.parent.tvdata_on_plex[ seriesName ][ seasno ] ) ),
                self.parent.tvdata_on_plex[ seriesName ] ) )
            seasons = len( self.parent.tvdata_on_plex[ seriesName ] )
            numEps = sum( map(
                lambda seasno: len( self.parent.tvdata_on_plex[ seriesName ][ seasno ] ),
                self.parent.tvdata_on_plex[ seriesName ] ) )
            dat = { 'seriesName' : seriesName,
                    'startDate' : startDate,
                    'endDate' : endDate,
                    'seasons' : seasons,
                    'numEps' : numEps,
                    'didEnd' : self.parent.did_end[ seriesName ],
                    'numMissing' : 0 }
            if seriesName in self.parent.missing_eps:
                dat[ 'numMissing' ] = len( self.parent.missing_eps[ seriesName ] )
            self.actualTVSeriesData.append( dat )

        #
        ## first remove all rows that exist
        initRowCount = self.rowCount( None )
        self.beginRemoveRows( QModelIndex( ), 0, initRowCount - 1 )
        self.endRemoveRows( )
        #
        ## now add in the data
        self.beginInsertRows( QModelIndex( ), 0, len( self.actualTVSeriesData ) - 1 )
        self.endInsertRows( )
        self.sort(0, Qt.AscendingOrder ) # triggers the fillout of rows and columns
        
    def sort( self, col, order ):
        self.layoutAboutToBeChanged.emit( )
        self.sortColumn = col
        self.layoutChanged.emit( )
        
    #
    ## engine code, actually show data in the table
    def data( self, index, role ):
        if not index.isValid( ):
            return ""
        row = index.row( )
        col = index.column( )
        data = self.actualTVSeriesData[ row ].copy( )
        #
        ## color background role
        if role == Qt.BackgroundRole:
            if data[ 'didEnd' ]:
                return QBrush( QColor( '#282a36' ) ) # change using cwheet to yellow-like
            else: return QBrush( QColor( '#6272a4' ) )
        elif role == Qt.DisplayRole:
            if col == 0: # series name
                return data[ 'seriesName' ]
            elif col == 1: # start date
                return data[ 'startDate' ].strftime('%Y %b %d')
            elif col == 2: # end date
                return data[ 'endDate' ].strftime('%Y %b %d')
            elif col == 3: # number of seasons
                return data[ 'seasons' ]
            elif col == 4: # number of eps
                return data[ 'numEps' ]
            elif col == 5:
                return data[ 'numMissing' ]

class TVDBShowGUI( QDialog ):
    def __init__( self, seriesName, tvdata, tvshow_dict,
                  parent = None, verify = True ):
        super( TVDBShowGUI, self ).__init__( parent )
        if parent is not None:
            assert( isinstance( parent, QDialog ) )
        assert( seriesName in tvdata )
        assert( seriesName in tvshow_dict )
        self.setWindowTitle( seriesName )
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #
        ## top widget contains a set of seasons in a QComboBox
        topWidget = QWidget( )
        topLayout = QHBoxLayout( )
        topWidget.setLayout( topLayout )
        topLayout.addWidget( QLabel( "SEASON" ) )
        seasonSelected = QComboBox( self )
        seasonSelected.addItems(
            list(map(lambda seasno: '%d' % seasno,
                     filter(lambda season: season != 0,
                            sorted( tvdata[ seriesName ] ) ) ) ) )
        seasonSelected.setEnabled( True )
        seasonSelected.setEditable( False )
        seasonSelected.setCurrentIndex( 0 )
        topLayout.addWidget( seasonSelected )
        myLayout.addWidget( topWidget )
        #
        ## now a stacked layout
        self.seasonWidget = QStackedWidget( )
        self.series_widgets = { }
        for season in filter(lambda season: season != 0,
                             sorted( tvdata[ seriesName ] ) ): 
            num_seasons = len(list(filter(lambda season: season != 0,
                                          sorted( tvdata[ seriesName ]))))
            self.series_widgets[ season ] = plextvdb_season_gui.TVDBSeasonGUI(
                seriesName, season, tvdata, tvshow_dict, verify = verify,
                parent = parent )
            self.seasonWidget.addWidget( self.series_widgets[ season ] )
            logging.debug( 'added %s season %d / %d.' % (
                seriesName, season, num_seasons ) )
        first_season = min( self.series_widgets )
        myLayout.addWidget( self.seasonWidget )
        #
        ## set size
        self.setFixedWidth( self.series_widgets[ first_season ].sizeHint( ).width( ) * 1.05 )
        self.setFixedHeight( 800 )
        #
        ## connect
        seasonSelected.installEventFilter( self )
        seasonSelected.currentIndexChanged.connect( self.selectSeason )
        quitAction = QAction( self )
        quitAction.setShortcuts( [ 'Ctrl+Q', 'Esc' ] )
        quitAction.triggered.connect( self.close )
        self.addAction( quitAction )
        #
        ##
        self.show( )

    def selectSeason( self, idx ):
        self.seasonWidget.setCurrentIndex( idx )
