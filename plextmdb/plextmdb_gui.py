import numpy, os, sys, requests, json, base64
import logging, glob, datetime, textwrap, titlecase
from . import plextmdb, mainDir, plextmdb_torrents
from PyQt4.QtCore import *
from PyQt4.QtGui import *
#
sys.path.append( mainDir )
from plexcore import plexcore

_headers = [ 'title', 'release date', 'popularity', 'rating', 'overview' ]
_colmap = { 0 : 'title',
            1 : 'release_date',
            2 : 'popularity',
            3 : 'vote_average' }

class TMDBMovieInfo( QDialog ):
    def screenGrab( self ):
        fname = str( QFileDialog.getSaveFileName(
            self, 'Save Screenshot', os.path.expanduser( '~' ),
            filter = '*.png' ) )
        if len( os.path.basename( fname.strip( ) ) ) == 0: return
        if not fname.lower( ).endswith( '.png' ):
            fname = '%s.png' % fname
        qpm = QPixmap.grabWidget( self )
        qpm.save( fname )
    
    def __init__( self, parent, datum, verify = True ):
        super( TMDBMovieInfo, self ).__init__( parent )
        self.token = parent.token
        self.title = datum[ 'title' ]
        self.setModal( True )
        self.verify = verify
        #
        full_info = datum[ 'overview' ]
        movie_full_path = datum[ 'poster_path' ]
        release_date = datum[ 'release_date' ]
        popularity = datum[ 'popularity' ]
        isFound = datum[ 'isFound' ]
        #
        myLayout = QVBoxLayout( )
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
        myLayout.addWidget(
            QLabel( 'RELEASE DATE: %s' % release_date.strftime( '%d %b %Y' ) ) )
        myLayout.addWidget( QLabel(
            'POPULARITY: %0.3f' % popularity ) )
        qte = QTextEdit( full_info )
        qte.setReadOnly( True )
        qte.setStyleSheet("""
        QTextEdit {
        background-color: #373949;
        }""" )
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
        printAction = QAction( self )
        printAction.setShortcut( 'Shift+Ctrl+P' )
        printAction.triggered.connect( self.screenGrab )
        self.addAction( printAction )
        #
        self.setFixedWidth( 450 )
        self.setFixedHeight( self.sizeHint( ).height( ) )
        self.show( )

    def launchTorrentWindow( self ):
        maxnum = int( self.numEntriesComboBox.currentText( ) )
        bypass = self.yesRadioButton.isChecked( )
        tmdbt = TMDBTorrents(
            self, self.token, self.title,
            bypass = bypass, maxnum = maxnum )
        result = tmdbt.exec_( )

class TMDBRadioButton( QRadioButton ):
    def __init__( self, text, value = None, parent = None ):
        super( TMDBRadioButton, self ).__init__( text, parent = parent )
        if value is not None: self.value = value
        else: self.value = text
        
class TMDBTorrents( QDialog ):
    def screenGrab( self ):
        fname = str( QFileDialog.getSaveFileName(
            self, 'Save Screenshot', os.path.expanduser( '~' ),
            filter = '*.png' ) )
        if len( os.path.basename( fname.strip( ) ) ) == 0: return
        if not fname.lower( ).endswith( '.png' ): fname = '%s.png' % fname
        qpm = QPixmap.grabWidget( self )
        qpm.save( fname )
    
    def __init__( self, parent, token, movie_name, bypass = False, maxnum = 10,
                  do_debug = False ):
        super( TMDBTorrents, self ).__init__( parent )
        self.setModal( True )
        self.token = token
        self.movie = movie_name
        self.setWindowTitle( 'MOVIE TORRENT DOWNLOAD' )
        self.statusLabel = QLabel( )
        self.summaryButton = QPushButton( 'SUMMARY' )
        self.sendButton = QPushButton( 'SEND' )
        self.downloadButton = QPushButton( 'DOWNLOAD' )
        self.addButton = QPushButton( 'ADD' )
        self.summaryButton.setEnabled( False )
        myButtonGroup = QButtonGroup( self )
        mainLayout = QVBoxLayout( )
        self.setLayout( mainLayout )
        self.torrentStatus = -1
        self.do_debug = do_debug
        #
        ##
        if parent is not None: self.verify = parent.verify
        else: self.verify = False
        if not bypass:
            data, status = plextmdb_torrents.get_movie_torrent(
                movie_name, verify = self.verify )
        else: status = 'FALURE'
        if status == 'SUCCESS':
            self.torrentStatus = 0
            self.data = { }
            for actmovie in data:
                title = actmovie[ 'title' ]
                allmovies = list(
                    filter(lambda tor: 'quality' in tor and '3D' not in tor['quality'],
                           actmovie['torrents'] ) )
                if len( allmovies ) == 0: continue
                allmovies2 = list(
                    filter(lambda tor: '720p' in tor['quality'], allmovies ) )
                if len( allmovies2 ) == 0: allmovies2 = allmovies
                url = allmovies2[0]['url']
                self.data[ title ] = requests.get( url ).content
            self.allRadioButtons = list(
                map(lambda name: TMDBRadioButton( name, name, self ),
                    sorted( self.data.keys( ) ) ) )
            self.statusLabel.setText( 'SUCCESS' )
        else: # now use Jackett for downloading movies
            #data, status = plextmdb.get_movie_torrent_kickass( movie_name, maxnum = maxnum )
            #data, status = plextmdb_torrents.get_movie_torrent_rarbg( movie_name, maxnum = maxnum )
            data, status = plextmdb_torrents.get_movie_torrent_jackett(
                movie_name, maxnum = maxnum, verify = verify )
            if status == 'SUCCESS':
                self.torrentStatus = 1
                self.data = { }
                logging.debug('DATA = %s' % data )
                for datum in data:
                    name = datum['title']
                    seeders = datum['seeders']
                    leechers = datum['leechers']
                    link = datum['link']
                    self.data[ name ] = ( seeders, leechers, link )
                self.allRadioButtons = list(
                    map(lambda name:
                        TMDBRadioButton( name, name, self ),
                        sorted( self.data.keys( ),
                                key = lambda nm: sum( self.data[nm][:2] ) )[::-1] ) )
                self.statusLabel.setText( 'SUCCESS' )
            else:
                self.torrentStatus = 2
                self.statusLabel.setText( 'FAILURE, COULD NOT FIND.' )
                self.sendButton.setEnabled( False )
                self.downloadButton.setEnabled( False )
        #
        topWidget = QWidget( self )
        topLayout = QHBoxLayout( )
        topWidget.setLayout( topLayout )
        topLayout.addWidget( self.summaryButton )
        topLayout.addWidget( self.sendButton )
        topLayout.addWidget( self.downloadButton )
        topLayout.addWidget( self.addButton )
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
        printAction = QAction( self )
        printAction.setShortcut( 'Shift+Ctrl+P' )
        printAction.triggered.connect( self.screenGrab )
        self.addAction( printAction )
        #
        self.setFixedWidth( 550 )
        self.setFixedWidth( max( 650, self.sizeHint( ).height( ) ) )
        self.show( )

    def showSummaryChosen( self ):
        whichChosen = max(
            map(lambda qbut: qbut.value,
                filter( lambda qbut: qbut.isChecked( ),
                        self.allRadioButtons ) ) )
        numSeeds, numLeeches, url = self.data[ whichChosen ]
        qdl = QDialog( self )
        mainColor = qdl.palette().color( QPalette.Background )
        qlayout = QVBoxLayout( )
        qte = QTextEdit( textwrap.fill( 'URL: %s' % url ) )
        qte.setReadOnly( True )
        qdl.setLayout( qlayout )
        qdl.setWindowTitle( whichChosen )
        qlayout.addWidget( QLabel( 'SEEDS + LEECHES: %d' % (
            numSeeds + numLeeches ) ) )
        qlayout.addWidget( qte )
        qdl.setFixedWidth( qdl.sizeHint( ).width( ) )
        qdl.setFixedHeight( qdl.sizeHint( ).height( ) )
        qdl.show( )
        result = qdl.exec_( )

    def chooseSentTorrent( self ):
        jsondata = { 'torrentStatus' : self.torrentStatus,
                     'token' : self.token }
        if self.torrentStatus in ( 0, 1 ):
            whichChosen = max(
                map(lambda qbut: str( qbut.text( ) ),
                    filter( lambda qbut: qbut.isChecked( ),
                            self.allRadioButtons ) ) )
        if self.torrentStatus == 0:
            jsondata['movie'] = whichChosen
            jsondata['data'] = base64.b64encode(
                self.data[ whichChosen ] ).decode('utf-8')
        elif self.torrentStatus == 1:
            _, _, url = self.data[ whichChosen ]
            jsondata[ 'movie' ] = self.movie
            jsondata[ 'data' ] = url
        else: jsondata[ 'movie' ] = self.movie

        if self.do_debug:
            json.dump(
                jsondata, open(
                    '%s.json' % '_'.join( os.path.basename( self.movie ).split( ) ), 'w' ) )

        response = requests.post(
            'https://tanimislam.ddns.net/flask/plex/sendmovieemail', json = jsondata,
            verify = self.verify )
        if response.status_code == 200:
            self.statusLabel.setText(
                'sent request for "%s"' % jsondata['movie'] )
        else: self.statusLabel.setText( 'ERROR: %s' % response.content )

    def chooseDownloadTorrent( self ):
        if self.torrentStatus not in ( 0, 1 ):
            return
        whichChosen = max( map( lambda qbut: qbut.value,
                                filter( lambda qbut: qbut.isChecked( ),
                                        self.allRadioButtons ) ) )
        #
        ## followed advice from http://stackoverflow.com/questions/4286036/how-to-have-a-directory-dialog-in-pyqt
        dirName = str( QFileDialog.getExistingDirectory(
            self, 'Choose directory to put torrent or magnet.') )
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
            

class TMDBGUI( QDialog ):
    movieSendList = pyqtSignal( list )
    movieRefreshRows = pyqtSignal( list )

    def screenGrab( self ):
        fname = str( QFileDialog.getSaveFileName(
            self, 'Save Screenshot', os.path.expanduser( '~' ),
            filter = '*.png' ) )
        if len( os.path.basename( fname.strip( ) ) ) == 0:
            return
        if not fname.lower( ).endswith( '.png' ):
            fname = fname + '.png'
        qpm = QPixmap.grabWidget( self )
        qpm.save( fname )
    
    def __init__( self, token, fullURL, movie_data_rows, isIsolated = True,
                  verify = True ):
        super( TMDBGUI, self ).__init__( )
        tmdbEngine = plextmdb.TMDBEngine( verify = verify )
        self.verify = verify
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
            printAction = QAction( self )
            printAction.setShortcut( 'Shift+Ctrl+P' )
            printAction.triggered.connect( self.screenGrab )
            self.addAction( printAction )
        #
        ##
        self.show( )

    def _connectTMDBGUIActions( self ):
        self.movieSendList.connect( self.tmdbtv.tm.emitMoviesHere )

    def _connectSelectYearGenreWidget( self ):
        self.sygWidget.mySignalSYG.connect( self.tmdbtv.tm.currentStatus )
        self.sygWidget.mySignalAndFill.connect( self.tmdbtv.tm.currentStatusAndFill )
        self.sygWidget.pushDataButton.clicked.connect( self.tmdbtv.tm.fillOutCalculation )
        self.sygWidget.pushDataButton.clicked.connect( self.sdWidget.enableMatching )
        self.sygWidget.pushDataButton.clicked.connect( self.emitMovieList )
        self.sygWidget.actorNamesLineEdit.returnPressed.connect( self.emitMovieList )
        self.sygWidget.actorNamesLineEdit.returnPressed.connect( self.sdWidget.enableMatching )
        self.sygWidget.movieNameLineEdit.returnPressed.connect( self.emitMovieList )
        self.sygWidget.movieNameLineEdit.returnPressed.connect( self.sdWidget.enableMatching )
        self.sygWidget.refreshDataButton.clicked.connect( self.refreshMovies )
        self.sygWidget.mySignalSYG.connect( self.sdWidget.setYearGenre )
        self.sygWidget.emitSignalSYG( )

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
        self.all_movies = list(map(
            lambda row: { 'title' : row['title'], 'year' : row['releasedate'].year }, movie_data_rows ))
        self.tmdbtv.tm.layoutAboutToBeChanged.emit( )
        self.tmdbtv.tm.layoutChanged.emit( ) # change the colors in the rows, if already there

    def setNewToken( self, newToken ):
        self.token = newToken

    def refreshMovies( self ):
        movie_data_rows, _ = plexcore.fill_out_movies_stuff(
            self.token, fullURL = self.fullURL, verify = self.verify )
        self.fill_out_movies( movie_data_rows )
        self.movieRefreshRows.emit( movie_data_rows )
        
class StatusDialogWidget( QWidget ):
    emitStatusToShow = pyqtSignal( int )

    def screenGrab( self ):
        fname = str( QFileDialog.getSaveFileName( self, 'Save Screenshot',
                                                  os.path.expanduser( '~' ),
                                                  filter = '*.png' ) )
        if len( os.path.basename( fname.strip( ) ) ) == 0:
            return
        if not fname.lower( ).endswith( '.png' ):
            fname = fname + '.png'
        qpm = QPixmap.grabWidget( self )
        qpm.save( fname )
    
    class MovieListDialog( QDialog ):
        def screenGrab( self ):
            fname = str( QFileDialog.getSaveFileName( self, 'Save Screenshot',
                                                      os.path.expanduser( '~' ),
                                                      filter = '*.png' ) )
            if len( os.path.basename( fname.strip( ) ) ) == 0:
                return
            if not fname.lower( ).endswith( '.png' ):
                fname = fname + '.png'
            qpm = QPixmap.grabWidget( self )
            qpm.save( fname )
        
        def __init__( self, parent, movieList ):
            super( StatusDialogWidget.MovieListDialog, self ).__init__( parent )
            self.setWindowTitle( 'MOVIE LIST FOR %d.' % parent.currentYear )
            self.setModal( True )
            #
            qte = QTextEdit('\n'.join( [
                '%d movies in library\n\n' % len( movieList ),
                '\n'.join(movieList) ] ) )
            qte.setStyleSheet("""
            QTextEdit {
            background-color: #373949;
            }""" )
            qte.setReadOnly( True )
            myLayout = QVBoxLayout( )
            self.setLayout( myLayout )
            #
            printAction = QAction( self )
            printAction.setShortcut( 'Shift+Ctrl+P' )
            printAction.triggered.connect( self.screenGrab )
            self.addAction( printAction )
            #
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
        myLayout.addWidget( self.statusLabel, 0, 0, 2, 2 )
        myLayout.addWidget( self.progressLabel, 0, 2, 2, 2 )
        myLayout.addWidget( self.showStatusComboBox, 0, 4, 2, 2 )
        myLayout.addWidget( QLabel( 'MOVIE NAME:' ), 2, 0, 1, 1 )
        myLayout.addWidget( self.movieNameLineEdit, 2, 1, 1, 3 )
        #
        printAction = QAction( self )
        printAction.setShortcut( 'Shift+Ctrl+P' )
        printAction.triggered.connect( self.screenGrab )
        self.addAction( printAction )
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
            background-color: #373949;
            }""" )
            myLayout.addWidget( qte )
            dlg.setFixedWidth( dlg.sizeHint( ).width( ) )
            dlg.setFixedHeight( 450 )
            qte.setPlainText('\n'.join([
                '%02d: %s' % ( idx + 1, title ) for
                (idx, title ) in
                enumerate( self.movieTitles )  ]) )
            dlg.show( )
            result = dlg.exec_( )
        
class SelectYearGenreWidget( QWidget ):
    mySignalSYG = pyqtSignal( int, tuple )
    mySignalAndFill = pyqtSignal( int, tuple )

    def screenGrab( self ):
        fname = str( QFileDialog.getSaveFileName( self, 'Save Screenshot',
                                                  os.path.expanduser( '~' ),
                                                  filter = '*.png' ) )
        if len( os.path.basename( fname.strip( ) ) ) == 0:
            return
        if not fname.lower( ).endswith( '.png' ):
            fname = fname + '.png'
        qpm = QPixmap.grabWidget( self )
        qpm.save( fname )
    
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
        self.genreComboBox.addItems( sorted( plextmdb.TMDBEngine( parent.verify ).getGenres( ) ) )
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
        printAction = QAction( self )
        printAction.setShortcut( 'Shift+Ctrl+P' )
        printAction.triggered.connect( self.screenGrab )
        self.addAction( printAction )
        self.isFinished = False
        #
        self.yearSpinBox.valueChanged.connect( self.emitSignalSYG )
        self.genreComboBox.currentIndexChanged.connect( self.emitSignalSYG )
        self.yearSpinBox.installEventFilter( self )
        self.genreComboBox.installEventFilter( self )
        #
        ## now another signal but this time also fill TMDBDataModel
        self.actorNamesLineEdit.returnPressed.connect( self.emitSignalAndFill )
        self.movieNameLineEdit.returnPressed.connect( self.emitSignalAndFill )

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
            
    def emitSignalSYG( self ):
        state = self.qbg.checkedId( )
        if state == 0:
            year = self.yearSpinBox.value( )
            genre = str(self.genreComboBox.currentText( ))
            genre_id = plextmdb.TMDBEngine( self.parent.verify ).getGenreIdFromGenre( genre )
            self.mySignalSYG.emit( state, ( year, genre_id, genre ) )
        elif state == 1:
            actors = tuple(map(lambda tok: titlecase.titlecase( ' '.join( tok.strip( ).split( ) ) ),
                               str( self.actorNamesLineEdit.text( ) ).strip( ).split(',') ) )
            self.mySignalSYG.emit( state, actors )
        elif state == 2:
            movieName = str( self.movieNameLineEdit.text( ) ).strip( )
            self.mySignalSYG.emit( state, ( movieName, ) )

    def emitSignalAndFill( self ):
        state = self.qbg.checkedId( )
        if state == 0: return
        if state == 1:
            actors = tuple(map(lambda tok: titlecase.titlecase( ' '.join( tok.strip( ).split( ) ) ),
                               str( self.actorNamesLineEdit.text( ) ).strip( ).split(',') ) )
            self.mySignalAndFill.emit( state, actors )
        elif state == 2:
            movieName = str( self.movieNameLineEdit.text( ) ).strip( )
            self.mySignalAndFill.emit( state, ( movieName, ) )
        
            
#
## now the table, table model, and cell objects.
class TMDBTableView( QTableView ):
    def __init__( self, parent ):
        super(TMDBTableView, self).__init__( parent )
        #
        self.token = parent.token
        self.tm = TMDBTableModel( self, parent.verify )
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
    
    def __init__( self, parent = None, verify = True ):
        super(TMDBTableModel, self).__init__( parent )
        self.parent = parent
        self.verify = verify
        self.actualMovieData = [ ]
        self.sortColumn = 2
        self.filterStatus = 2
        self.filterRegexp = QRegExp( '.', Qt.CaseInsensitive,
                                     QRegExp.RegExp )
        #
        ## stuff passed through
        self.status = -1
        self.year = -1
        self.genre_id = -1
        self.genre = ''
        self.movieName = ''

    def infoOnMovieAtRow( self, actualRow ):
        datum = self.actualMovieData[ actualRow ]
        tmdbmi = TMDBMovieInfo( self.parent, datum, verify = self.verify )
        result = tmdbmi.exec_( )

    def filterRow( self, rowNumber ):
        datum = self.actualMovieData[ rowNumber ]
        if self.filterRegexp.indexIn( datum[ 'title' ] ) == -1:
            return False
        if self.filterStatus == 2:
            return True
        elif self.filterStatus == 1:
            return datum[ 'isFound' ] == False
        elif self.filterStatus == 0:
            return datum[ 'isFound' ] == True

    def setFilterStatus( self, filterStatus ):
        self.filterStatus = filterStatus
        self.sort( -1, Qt.AscendingOrder )
        self.emitFilterChanged.emit( )

    def setFilterString( self, text ):
        mytext = str( text ).strip( )
        if len( mytext ) == 0: mytext = '.'
        self.filterRegexp = QRegExp(
            mytext, Qt.CaseInsensitive, QRegExp.RegExp )
        self.emitFilterChanged.emit( )

    def rowCount( self, parent ):
        return len( self.actualMovieData )

    def columnCount( self, parent ):
        return len( _headers ) - 1

    def headerData( self, col, orientation, role ):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return _headers[ col ]
        return None

    def currentStatus( self, status, tup ):
        assert( status in ( 0, 1, 2, ) )
        self.status = status
        if status == 0:
            self.year, self.genre_id, self.genre = tup
        elif status == 1:
            self.actors = list( tup )
        elif status == 2:
            self.movieName = max( tup )

    def currentStatusAndFill( self, status, tup ):
        assert( status in ( 0, 1, 2, ) )
        if status == 0: return
        self.status = status
        if status == 1:
            self.actors = list( tup )
        elif status == 2:
            self.movieName = max( tup )
        self.fillOutCalculation( )
    
    #
    ## engine code, actually do the calculation
    def fillOutCalculation( self ):
        if self.status == 0:
            assert( self.year >= 1980 )
            assert( self.year <= datetime.datetime.now( ).year )
            assert( self.genre_id in plextmdb.TMDBEngine(
                self.verify ).getGenreIds( ) )
            #
            ## now do the stuff...
            actualMovieData = plextmdb.getMovieData(
                self.year, self.genre_id, verify = self.verify )
        elif self.status == 1:
            actualMovieData = plextmdb.get_movies_by_actors(
                self.actors, verify = self.verify )
        elif self.status == 2:
            actualMovieData = plextmdb.get_movies_by_title(
                self.movieName, verify = self.verify )

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
        if self.status == 0:
            self.mySummarySignal.emit(
                0, ( self.year, self.genre,
                     len( self.actualMovieData ) ) )
        elif self.status == 1:
            self.mySummarySignal.emit(
                1, ( self.actors, len( self.actualMovieData ) ) )
        elif self.status == 2:
            self.mySummarySignal.emit(
                2, ( self.movieName, len( self.actualMovieData ) ) )

    def emitMoviesHere( self, allMoviesInPlex ):
        tmdbmovietitles = set(map(
            lambda datum: ( datum[ 'title' ],
                            datum[ 'release_date' ].year ),
            self.actualMovieData ) )
        allmoviesinplex_set = set(map(
            lambda datum: ( datum[ 'title' ],
                            datum[ 'year' ] ), allMoviesInPlex ) )
        self.emitMoviesHave.emit( sorted( tmdbmovietitles & allmoviesinplex_set ) )
        for datum in self.actualMovieData:
            tup = ( datum['title'], datum['release_date'].year )
            if tup in allmoviesinplex_set:
                datum[ 'isFound' ] = True
            else:
                datum[ 'isFound' ] = False
        self.sort( -1, Qt.AscendingOrder )
        
    def sort( self, ncol, order ):
        #if ncol not in (0, 1, 2, 3 ):
        #    return
        self.sortColumn = ncol
        self.layoutAboutToBeChanged.emit( )
        
        if ncol == 2:
            self.actualMovieData.sort(
                key = lambda datum: -datum[ 'popularity' ] )
        elif ncol in (0, 1 ):
            self.actualMovieData.sort(
                key = lambda datum: datum[ _colmap[ ncol ] ] )
        elif ncol == 3:
            self.actualMovieData.sort(
                key = lambda datum: -datum[ 'vote_average' ] )
        self.layoutChanged.emit( )

    def data( self, index, role ):
        if not index.isValid( ):
            return ""
        row = index.row( )
        col = index.column( )
        datum = self.actualMovieData[ row ]
        #
        ## color background role
        if role == Qt.BackgroundRole:
            isFound = datum[ 'isFound' ]
            if not isFound:
                popularity = datum[ 'popularity' ]
                hpop = numpy.log10( max( 1.0, popularity ) ) * 0.5
                hpop = min( 1.0, hpop )
                h = hpop * ( 0.81 - 0.45 ) + 0.45
                s = 0.85
                v = 0.31
                color = QColor( 'white' )
                color.setHsvF( h, s, v, 1.0 )
                return QBrush( color )
            else:
                #color = QColor( 'white' )
                #color.setHsvF( 0.45, 0.85, 0.31, 1.0 )
                return QBrush( QColor( "#873600" ) )
            
        elif role == Qt.DisplayRole:
            if col in (0, 2, 3):
                return datum[ _colmap[ col ] ]
            else:
                return datum[ 'release_date' ].strftime(
                    '%d %b %Y' )
        
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
        if colNumber == 1: myText = model.data(
                index, Qt.DisplayRole ).toString( )
        else: myText = '%0.3f' % model.data(
                index, Qt.DisplayRole ).toFloat( )[0]
        return QLabel( myText )

    def setEditorData( self, editor, index ):
        model = index.model( )
        colNumber = index.column( )
        assert( colNumber in (1, 2) )
        if colNumber == 1: myText = model.data(
                index, Qt.DisplayRole ).toString( )
        else: myText = '%0.3f' % model.data(
                index, Qt.DisplayRole).toFloat()[0]
        editor.setText( myText )
