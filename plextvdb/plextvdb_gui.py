from PyQt4.QtGui import *
from PyQt4.QtCore import *
import os, sys, numpy, glob, datetime
from . import mainDir, plextvdb
sys.path.append( mainDir )
from plexcore import plexcore

class TVDBGUI( QWidget ):
    mySignal = pyqtSignal( list )

    def __init__( self, token, fullURL ):
        libraries_dict = plexcore.get_libraries( fullURL = fullURL, token = token )
        if not any(map(lambda value: 'TV' in value, libraries_dict.values( ) ) ):
            raise ValueError( 'Error, could not find TV shows.' )
        key = max(map(lambda key: 'TV' in libraries_dict[ key ], libraries_dict ) )        
        tvdata = plexcore._get_library_data_show( key, fullURL = fullURL, token = token )
        if tvdata is None:
            raise ValueError( 'Error, could not find TV shows in the server.' )
        self.dt = datetime.datetime.now( ).date( )
        self.tvdata = tvdata
        self.tm = TVDBShowsTableModel( self )
        self.tv = TVDBShowsTableView( self )
        self.filterOnTVShows = QLineEdit( '' )
        #
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #
        topWidget = QWidget( )
        topLayout = QHBoxLayout( )
        topWidget.setLayout( topLayout )
        topLayout.addWidget( QLabel( 'TV SHOW FILTER' ) )
        topLayout.addWidget( self.filterOnTVShows )
        myLayout.addWidget( topWidget )
        #
        myLayout.addWidget( self.tv )
        #
        self.setSize( 800, 800 )
        self.show( )

class TVDBShowsTableView( QTableView ):
    def __init__( self, parent ):
        super( TVDBShowsTableView, self ).__init__( parent )
        self.parent = parent
        self.proxy = TVDBShowsQSortFilterProxyModel( self, self.parent.tm )
        self.setModel( self.proxy )
        #
        self.setShowGrid( True )
        self.setVerticalHeader( ).setResizeMode( QHeaderView.Fixed )
        self.horizontalHeader( ).setResizeMode( QHeaderView.Fixed )
        
        
