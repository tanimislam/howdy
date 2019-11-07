import os, sys, titlecase, datetime, json, re, urllib, time, glob
import pathos.multiprocessing as multiprocessing
from itertools import chain
from PyQt4.QtGui import QAction, QButtonGroup, QComboBox, QDialog, QFont
from PyQt4.QtGui import QFontMetrics, QGridLayout, QHBoxLayout, QLabel, QLineEdit
from PyQt4.QtGui import QPushButton, QRadioButton, QTextEdit, QVBoxLayout, QWidget
from PyQt4.QtGui import QFileDialog, QFontDatabase

from plexemail import plexemail, plexemail_basegui, emailAddress, emailName, get_email_contacts_dict
from plexcore import plexcore, mainDir, QDialogWithPrinting

class PlexEmailGUI( QDialogWithPrinting ):
    class EmailSendDialog( QDialogWithPrinting ):
        
        def __init__( self, parent ):
            super( PlexEmailGUI.EmailSendDialog, self ).__init__( parent, isIsolated = False )
            self.setModal( True )
            self.setWindowTitle( 'SEND EMAILS' )
            self.selectTestButton = QPushButton( 'TEST ADDRESS', self )
            self.selectAllButton = QPushButton( 'ALL ADDRESSES', self )
            self.sendEmailButton = QPushButton( 'SEND EMAIL', self )
            self.myButtonGroup = QButtonGroup( self )
            if emailName is None: emailString = emailAddress
            else: emailString = '%s <%s>' % ( emailName, emailAddress )
            self.allRadioButtons = list(
                map( lambda name: QRadioButton( name, self ),
                     [ emailString, ] +
                     sorted(map( lambda idx: parent.emailComboBox.itemText( idx ),
                                 range( parent.emailComboBox.count() ) ) ) ) )
            self.mainHtml = parent.mainEmailCanvas.toHtml( ).strip( )
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
            self.setFixedWidth( self.sizeHint( ).width( ) )
            self.setFixedHeight( self.sizeHint( ).height( ) )
            self.show( )

        def selectTest( self ):
            self.allRadioButtons[0].setChecked( True )
            list(map(lambda button: button.setChecked( False ),
                     self.allRadioButtons[1:]))

        def selectAll( self ):
            list(map(lambda button: button.setChecked( True ),
                     self.allRadioButtons ) )

        def sendEmail( self ):
            validLists = list(
                map(lambda button: str( button.text( ) ).strip( ),
                    filter(lambda button: button.isChecked( ), self.allRadioButtons ) ) )
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
                input_tuples.append(( self.mainHtml, email, name ))
            #
            ## now send the emails
            time0 = time.time( )
            self.statusLabel.setText( 'STARTING TO SEND EMAILS...')
            with multiprocessing.Pool( processes = multiprocessing.cpu_count( ) ) as pool:
                list( pool.map( plexemail.send_individual_email_perproc, input_tuples ) )
                self.statusLabel.setText( 'SENT %d EMAILS IN %0.3f SECONDS.' %
                                          ( len( input_tuples ), time.time() - time0 ) )
                #
                ## if I have sent out ALL EMAILS, then I mean to update the newsletter
                if len(validLists) == len( self.allRadioButtons ):
                    plexcore.set_date_newsletter( )
            
    class PrePostAmbleDialog( QDialogWithPrinting ):
        
        def __init__( self, parent, title = 'Preamble' ):
            super( PlexEmailGUI.PrePostAmbleDialog, self ).__init__(
                parent, isIsolated = False )
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
            mainText = r"""
            \documentclass{article}
            \usepackage{amsmath, amsfonts, graphicx, hyperref}

            \begin{document}
            
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
            htmlString = plexcore.processValidHTMLWithPNG(
                htmlString, self.pngWidget.getAllDataAsDict( ),
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
            qdl.setWindowTitle(
                'EXAMPLE WORKING HTML FOR %s' % self.windowTitle( ) )
            qdl.show( )
            result = qdl.exec_( )

        def sendValidLaTeX( self, showSection = True ):
            self.NoButton.toggle( )
            self.checkValidLaTeX( )
            myStr = self.textEdit.toPlainText( ).strip( )
            if not self.isValidLaTeX: return "", { }
            #
            if showSection:
                myString = """
                \section{%s}
                
                %s
                """ % ( self.sectionNameWidget.text( ).strip( ), myStr )
            else: myString = myStr
            return myString, self.pngWidget.getAllDataAsDict( )
            
    def __init__( self, doLocal = True, doLarge = False, verify = True ):
        super( PlexEmailGUI, self ).__init__( None )
        self.resolution = 1.0
        self.verify = verify
        if doLarge:
            self.resolution = 2.0
        for fontFile in glob.glob( os.path.join( mainDir, 'resources', '*.ttf' ) ):
            QFontDatabase.addApplicationFont( fontFile )
        self.setStyleSheet("""
        QWidget {
        font-family: Consolas;
        font-size: %d;
        }""" % ( int( 11 * self.resolution ) ) )
        dat = plexcore.checkServerCredentials(
            doLocal = doLocal, verify = self.verify )
        if dat is None:
            raise ValueError( "Error, cannot access the Plex media server." )
        self.fullURL, self.token = dat
            
        self.mainEmailCanvas = QTextEdit( self )
        self.mainEmailCanvas.setReadOnly( True )
        self.testEmailButton = QPushButton( 'TEST EMAIL', self )
        self.preambleButton = QPushButton( 'PREAMBLE', self )
        self.postambleButton = QPushButton( 'POSTAMBLE', self )
        self.sendEmailButton = QPushButton( 'SEND EMAIL', self )
        self.sendEmailButton.setEnabled( False )
        self.testEmailButton.setEnabled( False )
        self.emailComboBox = QComboBox( )
        self.setWindowTitle( 'PLEX EMAIL NEWSLETTER' )
        self.preambleDialog = PlexEmailGUI.PrePostAmbleDialog( self, title = 'PREAMBLE' )
        self.postambleDialog = PlexEmailGUI.PrePostAmbleDialog( self, title = 'POSTAMBLE' )
        self.preamble = ''
        self.postamble = ''
        self.getContacts( self.token )
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
        self.testEmailButton.clicked.connect( self.createSummaryEmail )
        # self.getContactsButton.clicked.connect( self.getContacts )
        self.preambleButton.clicked.connect( self.preambleDialog.show )
        self.postambleButton.clicked.connect( self.postambleDialog.show )
        self.sendEmailButton.clicked.connect( self.sendEmail )
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
        pngData = dict( chain.from_iterable([ pngDataPRE.items( ), pngDataPOST.items( ) ]) )
        if len(pngData) != len(pngDataPRE) + len( pngDataPOST ) and len(pngData) != 0:
            print( 'ERROR, MUST HAVE SOME INTERSECTIONS IN PNG FILE NAMES.' )
            print( 'COMMON PNG FILES: %s.' % sorted( set( pngDataPRE.keys( ) ) &
                                                     set( pngDataPOST.keys( ) ) ) )
            print( "I HOPE YOU KNOW WHAT YOU'RE DOING." )
        htmlString = plexemail.get_summary_html(
            self.token, fullURL = self.fullURL,
            preambleText = preambleText, postambleText = postambleText,
            pngDataDict = pngData )
        if len(htmlString) != 0:
            self.mainEmailCanvas.setHtml( htmlString )
            self.sendEmailButton.setEnabled( True )

    def sendEmail( self ):
        qd = PlexEmailGUI.EmailSendDialog( self )
        result = qd.exec_( )            
        
    def getContacts( self, token ):
        emails = plexcore.get_mapped_email_contacts(
            token, verify = self.verify )
        if len(emails) == 0: return
        self.testEmailButton.setEnabled( True )
        #
        ## now do some google client magic to get the names
        name_emails = get_email_contacts_dict(
            emails, verify = self.verify )
        self.emailComboBox.clear( )
        def get_email( input_tuple ):
            name, email = input_tuple
            if name is not None:
                return '%s <%s>' % ( name, email )
            return email
        self.emailComboBox.addItems(
            sorted( map( get_email, name_emails ) ) )
        self.emailComboBox.setEditable( False )
        self.emailComboBox.setCurrentIndex( 0 )
