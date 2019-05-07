import numpy, os, sys, requests
import logging, glob, datetime, pickle, gzip
from . import plextmdb, plextmdb_mygui, plextmdb_gui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from plexcore import plexcore, plexcore_gui

class TMDBTotGUI( QWidget ):
    emitNewToken = pyqtSignal( str )

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
    
    def __init__( self, fullurl, token, movie_data_rows = None, doLarge = False,
                  verify = True ):
        super( TMDBTotGUI, self ).__init__( )
        self.resolution = 1.0
        if doLarge: self.resolution = 2.0
        self.setWindowTitle('PLEX MOVIE GUI')
        tmdbEngine = plextmdb.TMDBEngine( verify = verify )
        self.fullurl = fullurl
        self.token = token
        self.setStyleSheet("""
        QWidget {
        font-family: Consolas;
        font-size: %d;
        }""" % ( int( 11 * self.resolution ) ) )
        #
        if movie_data_rows is None:
            movie_data_rows, _ = plexcore.fill_out_movies_stuff(
                self.token, fullurl = self.fullurl )            
        self.tmdb_gui = plextmdb_gui.TMDBGUI( token, fullurl, movie_data_rows, isIsolated = False,
                                              verify = verify )
        self.tmdb_mygui = plextmdb_mygui.TMDBMyGUI( token, movie_data_rows, isIsolated = False,
                                                    verify = verify )
        self.tmdb_gui.movieRefreshRows.connect( self.tmdb_mygui.fill_out_movies )
        self.helpDialog = HelpDialog( self )
        self.statusDialog = QLabel( )
        self.tabWidget = QTabWidget( self )
        self.tabWidget.setStyleSheet( 'QTabBar::tab { width: 340px; }' )
        #
        mainLayout = QVBoxLayout( )
        self.setLayout( mainLayout )
        #
        self.tabWidget.addTab( self.tmdb_gui,
                               'The List of Movies By Genre and Year' )
        self.tabWidget.addTab( self.tmdb_mygui,
                               'My Own Movies' )
        mainLayout.addWidget( self.tabWidget )
        mainLayout.addWidget( self.statusDialog )
        #
        printAction = QAction( self )
        printAction.setShortcut( 'Ctrl+P' )
        printAction.triggered.connect( self.screenGrab )
        self.addAction( printAction )
        #
        ##
        self._setupActions( )
        #
        ##
        qf = QFont( )
        qf.setFamily( 'Consolas' )
        qf.setPointSize( int( 11 * self.resolution ) )
        qfm = QFontMetrics( qf )        
        #self.setFixedWidth( 150 * qfm.width( 'A' ) )
        self.setFixedWidth( 700 )
        self.show( )

    def _setupActions( self ):
        quitAction = QAction( self )
        quitAction.setShortcuts( [ 'Ctrl+Q', 'Esc' ] )
        quitAction.triggered.connect( sys.exit )
        self.addAction( quitAction )
        #
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
            movie_data_rows, _ = plexcore.fill_out_movies_stuff( self.token, fullurl = self.fullurl )
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
        movie_data_rows, _ = plexcore.fill_out_movie_stuff( fullurl = self.fullurl,
                                                            token = self.token )
        self.tmdb_gui.fill_out_movies( movie_data_rows )
        self.tmdb_mygui.fill_out_movies( movie_data_rows )
        self.tmdb_gui.emitMovieList( )
        self.statusDialog.setText( 'FINISHED REFRESHING MOVIES' )

    def refresh_tokens( self ):
        self.statusDialog.setText( 'RELOGGING CREDENTIALS' )
        self.fullurl, self.token = plexcore_gui.returnToken( )
        self.emitNewToken.emit( self.token )
        self.statusDialog.setText( 'FINISHED RELOGGING CREDENTIALS' )

class HelpDialog( QDialog ):
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
    
    def __init__( self, parent ):
        from . import mainDir
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
        printAction = QAction( self )
        printAction.setShortcut( 'Shift+Ctrl+P' )
        printAction.triggered.connect( self.screenGrab )
        self.addAction( printAction )
        #
        myTextArea = QTextEdit( )
        myTextArea.setReadOnly( True )
        myTextArea.setHtml( open( os.path.join( mainDir, 'docs', 'plex_tmdb_totgui_help.html' ), 'r' ).read( ) )
        layout.addWidget( myTextArea )
        self.hide( )
        #
        self.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )

    def closeEvent( self, evt ):
        self.hide( )
