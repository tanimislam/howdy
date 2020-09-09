import glob, os, sys, textwrap, logging, time
from itertools import chain
from docutils.examples import html_parts
from bs4 import BeautifulSoup
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtNetwork import QNetworkAccessManager
#
import email.utils
#
from howdy.core import returnQAppWithFonts, QDialogWithPrinting
from howdy.email import email_basegui, get_all_email_contacts_dict

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

class EmailListDialog( QDialogWithPrinting ):

    class EmailListDelegate( QItemDelegate ):
        def __init__( self, parent ):
            super( EmailListDialog.EmailListDelegate, self ).__init__( parent )
            self.parent = parent

        def createEditor( self, parent, option, index ):
            lineedit = QLineEdit( parent )
            if index.column( ) == 0:
                lineedit.setCompleter( self.parent.emailCompleter )
            elif index.column( ) == 1:
                lineedit.setCompleter( self.parent.nameCompleter )
            return lineedit

        def setEditorData( self, editor, index ):
            index_unproxy = index.model( ).mapToSource( index )
            model = self.parent.emailListTableModel
            row = index_unproxy.row( )
            column = index_unproxy.column( )
            email = model.emails[ row ]
            name = model.names[ row ]
            if column == 0:
                editor.setText( email.strip( ) )
            elif column == 1:
                editor.setText( name.strip( ) )
    
    class EmailListTableModel( QAbstractTableModel ):
        _columnNames = [ 'EMAIL', 'NAME' ]

        statusSignal = pyqtSignal( str )
        
        def __init__( self, parent ):
            super( EmailListDialog.EmailListTableModel, self ).__init__( parent )
            self.parent = parent
            self.emails = [ ]
            self.names = [ ]
            self.key = parent.key

        def columnCount( self, parent ):
            return 2

        def rowCount( self, parent ):
            return len( self.emails )

        def headerData( self, col, orientation, role ):
            if orientation == Qt.Horizontal and role == Qt.DisplayRole:
                return self._columnNames[ col ]

        def flags(self, index):
            return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

        def data( self, index, role ):
            if not index.isValid( ): return None
            row = index.row( )
            col = index.column( )
            email = self.emails[ row ]
            name = self.names[ row ]
            if role != Qt.DisplayRole: return
            #
            if col == 0: return email
            if col == 1: return name

        def addEmail( self, input_tuple ):
            name, emailCurrent = input_tuple
            emails_lower = set(map(lambda emailC: emailC.lower( ), self.emails) )
            names_lower = set(map(lambda name: name.lower( ), self.names ) ) - set([''])
            if emailCurrent.lower( ) in emails_lower:
                self.statusSignal.emit( 'EMAIL ALREADY IN PLACE.' )
                return
            if name.lower( ) != '':
                if name.lower( ) in names_lower:
                    self.statusSignal.emit('NAME ALREADY IN PLACE.' )
                    return
            #
            ## now add the email and name
            self.layoutAboutToBeChanged.emit( )
            self.emails.append( emailCurrent )
            self.names.append( name )
            self.parent.allData[ self.key ] = sorted(
                map(email.utils.parseaddr, zip( self.names, self.emails ) ) )
            self.layoutChanged.emit( )
            self.sort( 1, Qt.AscendingOrder )

        def sort( self, ncol, order ):
            if len( self.emails ) == 0: return
            self.layoutAboutToBeChanged.emit( )
            email_names_list = sorted(zip(self.emails, self.names), key = lambda tup: tup[1] )
            self.emails = list( list(zip(*email_names_list))[0] )
            self.names = list( list(zip(*email_names_list))[1] )
            self.layoutChanged.emit( )            

        def removeEmailAtRow( self, row ):
            assert( row >= 0 and row < len( self.emails ) )
            self.layoutAboutToBeChanged.emit( )
            self.emails.pop( row )
            self.names.pop( row )
            self.parent.allData[ self.key ] = sorted(
                map(email.utils.parseaddr, zip( self.names, self.emails ) ) )
            self.layoutChanged.emit( )
            self.sort( 1, Qt.AscendingOrder )

        def setData( self, index, val, role ):
            if not index.isValid( ): return False
            if role != Qt.EditRole: return False
            #
            row = index.row( )
            col = index.column( )
            currentEmail = self.emails[ row ]
            currentName = self.names[ row ]
            if col == 0: # check and change email
                emails_rem = set(map(lambda emailC: emailC.lower( ), self.emails ) ) - set([ currentEmail.lower() ])
                _, checkEmail = email.utils.parseaddr( val.strip( ) )
                if checkEmail == '': return False
                if checkEmail.lower( ) in emails_rem: return False
                self.emails[ row ] = checkEmail
            elif col == 1: # check and change name
                names_rem =  set(map(lambda name: name.lower( ), self.names ) ) - set([ currentName.lower(), '' ])
                if val.strip( ).lower( ) in names_rem: return False
                self.names[ row ] = val.strip( )
            #
            self.parent.allData[ self.key ] = sorted(
                map(email.utils.parseaddr, zip( self.names, self.emails ) ) )
            self.sort( 1, Qt.AscendingOrder )
            return True

    class EmailListQSortFilterProxyModel( QSortFilterProxyModel ):
        def __init__( self, parent, tm ):
            super( EmailListDialog.EmailListQSortFilterProxyModel, self ).__init__( parent )
            self.setSourceModel( tm )

        def sort( self, ncol, order ):
            self.sourceModel( ).sort( ncol, order )

        def filterAcceptsRow( self, row, sourceParent ):
            return True
            
    class EmailListTableView( QTableView ):
        def __init__( self, parent ):
            super( EmailListDialog.EmailListTableView, self ).__init__( parent )
            self.parent = parent
            self.proxy = EmailListDialog.EmailListQSortFilterProxyModel(
                self, parent.emailListTableModel )
            self.setModel( self.proxy )
            self.setItemDelegate( EmailListDialog.EmailListDelegate( parent ) )
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

        def contextMenuEvent( self, evt ):
            menu = QMenu( self )
            addAction = QAction( 'ADD EMAIL', menu )
            addAction.triggered.connect( self.parent.emailListAddEmailName.show )
            menu.addAction( addAction )
            if len( self.parent.emailListTableModel.emails ) != 0:
                def removeEmail( ):
                    self.parent.emailListTableModel.removeEmailAtRow(
                        self.getValidIndexRow( ) )
                removeAction = QAction( 'REMOVE EMAIL', menu )
                removeAction.triggered.connect( removeEmail )
                menu.addAction( removeAction )
            menu.popup( QCursor.pos( ) )

        def getValidIndexRow( self ):
            index_valid_proxy = max(
                filter(
                    lambda index: index.column( ) == 0,
                    self.selectionModel( ).selectedIndexes( ) ) )
            index_valid = self.proxy.mapToSource( index_valid_proxy )
            return index_valid.row( )        
    
    class EmailListAddEmailName( QDialogWithPrinting ):

        statusSignal = pyqtSignal( tuple )
        
        def __init__( self, parent ):
            super( EmailListDialog.EmailListAddEmailName, self ).__init__(
                parent, doQuit = False, isIsolated = False )
            self.setWindowTitle( 'EMAIL AND NAME TO ADD' )
            self.emailLineEdit = QLineEdit( '' )
            self.nameLineEdit = QLineEdit( '' )
            self.parent = parent
            #
            myLayout = QGridLayout( )
            self.setLayout( myLayout )
            myLayout.addWidget( QLabel( 'EMAIL:' ), 0, 0, 1, 1 )
            myLayout.addWidget( self.emailLineEdit, 0, 1, 1, 3 )
            myLayout.addWidget( QLabel( 'NAME:' ), 1, 0, 1, 1 )
            myLayout.addWidget( self.nameLineEdit, 1, 1, 1, 3 )
            myLayout.addWidget( QLabel( 'PRESS SHIFT+CTRL+A TO ADD EMAIL + NAME.' ), 2, 0, 1, 4 )
            #
            self.emailLineEdit.returnPressed.connect( self.checkValidEmail )
            self.nameLineEdit.returnPressed.connect( self.checkValidName )
            self.emailLineEdit.setCompleter( parent.emailCompleter )
            self.nameLineEdit.setCompleter( parent.nameCompleter )
            addAction = QAction( self )
            addAction.setShortcut( 'Shift+Ctrl+A' )
            addAction.triggered.connect( self.addEmail )
            self.addAction( addAction )
            #
            self.setFixedWidth( 300 )
            self.hide( )

        def checkValidEmail( self, replaceName = True ):
            _, checkEmail = email.utils.parseaddr( self.emailLineEdit.text( ) )
            if checkEmail == '':
                self.emailLineEdit.setText( '' )
                return False
            self.emailLineEdit.setText( checkEmail )
            if checkEmail in self.parent.all_emails and replaceName:
                checkName = self.parent.allData[ 'emails dict rev' ][ checkEmail ]
                self.nameLineEdit.setText( checkName )
            return True

        def checkValidName( self ):
            checkName = self.nameLineEdit.text( ).strip( )
            self.nameLineEdit.setText( checkName )
            return True

        def addEmail( self ):
            checkEmail = ''
            if self.checkValidEmail( replaceName = False ):
                _, checkEmail = email.utils.parseaddr( self.emailLineEdit.text( ) )
            self.checkValidName( )
            checkName = self.nameLineEdit.text( ).strip( )
            self.statusSignal.emit(( checkName, checkEmail ))
            self.hide( )
            self.emailLineEdit.setText( '' )
            self.nameLineEdit.setText( '' )
            
    
    def __init__( self, parent, key = 'to' ):
        super( EmailListDialog, self ).__init__( parent, doQuit = False, isIsolated = False )
        assert( key in ( 'to', 'cc', 'bcc' ) )
        assert( key in parent.allData )
        self.key = key
        self.setWindowTitle( 'EMAIL %s' % key.upper( ) )
        #
        self.allData = parent.allData
        self.all_emails = sorted( parent.allData[ 'emails dict rev' ] )
        self.all_names = sorted( parent.allData[ 'emails dict' ] )
        self.emailCompleter = QCompleter( self.all_emails )
        self.nameCompleter = QCompleter( self.all_names )
        self.emailListAddEmailName = EmailListDialog.EmailListAddEmailName( self )
        self.emailListTableModel = EmailListDialog.EmailListTableModel( self )
        self.emailListTableView = EmailListDialog.EmailListTableView( self )
        #
        self.emailListAddEmailName.statusSignal.connect(
            self.emailListTableModel.addEmail )
        #
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        myLayout.addWidget( QLabel( 'FILTER BOX GOES HERE' ) )
        myLayout.addWidget( self.emailListTableView )
        myLayout.addWidget( QLabel( 'COMMENT BOX' ) )
        #
        self.setFixedWidth( 600 )
        self.setFixedHeight( 600 )
        self.hide( )

class FromDialog( QDialogWithPrinting ):
    class EmailListModel( QAbstractListModel ):
        def __init__( self, emails ):
            super( FromDialog.EmailListModel, self ).__init__( None )
            self.emails = [ ]
            self.changeData( emails )

        def rowCount( self, parent ):
            return len( self.emails )

        def data( self, index, role ):
            if not index.isValid( ): return None
            row = index.row( )
            return self.emails[ row ]

        def changeData( self, new_emails ):
            self.beginResetModel( )
            self.emails = sorted( set( new_emails ) )
            self.endResetModel( )

    class NameListModel( QAbstractListModel ):
        def __init__( self, names ):
            super( FromDialog.NameListModel, self ).__init__( None )
            self.beginResetModel( )
            self.names = sorted( set( names ) )
            self.endResetModel( )

        def rowCount( self, parent ):
            return len( self.names )

        def data( self, index, role ):
            if not index.isValid( ): return None
            row = index.row( )
            return self.names[ row ]
    
    def __init__( self, parent ):
        super( FromDialog, self ).__init__( parent, doQuit = False, isIsolated = False )
        self.setWindowTitle( 'SENDING EMAIL' )
        assert( 'from name' in parent.allData )
        assert( 'from email' in parent.allData )
        #
        self.parent = parent
        self.emailLineEdit = QLineEdit( '' )
        self.nameLineEdit = QLineEdit( '' )
        self.emailListModel = FromDialog.EmailListModel( sorted( self.parent.allData[ 'emails dict rev' ] ) )
        self.nameListModel = FromDialog.NameListModel( sorted( self.parent.allData[ 'emails dict' ] ) )
        #
        myLayout = QGridLayout( )
        self.setLayout( myLayout )
        myLayout.addWidget( QLabel( 'EMAIL:' ), 0, 0, 1, 1 )
        myLayout.addWidget( self.emailLineEdit, 0, 1, 1, 3 )
        myLayout.addWidget( QLabel( 'NAME:' ), 1, 0, 1, 1 )
        myLayout.addWidget( self.nameLineEdit, 1, 1, 1, 3 )
        #
        self.emailLineEdit.returnPressed.connect( self.setValidEmail )
        self.nameLineEdit.returnPressed.connect( self.setValidName )
        self.setCompleters( )
        #
        self.setFixedWidth( 300 )
        self.hide( )

    def setCompleters( self ):
        emailC = QCompleter( self )
        emailC.setPopup( QListView( self ) )
        emailC.setModel( self.emailListModel )
        emailC.setCompletionMode( QCompleter.PopupCompletion )
        emailC.setMaxVisibleItems( 7 )
        #self.emailLineEdit.setCompleter( emailC )
        self.emailLineEdit.setCompleter( QCompleter( sorted( self.parent.allData[ 'emails dict rev' ] ) ) )
        #
        nameC = QCompleter( self )
        nameC.setModel( self.nameListModel )
        nameC.setCompletionMode( QCompleter.PopupCompletion )
        nameC.setMaxVisibleItems( 7 )
        #self.nameLineEdit.setCompleter( nameC )
        self.nameLineEdit.setCompleter( QCompleter( sorted( self.parent.allData[ 'emails dict' ] ) ) )

    def closeEvent( self, evt ):
        self.hide( )
        self.setValidEmail( False )
        self.setValidName( False )
        self.parent.emailAndNameChangedSignal.emit( )

    def setValidEmail( self, emit = True ):
        _, checkEmail = email.utils.parseaddr( self.emailLineEdit.text( ) )
        if checkEmail == '':
            validEmail = self.parent.allData[ 'from email' ]
            self.emailLineEdit.setText( validEmail )
            return
        self.parent.allData[ 'from email' ] = checkEmail
        self.emailLineEdit.setText( checkEmail )
        if checkEmail in self.parent.allData[ 'emails dict rev' ]:
            checkName = self.parent.allData[ 'emails dict rev' ][ checkEmail ]
            self.parent.allData[ 'from name' ] = checkName
            self.nameLineEdit.setText( checkName )
            emails = self.parent.allData[ 'emails dict' ][ checkName ]
            #self.emailListModel.changeData( emails )
            #self.emailLineEdit.setCompleter( QCompleter( sorted( emails ) ) )
        if emit: self.parent.emailAndNameChangedSignal.emit( )

    def setValidName( self, emit = True, setEmail = False ):
        checkName = self.nameLineEdit.text( ).strip( )
        self.parent.allData[ 'from name' ] = checkName
        self.nameLineEdit.setText( checkName )
        if checkName == '' or checkName not in self.parent.allData[ 'emails dict' ]:
            emails = sorted( self.parent.allData[ 'emails dict rev' ] )
            #self.emailListModel.changeData( emails )
            self.emailLineEdit.setCompleter( QCompleter( sorted( emails ) ) )
        elif checkName in self.parent.allData[ 'emails dict' ]:
            emails = self.parent.allData[ 'emails dict' ][ checkName ]
            #self.emailListModel.changeData( emails )
            #self.emailLineEdit.setCompleter( QCompleter( sorted( emails ) ) )
        if emit: self.parent.emailAndNameChangedSignal.emit( )        

    def getEmailAndName( self ):
        validEmail = self.parent.allData[ 'from email' ]
        validName = self.parent.allData[ 'from name' ]
        if validEmail == '': return ''
        emailAndName = validEmail
        if validName == '': return emailAndName
        return email.utils.formataddr( ( validName, validEmail ) )

class ConvertWidget( QDialogWithPrinting ):
    emailAndNameChangedSignal = pyqtSignal( )
    
    def __init__( self, verify = True ):
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
        self.allData = {
            'from email' : '',
            'from name' : '',
            'to' : [ ],
            'cc' : [ ],
            'bcc' : [ ] }
        time0 = time.time( )
        self.allData[ 'emails dict' ] = get_all_email_contacts_dict(
            verify = verify, pagesize = 2000 )
        if len( self.allData[ 'emails dict' ] ) == 0:
            raise ValueError("Error, could find no Google contacts! Exiting..." )
        emails_dict_rev = dict(chain.from_iterable(
            map(lambda name: map(lambda email: ( email, name ), self.allData[ 'emails dict' ][ name ] ),
                self.allData[ 'emails dict' ] ) ) )
        self.allData[ 'emails dict rev' ] = emails_dict_rev                                                      
        logging.info( 'took %0.3f seconds to find all %d Google contacts.' % (
            time.time( ) - time0, len( self.allData[ 'emails dict' ] ) ) )
        #
        self.statusDialog = QLabel( )
        self.rowColDialog = QLabel( )
        self.textOutput = QPlainTextEdit( )
        self.textOutput.setTabStopWidth( 2 * qfm.width( 'A' ) )
        #
        self.fromDialog = FromDialog( self )
        self.toEmailListDialog = EmailListDialog( self, 'to' )
        self.ccEmailListDialog = EmailListDialog( self, 'cc' )
        self.bccEmailListDialog = EmailListDialog( self, 'bcc' )
        #
        self.fromButton = QPushButton( 'FROM' )
        self.toButton = QPushButton( 'TO' )
        self.ccButton = QPushButton( 'CC' )
        self.bccButton = QPushButton( 'BCC' )
        self.sendButton = QPushButton( 'SEND' )
        #
        self.fromLabel = QLabel( '' )
        self.subjLineEdit = QLineEdit( '' )
        #
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
        topLayout = QGridLayout( )
        topWidget.setLayout( topLayout )
        topLayout.addWidget( self.fromButton, 0, 0, 1, 1 )
        topLayout.addWidget( self.toButton, 0, 1, 1, 1 )
        topLayout.addWidget( self.ccButton, 0, 2, 1, 1 )
        topLayout.addWidget( self.bccButton, 0, 3, 1, 1 )
        topLayout.addWidget( self.sendButton, 0, 4, 1, 1 )
        #
        topLayout.addWidget( self.convertButton, 1, 0, 1, 1 )
        topLayout.addWidget( self.saveButton, 1, 1, 1, 1 )
        topLayout.addWidget( self.loadButton, 1, 2, 1, 1 )
        topLayout.addWidget( self.pngShowButton, 1, 3, 1, 1 )
        #
        topLayout.addWidget( QLabel( 'FROM:' ), 2, 0, 1, 1 )
        topLayout.addWidget( self.fromLabel, 2, 1, 1, 4 )
        topLayout.addWidget( QLabel( 'SUBJECT:' ), 3, 0, 1, 1 )
        topLayout.addWidget( self.subjLineEdit, 3, 1, 1, 4 )
        #
        myLayout.addWidget( topWidget )
        myLayout.addWidget( self.textOutput )
        botWidget = QWidget( )
        botLayout = QHBoxLayout( )
        botWidget.setLayout( botLayout )
        botLayout.addWidget( self.rowColDialog )
        botLayout.addWidget( self.statusDialog )
        myLayout.addWidget( botWidget )
        #
        self.fromButton.clicked.connect( self.fromDialog.show )
        self.toButton.clicked.connect( self.toEmailListDialog.show )
        self.ccButton.clicked.connect( self.ccEmailListDialog.show )
        self.bccButton.clicked.connect( self.bccEmailListDialog.show )
        self.emailAndNameChangedSignal.connect( self.changeEmailAndName )
        self.convertButton.clicked.connect( self.printHTML )
        self.saveButton.clicked.connect( self.saveFileName )
        self.loadButton.clicked.connect( self.loadFileName )
        self.pngShowButton.clicked.connect( self.pngWidget.show )
        self.textOutput.cursorPositionChanged.connect( self.showRowCol )
        self.subjLineEdit.returnPressed.connect( self.fixSubject )
        saveAction = QAction( self )
        saveAction.setShortcut( 'Ctrl+S' )
        saveAction.triggered.connect( self.saveFileName )
        self.addAction( saveAction )
        #
        self.setFixedHeight( 700 )
        self.setFixedWidth( 600 )

    def changeEmailAndName( self ):
        self.fromLabel.setText( self.fromDialog.getEmailAndName( ) )

    def fixSubject( self ):
        self.subjLineEdit.setText( self.subjLineEdit.text( ).strip( ) )

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
