import glob, os, sys, textwrap, logging
from docutils.examples import html_parts
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtNetwork import QNetworkAccessManager
#
from howdy.core import returnQAppWithFonts, QDialogWithPrinting
from howdy.email import email_basegui

def checkValidConversion( myString ):
    try:
        html_body = html_parts( myString )[ 'whole' ]
        html = BeautifulSoup( html_body, 'lxml' )
        return html.prettify( )
        return True
    except RuntimeError as e:
        return False

def convertString( myString ):
    try:
        html_body = html_parts( myString )[ 'whole' ]
        html = BeautifulSoup( html_body, 'lxml' )
        return html.prettify( )
    except RuntimeError as e:
        print( "Error, could not convert %s of format %s. Error = %s." % (
            myString, form.lower( ), str( e ) ) )
        return None

class HtmlView( QWebEngineView ):
    def __init__( self, parent, htmlString ):
        super( HtmlView, self ).__init__( parent )
        self.initHtmlString = htmlString
        self.setHtml( self.initHtmlString )
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

    def reset( self ):
        self.setHtml( self.initHtmlString )
        
    def on_loadFinished( self ):
        self.initialized = True

    def waitUntilReady( self ):
        if not self.initialized:
            loop = QEventLoop( )
            self.loadFinished.connect( loop.quit )
            loop.exec_( )

class ConvertWidget( QDialogWithPrinting ):
    def __init__( self ):
        super( ConvertWidget, self ).__init__( None, doQuit = True, isIsolated = True )
        self.setWindowTitle( 'RESTRUCTURED TEXT CONVERTER' )
        self.name = 'RESTRUCTURED TEXT'
        self.form = 'rst'
        self.suffix = 'rst' 
        self.setStyleSheet("""
        QWidget {
        font-family: Consolas;
        font-size: 11;
        }""" )
        #
        qf = QFont( )
        qf.setFamily( 'Consolas' )
        qf.setPointSize( 11 )
        qfm = QFontMetrics( qf )
        self.statusDialog = QLabel( )
        self.rowColDialog = QLabel( )
        self.textOutput = QPlainTextEdit( )
        self.textOutput.setTabStopWidth( 2 * qfm.width( 'A' ) )
        self.convertButton = QPushButton( 'CONVERT' )
        self.saveButton = QPushButton( 'SAVE' )
        self.loadButton = QPushButton( 'LOAD' )
        self.pngShowButton = QPushButton( 'SHOW PNGS' )
        #
        self.pngWidget = email_basegui.PNGWidget( self )
        self.pngWidget.hide( )
        #
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #
        topWidget = QWidget( )
        topLayout = QHBoxLayout( )
        topWidget.setLayout( topLayout )
        topLayout.addWidget( self.convertButton )
        topLayout.addWidget( self.saveButton )
        topLayout.addWidget( self.loadButton )
        topLayout.addWidget( self.pngShowButton )
        myLayout.addWidget( topWidget )
        myLayout.addWidget( self.textOutput )
        botWidget = QWidget( )
        botLayout = QHBoxLayout( )
        botWidget.setLayout( botLayout )
        botLayout.addWidget( self.rowColDialog )
        botLayout.addWidget( self.statusDialog )
        myLayout.addWidget( botWidget )
        #
        self.convertButton.clicked.connect( self.printHTML )
        self.saveButton.clicked.connect( self.saveFileName )
        self.loadButton.clicked.connect( self.loadFileName )
        self.pngShowButton.clicked.connect( self.showPNGs )
        self.textOutput.cursorPositionChanged.connect( self.showRowCol )
        saveAction = QAction( self )
        saveAction.setShortcut( 'Ctrl+S' )
        saveAction.triggered.connect( self.saveFileName )
        self.addAction( saveAction )
        #
        self.setFixedHeight( 650 )
        self.setFixedWidth( 600 )

    def showPNGs( self ):
        self.pngWidget.show( )
        # self.pngAddButton.setEnabled( False )

    def showRowCol( self ):
        cursor = self.textOutput.textCursor( )
        lineno = cursor.blockNumber( ) + 1
        colno  = cursor.columnNumber( ) + 1
        self.rowColDialog.setText( '(%d, %d)' % ( lineno, colno ) )

    #
    def saveFileName( self ):
        fname, _ = QFileDialog.getSaveFileName(
            self, 'Save %s' % self.name,
            os.path.expanduser( '~' ),
            filter = '*.%s' % self.suffix.lower( ) )
        if not fname.lower().endswith('.%s' % self.suffix.lower( ) ): return
        if len( os.path.basename( fname ) ) == 0: return
        if fname.lower( ).endswith( '.%s' % self.suffix.lower( ) ):
            with open( fname, 'w' ) as openfile:
                openfile.write( '%s\n' % self.getTextOutput( ) )

    def loadFileName( self ):
        fname, _ = QFileDialog.getOpenFileName(
            self, 'Open %s' % self.name,
            os.path.expanduser( '~' ),
            filter = '*.%s' % self.suffix.lower( ) )
        if not fname.lower().endswith('.%s' % self.suffix.lower( ) ): return
        if len( os.path.basename( fname ) ) == 0: return
        if fname.lower( ).endswith( '.%s' % self.suffix.lower( ) ):
            myString = open( fname, 'r' ).read( )
            self.textOutput.setPlainText( myString )
        

    def getTextOutput( self ):
        return r"%s" % self.textOutput.toPlainText( ).strip( )

    def printHTML( self ):
        self.statusDialog.setText( '' )
        myString = self.getTextOutput( )
        if not checkValidConversion( myString ):
            self.statusDialog.setText(
                'COULD NOT CONVERT FROM %s TO HTML' % form.upper( ) )
            return
        #
        qdl = QDialogWithPrinting( self, doQuit = False, isIsolated = True )
        #
        qdl.setModal( True )
        backButton = QPushButton( 'BACK' )
        forwardButton = QPushButton( 'FORWARD' )
        resetButton = QPushButton( 'RESET' )
        #
        ##
        qte = HtmlView( qdl, convertString( myString ) )
        qdlLayout = QVBoxLayout( )
        qdl.setLayout( qdlLayout )
        qdlLayout.addWidget( qte )
        bottomWidget = QWidget( )
        bottomLayout = QHBoxLayout( )
        bottomWidget.setLayout( bottomLayout )
        bottomLayout.addWidget( resetButton )
        bottomLayout.addWidget( backButton )
        bottomLayout.addWidget( forwardButton )
        qdlLayout.addWidget( bottomWidget )
        qf = QFont( )
        qf.setFamily( 'Consolas' )
        qf.setPointSize( 11 )
        qfm = QFontMetrics( qf )
        #qte.setWidth( 85 * qfm.width( 'A' ) )
        #qte.setHeight( 550 )
        #qdl.width( 85 * qfm.width( 'A' ) )
        #qdl.height( 550 )
        qte.setMinimumSize( 85 * qfm.width( 'A' ), 550 )
        qdl.setMinimumSize( 85 * qfm.width( 'A' ), 550 )
        #
        resetButton.clicked.connect( qte.reset )
        backButton.clicked.connect( qte.back )
        forwardButton.clicked.connect( qte.forward )
        qte.setHtml( convertString( myString ) )
        #
        qte.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        qdl.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        qdl.show( )
        qdl.exec_( )
