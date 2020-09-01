
import os, sys, titlecase, datetime, json, re, urllib, time, glob
import pathos.multiprocessing as multiprocessing
from docutils.examples import html_parts
from bs4 import BeautifulSoup
from itertools import chain
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
#
from howdy import resourceDir
from howdy.email import email, email_basegui, emailAddress, emailName, get_email_contacts_dict, get_email_service
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
            self.verify = parent.verify
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
            self.mainHtml = parent.htmlString.strip( )
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
            self.setFixedHeight( int( 0.5 * self.sizeHint( ).height( ) ) )
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
            for fullName in validLists:
                if fullName.endswith('>'):
                    name = fullName.split('<')[0].strip( )
                    fullEmail = fullName.split('<')[1].strip().replace('>', '').strip()
                else:
                    name = None
                    fullEmail = fullName.strip( )
                input_tuples.append(( fullEmail, name ))
            #
            ## now send the emails
            time0 = time.time( )
            self.statusLabel.setText( 'STARTING TO SEND EMAILS...')
            email_service = get_email_service( verify = self.verify )
            mydate = datetime.datetime.now( ).date( )
            def _send_email_perproc( input_tuple ):
                name, fullEmail = input_tuple
                subject = titlecase.titlecase(
                    'Plex Email Newsletter For %s' % mydate.strftime( '%B %Y' ) )
                email.send_individual_email_full(
                    self.mainHtml, subject, fullEmail, name = name,
                    email_service = email_service )
                return True
            with multiprocessing.Pool( processes = min(
                multiprocessing.cpu_count( ), len( input_tuples ) ) ) as pool:
                arrs = list( map( _send_email_perproc, input_tuples ) )
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
            if self.NoButton.isChecked( ): return ""
            #
            myStr = self.textEdit.toPlainText( ).strip( )
            sectionTitle = self.sectionNameWidget.text( ).strip( )
            if not showSection or len( sectionTitle ) == 0: mainText = myStr
            else: mainText = '\n'.join([ sectionTitle, ''.join([ '=' ] * len( sectionTitle )), '', myStr ])
            if not core_texts_gui.checkValidConversion( mainText, form = 'rst' ):
                return ""
            return mainText

        def closeEvent( self, evt ):
            self.hide( )

        def addPNGs( self ):
            self.pngWidget.show( )

        def getHTML( self ):
            sectionTitle = self.sectionNameWidget.text( ).strip( )
            mainText = '\n'.join([
                sectionTitle,
                '\n'.join([ '=' ] * len( sectionTitle )  ), '',
                self.textEdit.toPlainText( ).strip( ) ])
            try:
                html = core_texts_gui.convertString( mainText, form = 'rst' )
                return True, html
            except Exception as e:
                return False, None
            
    def __init__( self, doLocal = True, doLarge = False, verify = True ):
        super( HowdyEmailGUI, self ).__init__( None )
        self.resolution = 1.0
        self.verify = verify
        self.htmlString = ''
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
        self.checkEmailButton = QPushButton( 'CHECK EMAIL', self )
        self.emailListButton = QPushButton( 'PLEX GUESTS', self )
        #
        self.preambleButton = QPushButton( 'PREAMBLE', self )
        self.postambleButton = QPushButton( 'POSTAMBLE', self )
        #
        self.emailDialogButton = QPushButton( 'EMAIL DIALOG', self )
        #
        self.emailDialogButton.setEnabled( False )
        self.checkEmailButton.setEnabled( True )
        self.emailComboBox = QComboBox( )
        #
        self.setWindowTitle( 'HOWDY EMAIL NEWSLETTER' )
        self.preambleDialog = HowdyEmailGUI.PrePostAmbleDialog( self, title = 'PREAMBLE' )
        self.postambleDialog = HowdyEmailGUI.PrePostAmbleDialog( self, title = 'POSTAMBLE' )
        self.preamble = ''
        self.postamble = ''
        self.getContacts( self.token )
        myLayout = QGridLayout( )
        self.setLayout( myLayout )
        #
        self.emails_array = get_email_contacts_dict(
            core.get_mapped_email_contacts(
                self.token, verify = self.verify ), verify = self.verify )
        self.emails_array.append(( emailName, emailAddress ) )
        #
        myLayout.addWidget( self.checkEmailButton, 0, 0, 1, 1 )
        myLayout.addWidget( self.emailDialogButton, 0, 1, 1, 1 )
        myLayout.addWidget( self.preambleButton, 1, 0, 1, 1 )
        myLayout.addWidget( self.postambleButton, 1, 1, 1, 1 )
        myLayout.addWidget( self.emailListButton, 2, 0, 1, 2 )
        #
        self.checkEmailButton.clicked.connect( self.createSummaryEmail )
        self.preambleButton.clicked.connect( self.preambleDialog.show )
        self.postambleButton.clicked.connect( self.postambleDialog.show )
        self.emailDialogButton.clicked.connect( self.emailDialog )
        # self.emailTestButton.clicked.connect( self.testEmail )
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
        self.emailDialogButton.setEnabled( False )
        preambleText = self.preambleDialog.sendValidRST( True )
        postambleText = self.postambleDialog.sendValidRST( True )
        self.htmlString, self.restructuredTextString = email.get_summary_html(
            self.token, fullURL = self.fullURL,
            preambleText = preambleText, postambleText = postambleText )
        if len( self.htmlString ) == 0: return
        #
        qdl = QDialogWithPrinting( self, doQuit = False, isIsolated = True )
        qdl.setWindowTitle( 'HTML EMAIL BODY' )
        qte = core_texts_gui.HtmlView( qdl )
        qter = QTextEdit( self )
        qter.setReadOnly( True )
        qter.setPlainText( '%s\n' % self.htmlString )
        qterst = QTextEdit( self )
        qterst.setReadOnly( True )
        qterst.setPlainText( '%s\n' % self.restructuredTextString )
        qdlLayout = QVBoxLayout( )
        qdl.setLayout( qdlLayout )
        tw = QTabWidget( self )
        tw.addTab( qte, 'RENDERED HTML' )
        tw.addTab( qter, 'RAW HTML' )
        tw.addTab( qterst, 'RESTRUCTURED TEXT' )
        qdlLayout.addWidget( tw )
        qf = QFont( )
        qf.setFamily( 'Consolas' )
        qf.setPointSize( int( 11 ) )
        qfm = QFontMetrics( qf )
        qdl.setFixedWidth( 85 * qfm.width( 'A' ) )
        qdl.setFixedHeight( 550 )
        qte.setHtml( self.htmlString )
        qdl.show( )
        #
        ##
        result = qdl.exec_( )
        self.emailDialogButton.setEnabled( True )
        # self.testEmailButton.setEnabled( True )

    def emailDialog( self ):
        qd = HowdyEmailGUI.EmailSendDialog( self )
        result = qd.exec_( )

    def getContacts( self, token ):
        emails = core.get_mapped_email_contacts(
            token, verify = self.verify )
        if len(emails) == 0: return
        self.checkEmailButton.setEnabled( True )
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
