from PyQt4.QtGui import *
from PyQt4.QtCore import *
import os, sys, numpy, glob, datetime, time
import multiprocessing, logging, requests
from PIL import Image
from io import BytesIO
from . import plextvdb, mainDir
from plexcore import plexcore
from plextmdb import plextmdb

class TVShow( object ):
    
    @classmethod
    def _create_image( cls, imageURL ):
        try:
            response = requests.get( imageURL )
            if response.status_code != 200: return None
            return Image.open( BytesIO( response.content ) )
        except: return None
    
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
        
    def __init__( self, seriesName, token, verify = True ):
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
        self.imageURL, status = plextvdb.get_series_image( self.seriesId, token, verify = verify )
        self.img = TVShow._create_image( self.imageURL )
        
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
                    self.img = Image.open( BytesIO( response.content ) )
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

class TVDBGUI( QWidget ):
    mySignal = pyqtSignal( list )
    tvSeriesSendList = pyqtSignal( list )
    tvSeriesRefreshRows = pyqtSignal( list )

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
    
    def __init__( self, token, fullURL, tvdata_on_plex = None, missing_eps = None,
                  did_end = None ):
        super( TVDBGUI, self ).__init__( )
        libraries_dict = plexcore.get_libraries( fullURL = fullURL, token = token )
        if not any(map(lambda value: 'TV' in value, libraries_dict.values( ) ) ):
            raise ValueError( 'Error, could not find TV shows.' )
        self.key = max(map(lambda key: 'TV' in libraries_dict[ key ], libraries_dict ) )
        time0 = time.time( )
        if tvdata_on_plex is None:
            tvdata_on_plex = plexcore._get_library_data_show(
                self.key, fullURL = fullURL, token = token )
        if tvdata_on_plex is None:
            raise ValueError( 'Error, could not find TV shows on the server.' )
        self.tvdata_on_plex = tvdata_on_plex
        #
        showsToExclude = plextvdb.get_shows_to_exclude( tvdata_on_plex )
        if missing_eps is None:
            missing_eps = plextvdb.get_remaining_episodes(
                tvdata_on_plex, showSpecials = False,
                showsToExclude = showsToExclude )
        else:
            # find episodes here not in there
            showsToRemove = set( missing_eps ) - set( tvdata_on_plex )
            for show in showsToRemove: missing_eps.pop( show )
            showsToRemove = set( missing_eps ) & set( showsToExclude )
            for show in showsToRemove: missing_eps.pop( show )
        self.missing_eps = missing_eps
        if did_end is None:
            did_end = plextvdb.get_all_series_didend(
                self.tvdata_on_plex )
        else:
            what_missing = set( did_end ) - set( self.tvdata_on_plex )
            for seriesName in what_missing: did_end.pop( seriesName )
        self.did_end = did_end
        assert( set( self.did_end ) == set( self.tvdata_on_plex ) )
        #
        print('TVDBGUI: took %0.3f seconds to get tvdata_on_plex' %
              ( time.time( ) - time0 ) )
        self.token = token
        self.dt = datetime.datetime.now( ).date( )
        self.tm = TVDBShowsTableModel( self )
        self.tv = TVDBShowsTableView( self )
        self.filterOnTVShows = QLineEdit( '' )
        self.setWindowTitle( 'The List of TV Shows on the Plex Server' )
        self.tm.fillOutCalculation( )
        #
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        self.refreshButton = QPushButton( "REFRESH TV SHOWS" )
        #
        topWidget = QWidget( )
        topLayout = QGridLayout( )
        topWidget.setLayout( topLayout )
        topLayout.addWidget( QLabel( 'TV SHOW FILTER' ), 0, 0, 1, 1 )
        topLayout.addWidget( self.filterOnTVShows, 0, 1, 1, 3 )
        topLayout.addWidget( self.refreshButton, 0, 4, 1, 3 )
        myLayout.addWidget( topWidget )
        myLayout.addWidget( self.tv )
        #
        ## set size, make sure not resizable
        self.setStyleSheet("""
        QWidget {
        font-family: Consolas;
        font-size: %d;
        }""" % ( int( 11 * 1.0 ) ) )
        self.setFixedWidth( self.tv.frameGeometry( ).width( ) * 1.05 )
        #
        ## connect actions
        self.filterOnTVShows.textChanged.connect( self.tm.setFilterString )
        # self.refreshButton.clicked.connect( self.refreshTVShows ) ## don't do this yet
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

    def refreshTVShows( self ):
        fullURL, token = plexcore.checkServerCredentials( doLocal = True )
        if token is None:
            logging.debug("ERROR, COULD NOT GET NEW TOKEN.")
            return
        self.tvdata_on_plex = plexcore._get_library_data_show(
            self.key, fullURL = fullURL, token = token )
        showsToExclude = plextvdb.get_shows_to_exclude(
            self.tvdata_on_plex )
        self.missing_eps = plextvdb.get_remaining_episodes(
                self.tvdata_on_plex, showSpecials = False,
                showsToExclude = showsToExclude )
        self.did_end = plextvdb.get_all_series_didend(
            self.tvdata_on_plex )
        assert( set( self.did_end ) == set( self.tvdata_on_plex ) )
        self.tm.fillOutCalculation( )

class TVDBShowsTableView( QTableView ):
    def __init__( self, parent ):
        super( TVDBShowsTableView, self ).__init__( parent )
        self.parent = parent
        self.proxy = TVDBShowsQSortFilterProxyModel( self, self.parent.tm )
        self.setModel( self.proxy )
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
        self.tm.infoOnTVSeriesAtRow( index_valid.row( ) )

class TVDBShowsQSortFilterProxyModel( QSortFilterProxyModel ):
    def __init__( self, parent, model ):
        super( TVDBShowsQSortFilterProxyModel, self ).__init__( parent )
        self.setSourceModel( model )
        model.emitFilterChanged.connect( self.filterChanged )

    def sort( self, ncol, order ):
        self.sourceModel( ).sort( ncol, order )

    def filterAcceptsRow( self, rowNumber, sourceParent ):
        return self.sourceModel( ).filterRow( rowNumber )

class TVDBShowsTableModel( QAbstractTableModel ):
    _headers = [ "TV Series", "Start Date", "Last Date",
                 "Seasons", "Episodes", "Missing" ]
    emitFilterChanged = pyqtSignal( )
    
    def __init__( self, parent = None ):
        super( TVDBShowsTableModel, self ).__init__( parent )
        self.parent = parent # is the GUI that contains all the data
        self.actualTVSeriesData = [ ]
        self.sortColumn = 0
        self.filterStatus = 0 # 0, show everything; 1, show only tv series w/missing eps
        self.filterRegexp = QRegExp(
            '.', Qt.CaseInsensitive, QRegExp.RegExp )
        self.fillOutCalculation( )

    def infoOnTVSeriesAtRow( self, actualRow ):
        seriesName, seriesData, missingEps = self.actualTVSeriesData[ actualRow ]
        tvdbsi = TVDBSeriesInfo( seriesName, seriesData, missingEps )
        result = tvdbsi.exec_( )

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
        self.filterRegexp = QRegExp( mytext,
                                     Qt.CaseInsensitive,
                                     QRegExp.RegExp )
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
