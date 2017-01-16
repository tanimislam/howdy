import numpy, os, sys, requests
import logging, glob, datetime, pickle, gzip
from . import mainDir, plextmdb, plextmdb_mygui, plextmdb_gui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
sys.path.append( mainDir )
from plexcore import plexcore, plexcore_gui

class TMDBTotGUI( QWidget ):
    emitNewToken = pyqtSignal( str )

    def __init__( self, fullurl, token, movie_data_rows = None ):
        super( TMDBTotGUI, self ).__init__( )
        self.setWindowTitle('PLEX MOVIE GUI')
        tmdbEngine = plextmdb.TMDBEngine( )
        self.fullurl = fullurl
        self.token = token
        self.setStyleSheet("""
        QWidget {
        font-family: Consolas;        
        }""")
        #
        if movie_data_rows is None:
            movie_data_rows, _ = plexcore.fill_out_movies_stuff( self.token, fullurl = self.fullurl )
        self.tmdb_gui = plextmdb_gui.TMDBGUI( token, fullurl, movie_data_rows, isIsolated = False )
        self.tmdb_mygui = plextmdb_mygui.TMDBMyGUI( token, movie_data_rows, isIsolated = False )
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
        #
        mainLayout.addWidget( self.statusDialog )
        #
        ##
        self._setupActions( )
        #
        ##
        self.setFixedWidth( 750 )
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
        def leftTab( ):
            self.tabWidget.setCurrentIndex( 0 )
        def rightTab( ):
            self.tabWidget.setCurrentIndex( 1 )
        def refresh( ):
            qdl = QDialog( self )
            qdl.setModal( True )
            myLayout = QVBoxLayout( )
            qdl.setLayout( myLayout )
            mainColor = qdl.palette().color( QPalette.Background )
            qlb = QLabel( '\n'.join([ "REFRESHING MOVIE LIST", "BE PATIENT!" ]) )
            qlb.setStyleSheet("""
            QLabel {
            background-color: %s;
            }""" % mainColor.name( ) )
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
    def __init__( self, parent ):
        super( HelpDialog, self ).__init__( parent )
        self.setModal( True )
        self.setWindowTitle( 'HELP WINDOW' )
        layout = QVBoxLayout( )
        self.setLayout( layout )
        qf = QFont( )
        qf.setPointSize( 12 )
        qfm = QFontMetrics( qf )
        width = qfm.boundingRect( ''.join(['A'] * 55)).width( )
        self.setFixedWidth( width )
        self.setFixedHeight( 450 )
        myTextArea = QTextEdit( )
        myTextArea.setReadOnly( True )
        myTextArea.setHtml( open( os.path.join( mainDir, 'docs', 'plex_tmdb_totgui_help.html' ), 'r' ).read( ) )
        layout.addWidget( myTextArea )
        self.hide( )
        #
        self.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )

    def closeEvent( self, evt ):
        self.hide( )
