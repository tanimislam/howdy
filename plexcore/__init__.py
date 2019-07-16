import os, sys, signal
from functools import reduce

# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )

mainDir = reduce(lambda x,y: os.path.dirname( x ), range( 2 ),
                 os.path.abspath( __file__ ) )
sys.path.append( mainDir )

from plexcore import plexinitialization
_ = plexinitialization.PlexInitialization( )

import datetime, glob, logging, time, numpy
import geoip2.database, _geoip_geolite2, multiprocessing, multiprocessing.pool
from bs4 import BeautifulSoup
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, Column, String, JSON, Date, Boolean
from fuzzywuzzy.fuzz import partial_ratio
from PyQt4.QtGui import *
from PyQt4.QtCore import *

# resource file and stuff
baseConfDir = os.path.abspath( os.path.expanduser( '~/.config/plexstuff' ) )

#
## geoip stuff, exposes a single geop_reader from plexcore
_geoip_database = os.path.join(
    os.path.dirname( _geoip_geolite2.__file__ ),
    _geoip_geolite2.database_name )
assert( os.path.isfile( _geoip_database ) )

geoip_reader = geoip2.database.Reader( _geoip_database )
"""
This contains an on-disk MaxMind_ database, of type :py:class:`geoip2.database.Reader`, containing location information for IP addresses.

.. _Maxmind: https://www.maxmind.com/en/geoip2-services-and-databases
"""

def return_error_raw( msg ):
    """Returns a default ``tuple`` of type ``None, msg``, where ``msg`` is a str.

    :param msg: the error message.
    :returns: a ``tuple`` with structure ``( None, msg )``. ``msg`` should NEVER be ``SUCCESS``.
    :rtype: ``tuple``
    """
    return None, msg
    
    
def get_popularity_color( hpop, alpha = 1.0 ):
    """Get a color that represents some darkish cool looking color interpolated between 0 and 1.

    :param float hpop: the value (between 0 and 1) of the color.
    :param alpha: The alpha value of the color
    :returns: a :class:`QColor <PyQt4.QtGui.QColor>` object to put into a :class:`QWidget <PyQt4.QtGui.QWidget>`.
    :rtype: :class:`QColor <PyQt4.QtGui.QColor>`

    .. _QColor: https://www.riverbankcomputing.com/static/Docs/PyQt4/qcolor.html
    .. _QWidget: https://www.riverbankcomputing.com/static/Docs/PyQt4/qwidget.html

    """
    assert( hpop >= 0 )
    h = hpop * ( 0.81 - 0.45 ) + 0.45
    s = 0.85
    v = 0.31
    color = QColor( 'white' )
    color.setHsvF( h, s, v, alpha )
    return color

#
## a QLabel with save option of the pixmap
class QLabelWithSave( QLabel ):
    
    def screenGrab( self ):
        fname = str( QFileDialog.getSaveFileName(
            self, 'Save Pixmap', os.path.expanduser( '~' ),
            filter = '*.png' ) )
        if len( os.path.basename( fname.strip( ) ) ) == 0: return
        if not fname.lower( ).endswith( '.png' ):
            fname = '%s.png' % fname
        qpm = self.pixmap( )
        qpm.save( fname )

    def __init__( self, parent = None ):
        super( QLabel, self ).__init__( parent )

    def contextMenuEvent( self, event ):
        menu = QMenu( self )
        savePixmapAction = QAction( 'Save Pixmap', menu )
        savePixmapAction.triggered.connect( self.screenGrab )
        menu.addAction( savePixmapAction )
        menu.popup( QCursor.pos( ) )

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
    indexScalingSignal = pyqtSignal( int )
    
    def screenGrab( self ):
        fname = str( QFileDialog.getSaveFileName(
            self, 'Save Screenshot', os.path.expanduser( '~' ),
            filter = '*.png' ) )
        if len( os.path.basename( fname.strip( ) ) ) == 0: return
        if not fname.lower( ).endswith( '.png' ):
            fname = '%s.png' % fname
        qpm = QPixmap.grabWidget( self )
        qpm.save( fname )

    def reset_sizes( self ):
        self.initWidth = self.width( )
        self.initHeight = self.height( )
        self.resetSize( )

    def makeBigger( self ):
        newSizeRatio = min( self.currentSizeRatio + 1,
                            len( self.sizeRatios ) - 1 )
        if newSizeRatio != self.currentSizeRatio:
            self.setFixedWidth( self.initWidth * 1.05**( newSizeRatio - 5 ) )
            self.setFixedHeight( self.initHeight * 1.05**( newSizeRatio - 5 ) )
            self.currentSizeRatio = newSizeRatio
            self.indexScalingSignal.emit( self.currentSizeRatio - 5 )
            

    def makeSmaller( self ):
        newSizeRatio = max( self.currentSizeRatio - 1, 0 )
        if newSizeRatio != self.currentSizeRatio:
            self.setFixedWidth( self.initWidth * 1.05**( newSizeRatio - 5 ) )
            self.setFixedHeight( self.initHeight * 1.05**( newSizeRatio - 5 ) )
            self.currentSizeRatio = newSizeRatio
            self.indexScalingSignal.emit( self.currentSizeRatio - 5 )

    def resetSize( self ):
        if self.currentSizeRatio != 5:
            self.setFixedWidth( self.initWidth )
            self.setFixedHeight( self.initHeight )
            self.currentSizeRatio = 5
            self.indexScalingSignal.emit( 0 )
    #
    ## these commands are run after I am in the event loop. Get lists of sizes
    def on_start( self ):
        if not self.isIsolated: return
        self.reset_sizes( )
        #
        ## set up actions
        makeBiggerAction = QAction( self )
        makeBiggerAction.setShortcut( 'Ctrl+|' )
        makeBiggerAction.triggered.connect( self.makeBigger )
        self.addAction( makeBiggerAction )
        #
        
        makeSmallerAction = QAction( self )
        makeSmallerAction.setShortcut( 'Ctrl+_' )
        makeSmallerAction.triggered.connect( self.makeSmaller )
        self.addAction( makeSmallerAction )
        #
        resetSizeAction = QAction( self )
        resetSizeAction.setShortcut( 'Shift+Ctrl+R' )
        resetSizeAction.triggered.connect( self.resetSize )
        self.addAction( resetSizeAction )        

    def __init__( self, parent, isIsolated = True, doQuit = True ):
        """FIXME! briefly describe function

        Here is some math

        .. math::

        54x^2 + 4 = 7

        :param parent: 
        :param isIsolated: 
        :param doQuit: 
        :returns: 
        :rtype: 

        """
        super( QDialogWithPrinting, self ).__init__( parent )
        self.setModal( True )
        self.isIsolated = isIsolated
        self.initWidth = self.width( )
        self.initHeight = self.height( )
        self.sizeRatios = numpy.array(
            [ 1.05**(-idx) for idx in range(1, 6 ) ][::-1] + [ 1.0, ] +
            [ 1.05**idx for idx in range(1, 6 ) ] )
        self.currentSizeRatio = 5
        #
        ## timer to trigger on_start function on start of app
        QTimer.singleShot( 0, self.on_start )
        #
        if isIsolated:
            printAction = QAction( self )
            printAction.setShortcuts( [ 'Shift+Ctrl+P', 'Shift+Command+P' ] )
            printAction.triggered.connect( self.screenGrab )
            self.addAction( printAction )
            #
            quitAction = QAction( self )
            quitAction.setShortcuts( [ 'Ctrl+Q', 'Esc' ] )
            if not doQuit:
                quitAction.triggered.connect( self.hide )
            else:
                quitAction.triggered.connect( sys.exit )
            self.addAction( quitAction )

class ProgressDialog( QDialogWithPrinting ): # replace with QProgressDialog in the future?
    def __init__( self, parent, windowTitle = "", doQuit = True ):
        super( ProgressDialog, self ).__init__(
            parent, doQuit = doQuit )
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
        self.timer.timeout.connect( self.showTime )
        self.t0 = time.time( )
        self.timer.start( 5000 ) # every 5 seconds
        self.show( )

    def showTime( self ):
        dt = time.time( ) - self.t0
        self.elapsedTime.setText(
            '%0.1f seconds passed' % dt )
        if dt >= 50.0:
            logging.basicConfig( level = logging.DEBUG )

    def addText( self, text ):
        body_elem = self.parsedHTML.find_all('body')[0]
        txt_tag = self.parsedHTML.new_tag("p")
        txt_tag.string = text
        body_elem.append( txt_tag )
        self.errorDialog.setHtml( self.parsedHTML.prettify( ) )

    def stopDialog( self ):
        self.timer.stop( )
        self.hide( )

    def startDialog( self, initString = '' ):
        self.t0 = time.time( )
        self.timer.start( )
        #
        ## now reset the text
        self.parsedHTML = BeautifulSoup("""
        <html>
        <body>
        </body>
        </html>""", 'lxml' )
        self.errorDialog.setHtml( self.parsedHTML.prettify( ) )
        if len( initString ) != 0:
            self.addText( initString )
        self.show( )

def splitall( path_init ):
    """
    This routine is used by :func:`get_path_data_on_tvshow <plextvdb.plextvdb.get_path_data_on_tvshow>` to split a TV show file path into separate directory delimited tokens
    
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

def get_formatted_duration( totdur ):
    """
    This routine spits out a nice, formatted string representation of the duration, which is of
    type :py:class:`datetime <datetime.datetime>`.

    Args:
        totdur (datetime): a length of time, reprsented as a :class:`datetime <datetime.datetime>`.
    
    Returns:
        string: Formatted representation of that length of time.
    """
    dt = datetime.datetime.utcfromtimestamp( totdur )
    durstringsplit = []
    month_off = 1
    day_off = 1
    hour_off = 0
    min_off = 0
    if dt.year - 1970 != 0:
        durstringsplit.append('%d years' % ( dt.year - 1970 ) )
        month_off = 0
    if dt.month != month_off:
        durstringsplit.append('%d months' % ( dt.month - month_off ) )
        day_off = 0
    if dt.day != day_off:
        durstringsplit.append('%d days' % ( dt.day - day_off ) )
        hour_off = 0
    if dt.hour != hour_off:
        durstringsplit.append('%d hours' % ( dt.hour - hour_off ) )
        min_off = 0
    if dt.minute != min_off:
        durstringsplit.append('%d minutes' % ( dt.minute - min_off ) )
    if len(durstringsplit) != 0:
        durstringsplit.append('and %0.3f seconds' % ( dt.second + 1e-6 * dt.microsecond ) )
    else:
        durstringsplit.append('%0.3f seconds' % ( dt.second + 1e-6 * dt.microsecond ) )
    return ', '.join( durstringsplit )


def get_formatted_size( totsizebytes ):
    """
    This routine spits out a nice, formatted string representation of a file size,
    which is represented in int.

    Args:
        totsizebytes (int): size of a file in bytes.
    
    Returns:
        string: Formatted representation of that file size.
    """
    
    sizestring = ''
    if totsizebytes >= 1024**3:
        size_in_gb = totsizebytes * 1.0 / 1024**3
        sizestring = '%0.3f GB' % size_in_gb
    elif totsizebytes >= 1024**2:
        size_in_mb = totsizebytes * 1.0 / 1024**2
        sizestring = '%0.3f MB' % size_in_mb
    elif totsizebytes >= 1024:
        size_in_kb = totsizebytes * 1.0 / 1024
        sizestring = '%0.3f kB' % size_in_kb
    return sizestring

def get_formatted_size_MB( totsizeMB ):
    if totsizeMB >= 1024:
        size_in_gb = totsizeMB * 1.0 / 1024
        return '%0.3f GB' % size_in_gb
    elif totsizeMB > 0: return '%0.3f MB' % totsizeMB
    else: return ""

#
## string match with fuzzywuzzy
def get_maximum_matchval( check_string, input_string ):
    cstring = check_string.strip( ).lower( )
    istring = input_string.strip( ).lower( )
    return partial_ratio( check_string.strip( ).lower( ),
                          input_string.strip( ).lower( ) )

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
    Stored into the ``plexconfig`` table in the ``~/.config.plexstuff/app.db`` SQLite3_ database.

    Attributes:
        service: the name of the configuration service we store. Index on this unique key.
        data: JSON formatted information on the data stored here. For instance, username and password can be stored in the following way

        .. code:: json

            { 'username' : <USERNAME>,
              'password' : <PASSWORD> }

    """
    
    #
    ## create the table using Base.metadata.create_all( _engine )
    __tablename__ = 'plexconfig'
    __table_args__ = { 'extend_existing' : True }
    service = Column( String( 65536 ), index = True, unique = True, primary_key = True )
    data = Column( JSON )

class LastNewsletterDate( Base ):
    """
    This SQLAlchemy_ ORM class contains the date at which the last newsletter was sent.
    It is not used much, and now that `Tautulli`_ has newsletter functionality, I
    very likely won't use this at all. Stored into the ``plexconfig`` table in the
    ``~/.config/plexstuff/app.db`` SQLite3_ database.
        
    Attributes:
        date: the name of the configuration service we store.

    .. _Tautulli: https://tautulli.com
    .. _SQLAlchemy: https://www.sqlalchemy.org
    """
    #
    ## create the table using Base.metadata.create_all( _engine )
    __tablename__ = 'lastnewsletterdate'
    __table_args__ = {'extend_existing': True}
    date = Column( Date, onupdate = datetime.datetime.now,
                   index = True, primary_key = True )
    
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
