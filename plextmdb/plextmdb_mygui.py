import numpy, os, sys, requests
import logging, glob, datetime, pickle, gzip
from PyQt5.QtWidgets import QAbstractItemView, QAction, QComboBox, QDialog, QFileDialog, QFrame, QGridLayout, QHeaderView, QLabel, QLineEdit, QMenu, QStyledItemDelegate, QTableView, QTextEdit, QVBoxLayout, QHBoxLayout, QWidget
from PyQt5.QtGui import QBrush, QCursor, QImage, QPalette, QPixmap
from PyQt5.QtCore import pyqtSignal, QAbstractTableModel, QModelIndex, QRegExp, QSortFilterProxyModel, Qt

from plextmdb import plextmdb
from plexcore import plexcore, QDialogWithPrinting, get_popularity_color

_headers = [ 'title',  'popularity', 'rating', 'release date', 'added date',
             'genre' ]

_columnMapping = {
    0 : 'title',
    1 : 'rating',
    2 : 'contentrating',
    3 : 'releasedate',
    4 : 'addedat',
    5 : 'genre' }

# data = {
#     'title' : title,
#     'rating' : rating,
#     'contentrating' : contentrating,
#     'picurl' : picurl,
#     'releasedate' : releasedate,
#     'addedat' : addedat,
#     'summary' : summary,
#     'duration' : duration,
#     'totsize' : totsize }


class TMDBMyGUI( QDialogWithPrinting ):
    emitMinPopularity = pyqtSignal( float )

    @classmethod
    def create_decades_in_order( cls,  movie_data_rows ):
        decades_sorted_set = sorted(
            set( map(lambda entry: 10 * int( entry['releasedate' ].year * 0.1 ),
                     movie_data_rows ) ) )
        max_decade = max( decades_sorted_set )
        decades_in_order_dict = { -1 : 'BEFORE 1900' }
        for decade in range( 1900, max_decade + 10, 10 ):
            decades_in_order_dict[ decade ] = '%04ds' % decade
        return decades_in_order_dict
    
    def __init__( self, token, movie_data_rows, isIsolated = True, verify = True ):
        super( TMDBMyGUI, self ).__init__( None, isIsolated = isIsolated )
        tmdbEngine = plextmdb.TMDBEngine( verify = verify )
        if isIsolated:
            self.setWindowTitle( 'My Own Movies' )
            self.setStyleSheet("""
            QWidget {
            font-family: Consolas;
            font-size: 11px;
            }""" )
        #
        self.token = token
        self.verify = verify
        self.myTableView = MyMovieTableView( self )
        self.genreComboBox = QComboBox( self )
        self.genreComboBox.setEditable( False )
        self.decadesComboBox = QComboBox( self )
        self.decadesComboBox.setEditable( False )
        self.movieLineEdit = QLineEdit( self )
        self.minPopuLineEdit = QLineEdit( self )
        self.numMoviesLabel = QLabel( self )
        self.minPopularity = 0.0
        self.minPopuLineEdit.setText( '%0.1f' % self.minPopularity )
        #
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #print 
        topWidget = QWidget( self )
        topLayout = QGridLayout( )
        topWidget.setLayout( topLayout )
        colnums = [
            [ 2, 1, 1, 1, 1 ],
            [ 1, 1, 1, 3 ] ]
        #
        ## top row
        arr = numpy.array( colnums[ 0 ], dtype=int )
        cumarray =  numpy.cumsum(numpy.concatenate([
            [ 0 ], arr[:-1] ]))
        topLayout.addWidget( self.numMoviesLabel, 0, cumarray[ 0 ], 1, arr[ 0 ] )
        topLayout.addWidget( QLabel( 'GENRE:' ), 0, cumarray[ 1 ], 1, arr[ 1 ] )
        topLayout.addWidget( self.genreComboBox, 0, cumarray[ 2 ], 1, arr[ 2 ] )
        topLayout.addWidget( QLabel( 'DECADE:' ), 0, cumarray[ 3 ], 1, arr[ 3 ] )
        topLayout.addWidget( self.decadesComboBox, 0, cumarray[ 4 ], 1, arr[ 4 ] )
        #
        ## bottom row
        arr = numpy.array( colnums[ 1 ], dtype=int )
        cumarray =  numpy.cumsum(numpy.concatenate([
            [ 0 ], arr[:-1] ]))
        topLayout.addWidget( QLabel( 'MIN POPU.:' ), 1, cumarray[ 0 ], 1, arr[ 0 ] )
        topLayout.addWidget( self.minPopuLineEdit, 1, cumarray[ 1 ], 1, arr[ 1 ] )
        topLayout.addWidget( QLabel( 'MOVIE NAME' ), 1, cumarray[ 2 ], 1, arr[ 2 ] )
        topLayout.addWidget( self.movieLineEdit, 1, cumarray[ 3 ], 1, arr[ 3 ] )
        #
        myLayout.addWidget( topWidget )
        #
        myLayout.addWidget( self.myTableView )
        #
        ## set size, make sure not resizable
        #self.setFixedWidth( self.myTableView.sizeHint( ).width( ) )
        self.setFixedWidth( 780 )
        #self.setFixedWidth( 1.4 * self.myTableView.candidateWidth )
        #
        ## do this part first
        self.fill_out_movies( movie_data_rows )
        #
        self.genreComboBox.installEventFilter( self )
        self.genreComboBox.currentIndexChanged.connect( self.changeGenre )
        self.myTableView.tm.emitNumMovies.connect( self.setStatus )
        self.movieLineEdit.textChanged.connect( self.myTableView.tm.setFilterString )
        #
        ## change the decade for the movie to look at
        self.decadesComboBox.installEventFilter( self )
        self.decadesComboBox.currentIndexChanged.connect( self.changeDecade )
        #
        ## change the minimum popularity with editing
        self.minPopuLineEdit.returnPressed.connect( self.checkMinPopularity )
        self.emitMinPopularity.connect( self.myTableView.tm.setFilterMinPopularity )
        #
        ##
        self.show( )
        
    def fill_out_movies( self, movie_data_rows ):
        genres = sorted( set(
            map(lambda row: row[ 'genre' ], movie_data_rows ) ) )
        self.genreComboBox.addItems( genres )
        self.genreComboBox.addItem( 'ALL' )
        self.genreComboBox.setCurrentIndex( len( genres ) )
        #
        decades_in_order_dict = TMDBMyGUI.create_decades_in_order( movie_data_rows )
        self.decadesComboBox.addItems(
            list(map(lambda decade: decades_in_order_dict[ decade ],
                     sorted( decades_in_order_dict ) ) ) )
        self.decadesComboBox.addItem( 'ALL' )
        self.decadesComboBox.setCurrentIndex( 1 + len( decades_in_order_dict ) ) # last one
        #
        self.myTableView.tm.filloutMyMovieData( movie_data_rows )
        self.myTableView.tm.setFilterGenre( 'ALL' )
        self.myTableView.tm.setFilterDecade( 'ALL' )

    def checkMinPopularity( self ):
        try:
            popu = float( self.minPopuLineEdit.text( ) )
            assert( popu >= 0.0 )
            assert( popu <= 10.0 )
            self.minPopularity = popu # everything works out            
        except: pass
        #
        self.minPopuLineEdit.setText( '%0.1f' % self.minPopularity )
        self.emitMinPopularity.emit( self.minPopularity )
        
    def setStatus( self, num ):
        self.numMoviesLabel.setText('%d MOVIES HERE' % num )

    def changeGenre( self ):
        genre = str( self.genreComboBox.currentText( ) )
        self.myTableView.tm.setFilterGenre( genre )

    def changeDecade( self ):
        decade_string = str( self.decadesComboBox.currentText( ) )
        self.myTableView.tm.setFilterDecade( decade_string )

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
            self.setItemDelegateForColumn(
                idx, StringEntryDelegate( self ) )
        self.setShowGrid( True )
        self.verticalHeader( ).setSectionResizeMode( QHeaderView.Fixed )
        self.horizontalHeader( ).setSectionResizeMode( QHeaderView.Fixed )
        self.setSelectionBehavior( QAbstractItemView.SelectRows )
        self.setSelectionMode( QAbstractItemView.SingleSelection ) # single row        
        self.setSortingEnabled( True )
        #
        self.setColumnWidth(0, 210 )
        self.setColumnWidth(1, 100 )
        self.setColumnWidth(2, 100 )
        self.setColumnWidth(3, 100 )
        self.setColumnWidth(4, 100 )
        self.setColumnWidth(5, 100 )
        self.setFixedWidth( 210 + 5 * 100 )
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
        tm.emitFilterChanged.connect( self.invalidateFilter )
        
    def sort( self, ncol, order ):
        self.sourceModel( ).sort( ncol, order )

    def filterAcceptsRow( self, rowNumber, sourceParent ):
        return self.sourceModel( ).filterRow( rowNumber )

class MyMovieTableModel( QAbstractTableModel ):
    emitNumMovies = pyqtSignal( int )
    emitFilterChanged = pyqtSignal( )
    
    def __init__( self, parent = None ):
        super(MyMovieTableModel, self).__init__( parent )
        self.parent = parent
        self.myMovieData = [ ]
        self.rev_order_dict = { }
        self.filterGenre = 'ALL'
        self.filterDecade = -2
        self.filterRegexp = QRegExp( '.', Qt.CaseInsensitive,
                                     QRegExp.RegExp )
        self.filterMinPopu = 0.0
        self.emitFilterChanged.connect( self.returnNumMovies )

    def returnNumMovies( self ):
        numRows = len(list( filter(lambda rowNumber: self.filterRow( rowNumber ),
                                   range(len( self.myMovieData ) ) ) ) )
        self.emitNumMovies.emit( numRows )

    def filterRow( self, rowNumber ):
        data = self.myMovieData[ rowNumber ]
        #
        ## now check for decade
        if self.filterDecade != -2: # not ALL
            if self.filterDecade == -1: # before 1900
                if data[ 'releasedate' ].year >= 1900: return False
            else:
                if 10 * int( 0.1 * data[ 'releasedate' ].year ) != self.filterDecade:
                    return False
        #
        ## now check for popularity
        if data[ 'rating' ] < self.filterMinPopu: return False
        #
        ## now do the rest
        if self.filterRegexp.indexIn( data[ 'title' ] ) == -1:
            return False
        elif self.filterGenre == 'ALL':
            return True
        else:
            return data['genre'] == self.filterGenre
        
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
        #
        ## now create the set of movie data by decade fount here
        decades_in_order_dict = TMDBMyGUI.create_decades_in_order( myMovieData )
        self.rev_order_dict = dict(map(lambda decade: ( decades_in_order_dict[ decade ], decade ),
                                       decades_in_order_dict ) )
        self.rev_order_dict[ 'ALL' ] = -2
        
    def setFilterGenre( self, genre ):
        self.filterGenre = genre
        self.sort( -1, Qt.AscendingOrder )
        self.emitFilterChanged.emit( )

    def setFilterDecade( self, decade_string ):
        assert( decade_string in self.rev_order_dict )
        self.filterDecade = self.rev_order_dict[ decade_string ]
        self.emitFilterChanged.emit( )

    def setFilterString( self, text ):
        mytext = str( text ).strip( )
        if len( mytext ) == 0: mytext = '.'
        self.filterRegexp = QRegExp(
            mytext, Qt.CaseInsensitive,
            QRegExp.RegExp )
        self.emitFilterChanged.emit( )

    def setFilterMinPopularity( self, minPopularity ):
        self.filterMinPopu = minPopularity
        self.emitFilterChanged.emit( )

    def sort( self, ncol, order ):
        self.layoutAboutToBeChanged.emit( )
        if ncol == 1:
            self.myMovieData.sort(
                key = lambda row: -float( row[ 'rating' ] ) )
        elif ncol in (0, 3, 4):
            self.myMovieData.sort(
                key = lambda row: row[ _columnMapping[ ncol ] ] )
        self.layoutChanged.emit( )

    def data( self, index, role ):
        if not index.isValid( ): return None
        row = index.row( )
        col = index.column( )
        #
        ## color background role
        data = self.myMovieData[ row ]
        if role == Qt.BackgroundRole:
            popularity = data[ 'rating' ]
            hpop = min( 1.0, popularity * 0.1 )
            color = get_popularity_color( hpop )
            return QBrush( color )
        elif role == Qt.DisplayRole:
            if col in (0, 1, 2, 5):
                return data[
                    _columnMapping[ col ] ]
            else:
                return data[
                    _columnMapping[ col ] ].strftime( '%d %b %Y' )
            
    def infoOnMovieAtRow( self, currentRowIdx ):
        # first determine the actual movie row based on the current row number
        data = self.myMovieData[ currentRowIdx ]
        qdl = QDialog( self.parent )
        qdl.setModal( True )
        full_info = data[ 'summary' ]
        movie_full_path = data[ 'picurl' ]
        is_local_pic = data[ 'localpic' ]
        title = data[ 'title' ]
        release_date = data[ 'releasedate' ]
        popularity = data[ 'rating' ]
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
        background-color: #373949;
        }""" )
        qte.setFrameStyle( QFrame.NoFrame )
        myLayout.addWidget( qte )
        #
        qlabel = QLabel( )
        if is_local_pic:
            cont = plexcore.get_pic_data(
                movie_full_path, token = self.parent.token )
        else:
            cont = requests.get(
                movie_full_path, verify = self.parent.verify ).content
        qpm = QPixmap.fromImage( QImage.fromData( cont ) )
        qpm = qpm.scaledToWidth( 450 )
        qlabel.setPixmap( qpm )
        myLayout.addWidget( qlabel )
        #
        def screenGrab( ):
            fname = str( QFileDialog.getSaveFileName(
                qdl, 'Save Screenshot',
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
