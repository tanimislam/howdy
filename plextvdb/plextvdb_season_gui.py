from PyQt4.QtGui import *
from PyQt4.QtCore import *
from bs4 import BeautifulSoup
import copy, numpy, sys, requests, logging
from . import plextvdb
from plexcore import plexcore
from plextmdb import plextmdb

class TVDBSeasonGUI( QDialog ):

    @classmethod
    def processSeasonSummary( cls, season, episodes ):
        if len( episodes ) == 0: return ""
        eps_exist = list(filter(lambda epno: episodes[epno]['have_episode'] == True,
                                episodes ) )
        minDate = min(map(lambda episode: episode['date aired'], episodes.values( )  ) )
        maxDate = max(map(lambda episode: episode['date aired'], episodes.values( )  ) )
        html = BeautifulSoup("""
        <html>
          <p>%02d episodes in season %02d.</p>
          <p>%02d episodes in season %02d on Plex Server.</p>
          <p>first episode aired on %s.</p>
          <p>last episode aired on %s.</p>
        </html>""" % ( len( episodes ), season, len( eps_exist ), season,
                       minDate.strftime( '%B %d, %Y' ),
                       maxDate.strftime( '%B %d, %Y' ) ), "lxml" )
        body_elem = html.find_all('body')[0]
        if len( eps_exist ) != 0:
            average_duration_season_in_secs = numpy.array(
                list(map(lambda epno: episodes[ epno ][ 'duration' ],
                         eps_exist ) ) ).mean( )
            average_size_duration_in_bytes = numpy.array(
                list(map(lambda epno: episodes[ epno ][ 'size' ],
                         eps_exist ) ) ).mean( )
            #
            dur_tag = html.new_tag( "p" )
            dur_tag.string = "average duration of season %02d episodes: %s." % (
                season, plexcore.get_formatted_duration( average_duration_season_in_secs ) )
            siz_tag = html.new_tag( "p" )
            siz_tag.string = "average size of season %02d episodes: %s." % (
                season, plexcore.get_formatted_size( average_size_duration_in_bytes ) )
            body_elem.append( dur_tag )
            body_elem.append( siz_tag )
        return html.prettify( )

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

    def __init__( self, seriesName, seasno,
                  plex_tv_data, tvshow_dict, verify = True, parent = None ):
        super( TVDBSeasonGUI, self ).__init__( parent )
        self.parent = parent
        assert( seriesName in plex_tv_data )
        assert( seriesName in tvshow_dict )
        assert( seasno in plex_tv_data[ seriesName ] )
        assert( seasno in tvshow_dict[ seriesName ].seasonDict )
        episodes = plex_tv_data[ seriesName ][ seasno ].copy( )
        tvdb_season_info = tvshow_dict[ seriesName ].seasonDict[ seasno ]
        assert( tvdb_season_info.seasno == seasno )
        #
        self.setWindowTitle( '%s season %02d' % ( seriesName, seasno ) )
        #
        ## put in image and season number and seriesName 
        #
        ## put in overview information for episodes I have
        for epno in set( tvdb_season_info.episodes ) & set( episodes ):
            tvdb_epinfo = tvdb_season_info.episodes[ epno ]
            episodes[ epno ][ 'seriesName' ] = seriesName
            episodes[ epno ][ 'season' ] = seasno
            episodes[ epno ][ 'have_episode' ] = True
            episodes[ epno ][ 'episode' ] = epno
            episodes[ epno ][ 'overview' ] = tvdb_epinfo[ 'overview' ]
        #
        ## fill out those episodes don't have
        for epno in set( tvdb_season_info.episodes ) - set( episodes ):
            tvdb_epinfo = tvdb_season_info.episodes[ epno ]
            episodes[ epno] = {
                'seriesName' : seriesName,
                'season' : seasno,
                'have_episode' : False,
                'episode' : epno,
                'title' : tvdb_epinfo[ 'title' ],
                'date aired' : tvdb_epinfo[ 'airedDate' ],
                'overview' : tvdb_epinfo[ 'overview' ]
            }
        #
        ## main layout
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )        
        #
        ## now top widget with grid layout
        topWidget = QWidget( )
        topLayout = QHBoxLayout( )
        topWidget.setLayout( topLayout )
        leftImageWidget = QLabel( )
        leftImageWidget.setFixedWidth( 200 )
        if tvdb_season_info.imageURL is not None:
            response = requests.get( tvdb_season_info.imageURL,
                                     verify = verify )
            if response.status_code == 200:
                qpm = QPixmap.fromImage(
                    QImage.fromData( response.content ) )
                qpm = qpm.scaledToWidth( 200 )
                leftImageWidget.setPixmap( qpm )
        topLayout.addWidget( leftImageWidget )
        seasonSummaryArea = QTextEdit( )
        seasonSummaryArea.setReadOnly( True )
        #seasonSummaryArea.setLineWrapColumnOrWidth( 185 )
        #seasonSummaryArea.setLineWrapMode(QTextEdit.FixedPixelWidth)
        seasonSummaryArea.setHtml(
            TVDBSeasonGUI.processSeasonSummary( seasno, episodes ) )
        seasonSummaryArea.setFixedWidth( 200 )
        topLayout.addWidget( seasonSummaryArea )
        self.episodeSummaryArea = QTextEdit( )
        self.episodeSummaryArea.setReadOnly( True )
        self.episodeSummaryArea.setFixedWidth( 400 )
        #self.episodeSummaryArea.setLineWrapColumnOrWidth( 400 )
        #self.episodeSummaryArea.setLineWrapMode(QTextEdit.FixedPixelWidth)
        topLayout.addWidget( self.episodeSummaryArea )
        myLayout.addWidget( topWidget )
        #
        ## now the TV EPISODE FILTER thing
        midWidget = QWidget( )
        midLayout = QHBoxLayout( )
        midWidget.setLayout( midLayout )
        midLayout.addWidget( QLabel( 'TV EPISODE FILTER' ) )
        self.filterOnTVEpisodes = QLineEdit( '' )
        midLayout.addWidget( self.filterOnTVEpisodes )
        self.filterStatusComboBox = QComboBox( self )
        self.filterStatusComboBox.addItems([ 'ALL', 'NOT IN PLEX' ])
        self.filterStatusComboBox.setEnabled( True )
        self.filterStatusComboBox.setEditable( False )
        self.filterStatusComboBox.setCurrentIndex( 0 )
        midLayout.addWidget( self.filterStatusComboBox )
        myLayout.addWidget( midWidget )
        #
        ## now put in the table view and table model
        self.tm = TVDBSeasonTableModel( self, episodes )
        self.tv = TVDBSeasonTableView( self )
        #
        ## now add the TV season widget table view
        myLayout.addWidget( self.tv )
        #
        ## now add in signals and slots
        self.filterOnTVEpisodes.textChanged.connect( self.tm.setFilterString )
        self.filterStatusComboBox.installEventFilter( self )
        self.filterStatusComboBox.currentIndexChanged.connect( self.tm.setFilterStatus )
        #
        ## global actions
        #quitAction = QAction( self )
        #quitAction.setShortcuts( [ 'Ctrl+Q' ] )
        #quitAction.triggered.connect( sys.exit )
        #self.addAction( quitAction )
        #
        printAction = QAction( self )
        printAction.setShortcut( 'Shift+Ctrl+P' )
        printAction.triggered.connect( self.screenGrab )
        self.addAction( printAction )
        #
        ## all this for now...
        self.show( )

    def processEpisode( self, episode ):
        seriesName = episode[ 'seriesName' ]
        season = episode[ 'season' ]
        epno = episode[ 'episode' ]
        dateAired = episode[ 'date aired' ]
        overview = episode[ 'overview' ]
        html = BeautifulSoup("""
        <html>
          <p>%s, season %02d, episode %02d.</p>
          <p>aired on %s.</p>
          <p>%s.</p>
        </html>""" % (
            seriesName, season, epno, dateAired.strftime( '%d/%m/%Y' ),
            overview ), 'lxml' )
        body_elem = html.find_all('body')[0]
        if 'duration' in episode:
            dur_tag = html.new_tag( "p" )
            dur_tag.string = "duration: %s." % (
                plexcore.get_formatted_duration( episode[ 'duration' ] ) )
            body_elem.append( dur_tag )
        if 'size' in episode:
            siz_tag = html.new_tag( "p" )
            siz_tag.string = "size: %s." % (
                plexcore.get_formatted_size( episode[ 'size' ] ) )
            body_elem.append( siz_tag )
        self.episodeSummaryArea.setHtml( html.prettify( ) )
#
## column names: episode, name, date
class TVDBSeasonTableView( QTableView ):
    def __init__( self, parent ):
        super( TVDBSeasonTableView, self ).__init__( parent )
        self.parent = parent
        self.proxy = TVDBSeasonQSortFilterProxyModel(
            self, self.parent.tm )
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
        self.setColumnWidth( 0, 160 )
        self.setColumnWidth( 1, 320 )
        self.setColumnWidth( 2, 320 )
        self.setFixedWidth( 800 )
        self.setFixedHeight( 400 )
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

    def processCurrentRow( self, newIndex, oldIndex = None ):
        row_valid = self.proxy.mapToSource( newIndex ).row( )
        #
        ## episode data emit this row here
        self.parent.tm.emitRowSelected.emit( row_valid )
        

class TVDBSeasonQSortFilterProxyModel( QSortFilterProxyModel ):
    def __init__( self, parent, model ):
        super( TVDBSeasonQSortFilterProxyModel, self ).__init__( parent )
        self.setSourceModel( model )
        model.emitFilterChanged.connect( self.filterChanged )

    def sort( self, ncol, order ):
        self.sourceModel( ).sort( ncol, order )
        
    def filterAcceptsRow( self, rowNumber, sourceParent ):
        return self.sourceModel( ).filterRow( rowNumber )

class TVDBSeasonTableModel( QAbstractTableModel ):
    _headers = [ 'Episode', 'Name', 'Date' ]
    emitFilterChanged = pyqtSignal( )
    emitRowSelected = pyqtSignal( int )

    def __init__( self, parent, episodes ):
        super( TVDBSeasonTableModel, self ).__init__( parent )
        self.parent = parent
        self.actualTVSeasonData = [ ]
        self.sortColumn = 0
        self.filterStatus = 'ALL' # ALL, show everything; NOT MINE, show only missing episodes
        self.filterRegexp = QRegExp(
            '.', Qt.CaseInsensitive, QRegExp.RegExp )
        self.fillOutCalculation( episodes )
        self.emitRowSelected.connect( self.infoOnTVEpisodeAtRow )
        
    def infoOnTVEpisodeAtRow( self, actualRow ):
        self.parent.processEpisode(
            self.actualTVSeasonData[ actualRow ] )
        
    def filterRow( self, rowNumber ):
        episodeData = self.actualTVSeasonData[ rowNumber ]
        filterStatus = self.parent.filterStatusComboBox.currentText( ).strip( )
        if filterStatus == 'ALL':
            return self.filterRegexp.indexIn( episodeData[ 'title' ] ) != -1
        elif filterStatus == 'NOT MINE':
            if not episodeData[ 'missing' ]: return False
            return self.filterRegexp.indexIn( episodeData[ 'title' ] ) != -1
        else: return False
        
    def setFilterStatus( self, index ):
        self.emitFilterChanged.emit( )
        
    def setFilterString( self, text ):
        mytext = str( text ).strip( )
        if len( mytext ) == 0: mytext = '.'
        self.filterRegexp = QRegExp(
            mytext, Qt.CaseInsensitive, QRegExp.RegExp )
        self.emitFilterChanged.emit( )

    def rowCount( self, parent ):
        return len( self.actualTVSeasonData )

    def columnCount( self, parent ):
        return 3
    
    def headerData( self, col, orientation, role ):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[ col ]
        return None

    #
    ## get data from parent
    def fillOutCalculation( self, episodes ):
        self.actualTVSeasonData = sorted(
            episodes.values( ),
            key = lambda episode: episode[ 'episode' ] )
        #
        ## first remove all rows that exist
        initRowCount = self.rowCount( None )
        self.beginRemoveRows( QModelIndex( ), 0, initRowCount - 1 )
        self.endRemoveRows( )
        #
        ## now add in the data
        self.beginInsertRows( QModelIndex( ), 0, len( self.actualTVSeasonData ) - 1 )
        self.endInsertRows( )

    def sort( self, ncol, order ):
        self.layoutAboutToBeChanged.emit( )
        self.actualTVSeasonData.sort(
            key = lambda episode: episode[ 'episode' ] )
        self.layoutChanged.emit( )

    def data( self, index, role ):
        if not index.isValid( ): return None
        row = index.row( )
        col = index.column( )
        episode = self.actualTVSeasonData[ row ].copy( )
        #
        ## color background role
        if role == Qt.BackgroundRole:
            if not episode[ 'have_episode' ]:
                return QBrush( QColor( "#373949" ) )
        elif role == Qt.DisplayRole:
            if col == 0:
                return episode[ 'episode' ]
            elif col == 1:
                return episode[ 'title' ]
            elif col == 2:
                return episode[ 'date aired' ].strftime( '%d/%m/%Y' )
        return None
