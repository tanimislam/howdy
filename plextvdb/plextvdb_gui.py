from PyQt4.QtGui import *
from PyQt4.QtCore import *
import os, sys, numpy, glob, datetime, logging
from . import mainDir, plextvdb, get_token
sys.path.append( mainDir )
from plexcore import plexcore

class TVDBGUI( QWidget ):
    mySignal = pyqtSignal( list )

    def __init__( self, token, fullURL ):
        libraries_dict = plexcore.get_libraries( fullURL = fullURL, token = token )
        if not any(map(lambda value: 'TV' in value, libraries_dict.values( ) ) ):
            raise ValueError( 'Error, could not find TV shows.' )
        key = max(map(lambda key: 'TV' in libraries_dict[ key ], libraries_dict ) )
        dt0 = datetime.datetime.now( )
        tvdata_on_plex = plexcore._get_library_data_show( key, fullURL = fullURL, token = token )
        if tvdata_on_plex is None:
            raise ValueError( 'Error, could not find TV shows in the server.' )
        logging.debug('TVDBGUI: took %s to get tvdata_on_plex' % str( datetime.datetime.now( ) - dt0 ) )
        self.dt = datetime.datetime.now( ).date( )
        self.tvdata_on_plex = tvdata_on_plex
        self.tm = TVDBShowsTableModel( self )
        self.tv = TVDBShowsTableView( self )
        self.filterOnTVShows = QLineEdit( '' )
        #
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #
        topWidget = QWidget( )
        topLayout = QHBoxLayout( )
        topWidget.setLayout( topLayout )
        topLayout.addWidget( QLabel( 'TV SHOW FILTER' ) )
        topLayout.addWidget( self.filterOnTVShows )
        myLayout.addWidget( topWidget )
        #
        myLayout.addWidget( self.tv )
        #
        self.setSize( 800, 800 )
        self.show( )

class TVDBShowsTableView( QTableView ):
    def __init__( self, parent ):
        super( TVDBShowsTableView, self ).__init__( parent )
        self.parent = parent
        self.proxy = TVDBShowsQSortFilterProxyModel( self, self.parent.tm )
        self.setModel( self.proxy )
        #
        self.setShowGrid( True )
        self.setVerticalHeader( ).setResizeMode( QHeaderView.Fixed )
        self.horizontalHeader( ).setResizeMode( QHeaderView.Fixed )
        self.setSelectionBehavior( QAbstractItemView.SelectRows )
        self.setSelectionMode( QAbstractItemView.SingleSelection ) # single row        
        self.setSortingEnabled( True )
        #
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
                 "Seasons", "Non/Tot Episodes" ]
    emitFilterChanged = pyqtSignal( )
    
    def __init__( self, parent = None ):
        super( TVDBShowsTableModel, self ).__init__( parent )
        self.parent = parent
        self.actualTVSeriesData = [ ]
        self.sortColumn = 0
        self.filterStatus = 0 # 0, show everything; 1, show only tv series w/missing eps
        self.filterRegexp = QRegExp( '.', Qt.CaseInsensitive,
                                     QRegExp.RegExp )

    def infoOnTVSeriesAtRow( self, actualRow ):
        seriesName, seriesData, missingEps = self.actualTVSeriesData[ actualRow ]
        tvdbsi = TVDBSeriesInfo( seriesName, seriesData, missingEps )
        result = tvdbsi.exec_( )

    def filterRow( self, rowNumber ):
        if self.filterStatus == 0:
            return self.filterRegexp.indexIn( self.actualTVSeriesData[ rowNumber ][ 0 ] ) != -1
        elif self.filterStatus == 1:
            _, _, missing = self.actualTVSeriesData[ rowNumber ]
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
        return 5

    def headerData( self, col, orientation, role ):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[ col ]
        return None

    def fillOutCalculation( tvSeriesNames, tvSeriesData, missings ):
        assert( len( tvSeriesNames ) == len( tvSeriesData ) )
        assert( len( tvSeriesNames ) == len( missings ) )
        #
        ## first remove all rows that exist
        initRowCount = self.rowCount( None )
        self.beginRemoveRows( QModelIndex( ), 0, initRowCount - 1 )
        self.endRemoveRows( )
        #
        ## now add in the data
        self.beginInsertRows( QModelIndex( ), 0, len( tvSeriesData ) - 1 )
        self.actualTVSeriesData = zip( tvSeriesNames, tvSeriesData, missings )
        self.endInsertRows( )
        self.sort(0, Qt.AscendingOrder )
        
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
        tvSeriesName, tvSeries, missing = self.actualTVSeriesData[ row ]
        #
        ## color background role
        if role == Qt.BackgroundRole:
            if tvSeries.statusEnded:
                return QBrush( 'yellow' ) # change using cwheet to yellow-like
            else: return QBrush( 'pink' )
        elif role == Qt.DisplayRole:
            if col == 0: # series name
                return tvSeriesName
            elif col == 1: # start date
                return tvSeries.startDate.strftime('%Y %b %d')
            elif col == 2: # end date
                if tvSeries.statusEnded:
                    return tvSeries.endDate.strftime('%Y %b %d')
                else: return QVariant( "" )
            elif col == 3: # number of seasons
                numSeasons = len(filter(lambda seasno: seasno != 0,
                                        tvSeries.seasDict.keys( ) ) )
                return numSeasons
            elif col == 4: # number missing, number of eps
                validSeasons = set( tvSeries.seasDict.key( ) ) - set([0,])
                numEpsTot = sum(map(lambda season: len( tvSeries.seasDict[ season ].keys( ) ),
                                    validSeasons) )
                return "%d / %d" % ( len(missing), numEpsTot )
                
