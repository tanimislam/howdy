#!/usr/bin/env python3

import pypandoc, glob, os, sys, textwrap, qdarkstyle
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from plexcore import mainDir, returnQAppWithFonts

def checkValidLaTeX( myString ):
    try:
        mainHTML = pypandoc.convert_text(
            myString, 'html', format = 'latex',
            extra_args = [ '-s' ] )
        return True
    except RuntimeError:
        return False

class MainGUI( QWidget ):

    def printHTML( self ):
        mainText = r"""
            \documentclass[12pt, fleqn]{article}
            \usepackage{amsmath, amsfonts, graphicx, hyperref}

            \\begin{document}

            %s

            \end{document}
            """ % ( self.latexOutput.toPlainText( ).strip( ) )
        self.printString( mainText, toHTML = True )

    def printMarkdown( self ):
        mainText = r"""
            \documentclass[12pt, fleqn]{article}
            \usepackage{amsmath, amsfonts, graphicx, hyperref}

            \\begin{document}

            %s

            \end{document}
            """ % ( self.latexOutput.toPlainText( ).strip( ) )
        self.printString( mainText, toHTML = False )

    def printString( self, myString, toHTML = True ):
        self.statusLabel.setText( '' )
        if not checkValidLaTeX( myString ):
            statusLabel.setText( 'INVALID LATEX' )
            return
        qdl = QDialog( self )
        qdl.setModal( True )
        qsb = QPushButton( 'SAVE' )
        qdl.setModal( True )
        qte = QTextEdit( qdl )
        qte.setReadOnly( True )
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
        if toHTML:
            myHTML =  pypandoc.convert_text(
                myString, 'html', format = 'latex',
                extra_args = [ '-s' ] )
            print( myHTML )
            qte.setHtml( pypandoc.convert_text(
                myString, 'html', format = 'latex',
                extra_args = [ '-s' ] ) )
        else:
            qte.setPlainText( pypandoc.convert_text(
                myString, 'markdown', format = 'latex',
                extra_args = [ '-s' ] ) )
        def saveFilename( ):
            if toHTML:
                name = 'HTML'
                suffix = 'html'
            else:
                name = 'Markdown'
                suffix = 'md'
            while( True ):
                fname = str( QFileDialog.getSaveFileName( qdl, 'Save %s' % name,
                                                          os.path.expanduser( '~' ),
                                                          filter = '*.%s' % suffix ) )
                if fname.lower().endswith('.%s' % suffix) or len( os.path.basename( fname ) ) == 0:
                    break
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
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )                       
    mg = MainGUI( )
    result = app.exec_( )
