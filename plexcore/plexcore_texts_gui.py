import pypandoc, glob, os, sys, textwrap, logging
from docutils.examples import html_parts
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import QAction, QFileDialog, QLabel, QPushButton, QTabBar, QTabWidget, QTextEdit, QVBoxLayout, QWidget
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtNetwork import QNetworkAccessManager

from plexcore import mainDir, returnQAppWithFonts, plexcore_texts_gui
from plexcore import QDialogWithPrinting

from plexcore import mainDir

def checkValidConversion( myString, form = 'latex' ):
    assert( form.lower( ) in ( 'latex', 'markdown', 'rst' ) ), "error, format = %s not one of 'latex', 'markdown', or 'rst'" % form.lower( )
    try:
        mainHTML = pypandoc.convert_text(
            myString, 'html', format = form.lower( ),
            extra_args = [ '-s', '--mathjax' ] )
        return True
    except RuntimeError:
        return False

def convertString( myString, form = 'latex' ):
    assert( form.lower( ) in ( 'latex', 'markdown', 'rst' ) ), "error, format = %s not one of 'latex', 'markdown', or 'rst'" % form.lower( )
    try:
        if form.lower( ) == 'rst': # use docutils instead
            html_body = html_parts( myString )[ 'whole' ]
            html = BeautifulSoup( html_body, 'lxml' )
            return html.prettify( )
        return pypandoc.convert_text(
            myString, 'html', format = form.lower( ),
            extra_args = [ '-s', '--mathjax' ] )
    except RuntimeError as e:
        print( "Error, could not convert %s of format %s. Error = %s." % (
            myString, form.lower( ), str( e ) ) )
        return None

class HtmlView( QWebEngineView ):
    def __init__( self, parent ):
        super( HtmlView, self ).__init__( parent )
        #channel = QWebChannel( self )
        #self.page( ).setWebChannel( channel )
        #channel.registerObject( 'thisFormula', self )
        #
        # self.setHtml( myhtml )
        #self.loadFinished.connect( self.on_loadFinished )
        #self.initialized = False
        #
        self._setupActions( )
        self._manager = QNetworkAccessManager( self )

    def _setupActions( self ):
        backAction = QAction( self )
        backAction.setShortcut( 'Shift+Ctrl+1' )
        backAction.triggered.connect( self.back )
        self.addAction( backAction )
        forwardAction = QAction( self )
        forwardAction.setShortcut( 'Shift+Ctrl+2' )
        forwardAction.triggered.connect( self.forward )
        self.addAction( forwardAction )        
        
    def on_loadFinished( self ):
        self.initialized = True

    def waitUntilReady( self ):
        if not self.initialized:
            loop = QEventLoop( )
            self.loadFinished.connect( loop.quit )
            loop.exec_( )

class ConvertWidget( QDialogWithPrinting ):
    def __init__( self, parent, name = 'LaTeX', form = 'latex', suffix = 'tex' ):
        super( ConvertWidget, self ).__init__( parent, doQuit = False, isIsolated = False )
        assert( form.lower( ) in ( 'latex', 'markdown', 'rst' ) )
        self.name = name
        self.form = form.lower( )
        self.suffix = suffix.lower( )
        #
        qf = QFont( )
        qf.setFamily( 'Consolas' )
        qf.setPointSize( 11 )
        qfm = QFontMetrics( qf )
        self.statusDialog = QLabel( )
        self.textOutput = QTextEdit( )
        self.textOutput.setTabStopWidth( 2 * qfm.width( 'A' ) )
        self.convertButton = QPushButton( 'CONVERT' )
        #
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #
        myLayout.addWidget( self.convertButton )
        myLayout.addWidget( self.textOutput )
        myLayout.addWidget( self.statusDialog )
        self.convertButton.clicked.connect( self.printHTML )
        #
        self.setFixedHeight( 650 )
        self.setFixedWidth( self.sizeHint( ).width( ) )

    def printHTML( self ):
        myString = r"%s" % self.textOutput.toPlainText( ).strip( )
        self.statusDialog.setText( '' )
        if not plexcore_texts_gui.checkValidConversion(
                myString, form = self.form.lower( ) ):
            self.statusDialog.setText(
                'COULD NOT CONVERT FROM %s TO HTML' % form.upper( ) )
            return
        #
        qdl = QDialogWithPrinting( self, doQuit = False, isIsolated = True )
        qdl.setModal( True )
        qsb = QPushButton( 'SAVE' )
        qte = HtmlView( qdl )
        qdlLayout = QVBoxLayout( )
        qdl.setLayout( qdlLayout )
        qdlLayout.addWidget( qsb )
        qdlLayout.addWidget( qte )
        qf = QFont( )
        qf.setFamily( 'Consolas' )
        qf.setPointSize( 11 )
        qfm = QFontMetrics( qf )
        qte.setFixedWidth( 85 * qfm.width( 'A' ) )
        qte.setFixedHeight( 550 )
        qdl.setFixedWidth( 85 * qfm.width( 'A' ) )
        qdl.setFixedHeight( 550 )
        #
        qte.setHtml( plexcore_texts_gui.convertString(
            myString, form = self.form.lower( ) ) )
        #
        def saveFileName( ):
            fname, _ = QFileDialog.getSaveFileName(
                qdl, 'Save %s' % self.name,
                os.path.expanduser( '~' ),
                filter = '*.%s' % self.suffix.lower( ) )
            if not fname.lower().endswith('.%s' % self.suffix.lower( ) ): return
            if len( os.path.basename( fname ) ) == 0: return
            if fname.lower( ).endswith( '.%s' % self.suffix.lower( ) ):
                with open( fname, 'w' ) as openfile:
                    openfile.write( '%s\n' % textwrap.fill(
                        qte.toPlainText( ).strip( ) ) )
        qsb.clicked.connect( saveFileName )
        saveAction = QAction( qdl )
        saveAction.setShortcut( 'Ctrl+S' )
        saveAction.triggered.connect( saveFileName )
        qdl.addAction( saveAction )
        qdl.show( )
        qdl.exec_( )
    
class MainGUI( QDialogWithPrinting ):
        
    def __init__( self ):
        super( MainGUI, self ).__init__( None, doQuit = True, isIsolated = True )
        self.setWindowTitle( 'FORMAT CONVERTER 3 CHOICES' )
        self.setStyleSheet("""
        QWidget {
        font-family: Consolas;
        font-size: 11;
        }""" )
        #
        ## myLayout
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #
        tabWidget = QTabWidget( self )
        tabWidget.addTab(
            ConvertWidget( self, name = 'LaTeX', form = 'latex', suffix = 'tex' ), 'LaTeX' )
        tabWidget.addTab(
            ConvertWidget( self, name = 'Markdown', form = 'markdown', suffix = 'md' ), 'Markdown' )
        tabWidget.addTab(
            ConvertWidget( self, name = 'ReStructuredText', form = 'rst', suffix = 'rst' ),
            'ReStructuredText' )
        tabWidget.setCurrentIndex( 0 )
        myLayout.addWidget( tabWidget )
        ctw = tabWidget.currentWidget( )
        tabWidget.setStyleSheet( 'QTabBar::tab { width: %dpx; }' %int( 1.05 * ctw.size( ).width( ) ) )
        self._setupActions( tabWidget )
        #
        self.setFixedHeight( 750 )
        self.setFixedWidth( self.sizeHint( ).width( ) )
        self.show( )

    def _setupActions( self, tabWidget ):
        def leftTab( ): tabWidget.setCurrentIndex( 0 )
        def midTab( ): tabWidget.setCurrentIndex( 1 )
        def rightTab( ): tabWidget.setCurrentIndex( 2 )
        leftTabAction = QAction( self )
        leftTabAction.setShortcut( 'Shift+Ctrl+1' )
        leftTabAction.triggered.connect( leftTab )
        self.addAction( leftTabAction )
        midTabAction = QAction( self )
        midTabAction.setShortcut( 'Shift+Ctrl+2' )
        midTabAction.triggered.connect( midTab )
        self.addAction( midTabAction )
        rightTabAction = QAction( self )
        rightTabAction.setShortcut( 'Shift+Ctrl+3' )
        rightTabAction.triggered.connect( rightTab )
        self.addAction( rightTabAction )
