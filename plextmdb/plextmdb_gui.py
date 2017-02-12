import numpy, os, sys, requests, json, base64
import logging, glob, datetime, textwrap, titlecase
from . import plextmdb, mainDir, plextmdb_torrents
from PyQt4.QtCore import *
from PyQt4.QtGui import *
#
sys.path.append( mainDir )
from plexcore import plexcore, plexcore_gui

_headers = [ 'title', 'release date', 'popularity', 'rating', 'overview' ]

class TMDBMovieInfo( QDialog ):
    def __init__( self, parent, currentRow ):
        super( TMDBMovieInfo, self ).__init__( parent )
        self.token = parent.token
        self.title = currentRow[ 0 ]
        self.setModal( True )
        #
        full_info = currentRow[ -3 ]
        movie_full_path = currentRow[ -2 ]
        release_date = currentRow[ 1 ]
        popularity = currentRow[ 2 ]
        isFound = currentRow[ -1 ]
        #
        myLayout = QVBoxLayout( )
        mainColor = self.palette().color( QPalette.Background )
        self.setLayout( myLayout )
        if not isFound:
            self.getTorrentButton = QPushButton( 'GET MOVIE TORRENT' )
            myButtonGroup = QButtonGroup( )
            self.noRadioButton = QRadioButton( 'NO', self )
            self.yesRadioButton = QRadioButton( 'YES', self )
            for qrb in ( self.noRadioButton, self.yesRadioButton ):
                myButtonGroup.addButton( qrb )
            myButtonGroup.setExclusive( True )
            self.noRadioButton.setChecked( True )
            self.numEntriesComboBox = QComboBox( self )
            self.numEntriesComboBox.addItems([ '5', '10', '20', '40' ])
            self.numEntriesComboBox.setEditable( False )
            self.numEntriesComboBox.setCurrentIndex( 1 )
            topWidget = QWidget( self )
            topLayout = QGridLayout( )
            topWidget.setLayout( topLayout )
            topLayout.addWidget( self.getTorrentButton, 0, 0, 1, 5 )
            topLayout.addWidget( QLabel('BYPASS YTS?'), 1, 0, 1, 1 )
            topLayout.addWidget( self.noRadioButton, 1, 1, 1, 1 )
            topLayout.addWidget( self.yesRadioButton, 1, 2, 1, 1 )
            topLayout.addWidget( QLabel( 'MAXNUM' ), 1, 3, 1, 1 )
            topLayout.addWidget( self.numEntriesComboBox, 1, 4, 1, 1 )
            myLayout.addWidget( topWidget )
            self.getTorrentButton.clicked.connect( self.launchTorrentWindow )
        myLayout.addWidget( QLabel( 'TITLE: %s' % self.title ) )
        myLayout.addWidget( QLabel( 'RELEASE DATE: %s' %
                                    release_date.strftime( '%d %b %Y' ) ) )
        myLayout.addWidget( QLabel( 'POPULARITY: %0.3f' % popularity ) )
        qte = QTextEdit( full_info )
        qte.setReadOnly( True )
        qte.setStyleSheet("""
        QTextEdit {
        background-color: %s;
        }""" % mainColor.name( ) )
        qte.setFrameStyle( QFrame.NoFrame )
        myLayout.addWidget( qte )
        if movie_full_path is not None:
            response = requests.get( movie_full_path, verify = False )
            logging.debug( 'FULLMOVIEPATH: %s, size = %d' %
                           ( movie_full_path, len( response.content ) ) )
            qpm = QPixmap.fromImage( QImage.fromData( response.content ) )
            qpm = qpm.scaledToWidth( 450 )
            qlabel = QLabel( )
            qlabel.setPixmap( qpm )
            myLayout.addWidget( qlabel )
        #
        self.setFixedWidth( 450 )
        self.setFixedHeight( self.sizeHint( ).height( ) )
        self.show( )

    def launchTorrentWindow( self ):
        maxnum = int( self.numEntriesComboBox.currentText( ) )
        bypass = self.yesRadioButton.isChecked( )
        tmdbt = TMDBTorrents( self, self.token, self.title,
                              bypass = bypass, maxnum = maxnum )
        result = tmdbt.exec_( )

class TMDBRadioButton( QRadioButton ):
    def __init__( self, text, value, parent = None ):
        super( TMDBRadioButton, self ).__init__( text, parent = parent )
        self.value = value
        
class TMDBTorrents( QDialog ):
    def __init__( self, parent, token, movie_name, bypass = False, maxnum = 10 ):
        super( TMDBTorrents, self ).__init__( parent )
        self.setModal( True )
        self.token = token
        self.movie = movie_name
        self.setWindowTitle( 'MOVIE TORRENT DOWNLOAD' )
        self.statusLabel = QLabel( )
        self.summaryButton = QPushButton( 'SUMMARY' )
        self.sendButton = QPushButton( 'SEND' )
        self.downloadButton = QPushButton( 'DOWNLOAD' )
        self.summaryButton.setEnabled( False )
        myButtonGroup = QButtonGroup( self )
        mainLayout = QVBoxLayout( )
        self.setLayout( mainLayout )
        self.torrentStatus = -1
        #
        ##
        if not bypass:
            data, status = plextmdb_torrents.get_movie_torrent( movie_name )
        else:
            status = 'FALURE'
        if status == 'SUCCESS':
            self.torrentStatus = 0
            self.data = { }
            for actmovie in data:
                title = actmovie[ 'title' ]
                allmovies = filter(lambda tor: 'quality' in tor and '3D' not in tor['quality'],
                                   actmovie['torrents'] )
                if len( allmovies ) == 0:
                    continue
                allmovies2 = filter(lambda tor: '720p' in tor['quality'], allmovies )
                if len( allmovies2 ) == 0: allmovies2 = allmovies
                url = allmovies2[0]['url']
                self.data[ title ] = requests.get( url ).content
            self.allRadioButtons = map(lambda name:
                                       TMDBRadioButton( name, name, self ),
                                       sorted( self.data.keys( ) ) )
            self.statusLabel.setText( 'SUCCESS' )
        else:
            #data, status = plextmdb.get_movie_torrent_kickass( movie_name, maxnum = maxnum )
            data, status = plextmdb_torrents.get_movie_torrent_tpb( movie_name, maxnum = maxnum, doAny = False )
            if status != 'SUCCESS':
                data, status = plextmdb_torrents.get_movie_torrent_rarbg( movie_name, maxnum = maxnum )
            if status == 'SUCCESS':
                self.torrentStatus = 1
                self.data = { }
                logging.debug('DATA = %s' % data )
                for name, seeders, leechers, link in data:
                    self.data[ name ] = ( seeders, leechers, link )
                self.allRadioButtons = map(lambda name:
                                           TMDBRadioButton( '%s ( %d, %d )' % ( name, self.data[ name ][0],
                                                                                self.data[ name ][1] ),
                                                            name, self ),
                                           sorted( self.data.keys( ),
                                                   key = lambda nm: sum( self.data[nm][:2] ) ) )
                self.statusLabel.setText( 'SUCCESS' )
            else:
                self.torrentStatus = 2
                self.statusLabel.setText( 'FAILURE, COULD NOT FIND.' )
                self.sendButton.setEnabled( False )
                self.downloadButton.setEnabled( False )

        topWidget = QWidget( self )
        topLayout = QHBoxLayout( )
        topWidget.setLayout( topLayout )
        topLayout.addWidget( self.summaryButton )
        topLayout.addWidget( self.sendButton )
        topLayout.addWidget( self.downloadButton )
        mainLayout.addWidget( topWidget )
        if self.torrentStatus in ( 0, 1 ):
            for button in self.allRadioButtons:
                myButtonGroup.addButton( button )
            myButtonGroup.setExclusive( True )
            self.allRadioButtons[0].setChecked( True )
            myButtonsWidget = QWidget( self )
            myButtonsLayout = QVBoxLayout( )
            myButtonsWidget.setLayout( myButtonsLayout )
            for button in self.allRadioButtons:
                myButtonsLayout.addWidget( button )
            mainLayout.addWidget( myButtonsWidget )
            if self.torrentStatus == 1: self.summaryButton.setEnabled( True )
        mainLayout.addWidget( self.statusLabel )
        #
        self.summaryButton.clicked.connect( self.showSummaryChosen )
        self.sendButton.clicked.connect( self.chooseSentTorrent )
        self.downloadButton.clicked.connect( self.chooseDownloadTorrent )
        #
        self.setFixedWidth( 550 )
        self.setFixedWidth( max( 650, self.sizeHint( ).height( ) ) )
        self.show( )

    def showSummaryChosen( self ):
        whichChosen = max( map(lambda qbut: qbut.value,
                               filter( lambda qbut: qbut.isChecked( ),
                                       self.allRadioButtons ) ) )
        size, url = self.data[ whichChosen ]
        qdl = QDialog( self )
        mainColor = qdl.palette().color( QPalette.Background )
        qlayout = QVBoxLayout( )
        qte = QTextEdit( textwrap.fill( 'URL: %s' % url ) )
        qte.setStyleSheet("""
        QTextEdit {
        background-color: %s;
        }""" % mainColor.name( ) )
        qte.setReadOnly( True )
        qdl.setLayout( qlayout )
        qdl.setWindowTitle( whichChosen )
        qlayout.addWidget( QLabel( 'SIZE: %0.2f MB' % size ) )
        qlayout.addWidget( qte )
        qdl.setFixedWidth( qdl.sizeHint( ).width( ) )
        qdl.setFixedHeight( qdl.sizeHint( ).height( ) )
        qdl.show( )
        result = qdl.exec_( )

    def chooseSentTorrent( self ):
        jsondata = { 'torrentStatus' : self.torrentStatus,
                     'token' : self.token }
        if self.torrentStatus in ( 0, 1 ):
            whichChosen = max( map(lambda qbut: str( qbut.text( ) ),
                                   filter( lambda qbut: qbut.isChecked( ),
                                           self.allRadioButtons ) ) )
        if self.torrentStatus == 0:
            jsondata['movie'] = whichChosen
            jsondata['data'] = base64.b64encode( self.data[ whichChosen ] )
        elif self.torrentStatus == 1:
            _, _, url = self.data[ whichChosen ]
            jsondata[ 'movie' ] = self.movie
            jsondata[ 'data' ] = url
        else:
            jsondata[ 'movie' ] = self.movie

        response = requests.post( 'https://***REMOVED***islam.ddns.net/flask/plex/sendmovieemail',
                                  json = jsondata )
        if response.status_code == 200:
            self.statusLabel.setText( 'SENT REQUEST FOR %s' % jsondata['movie'] )
        else:
            message = response.json()['message']
            self.statusLabel.setText( 'ERROR: %s' % message )

    def chooseDownloadTorrent( self ):
        if self.torrentStatus not in ( 0, 1 ):
            return
        whichChosen = max( map( lambda qbut: qbut.value,
                                filter( lambda qbut: qbut.isChecked( ),
                                        self.allRadioButtons ) ) )
        #
        ## followed advice from http://stackoverflow.com/questions/4286036/how-to-have-a-directory-dialog-in-pyqt
        dirName = str( QFileDialog.getExistingDirectory( self, 'Choose directory to put torrent or magnet.') )
        if self.torrentStatus == 0:
            data = self.data[ whichChosen ]
            torrentFile = os.path.join( dirName, '%s.torrent' % whichChosen )
            with open( torrentFile, 'wb') as openfile:
                openfile.write( data )
        elif self.torrentStatus == 1:
            _, _, url = self.data[ whichChosen ]
            magnetURLFile = os.path.join( dirName, '%s.url' % whichChosen )
            with open( magnetURLFile, 'w') as openfile:
                openfile.write( '%s\n' % url )
            

class TMDBGUI( QWidget ):
    movieSendList = pyqtSignal( list )
    movieRefreshRows = pyqtSignal( list )
    
    def __init__( self, token, fullURL, movie_data_rows, isIsolated = True ):
        super( TMDBGUI, self ).__init__( )
        tmdbEngine = plextmdb.TMDBEngine( )
        self.all_movies = [ ]
        self.token = token
        self.fullURL = fullURL
        if isIsolated:
            self.setWindowTitle( 'The List of Movies By Genre and Year' )
        self.sygWidget = SelectYearGenreWidget( self )
        self.sdWidget = StatusDialogWidget( self )
        self.tmdbtv = TMDBTableView( self )
        self.statusDialog = QLabel( '' )
        self.fill_out_movies( movie_data_rows = movie_data_rows )
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        myLayout.addWidget( self.sygWidget )
        myLayout.addWidget( self.sdWidget )
        myLayout.addWidget( self.tmdbtv )
        myLayout.addWidget( self.statusDialog )
        #
        ## set size, make sure not resizable
        self.setFixedWidth( 680 )
        #
        ## connect signals to slots globally
        self._connectTMDBGUIActions( )
        self._connectStatusDialogWidget( )
        self._connectTMDBTableView( )
        self._connectSelectYearGenreWidget( )
        #
        ## global actions
        if isIsolated:
            quitAction = QAction( self )
            quitAction.setShortcuts( [ 'Ctrl+Q', 'Esc' ] )
            quitAction.triggered.connect( sys.exit )
            self.addAction( quitAction )
        #
        ##
        self.show( )

    def _connectTMDBGUIActions( self ):
        self.movieSendList.connect( self.tmdbtv.tm.emitMoviesHere )

    def _connectSelectYearGenreWidget( self ):
        self.sygWidget.mySignal.connect( self.tmdbtv.tm.setCurrentStatus )
        self.sygWidget.pushDataButton.clicked.connect( self.tmdbtv.tm.fillOutCalculation )
        self.sygWidget.pushDataButton.clicked.connect( self.sdWidget.enableMatching )
        self.sygWidget.pushDataButton.clicked.connect( self.emitMovieList )
        self.sygWidget.refreshDataButton.clicked.connect( self.refreshMovies )
        self.sygWidget.mySignal.connect( self.sdWidget.setYearGenre )
        self.sygWidget.emitSignal( )

    def _connectStatusDialogWidget( self ):
        self.sdWidget.emitStatusToShow.connect( self.tmdbtv.tm.setFilterStatus )
        self.sdWidget.movieNameLineEdit.textChanged.connect(
            self.tmdbtv.tm.setFilterString )

    def _connectTMDBTableView( self ):
        self.tmdbtv.tm.mySummarySignal.connect( self.sdWidget.processStatus )
        self.tmdbtv.tm.emitMoviesHave.connect( self.sdWidget.processMovieTitles )

    def emitMovieList( self ):
        if len( self.all_movies ) > 0:
            self.movieSendList.emit( self.all_movies )

    def fill_out_movies( self, movie_data_rows ):
        self.all_movies = sorted(set(map(lambda row: row[0], movie_data_rows )))
        self.tmdbtv.tm.layoutAboutToBeChanged.emit( )
        self.tmdbtv.tm.layoutChanged.emit( ) # change the colors in the rows, if already there

    def setNewToken( self, newToken ):
        self.token = newToken

    def refreshMovies( self ):
        movie_data_rows, _ = plexcore.fill_out_movies_stuff( self.token, fullurl = self.fullURL )
        self.fill_out_movies( movie_data_rows )
        self.movieRefreshRows.emit( movie_data_rows )
        
class StatusDialogWidget( QWidget ):
    emitStatusToShow = pyqtSignal( int )
    
    class MovieListDialog( QDialog ):
        def __init__( self, parent, movieList ):
            super( StatusDialogWidget.MovieListDialog, self ).__init__( parent )
            self.setWindowTitle( 'MOVIE LIST FOR %d.' % parent.currentYear )
            self.setModal( True )
            #
            qte = QTextEdit('\n'.join([ '%d movies in library\n\n' % len( movieList ),
                                        '\n'.join(movieList) ]) )
            qte.setStyleSheet("""
            QTextEdit {
            background-color: %s;
            }""" % self.palette().color( QPalette.Background ).name( ) )
            qte.setReadOnly( True )
            myLayout = QVBoxLayout( )
            self.setLayout( myLayout )
            myLayout.addWidget( qte )
            self.show( )
    
    def __init__( self, parent ):
        super( StatusDialogWidget, self ).__init__( parent )
        self.statusLabel = QLabel( )
        self.progressLabel = QLabel( )
        self.movieNameLineEdit = QLineEdit( )
        self.status = -1
        self.currentYear = -1
        self.actors = [ ]
        self.movieTitle = ''
        self.num_entries = 0
        self.movieTitles = [ ]
        self.showStatusComboBox = QComboBox( self )
        self.showStatusComboBox.addItems( [ 'MINE', 'NOT MINE', 'ALL' ] )
        self.showStatusComboBox.setEnabled( False )
        self.showStatusComboBox.setEditable( False )
        self.showStatusComboBox.setCurrentIndex( 2 )
        myLayout = QGridLayout( )
        self.setLayout( myLayout )
        myLayout.addWidget( self.statusLabel, 0, 0, 2, 1 )
        myLayout.addWidget( self.progressLabel, 0, 2, 1, 1 )
        myLayout.addWidget( self.showStatusComboBox, 0, 3, 1, 1 )
        myLayout.addWidget( QLabel( 'MOVIE NAME:' ), 1, 0, 1, 1 )
        myLayout.addWidget( self.movieNameLineEdit, 1, 1, 1, 3 )
        #
        self.showStatusComboBox.installEventFilter( self )
        self.showStatusComboBox.currentIndexChanged.connect( self.sendStatus )
    
    def processStatus( self, status, tup ):
        self.status = status
        if status == 0:
            year, genre, num_entries = tup
            self.currentYear = year
            self.num_entries = num_entries
            self.statusLabel.setText( '%d %s movies in %d' %
                                      ( num_entries, genre, year ) )
        elif status == 1:
            actors, num_entries = tup
            self.actors = list( actors )
            self.num_entries = num_entries
            self.statusLabel.setText( '%d movies by %s' % (
                num_entries, ', '.join( actors ) ) )
        elif status == 2:
            movieTitle, num_entries = tup
            self.movieTitle = movieTitle
            self.num_entries = num_entries
            self.statusLabel.setText( '%d movies with title %s' % (
                num_entries, movieTitle ) )

    def setYearGenre( self, status, tup):
        self.status = status
        if status == 0:
            self.currentYear, _, _ = tup
        elif status == 1:
            self.actors = list( tup )
        elif status == 2:
            self.movieTitle = max( tup )

    def enableMatching( self ): 
        self.showStatusComboBox.setEnabled( True )
        self.showStatusComboBox.setCurrentIndex( 2 )
        self.emitStatusToShow.emit( 2 )

    def sendStatus( self ):
        movieShowStatus = str( self.showStatusComboBox.currentText( ) )
        vals = { 'MINE' : 0, 'NOT MINE' : 1, 'ALL' : 2 }
        assert( movieShowStatus in vals )
        self.emitStatusToShow.emit( vals[ movieShowStatus ] )
                
    def processMovieTitles( self, movieTitles ):
        self.movieTitles = sorted( movieTitles )
        
    def showMatchingMovies( self ):
        if len( self.movieTitles ) > 0:
            colr = QColor( 'white' )
            colr.setHsvF( 0.75, 0.15, 1.0, 1.0 )
            dlg = QDialog( self )
            dlg.setWindowTitle( '%d Matching Movies For %d' % (
                len( self.movieTitles ), self.currentYear ) )
            myLayout = QVBoxLayout( )
            dlg.setLayout( myLayout )
            qte = QTextEdit( self )
            qf = QFont( )
            qf.setFamily( 'Consolas' )
            qf.setPointSize( 11 )
            qfm = QFontMetrics( qf )
            qte.setFixedWidth( 60 * qfm.width( 'A' ) )
            qte.setReadOnly( True )
            qte.setStyleSheet("""
            QTextEdit {
            background-color: %s;
            }""" % colr.name( ) )
            myLayout.addWidget( qte )
            dlg.setFixedWidth( dlg.sizeHint( ).width( ) )
            dlg.setFixedHeight( 450 )
            qte.setPlainText('\n'.join([ '%02d: %s' % ( idx + 1, title ) for
                                         (idx, title ) in
                                         enumerate( self.movieTitles )  ]) )
            dlg.show( )
            result = dlg.exec_( )
        
class SelectYearGenreWidget( QWidget ):
    mySignal = pyqtSignal( int, tuple )

    def eventFilter( self, receiver, event ):
        if event.type( ) == QEvent.KeyPress:
            if event.key( ) == Qt.Key_Enter:
                self.pushDataButton.clicked.emit( )
                return True
        return super( SelectYearGenreWidget, self ).eventFilter( receiver, event )
    
    def __init__( self, parent ):
        super( SelectYearGenreWidget, self).__init__( parent )
        self.parent = parent
        dtnow_year = datetime.datetime.now( ).year
        self.yearSpinBox = QSpinBox( self )
        self.yearSpinBox.setWrapping( True )
        self.yearSpinBox.setRange( 1980, dtnow_year )
        self.yearSpinBox.setValue( dtnow_year )
        self.yearSpinBox.setSingleStep( 1 )
        self.genreComboBox = QComboBox( self )
        self.genreComboBox.addItems( sorted( plextmdb.TMDBEngine( ).getGenres( ) ) )
        self.genreComboBox.setEditable( False )
        self.genreComboBox.setCurrentIndex( 0 )
        self.pushDataButton = QPushButton( 'GET MOVIES' )
        self.refreshDataButton = QPushButton( 'REFRESH MOVIES' )
        self.movieNameLineEdit = QLineEdit( '' )
        self.actorNamesLineEdit = QLineEdit( '' )
        #
        ## radio buttons
        genreRadioButton = QRadioButton( '', self )
        actorRadioButton = QRadioButton( '', self )
        movieRadioButton = QRadioButton( '', self )
        self.qbg = QButtonGroup( )
        self.qbg.setExclusive( True )
        self.qbg.addButton( genreRadioButton, 0 )
        self.qbg.addButton( actorRadioButton, 1 )
        self.qbg.addButton( movieRadioButton, 2 )
        self.qbg.buttonClicked.connect( self.setEnabledState )
        genreRadioButton.click( )
        #
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #
        topWidget = QWidget( )
        topLayout = QHBoxLayout( )
        topWidget.setLayout( topLayout )
        topLayout.addWidget( genreRadioButton )
        topLayout.addWidget( QLabel( 'YEAR' ) )
        topLayout.addWidget( self.yearSpinBox )
        topLayout.addWidget( QLabel( 'GENRE' ) )
        topLayout.addWidget( self.genreComboBox )
        topLayout.addWidget( self.pushDataButton )
        topLayout.addWidget( self.refreshDataButton )
        myLayout.addWidget( topWidget )
        #
        midWidget = QWidget( )
        midLayout = QHBoxLayout( )
        midWidget.setLayout( midLayout )
        midLayout.addWidget( actorRadioButton )
        midLayout.addWidget( QLabel( 'ACTORS:' ) )
        midLayout.addWidget( self.actorNamesLineEdit )
        myLayout.addWidget( midWidget )
        #
        botWidget = QWidget( )
        botLayout = QHBoxLayout( )
        botWidget.setLayout( botLayout )
        botLayout.addWidget( movieRadioButton )
        botLayout.addWidget( QLabel( 'MOVIE:' ) )
        botLayout.addWidget( self.movieNameLineEdit )
        myLayout.addWidget( botWidget )
        #
        self.yearSpinBox.valueChanged.connect( self.emitSignal )
        self.genreComboBox.currentIndexChanged.connect( self.emitSignal )
        self.yearSpinBox.installEventFilter( self )
        self.genreComboBox.installEventFilter( self )
        self.actorNamesLineEdit.returnPressed.connect( self.emitSignal )
        self.movieNameLineEdit.returnPressed.connect( self.emitSignal )

    def setEnabledState( self, qrb ):
        state = self.qbg.checkedId( )
        self.yearSpinBox.setEnabled( False )
        self.genreComboBox.setEnabled( False )
        self.actorNamesLineEdit.setEnabled( False )
        self.movieNameLineEdit.setEnabled( False )
        if state == 0:
            self.yearSpinBox.setEnabled( True )
            self.genreComboBox.setEnabled( True )
        elif state == 1:
            self.actorNamesLineEdit.setEnabled( True )
        elif state == 2:
            self.movieNameLineEdit.setEnabled( True )
            
    def emitSignal( self ):
        state = self.qbg.checkedId( )
        if state == 0:
            year = self.yearSpinBox.value( )
            genre = str(self.genreComboBox.currentText( ))
            genre_id = plextmdb.TMDBEngine( ).getGenreIdFromGenre( genre )
            self.mySignal.emit( state, ( year, genre_id, genre ) )
        elif state == 1:
            actors = tuple(map(lambda tok: titlecase.titlecase( ' '.join( tok.strip( ).split( ) ) ),
                               str( self.actorNamesLineEdit.text( ) ).strip( ).split(',') ) )
            self.mySignal.emit( state, actors )
            #self.parent.tmdbtv.tm.fillOutCalculation( )
        elif state == 2:
            movieName = str( self.movieNameLineEdit.text( ) ).strip( )
            self.mySignal.emit( state, ( movieName, ) )
            #self.parent.tmdbtv.tm.fillOutCalculation( )            
#
## now the table, table model, and cell objects.
class TMDBTableView( QTableView ):
    def __init__( self, parent ):
        super(TMDBTableView, self).__init__( parent )
        #
        self.token = parent.token
        self.tm = TMDBTableModel( self )
        self.proxy = TMDBQSortFilterProxyModel( self, self.tm )
        self.setModel( self.proxy )
        self.setItemDelegateForColumn(0, DescriptionDelegate( self ) )
        self.setItemDelegateForColumn(1, StringEntryDelegate( self ) )
        self.setItemDelegateForColumn(2, StringEntryDelegate( self ) )
        self.setItemDelegateForColumn(3, StringEntryDelegate( self ) )
        #
        self.setShowGrid( True )
        self.verticalHeader( ).setResizeMode( QHeaderView.Fixed )
        self.horizontalHeader( ).setResizeMode( QHeaderView.Fixed )
        self.setSelectionBehavior( QAbstractItemView.SelectRows )
        self.setSelectionMode( QAbstractItemView.SingleSelection ) # single row        
        self.setSortingEnabled( True )
        #
        self.setColumnWidth(0, 210 )
        self.setColumnWidth(1, 210 )
        self.setColumnWidth(2, 120 )
        self.setColumnWidth(3, 120 )
        self.setFixedWidth( 1.1 * ( 210 * 2 + 120 * 2 ) )
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
        popupAction.triggered.connect( self.popupMovie )
        self.addAction( popupAction )

    def contextMenuEvent( self, event ):
        indices_valid = filter(lambda index: index.column( ) == 0,
                               self.selectionModel().selectedIndexes( ) )
        menu = QMenu( self )
        infoAction = QAction( 'Information', menu )
        infoAction.triggered.connect( self.popupMovie )
        menu.addAction( infoAction )
        menu.popup( QCursor.pos( ) )

    def popupMovie( self ):
        index_valid_proxy = max(filter(lambda index: index.column( ) == 0,
                                       self.selectionModel().selectedIndexes( ) ) )
        index_valid = self.proxy.mapToSource( index_valid_proxy )
        self.tm.infoOnMovieAtRow( index_valid.row( ) )

#
## qsortfilterproxymodel to implement filtering
class TMDBQSortFilterProxyModel( QSortFilterProxyModel ):
    def __init__( self, parent, tm ):
        super(TMDBQSortFilterProxyModel, self).__init__( parent )
        #
        self.setSourceModel( tm )
        tm.emitFilterChanged.connect( self.filterChanged )

    def sort( self, ncol, order ):
        self.sourceModel( ).sort( ncol, order )

    def filterAcceptsRow( self, rowNumber, sourceParent ):
        return self.sourceModel( ).filterRow( rowNumber )
        
class TMDBTableModel( QAbstractTableModel ):
    mySummarySignal = pyqtSignal( int, tuple )
    disableEnableSignal = pyqtSignal( bool )
    emitMoviesHave = pyqtSignal( list )
    emitFilterChanged = pyqtSignal( )
    
    def __init__( self, parent = None ):
        super(TMDBTableModel, self).__init__( parent )
        self.parent = parent
        self.actualMovieData = []
        self.currentStatus = 0
        self.year = -1
        self.genre_id = -1
        self.genre = ''
        self.actors = [ ]
        self.movieName = ''
        self.sortColumn = 2
        self.filterStatus = 2
        self.filterRegexp = QRegExp( '.', Qt.CaseInsensitive,
                                     QRegExp.RegExp )

    def infoOnMovieAtRow( self, actualRow ):
        currentRow = self.actualMovieData[ actualRow ]
        tmdbmi = TMDBMovieInfo( self.parent, currentRow )        
        result = tmdbmi.exec_( )

    def filterRow( self, rowNumber ):
        if self.filterRegexp.indexIn( self.actualMovieData[ rowNumber ][ 0 ] ) == -1:
            return False
        if self.filterStatus == 2:
            return True
        elif self.filterStatus == 1:
            return self.actualMovieData[ rowNumber ][ -1 ] == False
        elif self.filterStatus == 0:
            return self.actualMovieData[ rowNumber ][ -1 ] == True
        
    def setCurrentStatus( self, status, tup):
        self.currentStatus = status
        if status == 0:
            self.year, self.genre_id, self.genre = tup
        elif status == 1:
            self.actors = list( tup )
        elif status == 2:
            self.movieName = max( tup )

    def setFilterStatus( self, filterStatus ):
        self.filterStatus = filterStatus
        self.sort( -1, Qt.AscendingOrder )
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
        return len( self.actualMovieData )

    def columnCount( self, parent ):
        return len( _headers ) - 1

    def headerData( self, col, orientation, role ):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant( _headers[ col ] )
        return QVariant( )
        
    #
    ## engine code, actually do the calculation
    def fillOutCalculation( self ):
        if self.currentStatus == 0:
            assert( self.year >= 1980 )
            assert( self.year <= datetime.datetime.now( ).year )
            assert( self.genre_id in plextmdb.TMDBEngine( ).getGenreIds( ) )
            #
            ## now do the stuff...
            actualMovieData = plextmdb.getMovieData( self.year, self.genre_id )
        elif self.currentStatus == 1:
            actualMovieData = plextmdb.get_movies_by_actors( self.actors )
        elif self.currentStatus == 2:
            actualMovieData = plextmdb.get_movies_by_title( self.movieName )

        #
        ## first remove all rows that exist
        initRowCount = self.rowCount( None )
        self.beginRemoveRows( QModelIndex( ), 0, initRowCount - 1 )
        self.endRemoveRows( )
        #
        ## now add in the data
        self.beginInsertRows( QModelIndex( ), 0, len( actualMovieData ) - 1 )
        self.actualMovieData = actualMovieData
        self.endInsertRows( )
        self.sort(2, Qt.AscendingOrder )
        if self.currentStatus == 0:
            self.mySummarySignal.emit( 0, ( self.year, self.genre,
                                            len( self.actualMovieData ) ) )
        elif self.currentStatus == 1:
            self.mySummarySignal.emit( 1, ( self.actors, len( self.actualMovieData ) ) )
        elif self.currentStatus == 2:
            self.mySummarySignal.emit( 2, ( self.movieName, len( self.actualMovieData ) ) )

    def emitMoviesHere( self, allMovieTitles ):
        tmdbmovietitles = set(map(lambda row: row[0], self.actualMovieData ) )
        self.emitMoviesHave.emit( sorted( tmdbmovietitles & set(allMovieTitles) ) )
        for row in self.actualMovieData:
            if row[0] in allMovieTitles:
                row[-1] = True
            else:
                row[-1] = False
        self.sort( -1, Qt.AscendingOrder )
        
    def sort( self, ncol, order ):
        #if ncol not in (0, 1, 2, 3 ):
        #    return
        self.sortColumn = ncol
        self.layoutAboutToBeChanged.emit( )
        if ncol == 2:
            self.actualMovieData.sort( key = lambda row: -row[2] )
        elif ncol in (0, 1 ):
            self.actualMovieData.sort( key = lambda row: row[ ncol ] )
        elif ncol == 3:
            self.actualMovieData.sort( key = lambda row: -float( row[ 3 ] ) )
        self.layoutChanged.emit( )

    def data( self, index, role ):
        if not index.isValid( ):
            return QVariant("")
        row = index.row( )
        col = index.column( )
        #
        ## color background role
        if role == Qt.BackgroundRole:
            isFound = self.actualMovieData[ row ][ -1 ]
            if not isFound:
                popularity = self.actualMovieData[ row ][ 2 ]
                h = numpy.log10( min( 100.0, popularity ) ) * 0.25
                s = 0.2
                v = 1.0
                alpha = 1.0
                color = QColor( 'white' )
                color.setHsvF( h, s, v, alpha )
                return QBrush( color )
            else:
                color = QColor( 'white' )
                color.setHsvF( 0.75, 0.15, 1.0, 1.0 )
                return QBrush( color )
        elif role == Qt.DisplayRole:
            if col in (0, 2, 3):
                return QVariant( self.actualMovieData[ row ][ col ] )
            else:
                dt = self.actualMovieData[ row ][ 1 ]
                return QVariant( dt.strftime('%d %b %Y') )
        
#
## long description delegate, creates an unmodifiable QTextEdit
class DescriptionDelegate( QStyledItemDelegate ):
    def __init__( self, owner ):
        super(DescriptionDelegate, self).__init__( owner )

    def createEditor( self, parent, option, index ):
        rowNumber = index.row( )
        colNumber = index.column( )
        model = index.model( )
        assert( colNumber in ( 0, 3 ) )
        myText = model.data( index, Qt.DisplayRole ).toString( )
        qto = QTextEdit( )
        qto.setReadOnly( True )
        qto.setLineWrapMode( QTextEdit.WidgetWidth )
        qto.setFixedWidth( 210 )
        qto.setFixedHeight( 56 )
        qto.setSizePolicy( QSizePolicy.Fixed )
        qto.setText( myText )
        return qto

    def setEditorData( self, editor, index ):
        model = index.model( )
        rowNumber = index.row( )
        colNumber = index.column( )
        assert( colNumber in (0, 3) )
        myText = model.data( index, Qt.DisplayRole ).toString( )
        editor.setText( myText )

class StringEntryDelegate( QStyledItemDelegate ):
    def __init__( self, owner ):
        super( StringEntryDelegate, self ).__init__( owner )

    def createEditor( self, parent, option, index ):
        model = index.model( )
        colNumber = index.column( )
        assert( colNumber in (1, 2) )
        if colNumber == 1:
            myText = model.data( index, Qt.DisplayRole ).toString( )
        else:
            myText = '%0.3f' % model.data( index, Qt.DisplayRole).toFloat()[0]
        return QLabel( myText )

    def setEditorData( self, editor, index ):
        model = index.model( )
        colNumber = index.column( )
        assert( colNumber in (1, 2) )
        if colNumber == 1:
            myText = model.data( index, Qt.DisplayRole ).toString( )
        else:
            myText = '%0.3f' % model.data( index, Qt.DisplayRole).toFloat()[0]
        editor.setText( myText ) 
