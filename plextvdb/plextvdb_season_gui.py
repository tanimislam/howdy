from PyQt4.QtGui import *
from PyQt4.QtCore import *
from bs4 import BeautifulSoup
import copy, numpy, sys, requests
import logging, datetime
import io, PIL.Image, base64
from . import plextvdb
from plexcore import plexcore, QDialogWithPrinting, QLabelWithSave
from plexcore import get_formatted_size, get_formatted_duration
from plextmdb import plextmdb

class TVDBSeasonGUI( QDialogWithPrinting ):

    @classmethod
    def find_missing_eps( cls, toGet, seriesName, season ):
        if seriesName not in toGet: return { }
        return set( map(lambda tup: tup[1],
                        filter(lambda tup: tup[0] == season,
                               toGet[ seriesName ] ) ) )
    
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
                season, get_formatted_duration( average_duration_season_in_secs ) )
            siz_tag = html.new_tag( "p" )
            siz_tag.string = "average size of season %02d episodes: %s." % (
                season, get_formatted_size( average_size_duration_in_bytes ) )
            body_elem.append( dur_tag )
            body_elem.append( siz_tag )
        return html.prettify( )

    def __init__( self, seriesName, seasno,
                  plex_tv_data, toGet, tvdb_token,
                  plex_token, verify = True, parent = None ):
        super( TVDBSeasonGUI, self ).__init__( parent, isIsolated = False, doQuit = False )
        self.setModal( True )
        self.parent = parent
        assert( seriesName in plex_tv_data )
        assert( seasno in plex_tv_data[ seriesName ]['seasons'] )
        plex_tv_episodes = plex_tv_data[ seriesName ]['seasons'][ seasno ].copy( )
        seasonPICURL = plex_tv_episodes['seasonpicurl']
        #
        self.setWindowTitle( '%s season %02d' % ( seriesName, seasno ) )
        self.currentEpisode = None
        #
        ## put in image and season number and seriesName 
        #
        ## put in overview information for episodes I have
        episodes = { }
        bad_eps = [ ]
        for epno in plex_tv_episodes[ 'episodes' ]:
            episodes[ epno ] = {
                'seriesName' : seriesName,
                'season' : seasno,
                'have_episode' : True,
                'episode' : epno,
                'title' : plex_tv_episodes['episodes'][ epno ][ 'title' ],
                'date aired' : plex_tv_episodes['episodes'][ epno ][ 'date aired' ],
                'overview' : plex_tv_episodes['episodes'][ epno ][ 'summary' ],
                'size' : plex_tv_episodes['episodes'][epno]['size'],
                'duration' : plex_tv_episodes['episodes'][epno]['duration'],
                'picurl' : plex_tv_episodes[ 'episodes' ][epno]['episodepicurl'],
                'plex_token' : plex_token,
                'verify' : verify
            }
            if episodes[ epno ][ 'date aired' ].year == 1900: # is bad
                bad_eps.append(( seasno, epno ))
        #
        ## fill out those episodes don't have, use TVDB and TMDB stuff
        ## ONLY on missing episodes
        missing_eps = TVDBSeasonGUI.find_missing_eps( toGet, seriesName, seasno )
        series_id = plextvdb.get_series_id( seriesName, tvdb_token, verify = verify )
        eps = plextvdb.get_episodes_series(
            series_id, tvdb_token, showSpecials = False,
            showFuture = False, verify = verify )
        if any(filter(lambda episode: episode['episodeName'] is None, eps ) ):
            tmdb_id = plextmdb.get_tv_ids_by_series_name( seriesName, verify = verify )
            if len( tmdb_id ) == 0: return
            tmdb_id = tmdb_id[ 0 ]
            eps = plextmdb.get_episodes_series_tmdb( tmdb_id, verify = verify )
        tvseason = plextvdb.TVSeason(
            seriesName, series_id, tvdb_token, seasno, verify = verify,
            eps = eps )
        assert( len(set( missing_eps ) -
                    set( tvseason.episodes.keys( ) ) ) == 0 )
        for epno in missing_eps:
            tvdb_epinfo = tvseason.episodes[ epno ]
            episodes[ epno] = {
                'seriesName' : seriesName,
                'season' : seasno,
                'have_episode' : False,
                'episode' : epno,
                'title' : tvdb_epinfo[ 'title' ],
                'date aired' : tvdb_epinfo[ 'airedDate' ],
                'overview' : tvdb_epinfo[ 'overview' ],
                'tvdb_token' : tvdb_token,
                'verify' : verify
            }
        for epno in map(lambda tup: tup[1], bad_eps ):
            if epno not in tvseason.episodes: continue
            tvdb_epinfo = tvseason.episodes[epno]
            episodes[epno]['date aired'] = tvdb_epinfo[ 'airedDate' ]
        #
        ## main layout
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )        
        #
        ## now top widget with grid layout
        topWidget = QWidget( )
        topLayout = QHBoxLayout( )
        topWidget.setLayout( topLayout )
        self.leftImageWidget = QLabelWithSave( )
        self.leftImageWidget.setFixedWidth( 200 )
        if seasonPICURL is not None:
            self.picData = plexcore.get_pic_data(
                seasonPICURL, plex_token )
            qpm = QPixmap.fromImage(
                QImage.fromData( self.picData ) )
            qpm = qpm.scaledToWidth( 200 )
            self.leftImageWidget.setPixmap( qpm )
        else: self.picData = None
        topLayout.addWidget( self.leftImageWidget )
        self.seasonSummaryArea = QTextEdit( )
        self.seasonSummaryArea.setReadOnly( True )
        #seasonSummaryArea.setLineWrapColumnOrWidth( 185 )
        #seasonSummaryArea.setLineWrapMode(QTextEdit.FixedPixelWidth)
        self.seasonSummaryArea.setHtml(
            TVDBSeasonGUI.processSeasonSummary( seasno, episodes ) )
        self.seasonSummaryArea.setFixedWidth( 200 )
        topLayout.addWidget( self.seasonSummaryArea )
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
        ## no clipping of this table view
        self.tv.setFixedSizes(
            topWidget.sizeHint( ).width( ),
            topWidget.sizeHint( ).height( ) )
        #
        ## now add the TV season widget table view
        myLayout.addWidget( self.tv )
        #
        ## now add in signals and slots
        self.filterOnTVEpisodes.textChanged.connect( self.tm.setFilterString )
        self.filterStatusComboBox.installEventFilter( self )
        self.filterStatusComboBox.currentIndexChanged.connect( self.tm.setFilterStatus )
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
                get_formatted_duration( episode[ 'duration' ] ) )
            body_elem.append( dur_tag )
        if 'size' in episode:
            siz_tag = html.new_tag( "p" )
            siz_tag.string = "size: %s." % (
                get_formatted_size( episode[ 'size' ] ) )
            body_elem.append( siz_tag )
        if len(set([ 'picurl', 'plex_token' ]) -
               set( episode ) ) == 0: # not add in the picture
            img_content = plexcore.get_pic_data(
                episode[ 'picurl' ], token = episode[ 'plex_token' ] )
            img = PIL.Image.open( io.BytesIO( img_content ) )
            mimetype = PIL.Image.MIME[ img.format ]
            par_img_tag = html.new_tag('p')
            img_tag = html.new_tag( 'img' )
            img_tag['width'] = 7.0 / 9 * self.episodeSummaryArea.width( )
            img_tag['src'] = "data:%s;base64,%s" % (
                mimetype, base64.b64encode( img_content ).decode('utf-8') )
            par_img_tag.append( img_tag )
            body_elem.append( par_img_tag )
                                             
        self.episodeSummaryArea.setHtml( html.prettify( ) )

    def rescale( self, indexScale ):
        #
        ## first set size of the image
        self.leftImageWidget.setFixedWidth(
            200 * 1.05**indexScale )
        if self.picData is not None:
            qpm = QPixmap.fromImage(
                QImage.fromData( self.picData ) )
            qpm = qpm.scaledToWidth( 200 * 1.05**indexScale )
            self.leftImageWidget.setPixmap( qpm )
        self.seasonSummaryArea.setFixedWidth(
            200 * 1.05**indexScale )
        #
        ## season summary area
        #
        ## episode summary area
        self.episodeSummaryArea.setFixedWidth(
            400 * 1.05**indexScale )
        if self.currentEpisode is not None:
            self.processEpisode( self.currentEpisode )
        #
        ## now rescale the table
        self.tv.rescale( indexScale )
        
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
        toBotAction = QAction( self )
        toBotAction.setShortcut( 'End' )
        toBotAction.triggered.connect( self.scrollToBottom )
        self.addAction( toBotAction )
        #
        toTopAction = QAction( self )
        toTopAction.setShortcut( 'Home' )
        toTopAction.triggered.connect( self.scrollToTop )
        self.addAction( toTopAction )

    # set the width and height of table view here
    def setFixedSizes( self, width, height ):
        self.columnWidth = width * 1.0 / 5
        self.finalHeight = height
        for colno in range( 5 ):
            self.setColumnWidth( colno, self.columnWidth )
        self.setFixedWidth( width )
        self.setFixedHeight( self.finalHeight )

    def processCurrentRow( self, newIndex, oldIndex = None ):
        row_valid = self.proxy.mapToSource( newIndex ).row( )
        #
        ## episode data emit this row here
        self.parent.tm.emitRowSelected.emit( row_valid )

    def rescale( self, indexScale ):
        for colno in range( 5 ):
            self.setColumnWidth(colno, self.columnWidth * 1.05**indexScale )
        self.setFixedWidth( 5 * self.columnWidth * 1.05**indexScale )
        self.setFixedHeight( self.finalHeight * 1.05**indexScale )

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
    _headers = [ 'Episode', 'Name', 'Date', 'Duration', 'Size' ]
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
        self.parent.currentEpisode = self.actualTVSeasonData[ actualRow ]
        
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
        return 5
    
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
            elif col == 3:
                if 'duration' in episode:
                    dur = episode[ 'duration' ]
                    hrdur, rem = divmod( dur, 3600 )
                    dur_string = datetime.datetime.fromtimestamp(
                        dur ).strftime('%M:%S.%f')[:-3]
                    if hrdur != 0: dur_string = '%d:%s' % (
                            hrdur, dur_string )
                else: dur_string = 'NOT IN LIB'
                return dur_string
            elif col == 4:
                if 'size' in episode:
                    return get_formatted_size(
                        episode[ 'size' ] )
                else:
                    return 'NOT IN LIB'
        return None
