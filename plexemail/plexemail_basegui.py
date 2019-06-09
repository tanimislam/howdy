import os, sys, base64, numpy, glob, hashlib, requests
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PIL import Image
from io import StringIO
from plexcore import PlexConfig, session

class PlexIMGClient( object ):    
    def __init__( self, verify = True ):
        #
        ## https://api.imgur.com/oauth2 advice on using refresh tokens
        self.verify = verify
        dat = plexcore.get_imgurl_credentials( )
        clientID, clientSECRET, clientREFRESHTOKEN = dat
        response = requests.post( 'https://api.imgur.com/oauth2/token',
                                  data = {'client_id': clientID,
                                          'client_secret': clientSECRET,
                                          'grant_type': 'refresh_token',
                                          'refresh_token': clientREFRESHTOKEN },
                                  verify = self.verify )
        if response.status_code != 200:
            raise ValueError( "ERROR, COULD NOT GET ACCESS TOKEN." )
        self.access_token = response.json()[ 'access_token' ]
        self.albumID = data_imgurl['mainALBUMID']
        #
        ## now get all the images in that album
        ## remember: Authorization: Bearer YOUR_ACCESS_TOKEN
        response = requests.get( 'https://api.imgur.com/3/album/%s/images' % self.albumID,
                                 headers = { 'Authorization' : 'Bearer %s' % self.access_token },
                                 verify = False )
        if response.status_code != 200:
            raise ValueError("ERROR, COULD NOT ACCESS ALBUM IMAGES." )
        self.imghashes = { }
        all_imgs = response.json( )[ 'data' ]
        for imgurl_img in all_imgs:
            name = imgurl_img[ 'name' ]
            imgName, imgMD5 = map(lambda tok: tok.strip(),
                                  name.split(':')[:2] )
            imgID = imgurl_img[ 'id' ]
            imgLINK = imgurl_img[ 'link' ]
            self.imghashes[ imgMD5 ] = ( imgName, imgID, imgLINK )

    def refreshImages( self ):
        response = requests.get( 'https://api.imgur.com/3/album/%s/images' % self.albumID,
                                 headers = { 'Authorization' : 'Bearer %s' % self.access_token },
                                 verify = self.verify )
        if response.status_code != 200:
            raise ValueError("ERROR, COULD NOT ACCESS ALBUM IMAGES." )
        self.imghashes = { }        
        all_imgs = response.json( )[ 'data' ]
        for imgurl_img in all_imgs:
            name = imgurl_img[ 'name' ]
            imgName, imgMD5 = map(lambda tok: tok.strip(),
                                  name.split(':')[:2] )
            imgID = imgurl_img[ 'id' ]
            imgLINK = imgurl_img[ 'link' ]
            self.imghashes[ imgMD5 ] = ( imgName, imgID, imgLINK )
            
    def upload_image( self, b64img, name, imgMD5 = None ):
        if imgMD5 is None:
            imgMD5 = hashlib.md5( b64img ).hexdigest( )
        if imgMD5 in self.imghashes:
            return self.imghashes[ imgMD5 ]
        #
        ## upload and add to the set of images
        data = { 'image' : b64img,
                 'type' : 'base64',
                 'name' : '%s : %s' % ( name, imgMD5 ),
                 'album' : self.albumID }
        response = requests.post( 'https://api.imgur.com/3/image', data = data,
                                  headers = { 'Authorization' : 'Bearer %s' % self.access_token },
                                  verify = self.verify )
        if response.status_code != 200:
            print('ERROR, COULD NOT UPLOAD IMAGE.')
            return
        responseData = response.json( )[ 'data' ]
        link = responseData[ 'link' ]
        id = responseData[ 'id' ]        
        self.imghashes[ imgMD5 ] = ( name, id, link )
        return ( name, id, link )

    def delete_image( self, b64img, imgMD5 = None ):
        if imgMD5 is None:
            imgMD5 = hashlib.md5( b64img ).hexdigest( )
        if imgMD5 not in self.imghashes:
            return False

        _, imgID, _ = self.imghashes[ imgMD5 ]
        response = requests.delete( 'https://api.imgur.com/3/image/%s' % imgID,
                                    headers = { 'Authorization' : 'Bearer %s' % self.access_token },
                                    verify = self.verify )
        self.imghashes.pop( imgMD5 )
        return True

class PNGPicObject( object ):
    def __init__( self, filename, actName, pImgClient ):
        assert( os.path.isfile( filename ) )
        assert( actName.endswith('.png') )
        self.actName = os.path.basename( actName )
        self.img = QImage( filename )
        self.originalImage = Image.open( filename )
        dpi = 300.0
        self.originalWidth = self.originalImage.size[0] * 2.54 / dpi # current width in cm
        self.currentWidth = self.originalWidth
        #
        ## do this from http://stackoverflow.com/questions/31826335/how-to-convert-pil-image-image-object-to-base64-string
        buffer = StringIO( )
        self.originalImage.save( buffer, format = 'PNG' )
        self.b64string = base64.b64encode( buffer.getvalue( ) )
        self.imgMD5 = hashlib.md5( self.b64string ).hexdigest( )
        _, _, link = pImgClient.upload_image( self.b64string, self.actName, imgMD5 = self.imgMD5 )
        self.imgurlLink = link
        
    def getInfoGUI( self, parent ):
        qdl = QDialog( parent )
        qdl.setModal( True )
        myLayout = QVBoxLayout( )
        mainColor = qdl.palette().color( QPalette.Background )
        qdl.setLayout( myLayout )
        myLayout.addWidget( QLabel( 'ACTNAME: %s' % self.actName ) )
        myLayout.addWidget( QLabel( 'URL: %s' % self.imgurlLink ) )
        qpm = QPixmap.fromImage( self.img ).scaledToWidth( 450 )
        qlabel = QLabel( )
        qlabel.setPixmap( qpm )
        qdl.setFixedWidth( 450 )
        qdl.setFixedHeight( qpm.height( ) )
        result = qdl.exec_( )

    def b64String( self ):
        #assert( self.currentWidth > 0 )
        #buffer = StringIO( )
        #reldif = abs( 2 * ( self.originalWidth - self.currentWidth ) / ( self.originalWidth + self.currentWidth ) )
        #self.originalImage.save( buffer, format = 'PNG' )
        #return base64.b64encode( buffer.getvalue( ) ), self.currentWidth, self.imgurlLink
        return self.b64string, self.currentWidth, self.imgurlLink

"""
Because Pandoc does not recognize image size at all, I will
need a separate column where I can specify the image width in cm.
"""
class PNGWidget( QDialog ):
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
    
    def __init__( self, parent ):
        super( PNGWidget, self ).__init__( parent )
        self.setModal( True )
        self.parent = parent
        self.setWindowTitle( 'PNG IMAGES' )
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        self.pngPicTableModel = PNGPicTableModel( self )
        self.pngTV = PNGPicTableView( self, self.pngPicTableModel )
        myLayout.addWidget( self.pngTV )
        #
        printAction = QAction( self )
        printAction.setShortcut( 'Shift+Ctrl+P' )
        printAction.triggered.connect( self.screenGrab )
        self.addAction( printAction )
        #
        # self.setFixedWidth( self.pngTV.sizeHint( ).width( ) )
        self.setFixedHeight( 450 )
        self.hide( )

    def closeEvent( self, evt ):
        evt.ignore( )
        if self.parent is not None:
            self.hide( )
            # self.parent.pngAddButton.setEnabled( True )
        else:
            sys.exit( 0 )

    def getAllDataAsDict( self ):
        return self.pngPicTableModel.getDataAsDict( )

class PNGPicTableView( QTableView ):
    def __init__( self, parent, pngpictablemodel ):
        super( PNGPicTableView, self ).__init__( parent )
        self.pImgClient = PlexIMGClient( verify = False )
        self.parent = parent
        self.setModel( pngpictablemodel )
        self.setShowGrid( True )
        self.verticalHeader( ).setResizeMode( QHeaderView.Fixed )
        self.horizontalHeader( ).setResizeMode( QHeaderView.Fixed )
        self.setSelectionBehavior( QAbstractItemView.SelectRows )
        self.setSelectionMode( QAbstractItemView.SingleSelection )
        self.setSortingEnabled( True )
        #
        self.setColumnWidth( 0, 220 )
        self.setColumnWidth( 1, 180 )
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
        numNow = len( self.model( ).pngPicObjects ) + 1
        while( True ):
            actName = 'figure_%03d.png' % numNow
            if actName not in set(map(lambda obj: obj.actName, self.model( ).pngPicObjects ) ):
                break
            numNow += 1
        self.model( ).addPicObject( PNGPicObject( pngFileName, actName, self.pImgClient ) )

    def info( self ):
        indices_valid = filter(lambda index: index.column( ) == 0,
                               self.selectionModel().selectedIndexes( ) )
        row = max(map(lambda index: index.row( ), indices_valid ) )
        self.model( ).infoOnPicAtRow( row )

    def remove( self ):
        indices_valid = filter(lambda index: index.column( ) == 0,
                               self.selectionModel().selectedIndexes( ) )
        row = max(map(lambda index: index.row( ), indices_valid ) )
        self.model( ).removePicObject( row )    
        
    def contextMenuEvent( self, event ):
        menu = QMenu( self )
        addAction = QAction( 'Add', menu )
        addAction.triggered.connect( self.add )
        menu.addAction( addAction )
        if len( self.model( ).pngPicObjects ) != 0:
            infoAction = QAction( 'Information', menu )
            infoAction.triggered.connect( self.info )
            menu.addAction( infoAction)
            removeAction = QAction( 'Remove', menu )
            removeAction.triggered.connect( self.remove )
            menu.addAction( removeAction )
        menu.popup( QCursor.pos( ) )        

class PNGPicTableModel( QAbstractTableModel ):
    def __init__( self, parent ):
        super(PNGPicTableModel, self).__init__( parent )
        self.parent = parent
        self.pngPicObjects = [ ]

    def infoOnPicAtRow( self, actualRow ):
        currentRow = self.pngPicObjects[ actualRow ]
        currentRow.getInfoGUI( self.parent )

    def rowCount( self, parent ):
        return len( self.pngPicObjects )

    def columnCount( self, parent ):
        return 2

    def flags( self, index ):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def headerData( self, col, orientation, role ):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if col == 0:
                return 'PNG PICTURE'
            elif col == 1:
                return 'WIDTH IN CM'
        return None

    def setData( self, index, value, role ):
        col = index.column( )
        row = index.row( )
        if col == 0:
            picObjNames = set(map(lambda picObject: picObject.actName, self.pngPicObjects ) )
            candActName = os.path.basename( str( value.toString( ) ).strip( ) )
            if not candActName.endswith('.png'):
                return False
            if candActName in picObjNames:
                return False
            self.pngPicObjects[ row ].actName = candActName
            return True
        elif col == 1:
            try:
                currentWidth = float( str( value.toString( ) ).strip( ) )
                if currentWidth <= 0:
                    return False
                self.pngPicObjects[ row ].currentWidth = currentWidth
                return True
            except:
                return False

    def data( self, index, role ):
        if not index.isValid( ):
            return ""
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

    def removePicObject( self, row ):
        assert( row >= 0 and row < len( self.pngPicObjects ) )
        self.pngPicObjects.pop( row )
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

if __name__=='__main__':
    app = QApplication([])
    qw = PNGWidget( None )
    qw.show( )
    result = app.exec_( )
