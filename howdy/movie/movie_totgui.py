import numpy, os, sys, requests, time
import logging, glob, datetime, pickle, gzip
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
#
from howdy import resourceDir
from howdy.movie import movie, movie_mygui, movie_gui
from howdy.core import core, core_gui
from howdy.core import QDialogWithPrinting, ProgressDialog, ProgressDialogThread
    
class HowdyMovieTotGUIThread( ProgressDialogThread ):
    
    movieDataRowsSignal = pyqtSignal( list )

    def __init__( self, parent, fullURL, token, movie_data_rows = None,
                  verify = False, time0 = -1 ):
        super( HowdyMovieTotGUIThread, self ).__init__(
            parent, 'PLEX MOVIE GUI PROGRESS WINDOW' )
        self.fullURL = fullURL
        self.token = token
        self.verify = verify
        self.movie_data_rows = movie_data_rows
        
    def run( self ):
        self.progress_dialog.show( )
        mystr = '0, started loading in movie data on %s.' % (
            datetime.datetime.now( ).strftime( '%B %d, %Y @ %I:%M:%S %p' ) )
        logging.info( mystr )
        self.emitString.emit( mystr )
        if self.movie_data_rows is None:
            self.movie_data_rows, _ = core.fill_out_movies_stuff(
                self.token, self.fullURL, verify = self.verify )
        mystr = '1, processed existing movie data in %0.3f seconds.' % (
            time.time( ) - self.time0 )
        logging.info( mystr )
        self.emitString.emit( mystr )
        time.sleep( 0.5 )
        mystr = '2, processed all movie data on %s.' % (
            datetime.datetime.now( ).strftime( '%B %d, %Y @ %I:%M:%S %p' ) )
        logging.info( mystr )
        self.emitString.emit( mystr )
        self.movieDataRowsSignal.emit( self.movie_data_rows )
        self.stopDialog.emit( )
        
class HowdyMovieTotGUI( QDialogWithPrinting ):
    emitNewToken = pyqtSignal( str )
    
    def process_movie_data_rows_init( self, movie_data_rows ):
        #
        ## now change everything
        self.setWindowTitle( 'PLEX MOVIE GUI' )
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #
        self.tmdb_gui = movie_gui.HowdyMovieGUI(
            self.token, self.fullurl, movie_data_rows, isIsolated = False,
            verify = self.verify )
        self.tmdb_mygui = movie_mygui.HowdyMovieMyGUI(
            self.token, movie_data_rows, isIsolated = False,
            verify = self.verify )
        self.tmdb_gui.movieRefreshRows.connect(
            self.tmdb_mygui.fill_out_movies )
        self.movie_data_rows = movie_data_rows
        #
        self.tabWidget.addTab(
            self.tmdb_gui, 'The List of Movies By Genre and Year' )
        self.tabWidget.addTab(
            self.tmdb_mygui, 'My Own Movies' )
        myLayout.addWidget( self.tabWidget )
        myLayout.addWidget( self.statusDialog )
        #
        ##
        self._setupActions( )
        #
        ##
        qf = QFont( )
        qf.setFamily( 'Consolas' )
        qf.setPointSize( int( 13 * self.resolution ) )
        qfm = QFontMetrics( qf )        
        #self.setFixedWidth( 130 * qfm.width( 'A' ) )
        #self.setFixedWidth( 700 )
        self.setFixedWidth( max(
            self.tmdb_gui.sizeHint( ).width( ),
            self.tmdb_mygui.sizeHint( ).width( ) ) )
        self.setFixedHeight( self.sizeHint( ).height( ) )
        self.show( )
        
    def __init__( self, fullurl, token, movie_data_rows = None,
                  doLarge = False, verify = True ):
        time0 = time.time( )
        super( HowdyMovieTotGUI, self ).__init__( None, doQuit = True )
        self.verify = verify
        self.resolution = 1.0
        if doLarge: self.resolution = 2.0
        tmdbEngine = movie.TMDBEngine( verify = verify )
        self.fullurl = fullurl
        self.token = token
        self.setStyleSheet("""
        QWidget {
        font-family: Consolas;
        font-size: %dpx;
        }""" % ( int( 13 * self.resolution ) ) )
        #
        self.helpDialog = HelpDialog( self )
        self.statusDialog = QLabel( )
        self.tabWidget = QTabWidget( self )
        self.tabWidget.setStyleSheet( 'QTabBar::tab { width: 340px; }' )
        self.hide( )
        #self.progress_dialog = ProgressDialog(
        #    self, 'PLEX MOVIE GUI PROGRESS WINDOW' )
        #
        ## have this happen in background, hope it works without crashing...
        self.mainInitThread = HowdyMovieTotGUIThread(
            self, fullurl, token, movie_data_rows = movie_data_rows,
            verify = self.verify, time0 = time0 )
        self.mainInitThread.movieDataRowsSignal.connect(
            self.process_movie_data_rows_init )
        self.mainInitThread.start( ) # make the magic start...

    def _setupActions( self ):
        helpAction = QAction( self )
        helpAction.setShortcut( 'Shift+Ctrl+H' )
        helpAction.triggered.connect( self.helpDialog.show )
        self.addAction( helpAction )
        #
        loginAction = QAction( self )
        loginAction.setShortcut( 'Shift+Ctrl+M' )
        loginAction.triggered.connect( self.refresh_tokens )
        self.addAction( loginAction )
        #
        def leftTab( ): self.tabWidget.setCurrentIndex( 0 )
        def rightTab( ): self.tabWidget.setCurrentIndex( 1 )
        def refresh( ):
            qdl = QDialog( self )
            qdl.setModal( True )
            myLayout = QVBoxLayout( )
            qdl.setLayout( myLayout )
            mainColor = qdl.palette().color( QPalette.Background )
            qlb = QLabel( '\n'.join([ "REFRESHING MOVIE LIST", "BE PATIENT!" ]) )
            qlb.setStyleSheet("""
            QLabel {
            background-color: #373949;
            }""" )
            myLayout.addWidget( qlb )
            qdl.setFixedWidth( 450 )
            qdl.setFixedHeight( qdl.sizeHint( ).height( ) )
            qdl.show( )
            movie_data_rows, _ = core.fill_out_movies_stuff(
                self.token, self.fullURL, verify = self.verify )
            self.tmdb_gui.fill_out_movies( movie_data_rows = movie_data_rows )
            self.tmdb_mygui.fill_out_movies( movie_data_rows = movie_data_rows )
            qdl.close( )
        leftTabAction = QAction( self )
        leftTabAction.setShortcut( 'Ctrl+1' )
        leftTabAction.triggered.connect( leftTab )
        self.addAction( leftTabAction )
        rightTabAction = QAction( self )
        rightTabAction.setShortcut( 'Ctrl+2' )
        rightTabAction.triggered.connect( rightTab )
        self.addAction( rightTabAction )
        refreshAction = QAction( self )
        refreshAction.setShortcut( 'Ctrl+R' )
        refreshAction.triggered.connect( refresh )
        self.addAction( refreshAction )
        #
        self.emitNewToken.connect( self.tmdb_gui.setNewToken )
        self.emitNewToken.connect( self.tmdb_mygui.setNewToken )

    def refresh_movies( self ):
        self.statusDialog.setText( 'REFRESHING MOVIES' )
        movie_data_rows, _ = core.fill_out_movie_stuff(
            fullurl = self.fullurl, token = self.token )
        self.tmdb_gui.fill_out_movies( movie_data_rows )
        self.tmdb_mygui.fill_out_movies( movie_data_rows )
        self.movie_data_rows = movie_data_rows
        self.tmdb_gui.emitMovieList( )
        self.statusDialog.setText( 'FINISHED REFRESHING MOVIES' )

    def refresh_tokens( self ):
        self.statusDialog.setText( 'RELOGGING CREDENTIALS' )
        self.fullurl, self.token = core_gui.returnToken( )
        self.emitNewToken.emit( self.token )
        self.statusDialog.setText( 'FINISHED RELOGGING CREDENTIALS' )

    def contextMenuEvent( self, event ):
        menu = QMenu( self )
        if not os.path.isdir( os.path.expanduser( '~/.config/howdy/tests' ) ):
            os.mkdir( os.path.expanduser( '~/.config/howdy/tests' ) )
        testDir = os.path.expanduser( '~/.config/howdy/tests' )
        def save_menu_rows( ):
            movieRowsFile = os.path.join(
                testDir, 'movie_data_rows.pkl.gz' )
            pickle.dump(
                self.movie_data_rows,
                gzip.open( movieRowsFile, 'wb' ) )
            
        saveAction = QAction( 'Save Movie Rows', menu )
        saveAction.triggered.connect( save_menu_rows )
        menu.addAction( saveAction )
        menu.popup( QCursor.pos( ) )

class HelpDialog( QDialog ):    
    def __init__( self, parent ):
        super( HelpDialog, self ).__init__( parent )
        self.setModal( True )
        self.setWindowTitle( 'HELP WINDOW' )
        layout = QVBoxLayout( )
        self.setLayout( layout )
        qf = QFont( )
        qf.setPointSize( int( 12 * parent.resolution ) )
        qfm = QFontMetrics( qf )
        width = qfm.boundingRect( ''.join(['A'] * 55)).width( )
        self.setFixedWidth( width )
        self.setFixedHeight( 450 )
        #
        myTextArea = QTextEdit( )
        myTextArea.setReadOnly( True )
        myTextArea.setHtml( open( os.path.join(
            resourceDir,
            'plex_tmdb_totgui_help.html' ), 'r' ).read( ) )
        layout.addWidget( myTextArea )
        self.hide( )
        #
        self.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )

    def closeEvent( self, evt ):
        self.hide( )
