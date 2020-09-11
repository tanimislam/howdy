import os, sys, titlecase, datetime, json, re, urllib, time, glob
import pathos.multiprocessing as multiprocessing
from email.utils import formataddr
from bs4 import BeautifulSoup
from itertools import chain
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
#
from howdy import resourceDir
from howdy.core import core, QDialogWithPrinting, check_valid_RST, convert_string_RST, HtmlView
from howdy.email import email, email_basegui, emailAddress, emailName, get_email_contacts_dict, get_email_service
from howdy.email.email_mygui import HowdyGuestEmailTV
#from howdy.email.email_demo_gui import HowdyEmailDemoGUI

class HowdyEmailGUI( QDialogWithPrinting ):

    class EmailSendDialogDelegate( QItemDelegate ):
        def __init__( self, model ):
            super( HowdyEmailGUI.EmailSendDialogDelegate, self ).__init__( )
            assert( isinstance( model, HowdyEmailGUI.EmailSendDialogTableModel ) )
            self.model = model

        def createEditor( self, parent, option, index ):
            index_unproxy = index.model( ).mapToSource( index )
            row = index_unproxy.row( )
            col = index_unproxy.column( )
            if col == 0:
                cb = QCheckBox( self )
                cb.setChecked( self.model.should_email[ row ] )
                return cb
            elif index.column( ) == 1:
                return QLabel( self.model.emails_full[ row ] )

        def setEditorData( self, editor, index ):
            index_unproxy = index.model( ).mapToSource( index )
            row = index_unproxy.row( )
            col = index_unproxy.column( )
            if col == 0: # is a QCheckBox
                editor.setChecked( self.model.should_email[ row ] )

        def editorEvent( self, event, model, option, index ):
            index_unproxy = model.mapToSource( index )
            row = index_unproxy.row( )
            col = index_unproxy.column( )
            if event.type( ) == QEvent.MouseButtonPress and col == 0:
                is_email = self.model.should_email[ row ]
                self.model.setData( index_unproxy, not is_email, Qt.CheckStateRole )
                event.accept( )
                return True
            return False

    #
    ## dont-understand-code here: https://stackoverflow.com/a/59230434/3362358
    class EmailSendDialogBooleanDelegate( QItemDelegate ):
        def __init__( self, model ):
            super( HowdyEmailGUI.EmailSendDialogBooleanDelegate, self ).__init__( )
            assert( isinstance( model, HowdyEmailGUI.EmailSendDialogTableModel ) )
            self.model = model
    
        def paint(self, painter, option, index):
            # Depends on how the data function of your table model is implemented
            # 'value' should receive a bool indicate if the checked value.
            value = index.data( Qt.CheckStateRole )  
            self.drawCheck(painter, option, option.rect, value)
            self.drawFocus(painter, option, option.rect)
    
        def editorEvent(self, event, model, option, index):
            if event.type() == QEvent.MouseButtonRelease:
                value = model.data(index, Qt.CheckStateRole )
                model.setData(index, not value, Qt.CheckStateRole )
                event.accept( )
                return True
            return False

    class EmailSendDialogQSortFilterModel( QSortFilterProxyModel ):
        def __init__( self, model ):
            super( HowdyEmailGUI.EmailSendDialogQSortFilterModel, self ).__init__( )
            self.setSourceModel( model )
            model.emitFilterChanged.connect( self.invalidateFilter )

        def filterAcceptsRow( self, rowNumber, sourceParent ):
            return self.sourceModel( ).filterRow( rowNumber )
            
    
    class EmailSendDialogTableModel( QAbstractTableModel ):
        _headers = [ 'SEND?', 'EMAIL' ]

        statusSignal = pyqtSignal( str )
        emitFilterChanged = pyqtSignal( )

        def __init__( self, emails_array, verify = True ):
            super( HowdyEmailGUI.EmailSendDialogTableModel, self ).__init__( )
            self.verify = verify
            self.emails_array = [ ]
            self.emails_full = [ ]
            self.should_email = [ ]
            self.setEmails( emails_array )
            #
            ##
            self.selectTestButton = QPushButton( 'TEST ADDRESS' )
            self.selectAllButton = QPushButton( 'ALL ADDRESSES' )
            self.sendEmailButton = QPushButton( 'SEND EMAIL' )
            self.selectTestButton.clicked.connect( self.selectTest )
            self.selectAllButton.clicked.connect( self.selectAll )
            self.sendEmailButton.clicked.connect( self.sendEmail )
            #
            ## now other members #2: the "show all emails" and "show selected emails"
            self.showAllEmailsButton = QRadioButton( 'ALL EMAILS' )
            self.showSelectedEmailsButton = QRadioButton( 'SELECTED EMAILS' )
            buttonGroup = QButtonGroup( )
            buttonGroup.addButton( self.showAllEmailsButton )
            buttonGroup.addButton( self.showSelectedEmailsButton )
            self.showAllEmailsButton.toggle( )
            self.showAllEmailsButton.clicked.connect( self.setFilterShowWhichEmails )
            self.showSelectedEmailsButton.clicked.connect( self.setFilterShowWhichEmails )
            #
            ## now other members #3: the QLineEdit doing a regex on filter on names OR emails
            self.filterOnNamesOrEmails = QLineEdit( '' )
            self.filterRegExp = QRegExp( '.', Qt.CaseInsensitive, QRegExp.RegExp )
            self.filterOnNamesOrEmails.textChanged.connect( self.setFilterString )
            self.showingEmailsLabel = QLabel( '' )
            self.emitFilterChanged.connect( self.showNumberFilterEmails )
            self.showNumberFilterEmails( )

        def setEmails( self, emails_array ):
            def get_email( input_tuple ):
                name, email = input_tuple
                if name is not None:
                    name = name.replace('"', '').strip( )
                    return formataddr((name, email))
                return email
            self.layoutAboutToBeChanged.emit( )
            self.emails_array = emails_array.copy( )
            self.emails_full = list(map(get_email, emails_array ) )
            self.should_email = [ False ] * len( self.emails_full )
            self.should_email[ 0 ] = True
            self.layoutChanged.emit( )
            self.emitFilterChanged.emit( )

        def selectTest( self ):
            self.layoutAboutToBeChanged.emit( )
            for idx in range( len( self.should_email ) ):
                self.should_email[ idx ] = False
            self.should_email[ 0 ] = True
            self.layoutChanged.emit( )

        def selectAll( self ):
            self.layoutAboutToBeChanged.emit( )
            for idx in range(len( self.should_email ) ):
                self.should_email[ idx ] = True
            self.layoutChanged.emit( )
        
        def sendEmail( self ):
            #
            ## choose which emails to send
            input_tuples = list(map(lambda tup: tup[1], filter(
                lambda tup: tup[0] == True,
                zip( self.should_email, self.emails_array ) ) ) )
            if len( input_tuples ) == 0:
                self.statusSignal.emit( 'SENT NO EMAILS.' )
                return
            #
            ## now send the emails
            time0 = time.time( )
            self.statusSignal.emit( 'STARTING TO SEND EMAILS...' )
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
            self.statusSignal.emit(
                'SENT %d EMAILS IN %0.3f SECONDS.' %
                ( len( input_tuples ), time.time() - time0 ) )
            #
            ## if I have sent out ALL EMAILS, then I mean to update the newsletter
            if all(self.should_email): core.set_date_newsletter( )
            
        def columnCount( self, parent ):
            return 2

        def rowCount( self, parent ):
            return len( self.emails_full )

        def headerData( self, col, orientation, role ):
            if orientation == Qt.Horizontal and role == Qt.DisplayRole:
                return 'EMAIL'

        def flags( self, index ):
            if index.column( ) == 0:
                return Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
            else: return Qt.ItemIsEnabled | Qt.ItemIsSelectable

        def data( self, index, role ):
            if not index.isValid( ): return None
            row = index.row( )
            col = index.column( )
            if role == Qt.DisplayRole and col == 1:
                return self.emails_full[ row ]
            elif role == Qt.CheckStateRole and col == 0:
                return self.should_email[ row ]

        def setData( self, index, val, role ):
            if not index.isValid( ): return False
            row = index.row( )
            col = index.column( )
            if col == 1: return False
            if role != Qt.CheckStateRole: return False
            self.should_email[ row ] = val
            return True

        def filterRow( self, rowNumber ):
            assert( rowNumber >= 0 )
            assert( rowNumber < len( self.emails_full ) )
            name, email = self.emails_array[ rowNumber ]
            #
            ## if not one of selected emails and ONLY show selected emails...
            if not self.showAllEmailsButton.isChecked( ) and not self.should_email[ rowNumber ]: return False
            if self.filterRegExp.indexIn( name ) != -1: return True
            if self.filterRegExp.indexIn( email ) != -1: return True
            return False

        def showNumberFilterEmails( self ):
            num_emails = len(list(filter(self.filterRow, range(len(self.emails_full)))))
            self.showingEmailsLabel.setText('SHOWING %d EMAILS' % num_emails )

        def setFilterString( self, newString ):
            mytext = newString.strip( )
            if len( mytext ) == 0: mytext = '.'
            self.filterRegExp = QRegExp( mytext, Qt.CaseInsensitive, QRegExp.RegExp )
            self.emitFilterChanged.emit( )

        def setFilterShowWhichEmails( self ):
            self.emitFilterChanged.emit( )
    
    class EmailSendDialogTableView( QTableView ):
        def __init__( self, model ):
            super( HowdyEmailGUI.EmailSendDialogTableView, self ).__init__( )
            proxyModel = HowdyEmailGUI.EmailSendDialogQSortFilterModel( model )
            self.setModel( proxyModel )
            self.setItemDelegateForColumn(
                0, HowdyEmailGUI.EmailSendDialogBooleanDelegate( model ) )
            #
            self.setShowGrid( True )
            self.verticalHeader( ).setSectionResizeMode( QHeaderView.Fixed )
            self.horizontalHeader( ).setSectionResizeMode( QHeaderView.Fixed )
            self.setSelectionBehavior( QAbstractItemView.SelectRows )
            self.setSelectionMode( QAbstractItemView.SingleSelection )
            self.setSortingEnabled( True )
            #
            self.setColumnWidth( 0, 180 )
            self.setColumnWidth( 1, 180 )
            #
            toBotAction = QAction( self )
            toBotAction.setShortcut( 'End' )
            toBotAction.triggered.connect( self.scrollToBottom )
            self.addAction( toBotAction )
            #
            toTopAction = QAction( self )
            toTopAction.setShortcut( 'Home' )
            toTopAction.triggered.connect( self.scrollToTop )
            self.addAction( toTopAction )
        
        def getValidIndexRow( self ):
            index_valid = max(
                filter(
                    lambda index: index.column( ) == 0,
                    self.selectionModel( ).selectedIndexes( ) ) )
            return index_valid.row( )
        
        def resizeTableColumns( self, width ):
            self.setColumnWidth( 0, int( 0.07 * width ) )
            self.setColumnWidth( 1, int( 0.93 * width ) )
    
    class EmailSendDialog( QDialogWithPrinting ):
        def __init__( self, parent ):
            super( HowdyEmailGUI.EmailSendDialog, self ).__init__(
                parent, isIsolated = False, doQuit = False )
            self.setModal( True )
            self.verify = parent.verify
            self.setWindowTitle( 'SEND EMAILS' )
            self.emailSendDialogTableModel = HowdyEmailGUI.EmailSendDialogTableModel(
                parent.emails_array, self.verify )
            emailSendDialogTableView = HowdyEmailGUI.EmailSendDialogTableView(
                self.emailSendDialogTableModel )
            self.statusLabel = QLabel( )
            #
            myLayout = QVBoxLayout( )
            self.setLayout( myLayout )
            #
            topLayout = QGridLayout( )
            topWidget = QWidget( self )
            topWidget.setLayout( topLayout )
            topLayout.addWidget( self.emailSendDialogTableModel.selectTestButton, 0, 0, 1, 1 )
            topLayout.addWidget( self.emailSendDialogTableModel.selectAllButton, 0, 1, 1, 1 )
            topLayout.addWidget( self.emailSendDialogTableModel.sendEmailButton, 0, 2, 1, 1 )
            #
            topLayout.addWidget( QLabel( 'FILTER' ), 1, 0, 1, 1 )
            topLayout.addWidget( self.emailSendDialogTableModel.filterOnNamesOrEmails, 1, 1, 1, 2 )
            #
            topLayout.addWidget( QLabel( 'SHOW EMAILS' ), 2, 0, 1, 1 )
            topLayout.addWidget( self.emailSendDialogTableModel.showAllEmailsButton, 2, 1, 1, 1 )
            topLayout.addWidget( self.emailSendDialogTableModel.showSelectedEmailsButton, 2, 2, 1, 1 )
            myLayout.addWidget( topWidget )
            #
            myLayout.addWidget( emailSendDialogTableView )
            #
            botWidget = QWidget( )
            botLayout = QHBoxLayout( )
            botWidget.setLayout( botLayout )
            botLayout.addWidget( self.statusLabel )
            botLayout.addWidget( self.emailSendDialogTableModel.showingEmailsLabel )
            myLayout.addWidget( botWidget )
            #
            self.emailSendDialogTableModel.statusSignal.connect( self.statusLabel.setText )
            #
            self.setFixedWidth( 500 )
            self.setFixedHeight( 600 )
            #self.setFixedWidth( self.sizeHint( ).width( ) )
            #self.setFixedHeight( int( 0.5 * self.sizeHint( ).height( ) ) )
            emailSendDialogTableView.resizeTableColumns( 500 )
            self.hide( )
            
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
            if not check_valid_RST( mainText ):
                self.statusLabel.setText( 'INVALID RESTRUCTUREDTEXT' )
                self.isValidRST = False
                return
            self.isValidRST = True
            html = convert_string_RST( mainText )
            self.statusLabel.setText( 'VALID RESTRUCTUREDTEXT' )
            #
            qdl = QDialogWithPrinting( self, doQuit = False, isIsolated = True )
            qdl.setWindowTitle( 'HTML EMAIL BODY' )
            qte = HtmlView( qdl )
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
            if not check_valid_RST( mainText ):
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
            if not check_valid_RST( mainText ):
                return False, None
            #
            html = convert_string_RST( mainText )
            return True, html
            
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
        self.emails_array = [( emailName, emailAddress ), ] + get_email_contacts_dict(
            core.get_mapped_email_contacts(
                self.token, verify = self.verify ), verify = self.verify )
        self.emailSendDialog = HowdyEmailGUI.EmailSendDialog( self )
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
        self.emailDialogButton.clicked.connect( self.emailSendDialog.show )
        self.emailListButton.clicked.connect( self.showEmails )
        #
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
        qte = HtmlView( qdl )
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
