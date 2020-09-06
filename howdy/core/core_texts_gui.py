import glob, os, sys, textwrap, logging
from docutils.examples import html_parts
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtNetwork import QNetworkAccessManager
#
from howdy.core import returnQAppWithFonts, QDialogWithPrinting

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
        self.textOutput = QPlainTextEdit( )
        self.textOutput.setTabStopWidth( 2 * qfm.width( 'A' ) )
        self.convertButton = QPushButton( 'CONVERT' )
        self.saveButton = QPushButton( 'SAVE' )
        #
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #
        topWidget = QWidget( )
        topLayout = QHBoxLayout( )
        topWidget.setLayout( topLayout )
        topLayout.addWidget( self.convertButton )
        topLayout.addWidget( self.saveButton )
        myLayout.addWidget( topWidget )
        myLayout.addWidget( self.textOutput )
        myLayout.addWidget( self.statusDialog )
        self.convertButton.clicked.connect( self.printHTML )
        self.saveButton.clicked.connect( self.saveFileName )
        saveAction = QAction( self )
        saveAction.setShortcut( 'Ctrl+S' )
        saveAction.triggered.connect( self.saveFileName )
        self.addAction( saveAction )
        #
        self.setFixedHeight( 650 )
        self.setFixedWidth( 600 )

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
        #
        ##
        qte = HtmlView( qdl )
        qdlLayout = QVBoxLayout( )
        qdl.setLayout( qdlLayout )
        qdlLayout.addWidget( qte )
        bottomWidget = QWidget( )
        bottomLayout = QHBoxLayout( )
        bottomWidget.setLayout( bottomLayout )
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
        backButton.clicked.connect( qte.back )
        forwardButton.clicked.connect( qte.forward )
        qte.setHtml( convertString( myString ) )
        #
        qte.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        qdl.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        qdl.show( )
        qdl.exec_( )
