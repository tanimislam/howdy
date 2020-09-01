
import os, sys, titlecase, datetime, json, re, urllib, time, glob
import pathos.multiprocessing as multiprocessing
from docutils.examples import html_parts
from bs4 import BeautifulSoup
from itertools import chain
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
#
from howdy import resourceDir
from howdy.email import email, email_basegui, emailAddress, emailName, get_email_contacts_dict
from howdy.email.email_mygui import HowdyGuestEmailTV
from howdy.core import core, QDialogWithPrinting
#
## throw an exception if cannot
try:
    from howdy.core import core_texts_gui
except ImportError as e:
    raise ValueError("Error, we need to be able to import PyQt5.QtWebEngineWidgets, which we cannot do. On Ubuntu Linux machines you can try 'apt install python3-pyqt5.qtwebengine'." )

class HowdyEmailGUI( QDialogWithPrinting ):
    class EmailSendDialog( QDialogWithPrinting ):
        
        def __init__( self, parent ):
            super( HowdyEmailGUI.EmailSendDialog, self ).__init__( parent, isIsolated = False )
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
            access_token = core.oauth_get_access_token( )
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
                list( pool.map( email.send_individual_email_perproc, input_tuples ) )
                self.statusLabel.setText( 'SENT %d EMAILS IN %0.3f SECONDS.' %
                                          ( len( input_tuples ), time.time() - time0 ) )
                #
                ## if I have sent out ALL EMAILS, then I mean to update the newsletter
                if len(validLists) == len( self.allRadioButtons ):
                    core.set_date_newsletter( )
            
    class PrePostAmbleDialog( QDialogWithPrinting ):
        
        def __init__( self, parent, title = 'Preamble' ):
            super( HowdyEmailGUI.PrePostAmbleDialog, self ).__init__(
                parent, isIsolated = False )
            self.parent = parent
            self.sectionNameWidget = QLineEdit( titlecase.titlecase( title ) )
            self.testTextButton = QPushButton( 'TEST TEXT' )
            self.pngAddButton = QPushButton( 'ADD PNGS' )
            self.textEdit = QTextEdit( )
            self.statusLabel = QLabel( )
            self.setWindowTitle( title )
            self.setModal( True )
            self.isValidRST = False
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
            self.pngWidget = email_basegui.PNGWidget( self )
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
            #self.testTextButton.clicked.connect( self.checkValidLaTeX )
            self.testTextButton.clicked.connect( self.checkRST )
            self.pngAddButton.clicked.connect( self.addPNGs )
            #
            self.setFixedHeight( 650 )
            self.setFixedWidth( self.sizeHint( ).width( ) )

        def checkRST( self ):
            self.statusLabel.setText( '' )
            myStr = self.textEdit.toPlainText( ).strip( )
            if len( myStr ) == 0:
                self.statusLabel.setText( 'INVALID RESTRUCTUREDTEXT' )
                self.isValidRST = False
                return
            sectionTitle = self.sectionNameWidget.text( ).strip( )
            mainText = '\n'.join([ sectionTitle, ''.join([ '=' ] * len( sectionTitle )), '', myStr ])
            if not core_texts_gui.checkValidConversion( mainText, form = 'rst' ):
                self.statusLabel.setText( 'INVALID RESTRUCTUREDTEXT' )
                self.isValidRST = False
                return
            self.isValidRST = True
            html = core_texts_gui.convertString( mainText, form = 'rst' )
            self.statusLabel.setText( 'VALID RESTRUCTUREDTEXT' )
            #
            qdl = QDialogWithPrinting( self, doQuit = False, isIsolated = True )
            qdl.setWindowTitle( 'HTML EMAIL BODY' )
            qte = core_texts_gui.HtmlView( qdl )
            qter = QTextEdit( self )
            qter.setReadOnly( True )
            qter.setPlainText( '%s\n' % html )
            qdlLayout = QVBoxLayout( )
            qdl.setLayout( qdlLayout )
            tw = QTabWidget( self )
            tw.addTab( qte, 'RENDERED HTML' )
            tw.addTab( qter, 'RAW HTML' )
            qdlLayout.addWidget( tw )
            qf = QFont( )
            qf.setFamily( 'Consolas' )
            qf.setPointSize( int( 11 ) )
            qfm = QFontMetrics( qf )
            qdl.setFixedWidth( 85 * qfm.width( 'A' ) )
            qdl.setFixedHeight( 550 )
            qte.setHtml( html )
            qdl.show( )
            #
            ##
            result = qdl.exec_( )

        def sendValidRST( self, showSection = False ):
            myStr = self.textEdit.toPlainText( ).strip( )
            if not showSection: mainText = myStr
            else: mainText = '\n'.join([ sectionTitle, ''.join([ '=' ] * len( sectionTitle )), '', myStr ])
            if not core_texts_gui.checkValidConversion( mainText, form = 'rst' ):
                return ""
            return mainText

        def closeEvent( self, evt ):
            self.NoButton.toggle( )
            self.hide( )

        def addPNGs( self ):
            self.pngWidget.show( )

        def getHTML( self ):
            sectionTitle = self.sectionNameWidget.text( ).strip( )
            mainText = '\n'.join([
                sectionTitle,
                '\n'.join([ '=' ] * len( sectionTitle )  ), '', self.textEdit.toPlainText( ).strip( ) ])
            try:
                html = core_texts_gui.convertString( mainText, form = 'rst' )
                return True, html
            except Exception as e:
                return False, None
            
    def __init__( self, doLocal = True, doLarge = False, verify = True ):
        super( HowdyEmailGUI, self ).__init__( None )
        self.resolution = 1.0
        self.verify = verify
        if doLarge:
            self.resolution = 2.0
        for fontFile in glob.glob( os.path.join( resourceDir, '*.ttf' ) ):
            QFontDatabase.addApplicationFont( fontFile )
        self.setStyleSheet("""
        QWidget {
        font-family: Consolas;
        font-size: %d;
        }""" % ( int( 11 * self.resolution ) ) )
        dat = core.checkServerCredentials(
            doLocal = doLocal, verify = self.verify )
        if dat is None:
            raise ValueError( "Error, cannot access the Plex media server." )
        self.fullURL, self.token = dat
        #
        self.testEmailButton = QPushButton( 'TEST EMAIL', self )
        self.preambleButton = QPushButton( 'PREAMBLE', self )
        self.postambleButton = QPushButton( 'POSTAMBLE', self )
        self.sendEmailButton = QPushButton( 'SEND EMAIL', self )
        self.sendEmailButton.setEnabled( False )
        self.testEmailButton.setEnabled( True )
        self.emailListButton = QPushButton( 'PLEX GUESTS' )
        self.setWindowTitle( 'PLEX EMAIL NEWSLETTER' )
        self.preambleDialog = HowdyEmailGUI.PrePostAmbleDialog( self, title = 'PREAMBLE' )
        self.postambleDialog = HowdyEmailGUI.PrePostAmbleDialog( self, title = 'POSTAMBLE' )
        self.preamble = ''
        self.postamble = ''
        myLayout = QGridLayout( )
        self.setLayout( myLayout )
        #
        self.emails_array = get_email_contacts_dict(
            core.get_mapped_email_contacts(
                self.token, verify = self.verify ), verify = self.verify )
        self.emails_array.append(( emailName, emailAddress ) )
        #
        myLayout.addWidget( self.testEmailButton, 0, 0, 1, 1 )
        myLayout.addWidget( self.sendEmailButton, 0, 1, 1, 1 )
        myLayout.addWidget( self.preambleButton, 1, 0, 1, 1 )
        myLayout.addWidget( self.postambleButton, 1, 1, 1, 1 )
        myLayout.addWidget( self.emailListButton, 2, 0, 1, 2 )
        #
        self.testEmailButton.clicked.connect( self.createSummaryEmail )
        self.preambleButton.clicked.connect( self.preambleDialog.show )
        self.postambleButton.clicked.connect( self.postambleDialog.show )
        self.sendEmailButton.clicked.connect( self.sendEmail )
        self.emailListButton.clicked.connect( self.showEmails )
        #
        #qf = QFont( )
        #qf.setFamily( 'Consolas' )
        #qf.setPointSize( int( 11 * self.resolution ) )
        #qfm = QFontMetrics( qf )
        #self.setFixedWidth( 55 * qfm.width( 'A' ) )
        #self.setFixedHeight( 33 * qfm.height( ) )
        self.show( )

    def showEmails( self ):
        qdl = QDialogWithPrinting( self, doQuit = False, isIsolated = True )
        qdl.setModal( True )
        qdl.setWindowTitle( 'PLEX MAPPED GUEST EMAILS' )
        myLayout = QVBoxLayout( )
        qdl.setLayout( myLayout )
        def email_name_dict( tup ):
            name, email = tup
            data_dict = { 'email' : email }
            if name is not None:
                data_dict[ 'name' ] = name
            return data_dict
        emailMapping = list(
            map( email_name_dict, self.emails_array ) )
        pgetv = HowdyGuestEmailTV(
            qdl, emailMapping, self.resolution )
        myLayout.addWidget( pgetv )
        qdl.setFixedWidth( pgetv.totalWidth )
        qdl.setFixedHeight( pgetv.totalHeight )
        qdl.show( )
        result = qdl.exec_( )

    def createSummaryEmail( self ):
        self.sendEmailButton.setEnabled( False )
        preambleText = self.preambleDialog.sendValidRST( False )
        postambleText = self.postambleDialog.sendValidRST( )
        htmlString = email.get_summary_html(
            self.token, fullURL = self.fullURL,
            preambleText = preambleText, postambleText = postambleText )
        if len( htmlString ) == 0: return
        #
        qdl = QDialogWithPrinting( self, doQuit = False, isIsolated = True )
        qdl.setWindowTitle( 'HTML EMAIL BODY' )
        qte = core_texts_gui.HtmlView( qdl )
        qter = QTextEdit( self )
        qter.setReadOnly( True )
        qter.setPlainText( '%s\n' % htmlString )
        qdlLayout = QVBoxLayout( )
        qdl.setLayout( qdlLayout )
        tw = QTabWidget( self )
        tw.addTab( qte, 'RENDERED HTML' )
        tw.addTab( qter, 'RAW HTML' )
        qdlLayout.addWidget( tw )
        qf = QFont( )
        qf.setFamily( 'Consolas' )
        qf.setPointSize( int( 11 ) )
        qfm = QFontMetrics( qf )
        qdl.setFixedWidth( 85 * qfm.width( 'A' ) )
        qdl.setFixedHeight( 550 )
        qte.setHtml( htmlString )
        qdl.show( )
        #
        ##
        result = qdl.exec_( )
        # self.mainEmailCanvas.setHtml( htmlString )
        self.sendEmailButton.setEnabled( True )

    def sendEmail( self ):
        qd = HowdyEmailGUI.EmailSendDialog( self )
        result = qd.exec_( )
