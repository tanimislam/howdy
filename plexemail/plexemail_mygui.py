import os, sys, titlecase, datetime, tabulate
import json, re, urllib, time, glob, multiprocessing
from docutils.examples import html_parts
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import QAction, QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget, QTabWidget, QApplication, QTableView, QHeaderView, QAbstractItemView, QMenu
from PyQt5.QtGui import QFont, QFontDatabase, QFontMetrics, QCursor
from PyQt5.QtCore import QAbstractTableModel, Qt

from plexcore import plexcore, mainDir, QDialogWithPrinting, plexcore_texts_gui
from plexemail import plexemail, plexemail_basegui, emailAddress, emailName
from plexemail import get_email_contacts_dict

class QLineCustom( QLineEdit ):
    def __init__( self ):
        super( QLineCustom, self ).__init__( )
        
    def returnPressed( ):
        self.setText( titlecase.titlecase( self.text( ) ).strip( ) )

class PlexGuestEmailTM( QAbstractTableModel ):
    def __init__( self, parent, emailMapping ):
        super( PlexGuestEmailTM, self ).__init__( parent )
        self.headers = [ 'NAME', 'EMAIL' ]
        self.layoutAboutToBeChanged.emit( )
        emails_names_dict = { }
        for entry in emailMapping:
            if 'name' in entry:
                key = '%s <%s>' % (
                    ' '.join( entry[ 'name' ].split( )[::-1] ), entry[ 'email' ] )
                emails_names_dict[ key ] = (
                    entry[ 'name' ], entry[ 'email' ] )
            else:
                key = entry[ 'email' ]
                emails_names_dict[ key ] = (
                    "", entry[ 'email' ] )
        emailnames_sorted = sorted( emails_names_dict.keys( ) )
        self.names = list(map(lambda key: emails_names_dict[ key ][ 0 ],
                              emailnames_sorted ) )
        self.emails = list(map(lambda key: emails_names_dict[ key ][ 1 ],
                               emailnames_sorted ) )
        self.layoutChanged.emit( )

    def rowCount( self, parent ):
        return len( self.emails )

    def columnCount( self, parent ):
        return 2

    def headerData( self, col, orientation, role ):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[ col ]
        return None

    def data( self, index, role ):
        if not index.isValid( ): return None
        row = index.row( )
        col = index.column( )
        if role == Qt.DisplayRole:
            if col == 0: return self.names[ row ]
            elif col == 1: return self.emails[ row ]

    def copyEmailAndAddressAtRow(self, row ):
        if row < 0: return
        if row >= len( self.names ): return
        if self.names[ row ] == "":
            txtToCopy = self.emails[ row ]
        else:
            txtToCopy = "%s <%s>" % (
                self.names[row], self.emails[ row ] )
        #
        ## copy to clipboard
        QApplication.clipboard( ).setText( txtToCopy )

        
class PlexGuestEmailTV( QTableView ):

    @classmethod
    def getTargetWidth( cls, coll_of_strings, resolution ):
        qf = QFont( )
        qf.setFamily( 'Consolas' )
        qf.setPointSize( int( 11 * resolution ) )
        qfm = QFontMetrics( qf )
        #
        return int(
            1.50 * max(map(lambda string: qfm.width( string.strip( ) ), coll_of_strings ) ) )

    @classmethod
    def getTargetHeight( cls, num_rows, resolution ):
        qf = QFont( )
        qf.setFamily( 'Consolas' )
        qf.setPointSize( int( 11 * resolution ) )
        qfm = QFontMetrics( qf )
        #
        return int(
            1.15 * num_rows * qfm.height( ) )
    
    def __init__( self, parent, emailMapping, resolution ):
        super( PlexGuestEmailTV, self ).__init__( parent )
        #
        self.tm = PlexGuestEmailTM( parent, emailMapping )
        self.setModel( self.tm )
        self.setShowGrid( True )
        self.verticalHeader( ).setSectionResizeMode( QHeaderView.Fixed )
        self.horizontalHeader( ).setSectionResizeMode( QHeaderView.Fixed )
        self.setSelectionBehavior( QAbstractItemView.SelectRows )
        self.setSelectionMode( QAbstractItemView.SingleSelection ) # single row
        #
        self.menu = QMenu( self )
        copyAction = QAction( 'Copy Email and Name', self.menu )
        copyAction.triggered.connect( self.copyEmailAndName )
        self.menu.addAction( copyAction )
        printTableAction = QAction( 'Dump Table', self.menu )
        printTableAction.triggered.connect( self.printTable )
        self.menu.addAction( printTableAction )
        #
        ## get info from each column
        self.setColumnWidth( 0, PlexGuestEmailTV.getTargetWidth(
            [ 'NAME', ] + list(map(lambda entry: entry[ 'name' ],
                                   filter(lambda entry: 'name' in entry,
                                          emailMapping ) ) ),
            resolution ) )
        self.setColumnWidth( 1, PlexGuestEmailTV.getTargetWidth(
            [ 'EMAIL', ] + list(map(lambda entry: entry[ 'email' ],
                                    emailMapping ) ),
            resolution ) )
        self.setFixedHeight( PlexGuestEmailTV.getTargetHeight(
            len( emailMapping ), resolution ) )
        self.totalWidth = 1.02 * (
            self.columnWidth( 0 ) + self.columnWidth( 1 ) )
        self.totalHeight = self.size( ).height( )

    def contextMenuEvent( self, evt ):
        self.menu.popup( QCursor.pos( ) )

    def copyEmailAndName( self ):
        index_valid = max( self.selectionModel( ).selectedIndexes( ) )
        self.tm.copyEmailAndAddressAtRow( index_valid.row( ) )

    def printTable( self ):
        names = self.tm.names
        emails = self.tm.emails
        data = list(zip(names, emails))
        mytxt = tabulate.tabulate( data, headers = [ 'NAME', 'EMAIL' ],
                                   tablefmt = 'rst' )
        QApplication.clipboard( ).setText( mytxt )

class PlexEmailMyGUI( QDialogWithPrinting ):
    
    def __init__( self, doLocal = True, doLarge = False, verify = True ):
        super( PlexEmailMyGUI, self ).__init__( None )
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
        #
        self.setWindowTitle( 'SEND CUSTOM EMAIL' )
        qf = QFont( )
        qf.setFamily( 'Consolas' )
        qf.setPointSize( int( 11 * self.resolution ) )
        qfm = QFontMetrics( qf )
        self.mainEmailCanvas = QTextEdit( )
        self.mainEmailCanvas.setTabStopWidth( 2 * qfm.width( 'A' ) )
        self.subjectLine = QLineCustom( )
        self.statusLabel = QLabel( )
        self.checkRSTButton = QPushButton( '\n'.join( 'CHECK EMAIL'.split( ) ) )
        self.emailListButton = QPushButton( '\n'.join( 'PLEX GUESTS'.split( ) ) )
        self.emailSendButton = QPushButton( '\n'.join( 'SEND ALL EMAIL'.split( ) ) )
        self.emailTestButton = QPushButton( '\n'.join( 'SEND TEST EMAIL'.split( ) ) )
        self.pngShowButton = QPushButton( 'SHOW PNGS' )
        self.emailSendButton.setEnabled( False )
        self.emailTestButton.setEnabled( False )
        #
        self.emails_array = get_email_contacts_dict(
            plexcore.get_mapped_email_contacts(
                self.token, verify = self.verify ), verify = self.verify )
        self.emails_array.append(( emailName, emailAddress ) )
        #
        self.pngWidget = plexemail_basegui.PNGWidget( self )
        self.pngWidget.hide( )
        #
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #
        topWidget = QWidget( )
        topLayout = QGridLayout( )
        topWidget.setLayout( topLayout )
        topLayout.addWidget( self.checkRSTButton, 0, 0, 1, 2 )
        topLayout.addWidget( self.emailListButton, 0, 2, 1, 2 )
        topLayout.addWidget( self.emailSendButton, 0, 4, 1, 2 )
        topLayout.addWidget( self.emailTestButton, 0, 6, 1, 2 )
        topLayout.addWidget( self.pngShowButton, 1, 0, 1, 8 )
        topLayout.addWidget( QLabel( 'SUBJECT:' ), 2, 0, 1, 3 )
        topLayout.addWidget( self.subjectLine, 2, 2, 1, 6 )
        myLayout.addWidget( topWidget )
        #
        myLayout.addWidget( self.mainEmailCanvas )
        myLayout.addWidget( self.statusLabel )
        #
        if len( self.emails_array ) == 0:
            self.emailListButton.setEnabled( False )
            self.emailTestButton.setEnabled( False )
        self.emailListButton.clicked.connect( self.showEmails )
        self.checkRSTButton.clicked.connect( self.checkRST )
        self.emailSendButton.clicked.connect( self.sendEmail )
        self.emailTestButton.clicked.connect( self.testEmail )
        self.pngShowButton.clicked.connect( self.showPNGs )
        #
        self.setFixedWidth( 55 * qfm.width( 'A' ) )
        self.setFixedHeight( 33 * qfm.height( ) )
        self.show( )

    def showPNGs( self ):
        self.pngWidget.show( )
        # self.pngAddButton.setEnabled( False )

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
            map( email_name_dict,
                 sorted( self.emails_array,
                         key = lambda tup: tup[0].split( )[-1] ) ) )
        pgetv = PlexGuestEmailTV(
            qdl, emailMapping, self.resolution )
        myLayout.addWidget( pgetv )
        qdl.setFixedWidth( pgetv.totalWidth )
        qdl.setFixedHeight( pgetv.totalHeight )
        qdl.show( )
        result = qdl.exec_( )

    def checkRST( self ):
        self.statusLabel.setText( '' )
        myStr = self.mainEmailCanvas.toPlainText( ).strip( )
        if len( myStr ) == 0:
            self.emailSendButton.setEnabled( False )
            self.emailTestButton.setEnabled( False )
            self.statusLabel.setText( 'INVALID RESTRUCTUREDTEXT' )
            return
        mainText = '\n'.join([ 'Hello Friend,', '', myStr ])
        if not plexcore_texts_gui.checkValidConversion( mainText, form = 'rst' ):
            self.emailSendButton.setEnabled( False )
            self.emailTestButton.setEnabled( False )
            self.statusLabel.setText( 'INVALID RESTRUCTUREDTEXT' )
            return
        html = plexcore_texts_gui.convertString( mainText, form = 'rst' )
        self.emailSendButton.setEnabled( True )
        self.emailTestButton.setEnabled( True )
        self.statusLabel.setText( 'VALID RESTRUCTUREDTEXT' )
        #
        qdl = QDialogWithPrinting( self, doQuit = False, isIsolated = True )
        qdl.setWindowTitle( 'HTML EMAIL BODY' )
        qte = plexcore_texts_gui.HtmlView( qdl )
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
        qf.setPointSize( int( 11 * self.resolution ) )
        qfm = QFontMetrics( qf )
        qdl.setFixedWidth( 85 * qfm.width( 'A' ) )
        qdl.setFixedHeight( 550 )
        qte.setHtml( html )
        qdl.show( )
        #
        ##
        result = qdl.exec_( )

    def getHTML( self ):
        mainText = '\n'.join([ 'Hello Friend', '', self.mainEmailCanvas.toPlainText( ).strip( ) ])
        try:
            html = plexcore_texts_gui.convertString( mainText, form = 'rst' )
            # html = plexcore.processValidHTMLWithPNG( html, self.pngWidget.getAllDataAsDict( ) )
            return True, html
        except Exception as e:
            return False, None

    def toHTML( self, filename ):
        self.statusLabel.setText( 'TO HTML FILE' )
        status, html = self.getHTML( )
        
    def sendEmail( self ):
        self.statusLabel.setText( 'SENDING EMAIL' )
        status, html = self.getHTML( )
        if not status:
            self.emailSendButton.setEnabled( False )
            self.statusLabel.setText( 'INVALID RESTRUCTUREDTEXT' )
            return
        subject = titlecase.titlecase( self.subjectLine.text( ).strip( ) )
        if len(subject) == 0:
            subject = 'GENERIC SUBJECT FOR %s' % datetime.datetime.now( ).strftime( '%B-%m-%d' )
        for name, email in self.emails_array:
            plexemail.send_individual_email_full( html, subject, email, name = name, )
        self.statusLabel.setText( 'EMAILS SENT' )

    def testEmail( self ):
        self.statusLabel.setText( 'SENDING EMAIL TO %s.' % emailAddress.upper( ) )
        status, html = self.getHTML( )
        if not status:
            self.emailSendButton.setEnabled( False )
            self.statusLabel.setText( 'INVALID RESTRUCTUREDTEXT' )
            return
        subject = titlecase.titlecase( self.subjectLine.text( ).strip( ) )
        if len( subject ) == 0:
            subject = 'GENERIC SUBJECT FOR %s' % datetime.datetime.now( ).strftime( '%B-%m-%d' )
        #
        plexemail.send_individual_email_full(
            html, subject, emailAddress, name = emailName )
        self.statusLabel.setText( 'EMAILS SENT TO %s.' % emailAddress.upper( ) )
