from PyQt4.QtGui import *
from PyQt4.QtCore import *
import os, sys, numpy, glob, datetime, inspect
import logging, requests, time, io, PIL.Image
from multiprocessing import Process, Manager
import pathos.multiprocessing as multiprocessing
from bs4 import BeautifulSoup
from functools import reduce
from urllib.parse import urlparse
from . import plextvdb, mainDir, get_token
from .plextvdb_season_gui import TVDBSeasonGUI
from plexcore import plexcore, geoip_reader
from plextmdb import plextmdb

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

    class TVDBGUIThread( QThread ):
        emitString = pyqtSignal( str )
        finalData = pyqtSignal( dict )
        
        def __init__( self, fullURL, token, tvdata_on_plex = None,
                      didend = None, toGet = None, verify = False ):
            super( QThread, self ).__init__( )
            self.fullURL = fullURL
            self.token = token
            self.tvdata_on_plex = tvdata_on_plex
            self.didend = didend
            self.toGet = toGet
            self.verify = verify

        def run( self ):
            time0 = time.time( )
            dtnow = datetime.datetime.now( )
            final_data_out = { }
            mytxt = '0, started loading in data on %s.' % (
                datetime.datetime.now( ).strftime( '%B %d, %Y @ %I:%M:%S %p' ) )
            logging.info( mytxt )
            self.emitString.emit( mytxt )
            libraries_dict = plexcore.get_libraries(
                fullURL = self.fullURL, token = self.token, do_full = True )
            if not any(map(lambda value: 'show' in value[-1], libraries_dict.values( ) ) ):
                raise ValueError( 'Error, could not find TV shows.' )
            library_name = max(map(lambda key: libraries_dict[ key ][ 0 ],
                                    filter(lambda key: libraries_dict[key][1] == 'show',
                                           libraries_dict ) ) )
            final_data_out[ 'library_name'] = library_name
            mytxt = '1, found TV library in %0.3f seconds.' % ( time.time( ) - time0 )
            logging.info( mytxt )
            self.emitString.emit( mytxt )
            #
            if self.tvdata_on_plex is None:
                tvdata_on_plex = plexcore.get_library_data(
                    library_name, fullURL = self.fullURL, token = self.token )
            if self.tvdata_on_plex is None:
                raise ValueError( 'Error, could not find TV shows on the server.' )
            mytxt = '2, loaded TV data from Plex server in %0.3f seconds.' % (
                time.time( ) - time0 )
            logging.info( mytxt )
            self.emitString.emit( mytxt )
            #
            showsToExclude = plextvdb.get_shows_to_exclude(
                self.tvdata_on_plex )
            #
            ## using a stupid-ass pattern to shave some seconds off...
            def _process_didend( dide, tvdon_plex, do_verify, t0, shared_list ):
                if dide is not None:
                    shared_list.append( ( 'didend', dide ) )
                    return
                dide = plextvdb.get_all_series_didend(
                    tvdon_plex, verify = do_verify )
                mytxt = '3b, added information on whether shows ended in %0.3f seconds.' % (
                    time.time( ) - t0 )
                logging.info( mytxt )
                self.emitString.emit( mytxt )
                shared_list.append( ( 'didend', dide ) )

            def _process_missing( toge, tvdon_plex, showsexc, do_verify, t0, shared_list ):
                if toge is not None:
                    shared_list.append( ( 'toGet', toge ) )
                    return
                toge = plextvdb.get_remaining_episodes(
                    tvdon_plex, showSpecials = False, showsToExclude = showsexc,
                    verify = do_verify )
                mytxt = '3b, found missing episodes in %0.3f seconds.' % ( time.time( ) - t0 )
                logging.info( mytxt )
                self.emitString.emit( mytxt )
                shared_list.append( ( 'toGet', toge ) )

            def _process_plot_tvshowstats( tvdon_plex, t0, shared_list ):
                tvdata_date_dict = plextvdb.get_tvdata_ordered_by_date(
                    tvdon_plex )
                years_have = set(map(lambda date: date.year, tvdata_date_dict ) )
                with multiprocessing.Pool(
                        processes = multiprocessing.cpu_count( ) ) as pool:
                    figdictdata = dict( pool.map(
                        lambda year: ( year, plextvdb.create_plot_year_tvdata(
                            tvdata_date_dict, year, shouldPlot = False ) ),
                        years_have ) )
                mytxt = '3b, made plots of tv shows added in %d years in %0.3f seconds.' % (
                    len( years_have ), time.time( ) - time0 )
                logging.info( mytxt )
                self.emitString.emit( mytxt )
                shared_list.append( ( 'plotYears', figdictdata ) )

            manager = Manager( )
            shared_list = manager.list( )
            jobs = [ Process( target=_process_didend, args=(
                self.didend, self.tvdata_on_plex, self.verify, time0, shared_list ) ),
                     Process( target=_process_missing, args=(
                         self.toGet, self.tvdata_on_plex, showsToExclude, self.verify,
                         time0, shared_list ) ) ]
            # Process( target=_process_plot_tvshowstats, args=(
            #     self.tvdata_on_plex, time0, shared_list ) ) ]
            for process in jobs: process.start( )
            for process in jobs: process.join( )
            final_data = dict( shared_list )
            assert( set( final_data ) == set([ 'didend', 'toGet' ]) )
            self.didend = final_data[ 'didend' ]
            self.toGet = final_data[ 'toGet' ]
            for seriesName in self.tvdata_on_plex:
                self.tvdata_on_plex[ seriesName ][ 'didEnd' ] = self.didend[ seriesName ]
            final_data_out[ 'tvdata_on_plex' ] = self.tvdata_on_plex
            mytxt = '4, finished loading in all data on %s.' % (
                datetime.datetime.now( ).strftime( '%B %d, %Y @ %I:%M:%S %p' ) )
            logging.info( mytxt )
            self.emitString.emit( mytxt )
            missing_eps = dict(map(
                lambda seriesName: ( seriesName, self.toGet[ seriesName ][ 'episodes' ] ),
                filter( lambda sname: sname in self.toGet and sname not in showsToExclude,
                        self.tvdata_on_plex ) ) )
            final_data_out[ 'missing_eps' ] = missing_eps
            self.finalData.emit( final_data_out )
            

    @classmethod
    def getShowSummary( cls, seriesName, tvdata_on_plex, missing_eps ):
        seasons_info = tvdata_on_plex[ seriesName ][ 'seasons' ]
        overview = tvdata_on_plex[ seriesName ][ 'summary' ]
        didend = tvdata_on_plex[ seriesName ][ 'didEnd' ]
        num_total = sum(list(
            map(lambda seasno: len( seasons_info[ seasno ][ 'episodes' ] ),
                set( seasons_info ) - set([0]))))
        if seriesName not in missing_eps: num_missing = 0
        else: num_missing = len( missing_eps[ seriesName ] )
        if didend: show_status = "Show has ended"
        else: show_status = "Show is still ongoing"
        minDate = min(
            map(lambda seasno: min(
                map(lambda epno: seasons_info[ seasno ]['episodes'][epno]['date aired' ],
                    seasons_info[ seasno ]['episodes'] ) ), set( seasons_info ) - set([0])))
        maxDate = max(
            map(lambda seasno: max(
                map(lambda epno: seasons_info[ seasno ]['episodes'][epno]['date aired' ],
                    seasons_info[ seasno ]['episodes'] ) ), set( seasons_info ) - set([0])))
        
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
                       map(lambda epno: seasons_info[ seasno ]['episodes'][ epno ][ 'duration' ],
                           seasons_info[ seasno ]['episodes'] ) ), set( seasons_info ) - set([0]))))).mean( )
        average_size_in_bytes = numpy.array(
            reduce(lambda x,y: x+y,
                   list(map(lambda seasno: list(
                       map(lambda epno: seasons_info[ seasno ]['episodes'][ epno ][ 'size' ],
                           seasons_info[ seasno ]['episodes'] ) ), set( seasons_info ) - set([0]))))).mean( )
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
    def getSummaryImg( cls, imageURL, token ):
        if imageURL is None: return None
        return plexcore.get_pic_data( imageURL, token )

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
        assert( seriesName in self.tvdata_on_plex )
        if seriesName not in self.summaryShowInfo:
            self.summaryShowInfo[ seriesName ] = TVDBGUI.getShowSummary(
                seriesName, self.tvdata_on_plex, self.missing_eps )
            
        if seriesName not in self.showImages:
            self.showImages[ seriesName ] = TVDBGUI.getSummaryImg(
                self.tvdata_on_plex[ seriesName ][ 'picurl' ],
                self.token )

        showSummary = self.summaryShowInfo[ seriesName ]
        showImg = self.showImages[ seriesName ]
        #
        ## now put this into summary image on left, summary info on right
        if showImg is not None:
            qpm = QPixmap.fromImage( QImage.fromData( showImg ) )
            qpm = qpm.scaledToWidth( 600 )
            self.summaryShowImage.setPixmap( qpm )
        else: self.summaryShowImage.setPixmap( )
        self.summaryShowInfoArea.setHtml( showSummary )

    def _primordial_put_strings( self, extra_string ):
        self.primordialErrorStrings.append( extra_string )
        myHTML = """
        <html>
          %s
        </html>""" % '\n'.join(map(lambda estring: '<p>%s</p>' % estring,
                                   self.primordialErrorStrings ) )
        self.primordialErrorDialog.setHtml( myHTML )

    def _process_final_state( self, final_data_out ):
        self.hide( )
        self.setWindowTitle( 'The List of TV Shows on the Plex Server' )
        #
        ## delete all widgets in current layout
        while self.myLayout.count( ):
            myWidget = self.myLayout.takeAt( 0 ).widget( )
            myWidget.deleteLater( )
        #
        self.library_name = final_data_out[ 'library_name' ]
        self.tvdata_on_plex = final_data_out[ 'tvdata_on_plex' ]
        self.missing_eps = final_data_out[ 'missing_eps' ]
        #
        self.instantiatedTVShows = { }
        self.dt = datetime.datetime.now( ).date( )
        self.filterOnTVShows = QLineEdit( '' )
        self.setWindowTitle( 'The List of TV Shows on the Plex Server' )
        self.showImages = { }
        self.summaryShowInfo = { }
        #
        self.refreshButton = QPushButton( "REFRESH TV SHOWS" )
        self.tokenLabel = QLabel( )
        self.plexURLLabel = QLabel( )
        self.locationLabel = QLabel( )
        self.processPlexInfo( )
        #
        self.tm = TVDBTableModel( self )
        self.tv = TVDBTableView( self )
        self.tm.fillOutCalculation( )
        #
        topWidget = QWidget( )
        topLayout = QGridLayout( )
        topWidget.setLayout( topLayout )
        topLayout.addWidget( QLabel( 'PLEX TOKEN:' ), 0, 0, 1, 1 )
        topLayout.addWidget( self.tokenLabel, 0, 1, 1, 1 )
        topLayout.addWidget( QLabel( 'PLEX URL:' ), 1, 0, 1, 1 )
        topLayout.addWidget( self.plexURLLabel, 1, 1, 1, 1 )
        topLayout.addWidget( QLabel( 'LOCATION:' ), 2, 0, 1, 1 )
        topLayout.addWidget( self.locationLabel, 2, 1, 1, 1 )
        self.myLayout.addWidget( topWidget )
        #
        midWidget = QWidget( )
        midLayout = QGridLayout( )
        midLayout.addWidget( QLabel( 'TV SHOW FILTER' ), 0, 0, 1, 1 )
        midLayout.addWidget( self.filterOnTVShows, 0, 1, 1, 3 )
        midLayout.addWidget( self.refreshButton, 0, 4, 1, 3 )
        self.myLayout.addWidget( midWidget )
        self.myLayout.addWidget( self.tv )
        #
        botWidget = QWidget( )
        botLayout = QVBoxLayout( )
        botWidget.setLayout( botLayout )
        self.summaryShowImage = QLabel( )
        self.summaryShowImage.setFixedWidth( 600 )
        botLayout.addWidget( self.summaryShowImage )
        self.summaryShowInfoArea = QTextEdit( )
        self.summaryShowInfoArea.setReadOnly( True )
        botLayout.addWidget( self.summaryShowInfoArea )
        self.myLayout.addWidget( botWidget )
        #
        ## set size, make sure not resizable
        self.setFixedWidth( self.tv.frameGeometry( ).width( ) * 1.05 )
        self.setFixedHeight( 900 )
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
        self.show( )
                                
    def __init__( self, token, fullURL, tvdata_on_plex = None,
                  didend = None, toGet = None, verify = True ):
        super( TVDBGUI, self ).__init__( )
        self.fullURL = fullURL
        self.token = token
        self.tvdb_token = get_token( verify = verify )
        self.verify = verify
        self.setStyleSheet("""
        QWidget {
        font-family: Consolas;
        font-size: 11;
        }""" )
        self.setWindowTitle( 'PLEX TV GUI PROGRESS WINDOW' )
        self.myLayout = QVBoxLayout( )
        self.setLayout( self.myLayout )
        self.setFixedWidth( 300 )
        self.setFixedHeight( 300 )
        self.primordialErrorDialog = QTextEdit( )
        self.primordialErrorDialog.setReadOnly( True )
        self.primordialErrorStrings = [ ]
        self.myLayout.addWidget( self.primordialErrorDialog )
        self.show( )
        #
        self.initThread = TVDBGUI.TVDBGUIThread(
            fullURL, token, tvdata_on_plex = tvdata_on_plex,
            didend = didend, toGet = toGet, verify = verify )
        self.initThread.emitString.connect( self._primordial_put_strings )
        self.initThread.finalData.connect( self._process_final_state )
        self.initThread.start( )

    def refreshTVShows( self ):
        time0 = time.time( )
        self.tvdata_on_plex = plexcore.get_library_data(
            self.library_name, fullURL = self.fullURL, token = self.token )
        didend = plexcore.get_all_series_didend(
            self.tvdata_on_plex, verify = verify )
        for seriesName in self.tvdata_on_plex:
            self.tvdata_on_plex[ seriesName ][ 'didEnd' ] = didend[ seriesName ]
        showsToExclude = plextvdb.get_shows_to_exclude(
            self.tvdata_on_plex )
        toGet = plextvdb.get_remaining_episodes(
                self.tvdata_on_plex, showSpecials = False,
            showsToExclude = showsToExclude )
        self.missing_eps = dict(map(
            lambda seriesName: ( seriesName, toGet[ seriesName ][ 'episodes' ] ),
            set( toGet ) - set( showsToExclude ) ) )
        self.tm.fillOutCalculation( )
        logging.info( 'refreshed all TV shows in %0.3f seconds.' % (
            time.time( ) - time0 ) )

    def processPlexInfo( self ):
        self.tokenLabel.setText( self.token )
        self.plexURLLabel.setText( self.fullURL )
        ipaddr = urlparse( self.fullURL ).netloc.split(':')[0]
        if ipaddr not in ( '127.0.0.1', 'localhost' ):
            myloc = geoip_reader.city( ipaddr )
            self.locationLabel.setText( '%s, %s, %s.' % (
                myloc.city.name, myloc.subdivisions.most_specific.iso_code,
                myloc.country.name ) )
        else: self.locationLabel.setText( 'LOCALHOST' )

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
        if seriesName not in self.parent.instantiatedTVShows:
            self.parent.instantiatedTVShows[ seriesName ] = TVDBShowGUI(
                seriesName, self.parent.tvdata_on_plex,
                self.parent.missing_eps, self.parent.tvdb_token,
                self.parent.token, parent = self.parent,
                verify = self.parent.verify )
        tvdbsi = self.parent.instantiatedTVShows[ seriesName ]
        result = tvdbsi.exec_( )

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
        tvdata_on_plex = self.parent.tvdata_on_plex
        missing_eps = self.parent.missing_eps
        for seriesName in sorted( tvdata_on_plex ):
            seasons_info = tvdata_on_plex[ seriesName ][ 'seasons' ]
            startDate = min( map(
                lambda seasno: min(
                    map(lambda epno: seasons_info[ seasno ]['episodes'][ epno ][ 'date aired' ],
                        seasons_info[seasno]['episodes'] ) ), set(seasons_info) - set([0]) ) )
            endDate = max( map(
                lambda seasno: max(
                    map(lambda epno: seasons_info[ seasno ]['episodes'][ epno ][ 'date aired' ],
                        seasons_info[ seasno ]['episodes'] ) ), set(seasons_info) - set([0]) ) )
            seasons = len( seasons_info.keys( ) )
            numEps = sum( map(
                lambda seasno: len( seasons_info[ seasno ][ 'episodes' ] ),
                seasons_info ) )
            dat = { 'seriesName' : seriesName,
                    'startDate' : startDate,
                    'endDate' : endDate,
                    'seasons' : seasons,
                    'numEps' : numEps,
                    'didEnd' : tvdata_on_plex[ seriesName ][ 'didEnd' ],
                    'numMissing' : 0 }
            if seriesName in missing_eps:
                dat[ 'numMissing' ] = len( missing_eps[ seriesName ] )
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
        colMapping = { 0 : 'seriesName', 1 : 'startDate', 2 : 'endDate' }
        if col in ( 0, 1, 2 ):
            self.actualTVSeriesData.sort(
                key = lambda dat: dat[ colMapping[ col ] ] )
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
    
    def __init__( self, seriesName, tvdata, missing_eps,
                  tvdb_token, plex_token,
                  parent = None, verify = True ):
        super( TVDBShowGUI, self ).__init__( parent )
        if parent is not None:
            assert( isinstance( parent, QDialog ) )
        assert( seriesName in tvdata )
        seriesInfo = tvdata[ seriesName ]
        self.setWindowTitle( seriesName )
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #
        ## top widget contains a set of seasons in a QComboBox
        sorted_seasons = sorted( set( seriesInfo[ 'seasons' ] ) - set([ 0 ]) )
        topWidget = QWidget( )
        topLayout = QHBoxLayout( )
        topWidget.setLayout( topLayout )
        topLayout.addWidget( QLabel( "SEASON" ) )
        seasonSelected = QComboBox( self )
        seasonSelected.addItems(
            list(map(lambda seasno: '%d' % seasno,
                     sorted_seasons)))
        seasonSelected.setEnabled( True )
        seasonSelected.setEditable( False )
        seasonSelected.setCurrentIndex( 0 )
        topLayout.addWidget( seasonSelected )
        myLayout.addWidget( topWidget )
        #
        ## now a stacked layout
        self.seasonWidget = QStackedWidget( )
        self.series_widgets = { }
        num_seasons = len(sorted_seasons)
        for season in sorted_seasons:
            self.series_widgets[ season ] = TVDBSeasonGUI(
                seriesName, season, tvdata, missing_eps, tvdb_token, plex_token,
                verify = verify, parent = parent )
            self.seasonWidget.addWidget( self.series_widgets[ season ] )
            logging.info( 'added %s season %d / %d.' % (
                seriesName, season, num_seasons ) )
        first_season = min( self.series_widgets )
        myLayout.addWidget( self.seasonWidget )
        #
        ## set size
        self.setFixedWidth( self.series_widgets[ first_season ].sizeHint( ).width( ) * 1.05 )
        #self.setFixedWidth( 800 )
        self.setFixedHeight( 800 )
        #
        ## connect
        seasonSelected.installEventFilter( self )
        seasonSelected.currentIndexChanged.connect( self.selectSeason )
        #
        quitAction = QAction( self )
        quitAction.setShortcuts( [ 'Ctrl+Q', 'Esc' ] )
        quitAction.triggered.connect( self.close )
        self.addAction( quitAction )
        printAction = QAction( self )
        printAction.setShortcut( 'Shift+Ctrl+P' )
        printAction.triggered.connect( self.screenGrab )
        self.addAction( printAction )
        #
        ##
        self.show( )

    def selectSeason( self, idx ):
        self.seasonWidget.setCurrentIndex( idx )
