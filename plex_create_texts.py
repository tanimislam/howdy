#!/usr/bin/env python3

import pypandoc, glob, os, sys, textwrap, qdarkstyle
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtNetwork import QNetworkAccessManager
from plexcore import mainDir, returnQAppWithFonts

def checkValidLaTeX( myString ):
    try:
        mainHTML = pypandoc.convert_text(
            myString, 'html', format = 'latex',
            extra_args = [ '-s' ] )
        return True
    except RuntimeError:
        return False

class DemoShowFormulas( QWebEngineView ):
    def __init__( self, parent ):
        super( DemoShowFormulas, self ).__init__( parent )
        #channel = QWebChannel( self )
        #self.page( ).setWebChannel( channel )
        #channel.registerObject( 'thisFormula', self )
        #
        # self.setHtml( myhtml )
        #self.loadFinished.connect( self.on_loadFinished )
        #self.initialized = False
        #
        self._manager = QNetworkAccessManager( self )

    def on_loadFinished( self ):
        self.initialized = True

    def waitUntilReady( self ):
        if not self.initialized:
            loop = QEventLoop( )
            self.loadFinished.connect( loop.quit )
            loop.exec_( )
    
class MainGUI( QWidget ):

    def printHTML( self ):
        mainText = r"""
            %s
            """ % ( self.latexOutput.toPlainText( ).strip( ) )
        self.printString( mainText, name = 'HTML' )

    def printMarkdown( self ):
        mainText = r"""
            %s
            """ % ( self.latexOutput.toPlainText( ).strip( ) )
        self.printString( mainText, name = 'Markdown' )

    def printString( self, myString, name = 'HTML' ):
        self.statusLabel.setText( '' )
        if not checkValidLaTeX( myString ):
            statusLabel.setText( 'INVALID LATEX' )
            return
        qdl = QDialog( self )
        qdl.setModal( True )
        qsb = QPushButton( 'SAVE' )
        qdl.setModal( True )
        qte = DemoShowFormulas( qdl )
        #qte = QTextEdit( qdl )
        #qte.setReadOnly( True )
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
        if name == 'HTML':
            myHTML =  pypandoc.convert_text(
                myString, 'html', format = 'latex',
                extra_args = [ '-s', '--mathjax' ] )
            qte.setHtml( pypandoc.convert_text(
                myString, 'html', format = 'latex',
                extra_args = [ '-s', '--mathjax' ] ) )
        elif name == 'Markdown':
            myMD = pypandoc.convert_text(
                myString, 'markdown', format = 'latex',
                extra_args = [ '-s' ] )
            #qte.setPlainText( pypandoc.convert_text(
            #    myString, 'markdown', format = 'latex',
            #    extra_args = [ '-s' ] ) )
        def saveFilename( ):
            if name == 'HTML':
                suffix = 'html'
            elif name == 'Markdown':
                suffix = 'md'
            fname = str( QFileDialog.getSaveFileName(
                qdl, 'Save %s' % name,
                os.path.expanduser( '~' ),
                filter = '*.%s' % suffix ) )
            if not fname.lower().endswith('.%s' % suffix): return
            if len( os.path.basename( fname ) ) == 0: return
            if fname.lower().endswith('.%s' % suffix ):
                with open( fname, 'w') as openfile:
                    openfile.write('%s\n' % textwrap.fill( str( qte.toPlainText( ) ).strip( ) ) )
        qsb.clicked.connect( saveFilename )
        saveAction = QAction( qdl )
        saveAction.setShortcut('Ctrl+S')
        saveAction.triggered.connect( saveFilename )
        qdl.addAction( saveAction )
        qdl.show( )
        result = qdl.exec_( )
        
    def __init__( self ):
        super( MainGUI, self ).__init__( )
        self.setWindowTitle( 'FORMAT CONVERTER' )
        self.toHTML = QPushButton( 'HTML' )
        self.toMarkdown = QPushButton( 'MARKDOWN' )
        qf = QFont( )
        qf.setFamily( 'Consolas' )
        qf.setPointSize( 11 )
        qfm = QFontMetrics( qf )
        self.setStyleSheet("""
        QWidget {
        font-family: Consolas;
        font-size: 11;
        }""" )
        self.latexOutput = QTextEdit( )
        self.latexOutput.setTabStopWidth( 2 * qfm.width( 'A' ) )
        self.statusLabel = QLabel( )
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #
        topLayout = QHBoxLayout( )
        topWidget = QWidget( )
        topWidget.setLayout( topLayout )
        topLayout.addWidget( self.toHTML )
        topLayout.addWidget( self.toMarkdown )
        myLayout.addWidget( topWidget )
        #
        myLayout.addWidget( self.latexOutput )
        myLayout.addWidget( self.statusLabel )
        #
        quitAction = QAction( self )
        quitAction.setShortcuts([ 'Ctrl+Q', 'Esc' ])
        quitAction.triggered.connect( sys.exit )
        self.addAction( quitAction )
        self.toHTML.clicked.connect( self.printHTML )
        self.toMarkdown.clicked.connect( self.printMarkdown )
        toHTMLAction = QAction( self )
        toHTMLAction.setShortcut( 'Ctrl+Shift+H' )
        toHTMLAction.triggered.connect( self.printHTML )
        self.addAction( toHTMLAction )
        toMarkdownAction = QAction( self )
        toMarkdownAction.setShortcut( 'Ctrl+Shift+M' )
        toMarkdownAction.triggered.connect( self.printMarkdown )
        self.addAction( toMarkdownAction )
        #
        self.setFixedHeight( 650 )
        self.setFixedWidth( self.sizeHint( ).width( ) )
        self.show( )

if __name__=='__main__':
    app = returnQAppWithFonts( )
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt5( ) )                       
    mg = MainGUI( )
    result = app.exec_( )
