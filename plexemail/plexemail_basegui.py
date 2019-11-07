import os, sys, numpy, glob, datetime
from PIL import Image
from PyQt5.QtWidgets import QAbstractItemView, QAction, QFileDialog, QHeaderView, QMenu, QTableView, QVBoxLayout
from PyQt5.QtGui import QBrush, QColor, QCursor
from PyQt5.QtCore import QAbstractTableModel, Qt

from plexcore import plexcore, QDialogWithPrinting
from plexemail import PlexIMGClient, PNGPicObject

"""
Because Pandoc does not recognize image size at all, I will
need a separate column where I can specify the image width in cm.
"""
class PNGWidget( QDialogWithPrinting ):
    
    def __init__( self, parent ):
        if parent is not None:
            super( PNGWidget, self ).__init__( parent, isIsolated = True, doQuit = False )
        else:
            super( PNGWidget, self ).__init__( parent, isIsolated = True, doQuit = True )
        self.setModal( True )
        self.parent = parent
        self.setWindowTitle( 'PNG IMAGES' )
        self.pIMGClient = PlexIMGClient( verify = False )
        #
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        self.pngPicTableModel = PNGPicTableModel( self )
        self.pngTV = PNGPicTableView( self )
        myLayout.addWidget( self.pngTV )
        #
        # self.setFixedWidth( self.pngTV.sizeHint( ).width( ) )
        self.setFixedHeight( 450 )
        self.hide( )

    def getAllDataAsDict( self ):
        return self.pngPicTableModel.getDataAsDict( )

class PNGPicTableView( QTableView ):
    def __init__( self, parent ):
        super( PNGPicTableView, self ).__init__( parent )
        self.parent = parent
        self.setModel( parent.pngPicTableModel )
        self.setShowGrid( True )
        self.verticalHeader( ).setSectionResizeMode( QHeaderView.Fixed )
        self.horizontalHeader( ).setSectionResizeMode( QHeaderView.Fixed )
        self.setSelectionBehavior( QAbstractItemView.SelectRows )
        self.setSelectionMode( QAbstractItemView.SingleSelection )
        self.setSortingEnabled( True )
        #
        self.setColumnWidth( 0, 200 )
        self.setColumnWidth( 1, 80 )
        self.setColumnWidth( 2, 120 )
        self.setFixedWidth( 410 )
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

    def add( self ):
        pngFileName = str( QFileDialog.getOpenFileName( self, 'Choose PNG file', os.getcwd( ),
                                                        filter = '*.png' ) )
        if len( os.path.basename( pngFileName.strip( ) ) ) == 0:
            return
        if not os.path.isfile( pngFileName ):
            return
        numNow = len( self.parent.pngPicTableModel.pngPicObjects ) + 1
        while( True ):
            actName = 'figure_%03d.png' % numNow
            if actName not in set(map(lambda obj: obj.actName, self.parent.pngPicTableModel.pngPicObjects ) ):
                break
            numNow += 1
        self.parent.pngPicTableModel.addPicObject(
            PNGPicObject( {
                'initialization' : 'FILE',
                'filename' : pngFileName,
                'actName' : actName }, self.parent.pIMGClient ) )

    def info( self ):
        indices_valid = list(
            filter(lambda index: index.column( ) == 0,
                   self.selectionModel().selectedIndexes( ) ) )
        row = max(map(lambda index: index.row( ), indices_valid ) )
        self.parent.pngPicTableModel.infoOnPicAtRow( row )

    def remove( self ):
        indices_valid = filter(lambda index: index.column( ) == 0,
                               self.selectionModel().selectedIndexes( ) )
        row = max(map(lambda index: index.row( ), indices_valid ) )
        self.parent.pngPicTableModel.removePicObject( row )

    def removeAndDelete( self ):
        indices_valid = filter(lambda index: index.column( ) == 0,
                               self.selectionModel().selectedIndexes( ) )
        row = max(map(lambda index: index.row( ), indices_valid ) )
        self.parent.pngPicTableModel.removeAndDeletePicObject( row )
        
    def contextMenuEvent( self, event ):
        menu = QMenu( self )
        addAction = QAction( 'Add', menu )
        addAction.triggered.connect( self.add )
        menu.addAction( addAction )
        if len( self.parent.pngPicTableModel.pngPicObjects ) != 0:
            infoAction = QAction( 'Information', menu )
            infoAction.triggered.connect( self.info )
            menu.addAction( infoAction)
            removeAction = QAction( 'Remove', menu )
            removeAction.triggered.connect( self.remove )
            menu.addAction( removeAction )
            removeAndDeleteAction = QAction( 'Remove and Delete', menu )
            removeAndDeleteAction.triggered.connect( self.removeAndDelete )
            menu.addAction( removeAndDeleteAction )
        menu.popup( QCursor.pos( ) )        

class PNGPicTableModel( QAbstractTableModel ):
    def __init__( self, parent ):
        super(PNGPicTableModel, self).__init__( parent )
        self.parent = parent
        self.layoutAboutToBeChanged.emit( )
        self.pngPicObjects = sorted( PNGPicObject.createPNGPicObjects(
            parent.pIMGClient ), key = lambda pngpo: pngpo.imgDateTime )[::-1]
        self.layoutChanged.emit( )

    def infoOnPicAtRow( self, actualRow ):
        currentRow = self.pngPicObjects[ actualRow ]
        currentRow.getInfoGUI( self.parent )

    def rowCount( self, parent ):
        return len( self.pngPicObjects )

    def columnCount( self, parent ):
        return 3

    def flags( self, index ):
        col = index.column( )
        if col in ( 0, ):
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData( self, col, orientation, role ):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if col == 0: return 'PNG PICTURE'
            elif col == 1: return 'WIDTH IN CM'
            elif col == 2: return 'UPLOADED'
        return None

    def setData( self, index, value, role ):
        col = index.column( )
        row = index.row( )
        if col == 0:
            picObjNames = set(map(lambda picObject: picObject.actName, self.pngPicObjects ) )
            candActName = os.path.basename( value.strip( ) )
            if not candActName.endswith('.png'):
                return False
            if candActName in picObjNames:
                return False
            self.pngPicObjects[ row ].changeName(
                candActName, self.parent.pIMGClient )
            return True
        elif col == 1:
            try:
                currentWidth = float( str( value.toString( ) ).strip( ) )
                if currentWidth <= 0:
                    return False
                self.pngPicObjects[ row ].currentWidth = currentWidth
                return True
            except Exception as e:
                return False

    def data( self, index, role ):
        if not index.isValid( ): return ""
        row = index.row( )
        col = index.column( )
        if role == Qt.BackgroundRole:
            color = QColor( 'yellow' )
            color.setAlphaF( 0.2 )
            return QBrush( color )
        elif role == Qt.DisplayRole:
            if col == 0:
                return self.pngPicObjects[ row ].actName
            elif col == 1:
                return '%0.3f' % self.pngPicObjects[ row ].currentWidth
            elif col == 2:
                return self.pngPicObjects[ row ].imgDateTime.strftime( '%d/%m/%Y' )

    def sort( self, col, order ): # sort on datetime
        self.layoutAboutToBeChanged.emit( )
        print( self.pngPicObjects[0].imgDateTime )
        self.pngPicObjects.sort(
            key = lambda pngpo: -datetime.datetime.timestamp( pngpo.imgDateTime ) )
        self.layoutChanged.emit( )

    def removePicObject( self, row ):
        assert( row >= 0 and row < len( self.pngPicObjects ) )
        pngpo = self.pngPicObjects.pop( row )
        pngpo.delete( parent.plexImgClient )
        self.layoutAboutToBeChanged.emit( )
        self.layoutChanged.emit( )

    def removeAndDeletePicObject( self, row ):
        assert( row >= 0 and row < len( self.pngPicObjects ) )
        pngpo = self.pngPicObjects.pop( row )
        self.parent.pIMGClient.delete_image( pngpo.b64string, pngpo.imgMD5 )
        self.layoutAboutToBeChanged.emit( )
        self.layoutChanged.emit( )

    def addPicObject( self, pngPicObject ):
        picObjNames = set(map(lambda picObject: picObject.actName, self.pngPicObjects ) )
        assert( pngPicObject.actName not in picObjNames )
        self.pngPicObjects.append( pngPicObject )
        self.layoutAboutToBeChanged.emit( )
        self.layoutChanged.emit( )

    def getDataAsDict( self ):
        data = { }
        for pngpo in self.pngPicObjects:
            b64data, widthInCM, link = pngpo.b64String( )
            data[ pngpo.actName ] = ( b64data, widthInCM, link )
        return data
