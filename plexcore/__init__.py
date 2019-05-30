# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )

from . import plexinitialization
_ = plexinitialization.PlexInitialization( )

import os, sys, xdg.BaseDirectory, signal, datetime, glob
import geoip2.database, _geoip_geolite2, time
from bs4 import BeautifulSoup
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, Column, String, JSON, Date, Boolean
from PyQt4.QtGui import *
from PyQt4.QtCore import *

#
## geoip stuff, exposes a single geop_reader from plexcore
_geoip_database = os.path.join(
    os.path.dirname( _geoip_geolite2.__file__ ),
    _geoip_geolite2.database_name )
assert( os.path.isfile( _geoip_database ) )

geoip_reader = geoip2.database.Reader( _geoip_database )
"""This contains an on-disk _`MaxMind` database containing location information for IP addresses.

.. _MaxMind: https://www.maxmind.com/en/geoip2-services-and-databases
"""



#
## now make a QWidget subclass that automatically allows for printing and quitting
class QWidgetWithPrinting( QWidget ):
    def screenGrab( self ):
        fname = str( QFileDialog.getSaveFileName(
            self, 'Save Screenshot', os.path.expanduser( '~' ),
            filter = '*.png' ) )
        if len( os.path.basename( fname.strip( ) ) ) == 0: return
        if not fname.lower( ).endswith( '.png' ):
            fname = '%s.png' % fname
        qpm = QPixmap.grabWidget( self )
        qpm.save( fname )

    def __init__( self, parent, isIsolated = True, doQuit = False ):
        super( QWidgetWithPrinting, self ).__init__( parent )
        if isIsolated:
            printAction = QAction( self )
            printAction.setShortcut( 'Shift+Ctrl+P' )
            printAction.triggered.connect( self.screenGrab )
            self.addAction( printAction )
            #
            quitAction = QAction( self )
            quitAction.setShortcuts( [ 'Ctrl+Q', 'Esc' ] )
            if not doQuit: quitAction.triggered.connect( self.close )
            else: quitAction.triggered.connect( sys.exit )
            self.addAction( quitAction )

class QDialogWithPrinting( QDialog ):
    def screenGrab( self ):
        fname = str( QFileDialog.getSaveFileName(
            self, 'Save Screenshot', os.path.expanduser( '~' ),
            filter = '*.png' ) )
        if len( os.path.basename( fname.strip( ) ) ) == 0: return
        if not fname.lower( ).endswith( '.png' ):
            fname = '%s.png' % fname
        qpm = QPixmap.grabWidget( self )
        qpm.save( fname )

    def __init__( self, parent, isIsolated = True, doQuit = False ):
        super( QDialogWithPrinting, self ).__init__( parent )
        if isIsolated:
            printAction = QAction( self )
            printAction.setShortcut( 'Shift+Ctrl+P' )
            printAction.triggered.connect( self.screenGrab )
            self.addAction( printAction )
            #
            quitAction = QAction( self )
            quitAction.setShortcuts( [ 'Ctrl+Q', 'Esc' ] )
            if not doQuit: quitAction.triggered.connect( self.close )
            else: quitAction.triggered.connect( sys.exit )
            self.addAction( quitAction )

class ProgressDialog( QDialogWithPrinting ): # replace with QProgressDialog in the future?
    def __init__( self, parent, windowTitle = "" ):
        super( ProgressDialog, self ).__init__(
            parent, doQuit = True )
        self.setModal( True )
        self.setWindowTitle( 'PROGRESS' )
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        self.setFixedWidth( 300 )
        self.setFixedHeight( 400 )
        myLayout.addWidget( QLabel( windowTitle ) )
        self.errorDialog = QTextEdit( )
        self.parsedHTML = BeautifulSoup("""
        <html>
        <body>
        </body>
        </html>""", 'lxml' )
        self.errorDialog.setHtml( self.parsedHTML.prettify( ) )
        self.errorDialog.setReadOnly( True )
        self.errorDialog.setStyleSheet("""
        QTextEdit {
        background-color: #373949;
        }""" )
        myLayout.addWidget( self.errorDialog )
        #
        self.elapsedTime = QLabel( )
        self.elapsedTime.setStyleSheet("""
        QLabel {
        background-color: #373949;
        }""" )
        myLayout.addWidget( self.elapsedTime )
        self.timer = QTimer( )
        self.t0 = time.time( )
        self.timer.timeout.connect( self.showTime )
        self.timer.start( 5000 ) # every 5 seconds
        self.show( )

    def showTime( self ):
        self.elapsedTime.setText(
            '%0.1f seconds passed' % ( time.time( ) - self.t0 ) )

    def addText( self, text ):
        body_elem = self.parsedHTML.find_all('body')[0]
        txt_tag = self.parsedHTML.new_tag("p")
        txt_tag.string = text
        body_elem.append( txt_tag )
        self.errorDialog.setHtml( self.parsedHTML.prettify( ) )

    def stopDialog( self ):
        self.timer.stop( )
        self.hide( )

def splitall( path_init ):
    """
    This routine is used by ``plextvdb.plextvdb.get_path_data_on_tvshow`` to split a TV show file path
    into separate directory delimited tokens
    
    Args:
        path_init (string): The absolute path of the file.

    Returns:
        list: each subdirectory, and file basename, in the path
    """
    allparts = [ ]
    path = path_init
    while True:
        parts = os.path.split( path )
        if parts[0] == path:
            allparts.insert( 0, parts[ 0 ] )
            break
        elif parts[1] == path:
            allparts.insert( 0, parts[ 1 ] )
            break
        else:
            path = parts[0]
            allparts.insert( 0, parts[ 1 ] )
    return allparts

# resource file and stuff
mainDir = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
baseConfDir = xdg.BaseDirectory.save_config_path( 'plexstuff' )
sys.path.append( mainDir )


def returnQAppWithFonts( ):
    app = QApplication([])
    fontNames = sorted(glob.glob( os.path.join( mainDir, 'resources', '*.tff' ) ) )
    for fontName in fontNames: QFontDatabase.addApplicationFont( fontName )
    return app


# follow directions in http://pythoncentral.io/introductory-tutorial-python-sqlalchemy/
_engine = create_engine( 'sqlite:///%s' % os.path.join( baseConfDir, 'app.db') )
Base = declarative_base( )
Base.metadata.bind = _engine
session = sessionmaker( bind = _engine )( )

#
## this will be used to replace all the existing credentials stored in separate tables
class PlexConfig( Base ):
    """
    This SQLAlchemy ORM class contains the configuration data used for running all the plexstuff tools.
    Stored into the ``plexconfig`` table in the ``app.db`` SQLITE database.

    Attributes:
        service: the name of the configuration service we store. Index on this unique key.
        data: JSON formatted information on the data stored here. For instance, username and password can be
        stored in the following way::

            { 'username' : ``username``,
              'password' : ``password``
            }

    """
    
    #
    ## create the table using Base.metadata.create_all( _engine )
    __tablename__ = 'plexconfig'
    __table_args__ = { 'extend_existing' : True }
    service = Column( String( 65536 ), index = True, unique = True, primary_key = True )
    data = Column( JSON )

class LastNewsletterDate( Base ):
    """
    This SQLAlchemy ORM class contains the date at which the last newsletter was sent.
    It is not used much, and now that `Tautulli`_ has newsletter functionality, I
    very likely won't use this at all. Stored into the ``plexconfig`` table in the
    ``app.db`` SQLITE database.
        
    Attributes:
        date: the name of the configuration service we store.

    .. _Tautulli: https://tautulli.com/#features
    """
    #
    ## create the table using Base.metadata.create_all( _engine )
    __tablename__ = 'lastnewsletterdate'
    __table_args__ = {'extend_existing': True}
    date = Column( Date, onupdate = datetime.datetime.now, index = True, primary_key = True )
    
class PlexGuestEmailMapping( Base ):
    #
    ## create the table using Base.metadata.create_all( _engine )
    __tablename__ = 'plexguestemailmapping'
    __table_args__ = { 'extend_existing' : True }
    plexemail = Column( String( 256 ), index = True, unique = True, primary_key = True )
    plexmapping = Column( String( 65536 ) )
    plexreplaceexisting = Column( Boolean )

    
def create_all( ):
    Base.metadata.create_all( _engine )
    session.commit( )

create_all( )
