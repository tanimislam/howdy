import os, sys, titlecase, datetime
import json, re, urllib, time, plexemail, plexemail_basegui
import mutagen.mp3, mutagen.mp4, glob, multiprocessing
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ConfigParser import RawConfigParser
from . import mainDir
from plexcore import plexcore

class PlexEmailGUI( QWidget ):
    class EmailSendDialog( QDialog ):
        def screenGrab( self ):
            fname = str( QFileDialog.getSaveFileName( self, 'Save Screenshot',
                                                      os.path.expanduser( '~' ),
                                                      'PNG Images (*.png)' ) )
            if len( os.path.basename( fname.strip( ) ) ) == 0: return
            if not fname.lower( ).endswith( '.png' ):
                fname = fname + '.png'
            qpm = QPixmap.grabWidget( self )
            qpm.save( fname )
        
        def __init__( self, parent ):
            super( PlexEmailGUI.EmailSendDialog, self ).__init__( parent )
            self.setModal( True )
            self.setWindowTitle( 'SEND EMAILS' )
            self.selectTestButton = QPushButton( 'TEST ADDRESS', self )
            self.selectAllButton = QPushButton( 'ALL ADDRESSES', self )
            self.sendEmailButton = QPushButton( 'SEND EMAIL', self )
            self.myButtonGroup = QButtonGroup( self )
            self.allRadioButtons = map( lambda name: QRadioButton( name, self ),
                                        [ 'Tanim Islam <***REMOVED***.islam@gmail.com>', ] +
                                        sorted(map( lambda idx: parent.emailComboBox.itemText( idx ),
                                                    range( parent.emailComboBox.count() ) ) ) )
            self.mainHtml = unicode( parent.mainEmailCanvas.toHtml( ) ).strip( )
            for button in self.allRadioButtons:
                self.myButtonGroup.addButton( button )
            self.myButtonGroup.setExclusive( False )
            self.allRadioButtons[0].setChecked( True )
            for button in self.allRadioButtons[1:]:
                button.setChecked( False )
            self.statusLabel = QLabel( )
            myLayout = QVBoxLayout( )
            self.setLayout( myLayout )
            #
            topLayout = QHBoxLayout( )
            topWidget = QWidget( self )
            topWidget.setLayout( topLayout )
            topLayout.addWidget( self.selectTestButton )
            topLayout.addWidget( self.selectAllButton )
            topLayout.addWidget( self.sendEmailButton )
            myLayout.addWidget( topWidget )
            #
            myButtonsWidget = QWidget( )
            myButtonsLayout = QVBoxLayout( )
            myButtonsWidget.setLayout( myButtonsLayout )
            for button in self.allRadioButtons:
                myButtonsLayout.addWidget( button )
            myLayout.addWidget( myButtonsWidget )
            #
            myLayout.addWidget( self.statusLabel )
            #
            self.selectTestButton.clicked.connect( self.selectTest )
            self.selectAllButton.clicked.connect( self.selectAll )
            self.sendEmailButton.clicked.connect( self.sendEmail )
            #
            printAction = QAction( self )
            printAction.setShortcut( 'Shift+Ctrl+P' )
            printAction.triggered.connect( self.screenGrab )
            self.addAction( printAction )
            #
            self.setFixedWidth( self.sizeHint( ).width( ) )
            self.setFixedHeight( self.sizeHint( ).height( ) )
            self.show( )

        def selectTest( self ):
            self.allRadioButtons[0].setChecked( True )
            for button in self.allRadioButtons[1:]:
                button.setChecked( False )

        def selectAll( self ):
            for button in self.allRadioButtons:
                button.setChecked( True )

        def sendEmail( self ):
            validLists = map(lambda button: str( button.text( ) ).strip( ),
                             filter(lambda button: button.isChecked( ), self.allRadioButtons ) )
            if len(validLists) == 0:
                return
            input_tuples = []
            #
            ## access token
            access_token = plexcore.oauth_get_access_token( )
            for fullName in validLists:
                if fullName.endswith('>'):
                    name = fullName.split('<')[0].strip( )
                    email = fullName.split('<')[1].strip().replace('>', '').strip()
                else:
                    name = None
                    email = fullName.strip( )
                input_tuples.append(( self.mainHtml, access_token, email, name ))
            #
            ## now send the emails
            time0 = time.time( )
            self.statusLabel.setText( 'STARTING TO SEND EMAILS...')
            pool = multiprocessing.Pool( processes = multiprocessing.cpu_count( ) )
            pool.map( plexemail.send_individual_email_perproc, input_tuples )
            self.statusLabel.setText( 'SENT %d EMAILS IN %0.3f SECONDS.' %
                                      ( len( input_tuples ), time.time() - time0 ) )
            #
            ## if I have sent out ALL EMAILS, then I mean to update the newsletter
            if len(validLists) == len( self.allRadioButtons ):
                plexemail.set_date_newsletter( )
            
    class PrePostAmbleDialog( QDialog ):
        def screenGrab( self ):
            fname = str( QFileDialog.getSaveFileName( self, 'Save Screenshot',
                                                      os.path.expanduser( '~' ),
                                                      'PNG Images (*.png)' ) )
            if len( os.path.basename( fname.strip( ) ) ) == 0: return
            if not fname.lower( ).endswith( '.png' ):
                fname = fname + '.png'
            qpm = QPixmap.grabWidget( self )
            qpm.save( fname )
        
        def __init__( self, parent, title = 'Preamble' ):
            super( PlexEmailGUI.PrePostAmbleDialog, self ).__init__( parent )
            self.parent = parent
            self.sectionNameWidget = QLineEdit( titlecase.titlecase( title ) )
            self.testTextButton = QPushButton( 'TEST TEXT' )
            self.pngAddButton = QPushButton( 'ADD PNGS' )
            self.textEdit = QTextEdit( )
            self.statusLabel = QLabel( )
            self.setWindowTitle( title )
            self.setModal( True )
            self.isValidLaTeX = True
            #
            self.YesButton = QRadioButton( 'YES', self )
            self.NoButton = QRadioButton( 'NO', self )
            radioButtonsWidget = QWidget( )
            radioButtonsLayout = QHBoxLayout( )
            radioButtonsWidget.setLayout( radioButtonsLayout )
            radioButtonsLayout.addWidget( self.YesButton )
            radioButtonsLayout.addWidget( self.NoButton )
            self.NoButton.toggle( )
            #
            self.pngWidget = plexemail_basegui.PNGWidget( self )
            self.pngWidget.hide( )
            #
            myLayout = QVBoxLayout( )
            self.setLayout( myLayout )
            #
            topLayout = QGridLayout( )
            topWidget = QWidget( )
            topWidget.setLayout( topLayout )
            topLayout.addWidget( QLabel( 'SECTION' ), 0, 0, 1, 1 )
            topLayout.addWidget( self.sectionNameWidget, 0, 1, 1, 2 )
            topLayout.addWidget( radioButtonsWidget, 1, 0, 1, 2 )
            topLayout.addWidget( self.testTextButton, 1, 2, 1, 1 )
            topLayout.addWidget( self.pngAddButton, 1, 3, 1, 1 )
            myLayout.addWidget( topWidget )
            #
            myLayout.addWidget( self.textEdit )
            myLayout.addWidget( self.statusLabel )
            #
            self.testTextButton.clicked.connect( self.checkValidLaTeX )
            self.pngAddButton.clicked.connect( self.addPNGs )
            #            
            openAction = QAction( self )
            openAction.setShortcut( 'Ctrl+O' )
            openAction.triggered.connect( self.openLatex )
            self.addAction( openAction )
            #
            printAction = QAction( self )
            printAction.setShortcut( 'Shift+Ctrl+P' )
            printAction.triggered.connect( self.screenGrab )
            self.addAction( printAction )
            #
            self.setFixedHeight( 650 )
            self.setFixedWidth( self.sizeHint( ).width( ) )

        def closeEvent( self, evt ):
            self.NoButton.toggle( )
            self.hide( )

        def addPNGs( self ):
            self.pngWidget.show( )

        def openLatex( self ):
            while( True ):
                fname = str( QFileDialog.getOpenFileName( self, 'Open LaTeX File',
                                                          os.getcwd( ),
                                                          filter = "*.tex" ) )
                if fname.lower( ).endswith( '.tex' ) or len( os.path.basename( fname ) ) == 0:
                    break
            if fname.lower( ).endswith( '.tex' ):
                lines = map(lambda line: line.replace('\n', ''),
                            open( fname, 'r').readlines() )
                lineBegin, _ = min(filter(lambda tup: tup[1] == '\\begin{document}',
                                          enumerate(lines)))
                if lineBegin is None:
                    return
                lineEnd, _ = max(filter(lambda tup: tup[1] == '\\end{document}',
                                        enumerate(lines)))
                if lineEnd is None:
                    return
                if lineBegin >= lineEnd:
                    return
                self.textEdit.setText( '\n'.join( lines[ lineBegin+1:lineEnd ] ) )
            
        def checkValidLaTeX( self ):
            myStr = self.textEdit.toPlainText( ).strip( )
            mainText = """
            \documentclass{article}
            \usepackage{amsmath, amsfonts, graphicx, hyperref}

            \\begin{document}
            
            \section{%s}

            %s

            \end{document}
            """ % ( self.sectionNameWidget.text( ).strip( ), myStr )
            htmlString = plexcore.latexToHTML( mainText )
            if htmlString is None:
                self.isValidLaTeX = False
                self.statusLabel.setText( "ERROR: INVALID TEXT" )
                return
            self.isValidLaTeX = True
            self.statusLabel.setText( "VALID TEXT" )
            if not self.YesButton.isChecked( ): return
            htmlString = plexcore.processValidHTMLWithPNG( htmlString,
                                                           self.pngWidget.getAllDataAsDict( ),
                                                           doEmbed = True )
            qdl = QDialog( self )
            qdl.setModal( True )
            qdlLayout = QVBoxLayout( )
            qte = QTextEdit( )
            qdl.setLayout( qdlLayout )
            qdlLayout.addWidget( qte )
            qte.setReadOnly( True )
            qte.setHtml( htmlString )
            qdl.setFixedWidth( 350 )
            qdl.setFixedHeight( 550 )
            qdl.setWindowTitle( 'EXAMPLE WORKING HTML FOR %s' %
                                self.windowTitle( ) )
            qdl.show( )
            result = qdl.exec_( )

        def sendValidLaTeX( self, showSection = True ):
            self.NoButton.toggle( )
            self.checkValidLaTeX( )
            myStr = unicode( self.textEdit.toPlainText( ).toUtf8( ), encoding='UTF-8').strip( )
            if self.isValidLaTeX:
                if showSection:
                    myString = unicode( """
                    \section{%s}
                    
                    %s
                    """ % ( str( self.sectionNameWidget.text( ) ).strip( ),
                            myStr ) )
                else:
                    myString = unicode( """
                    %s
                    """ % myStr )
                return myString, self.pngWidget.getAllDataAsDict( )
            else:
                return "", { }

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
            
    def __init__( self, token, doLocal = True, doLarge = False ):
        super( PlexEmailGUI, self ).__init__( )
        self.resolution = 1.0
        if doLarge:
            self.resolution = 2.0
        for fontFile in glob.glob( os.path.join( mainDir, 'resources', '*.ttf' ) ):
            QFontDatabase.addApplicationFont( fontFile )
        self.setStyleSheet("""
        QWidget {
        font-family: Consolas;
        font-size: %d;
        }""" % ( int( 11 * self.resolution ) ) )
        self.doLocal = doLocal
        self.mainEmailCanvas = QTextEdit( self )
        self.mainEmailCanvas.setReadOnly( True )
        self.testEmailButton = QPushButton( 'TEST EMAIL', self )
        self.preambleButton = QPushButton( 'PREAMBLE', self )
        self.postambleButton = QPushButton( 'POSTAMBLE', self )
        self.sendEmailButton = QPushButton( 'SEND EMAIL', self )
        self.sendEmailButton.setEnabled( False )
        self.testEmailButton.setEnabled( False )
        self.emailComboBox = QComboBox( )
        self.setWindowTitle( 'TEST PLEX EMAIL NEWSLETTER' )
        self.preambleDialog = PlexEmailGUI.PrePostAmbleDialog( self, title = 'PREAMBLE' )
        self.postambleDialog = PlexEmailGUI.PrePostAmbleDialog( self, title = 'POSTAMBLE' )
        self.preamble = ''
        self.postamble = ''
        self.token = token
        self.getContacts( token )
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #
        topLayout = QGridLayout( )
        topWidget = QWidget( )
        topWidget.setLayout( topLayout )
        myLayout.addWidget( topWidget )
        topLayout.addWidget( self.testEmailButton, 0, 0, 1, 1 )
        topLayout.addWidget( self.preambleButton, 0, 1, 1, 1 )
        topLayout.addWidget( self.postambleButton, 0, 2, 1, 1 )
        topLayout.addWidget( self.sendEmailButton, 0, 3, 1, 1 )
        topLayout.addWidget( QLabel( 'CONTACTS BUTTON' ), 1, 0, 1, 1 )
        topLayout.addWidget( self.emailComboBox, 1, 1, 1, 3 )
        #
        myLayout.addWidget( self.mainEmailCanvas )
        #
        quitAction = QAction( self )
        quitAction.setShortcuts( ['Ctrl+Q', 'Esc' ] )
        quitAction.triggered.connect( sys.exit )
        self.addAction( quitAction )
        self.testEmailButton.clicked.connect( self.createSummaryEmail )
        # self.getContactsButton.clicked.connect( self.getContacts )
        self.preambleButton.clicked.connect( self.preambleDialog.show )
        self.postambleButton.clicked.connect( self.postambleDialog.show )
        self.sendEmailButton.clicked.connect( self.sendEmail )
        #
        printAction = QAction( self )
        printAction.setShortcut( 'Shift+Ctrl+P' )
        printAction.triggered.connect( self.screenGrab )
        self.addAction( printAction )
        #
        qf = QFont( )
        qf.setFamily( 'Consolas' )
        qf.setPointSize( int( 11 * self.resolution ) )
        qfm = QFontMetrics( qf )
        self.setFixedWidth( 55 * qfm.width( 'A' ) )
        self.setFixedHeight( 33 * qfm.height( ) )
        self.show( )

    def createSummaryEmail( self ):
        self.mainEmailCanvas.setPlainText( '' )
        self.sendEmailButton.setEnabled( False )
        preambleText, pngDataPRE = self.preambleDialog.sendValidLaTeX( False )
        postambleText, pngDataPOST = self.postambleDialog.sendValidLaTeX( )
        pngData = dict( pngDataPRE.items( ) + pngDataPOST.items( ) )
        if len(pngData) != len(pngDataPRE) + len( pngDataPOST ) and len(pngData) != 0:
            print( 'ERROR, MUST HAVE SOME INTERSECTIONS IN PNG FILE NAMES.' )
            print( 'COMMON PNG FILES: %s.' % sorted( set( pngDataPRE.keys( ) ) &
                                                     set( pngDataPOST.keys( ) ) ) )
            print( "I HOPE YOU KNOW WHAT YOU'RE DOING." )
        htmlString = plexemail.get_summary_html( preambleText = preambleText,
                                                 postambleText = postambleText,
                                                 pngDataDict = pngData,
                                                 token = self.token,
                                                 doLocal = self.doLocal )
        if len(htmlString) != 0:
            self.mainEmailCanvas.setHtml( htmlString )
            self.sendEmailButton.setEnabled( True )

    def sendEmail( self ):
        qd = PlexEmailGUI.EmailSendDialog( self )
        result = qd.exec_( )            
        
    def getContacts( self, token ):
        emails = plexcore.get_mapped_email_contacts( token )
        if len(emails) == 0:
            return
        self.testEmailButton.setEnabled( True )
        #
        ## now do some google client magic to get the names
        name_emails = plexemail.get_email_contacts_dict( emails )
        self.emailComboBox.clear( )
        items = []
        for name, email in name_emails:
            if name is not None:
                items.append('%s <%s>' % ( name, email ) )
            else:
                items.append( email )
        self.emailComboBox.addItems( sorted( items ) )
        self.emailComboBox.setEditable( False )
        self.emailComboBox.setCurrentIndex( 0 )
