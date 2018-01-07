import numpy, os, sys, requests
import logging, glob, datetime, pickle, gzip
from . import plextmdb
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from plexcore import plexcore

_headers = [ 'title',  'popularity', 'rating', 'release date', 'added date',
             'genre' ]

class TMDBMyGUI( QWidget ):
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
    
    def __init__( self, token, movie_data_rows, isIsolated = True ):
        super( TMDBMyGUI, self ).__init__( )
        tmdbEngine = plextmdb.TMDBEngine( )
        self.setStyleSheet("""
        QWidget {
        font-family: Consolas;        
        }""")
        if isIsolated:
            self.setWindowTitle( 'My Own Movies' )
        #
        self.token = token
        self.myTableView = MyMovieTableView( self )
        self.genreComboBox = QComboBox( self )
        self.genreComboBox.setEditable( False )
        self.movieLineEdit = QLineEdit( )
        self.genreLabel = QLabel( self )
        #
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #print 
        topWidget = QWidget( )
        topLayout = QGridLayout( )
        topWidget.setLayout( topLayout )
        topLayout.addWidget( self.genreLabel, 0, 0, 1, 4 )
        topLayout.addWidget( QLabel( 'GENRE:' ), 0, 4, 1, 1 )
        topLayout.addWidget( self.genreComboBox, 0, 5, 1, 1 )
        topLayout.addWidget( QLabel( 'MOVIE NAME:' ), 1, 0, 1, 1 )
        topLayout.addWidget( self.movieLineEdit, 1, 1, 1, 5 )
        myLayout.addWidget( topWidget )
        #
        myLayout.addWidget( self.myTableView )
        #
        ## set size, make sure not resizable
        self.setFixedWidth( 680 )
        #
        ## global actions
        if isIsolated:
            quitAction = QAction( self )
            quitAction.setShortcuts( [ 'Ctrl+Q', 'Esc' ] )
            quitAction.triggered.connect( sys.exit )
            self.addAction( quitAction )
            #
            printAction = QAction( self )
            printAction.setShortcut( 'Shift+Ctrl+P' )
            printAction.triggered.connect( self.screenGrab )
            self.addAction( printAction )
        #
        self.genreComboBox.installEventFilter( self )
        self.genreComboBox.currentIndexChanged.connect( self.changeGenre )
        self.myTableView.tm.emitGenreNumMovies.connect( self.setGenreStatus )
        self.movieLineEdit.textChanged.connect( self.myTableView.tm.setFilterString )            
        #
        ##
        self.fill_out_movies( movie_data_rows )
        #
        ##
        self.show( )

    def fill_out_movies( self, movie_data_rows ):
        genres = sorted( set( map(lambda row: row[-3], movie_data_rows ) ) )
        self.genreComboBox.addItems( genres )
        self.genreComboBox.addItem( 'ALL' )
        self.genreComboBox.setCurrentIndex( len( genres ) )
        self.myTableView.tm.filloutMyMovieData( movie_data_rows )
        self.myTableView.tm.setFilterStatus( str( self.genreComboBox.currentText( ) ) )

    def setGenreStatus( self, genre, num ):
        if genre == 'ALL':
            self.genreLabel.setText('%d MOVIES TOTAL' % num )
        else:
            self.genreLabel.setText('%d MOVIES IN %s GENRE' % ( num, str( genre ).upper( ) ) )

    def changeGenre( self ):
        genre = str( self.genreComboBox.currentText( ) )
        self.myTableView.tm.setFilterStatus( genre )

    def setNewToken( self, newToken ):
        self.token = newToken

class MyMovieTableView( QTableView ):
    def __init__( self, parent ):
        super( MyMovieTableView, self ).__init__( )
        #
        self.tm = MyMovieTableModel( parent )
        self.proxy = MyMovieQSortFilterProxyModel( self, self.tm )
        self.setModel( self.proxy )
        for idx in range(6):
            self.setItemDelegateForColumn( idx, StringEntryDelegate( self ) )
        self.setShowGrid( True )
        self.verticalHeader( ).setResizeMode( QHeaderView.Fixed )
        self.horizontalHeader( ).setResizeMode( QHeaderView.Fixed )
        self.setSelectionBehavior( QAbstractItemView.SelectRows )
        self.setSelectionMode( QAbstractItemView.SingleSelection ) # single row        
        self.setSortingEnabled( True )
        #
        self.setColumnWidth(0, 210 )
        self.setColumnWidth(1, 100 )
        self.setColumnWidth(2, 100 )
        #self.setColumnWidth(3, 120 )
        #self.setFixedWidth( 1.1 * ( 210 * 2 + 120 * 2 ) )
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
        #
        ## now do the same thing for contextMenuEvent with action
        popupAction = QAction( self )
        popupAction.setShortcut( 'Ctrl+Shift+S' )
        popupAction.triggered.connect( self.infoOnMovieAtRow )
        self.addAction( popupAction )

    def contextMenuEvent( self, event ):
        menu = QMenu( self )
        infoAction = QAction( 'Information', menu )
        infoAction.triggered.connect( self.infoOnMovieAtRow )
        menu.addAction( infoAction )
        menu.popup( QCursor.pos( ) )

    def infoOnMovieAtRow( self ):
        index_valid_proxy = max(filter(lambda index: index.column( ) == 0,
                                       self.selectionModel().selectedIndexes( ) ) )
        index_valid = self.proxy.mapToSource( index_valid_proxy )
        self.tm.infoOnMovieAtRow( index_valid.row( ) )
#
## qsortfilterproxymodel to implement filtering
class MyMovieQSortFilterProxyModel( QSortFilterProxyModel ):
    def __init__( self, parent, tm ):
        super(MyMovieQSortFilterProxyModel, self).__init__( parent )
        #
        self.setSourceModel( tm )
        tm.emitFilterChanged.connect( self.filterChanged )
        
    def sort( self, ncol, order ):
        self.sourceModel( ).sort( ncol, order )

    def filterAcceptsRow( self, rowNumber, sourceParent ):
        return self.sourceModel( ).filterRow( rowNumber )

class MyMovieTableModel( QAbstractTableModel ):
    emitGenreNumMovies = pyqtSignal( str, int )
    emitFilterChanged = pyqtSignal( )

    def __init__( self, parent = None ):
        super(MyMovieTableModel, self).__init__( parent )
        self.parent = parent
        self.myMovieData = [ ]
        self.filterStatus = 'ALL'
        self.filterRegexp = QRegExp( '.', Qt.CaseInsensitive,
                                     QRegExp.RegExp )

    def filterRow( self, rowNumber ):
        if self.filterRegexp.indexIn( self.myMovieData[ rowNumber ][ 0 ] ) == -1:
            return False
        if self.filterStatus == 'ALL':
            return True
        genre = self.myMovieData[ rowNumber ][ -3 ]
        return genre == self.filterStatus
            
    def setFilterStatus( self, filterStatus ):
        self.filterStatus = str( filterStatus )
        self.sort( -1, Qt.AscendingOrder )
        numRows = len(list( filter(lambda rowNumber: self.filterRow( rowNumber ),
                                   range(len( self.myMovieData ) ) ) ) )
        self.emitGenreNumMovies.emit( self.filterStatus, numRows )
        
    def rowCount( self, parent ):
        return len( self.myMovieData )

    def columnCount( self, parent ):
        return len( _headers )

    def headerData( self, col, orientation, role ):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return  _headers[ col ]
        return None

    def filloutMyMovieData( self, myMovieData ):
        #
        ## first remove all rows that exist
        initRowCount = self.rowCount( None )
        self.beginRemoveRows( QModelIndex( ), 0, initRowCount - 1 )
        self.endRemoveRows( )
        #
        ## now add in the data
        self.beginInsertRows( QModelIndex( ), 0, len( myMovieData ) - 1 )
        self.myMovieData = myMovieData
        self.endInsertRows( )
        self.sort( 1, Qt.AscendingOrder )

    def setFilterString( self, text ):
        mytext = str( text ).strip( )
        if len( mytext ) == 0:
            mytext = '.'
        self.filterRegexp = QRegExp( mytext,
                                     Qt.CaseInsensitive,
                                     QRegExp.RegExp )
        self.emitFilterChanged.emit( )

    def sort( self, ncol, order ):
        self.layoutAboutToBeChanged.emit( )
        if ncol == 1:
            self.myMovieData.sort( key = lambda row: -float( row[ 1 ] ) )
        elif ncol in (0, 3, 4):
            self.myMovieData.sort( key = lambda row: row[ ncol ] )
        self.layoutChanged.emit( )

    def data( self, index, role ):
        if not index.isValid( ):
            return QVariant("")
        row = index.row( )
        col = index.column( )
        #
        ## color background role
        if role == Qt.BackgroundRole:
            popularity = self.myMovieData[ row ][ 1 ]
            h = popularity * 0.095
            s = 0.2
            v = 1.0
            alpha = 1.0
            color = QColor( 'white' )
            color.setHsvF( h, s, v, alpha )
            return QBrush( color )
        elif role == Qt.DisplayRole:
            if col in (0, 1, 2, 5):
                return QVariant( self.myMovieData[ row ][ col ] )
            else:
                dt = self.myMovieData[ row ][ col ]
                return QVariant( dt.strftime('%d %b %Y') )
            
    def infoOnMovieAtRow( self, currentRowIdx ):
        # first determine the actual movie row based on the current row number
        currentRow = self.myMovieData[ currentRowIdx ]
        qdl = QDialog( self.parent )
        qdl.setModal( True )
        full_info = currentRow[ -2 ]
        movie_full_path = currentRow[ -1 ]
        title = currentRow[ 0 ]
        release_date = currentRow[ 3 ]
        popularity = currentRow[ 1 ]
        #
        myLayout = QVBoxLayout( )
        mainColor = qdl.palette().color( QPalette.Background )
        qdl.setLayout( myLayout )
        myLayout.addWidget( QLabel( 'TITLE: %s' % title ) )
        myLayout.addWidget( QLabel( 'RELEASE DATE: %s' %
                                    release_date.strftime( '%d %b %Y' ) ) )
        myLayout.addWidget( QLabel( 'POPULARITY: %0.3f' % popularity ) )
        qte = QTextEdit( full_info )
        qte.setReadOnly( True )
        qte.setStyleSheet("""
        QTextEdit {
        background-color: %s;
        }""" % mainColor.name( ) )
        qte.setFrameStyle( QFrame.NoFrame )
        myLayout.addWidget( qte )
        #
        qpm = QPixmap.fromImage( QImage.fromData(
            plexcore.get_pic_data( movie_full_path, token = self.parent.token ) ) )
        qpm = qpm.scaledToWidth( 450 )
        qlabel = QLabel( )
        qlabel.setPixmap( qpm )
        myLayout.addWidget( qlabel )
        #
        def screenGrab( ):
            fname = str( QFileDialog.getSaveFileName( qdl, 'Save Screenshot',
                                                      os.path.expanduser( '~' ),
                                                      filter = '*.png' ) )
            if len( os.path.basename( fname.strip( ) ) ) == 0:
                return
            if not fname.lower( ).endswith( '.png' ):
                fname = fname + '.png'
            qpm = QPixmap.grabWidget( qdl )
            qpm.save( fname )
        printAction = QAction( qdl )
        printAction.setShortcut( 'Shift+Ctrl+P' )
        printAction.triggered.connect( screenGrab )
        qdl.addAction( printAction )
        #
        qdl.setFixedWidth( 450 )
        qdl.setFixedHeight( qdl.sizeHint( ).height( ) )
        qdl.show( )
        result = qdl.exec_( )
        
class StringEntryDelegate( QStyledItemDelegate ):
    def __init__( self, owner ):
        super( StringEntryDelegate, self ).__init__( owner )

    def createEditor( self, parent, option, index ):
        model = index.model( )
        colNumber = index.column( )
        if colNumber in (0, 2, 3, 4, 5):
            myText = model.data( index, Qt.DisplayRole ).toString( )
        else:
            myText = '%0.1f' % model.data( index, Qt.DisplayRole).toFloat()[0]
        return QLabel( myText )

    def setEditorData( self, editor, index ):
        model = index.model( )
        colNumber = index.column( )
        if colNumber in (0, 2, 3, 4, 5):
            myText = model.data( index, Qt.DisplayRole ).toString( )
        else:
            myText = '%0.1f' % model.data( index, Qt.DisplayRole).toFloat()[0]
        editor.setText( myText )
