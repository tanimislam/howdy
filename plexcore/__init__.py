import os, sys, signal
from functools import reduce

# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )

mainDir = reduce(lambda x,y: os.path.dirname( x ), range( 2 ),
                 os.path.abspath( __file__ ) )
sys.path.append( mainDir )

#
## not working right now when doing read the docs
from plexcore import plexinitialization
_ = plexinitialization.PlexInitialization( )

import datetime, glob, logging, time, numpy
import geoip2.database, _geoip_geolite2, multiprocessing, multiprocessing.pool
from bs4 import BeautifulSoup
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, Column, String, JSON, Date, Boolean
from fuzzywuzzy.fuzz import partial_ratio
from PyQt4.QtGui import QLabel, QDialog
from PyQt4.QtCore import pyqtSignal

# resource file and stuff
baseConfDir = os.path.abspath( os.path.expanduser( '~/.config/plexstuff' ) )
"""
the directory where Plexstuff configuration data is stored -- ``~/.config/plexstuff``.
"""

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

    :param str msg: the error message.
    :returns: a ``tuple`` with structure ``(None, msg)``. ``msg`` should NEVER be ``SUCCESS``.
    :rtype: tuple
    """
    return None, msg
    
    
def get_popularity_color( hpop, alpha = 1.0 ):
    """Get a color that represents some darkish cool looking color interpolated between 0 and 1.

    :param float hpop: the value (between 0 and 1) of the color.
    :param float alpha: The alpha value of the color (between 0 and 1).
    :returns: a :class:`QColor <PyQt4.QtGui.QColor>` object to put into a :class:`QWidget <PyQt4.QtGui.QWidget>`, or converted into a hex color.
    :rtype: :class:`QColor <PyQt4.QtGui.QColor>`

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
    """
    A convenient PyQt4_ widget that inherits from :py:class:`QLabel <PyQt4.QtGui.QLabel>`, but allows screen shots.
    """
    
    def screenGrab( self ):
        """
        take a screen shot of itself and save to a PNG file through a :py:class:`QFileDialog <PyQt4.QtGui.QFileDialog>`.
        """
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
        """Constructs a `context menu`_ with a single action, *Save Pixmap*, that takes a screen shot of this widget, using :py:meth:`screenGrab <plexcore.QLabelWithSave.screenGrab>`.

        :param event: default :py:class:`QEvent <PyQt4.QtCore.QEvent>` argument needed to create a context menu. Is not used in this method.

        .. _context menu: https://en.wikipedia.org/wiki/Context_menu

        """
        menu = QMenu( self )
        savePixmapAction = QAction( 'Save Pixmap', menu )
        savePixmapAction.triggered.connect( self.screenGrab )
        menu.addAction( savePixmapAction )
        menu.popup( QCursor.pos( ) )

class QDialogWithPrinting( QDialog ):
    """
    A convenient PyQt4_ widget, inheriting from :py:class:`QDialog <PyQt4.QtGui.QDialog>`, that allows for screen grabs and keyboard shortcuts to either hide this dialog window or quit the underlying program. This PyQt4_ widget is also resizable, in relative increments of 5% larger or smaller, to a maximum of :math:`1.05^5` times the initial size, and to a minimum of :math:`1.05^{-5}` times the initial size.
    
    Args:
        parent (:py:class:`QWidget <PyQt4.QtGui.QWidget>`): the parent :py:class:`QWidget <PyQt4.QtGui.QWidget>` to this dialog widget.
        isIsolated (bool): If ``True``, then this widget is detached from its parent. If ``False``, then this widget is embedded into a layout in the parent widget.
        doQuit (bool): if ``True``, then using the quit shortcuts (``Esc`` or ``Ctrl+Shift+Q``) will cause the underlying program to exit. Otherwise, hide the progress dialog.

     Attributes:
        indexScalingSignal: a :py:class:`pyqtSignal <PyQt4.QtCore.pyqtSignal>` that can be connected to other PyQt4_ events or methods, if resize events want to be recorded.
    """
    
    indexScalingSignal = pyqtSignal( int )
    
    def screenGrab( self ):
        """
        take a screen shot of itself and saver to a PNG file through a :py:class:`QFileDialog <PyQt4.QtGui.QFileDialog>`.
        """
        fname = str( QFileDialog.getSaveFileName(
            self, 'Save Screenshot', os.path.expanduser( '~' ),
            filter = '*.png' ) )
        if len( os.path.basename( fname.strip( ) ) ) == 0: return
        if not fname.lower( ).endswith( '.png' ):
            fname = '%s.png' % fname
        qpm = QPixmap.grabWidget( self )
        qpm.save( fname )

    def reset_sizes( self ):
        """
        Sets the default widget size to the current size.
        """
        
        self.initWidth = self.width( )
        self.initHeight = self.height( )
        self.resetSize( )

    def makeBigger( self ):
        """
        makes the widget incrementally 5% larger, for a maximum of :math:`1.05^5`, or approximately 28% larger than, the initial size.
        """
        
        newSizeRatio = min( self.currentSizeRatio + 1,
                            len( self.sizeRatios ) - 1 )
        if newSizeRatio != self.currentSizeRatio:
            self.setFixedWidth( self.initWidth * 1.05**( newSizeRatio - 5 ) )
            self.setFixedHeight( self.initHeight * 1.05**( newSizeRatio - 5 ) )
            self.currentSizeRatio = newSizeRatio
            self.indexScalingSignal.emit( self.currentSizeRatio - 5 )
            
    def makeSmaller( self ):
        """
        makes the widget incrementally 5% smaller, for a minimum of :math:`1.05^{-5}`, or approximately 28% smaller than, the initial size.
        """
        newSizeRatio = max( self.currentSizeRatio - 1, 0 )
        if newSizeRatio != self.currentSizeRatio:
            self.setFixedWidth( self.initWidth * 1.05**( newSizeRatio - 5 ) )
            self.setFixedHeight( self.initHeight * 1.05**( newSizeRatio - 5 ) )
            self.currentSizeRatio = newSizeRatio
            self.indexScalingSignal.emit( self.currentSizeRatio - 5 )

    def resetSize( self ):
        """
        reset the widget size to the initial size.
        """
        
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
            printAction.setShortcuts( [ 'Shift+Ctrl+P' ] )
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

class ProgressDialog( QDialogWithPrinting ):
    """
    A convenient PyQt4_ widget, inheriting from :py:class:`QDialogWithPrinting <plexcore.QDialogWithPrinting>`, that acts as a GUI blocking progress window for longer lasting operations. Like its parent class, this dialog widget is also resizable. This shows the passage of the underlying slow process in 5 second increments.

    This progress dialog exposes three methods -- :py:meth:`addText <plexcore.ProgressDialog.addText>`, :py:meth:`stopDialog <plexcore.ProgressDialog.stopDialog>`, and :py:meth:`startDialog <plexcore.ProgressDialog.startDialog>` -- to which a custom :py:class:`QThread <PyQt4.QtCore.QThread>` object can connect.
    * :py:meth:`startDialog <plexcore.ProgressDialog.startDialog>` is triggered on long operation start, sometimes with an initial message.
    * :py:meth:`addText <plexcore.ProgressDialog.addText>` is triggered when some intermediate progress text must be returned.
    * :py:meth:`stopDialog <plexcore.ProgressDialog.stopDialog>` is triggered on process end.

    Args:
        parent (:py:class:`QWidget <PyQt4.QtGui.QWidget>`): the parent :py:class:`QWidget <PyQt4.QtGui.QWidget>` on which this dialog widget blocks.
        windowTitle (str): the label to put on this progress dialog in an internal :py:class:`QLabel <PyQt4.QtGui.QLabel>`.
        doQuit (bool): if ``True``, then using the quit shortcuts (``Esc`` or ``Ctrl+Shift+Q``) will cause the underlying program to exit. Otherwise, hide the progress dialog.
    """
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
        self.mainDialog = QTextEdit( )
        self.parsedHTML = BeautifulSoup("""
        <html>
        <body>
        </body>
        </html>""", 'lxml' )
        self.mainDialog.setHtml( self.parsedHTML.prettify( ) )
        self.mainDialog.setReadOnly( True )
        self.mainDialog.setStyleSheet("""
        QTextEdit {
        background-color: #373949;
        }""" )
        myLayout.addWidget( self.mainDialog )
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
        """adds some text to this progress dialog window.

        :param str text: the text to add.
        
        """
        body_elem = self.parsedHTML.find_all('body')[0]
        txt_tag = self.parsedHTML.new_tag("p")
        txt_tag.string = text
        body_elem.append( txt_tag )
        self.mainDialog.setHtml( self.parsedHTML.prettify( ) )

    def stopDialog( self ):
        """stops running, and hides, this progress dialog.
        """
        
        self.timer.stop( )
        self.hide( )

    def startDialog( self, initString = '' ):
        """starts running the progress dialog, with an optional labeling string, and starts the timer.

        :param str initString: optional internal labeling string.
        """
        self.t0 = time.time( )
        self.timer.start( )
        #
        ## now reset the text
        self.parsedHTML = BeautifulSoup("""
        <html>
        <body>
        </body>
        </html>""", 'lxml' )
        self.mainDialog.setHtml( self.parsedHTML.prettify( ) )
        if len( initString ) != 0:
            self.addText( initString )
        self.show( )

def splitall( path_init ):
    """
    This routine is used by :func:`get_path_data_on_tvshow <plextvdb.plextvdb.get_path_data_on_tvshow>` to split a TV show file path into separate directory delimited tokens.
    
    Args:
        path_init (str): The absolute path of the file.

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
        totdur (:py:class:`datetime <datetime.datetime>`): a length of time, represented as a :class:`datetime <datetime.datetime>`.
    
    Returns:
        str: Formatted representation of that length of time.
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
    This routine spits out a nice, formatted string representation of a file size, which is represented in int.
    
    This method works like this.

    .. code:: python
       
       get_formatted_size( int(2e3) ) = '1.953 kB' # kilobytes
       get_formatted_size( int(2e6) ) = '1.907 MB' # megabytes
       get_formatted_size( int(2e9) ) = '1.863 GB' # gigabytes

    Args:
        totsizebytes (int): size of a file in bytes.
    
    Returns:
        str: Formatted representation of that file size.

    .. seealso:: :py:meth:`get_formatted_size_MB <plexcore.get_formatted_size_MB>`
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
    """
    Same as :py:meth:`get_formatted_size <plexcore.get_formatted_size>`, except this operates on file sizes in units of megabytes rather than bytes.

    :param int totsizeMB: size of the file in megabytes.
    
    :returns: Formatted representation of that file size.
    
    :rtype: str

    .. seealso:: :py:meth:`get_formatted_size <plexcore.get_formatted_size>`

    """
    if totsizeMB >= 1024:
        size_in_gb = totsizeMB * 1.0 / 1024
        return '%0.3f GB' % size_in_gb
    elif totsizeMB > 0: return '%0.3f MB' % totsizeMB
    else: return ""

#
## string match with fuzzywuzzy
def get_maximum_matchval( check_string, input_string ):
    """
    Returns the `Levenshtein`_ distance of two strings, implemented using  A perfect match is a score of ``100.0``.

    :param str check_string: first string.
    :param str input_string: second string.
    :returns: the `Levenshtein`_ distance between the two strings.
    :rtype: float

    .. _Levenshtein: https://en.wikipedia.org/wiki/Levenshtein_distance
    """
    cstring = check_string.strip( ).lower( )
    istring = input_string.strip( ).lower( )
    return partial_ratio( check_string.strip( ).lower( ),
                          input_string.strip( ).lower( ) )

def returnQAppWithFonts( ):
    """
    returns a customized :py:class:`QApplication <PyQt4.QtGui.QApplication>` with all custom fonts loaded.
    """
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
    This SQLAlchemy_ ORM class contains the configuration data used for running all the plexstuff tools.
    Stored into the ``plexconfig`` table in the SQLite3_ configuration database.

    Attributes:
        service: the name of the configuration service we store. Index on this unique key.
        data: JSON formatted information on the data stored here. For instance, username and password can be stored in the following way

    .. code:: JSON

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
    very likely won't use this at all. Stored into the ``lastnewsletterdate`` table in the
    ``~/.config/plexstuff/app.db`` SQLite3_ configuration database.
        
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
    """
    This SQLAlchemy_ ORM class contains mapping of emails of Plex_ server users, to other email addresses. This is used to determine other email addresses to which Plexstuff one-off or newsletter emails are delivered. Stored in the ``plexguestemailmapping`` table in the SQLite3_ configuration database.

    The structure of each row in this table is straightforward. Each column in the table is a member of the object in this ORM class. 
    
    * the main column is *plexemail*, which must be a Plex_ user who has access to the Plex_ server.
    * the second column is *plexmapping*, which is a collection of **different** email addresses, to which the Plexstuff emails are sent. For example, if a Plex_ user with email address ``A@email.com`` would like to send email to ``B@mail.com`` and ``C@mail.com``, the *plexmapping* column would be ``B@mail.com,C@mail.com``. NONE of the mapped emails will match *plexemail*.
    * the third column  is *plexreplaceexisting*, a boolean that determines whether Plexstuff email also goes to the Plex_ user's email address. From the example above, if ``True`` then a Plex_ user at ``A@mail.com`` will have email delivered ONLY to ``B@mail.com`` and ``C@mail.com``. If ``False``, then that same Plex_ user will have email delivered to all three email addresses (``A@mail.com``, ``B@mail.com``, and ``C@mail.com``).
    
        
    Attributes:
        plexemail: the email address of a Plex_ user who has stream access to the Plex_ server.
        plexmapping: the mapping, as a comma-delimited string, of other email addresses to deliver Plexstuff emails.
        plexreplaceexisting: if ``True``, only send Plexstuff emails of Plex_ user to new email addresses. If ``False``, also send to email address of Plex_ user.

    """
    #
    ## create the table using Base.metadata.create_all( _engine )
    __tablename__ = 'plexguestemailmapping'
    __table_args__ = { 'extend_existing' : True }
    plexemail = Column( String( 256 ), index = True, unique = True, primary_key = True )
    plexmapping = Column( String( 65536 ) )
    plexreplaceexisting = Column( Boolean )
    
def create_all( ):
    """
    creates the necessary SQLite3_ tables into ``~/.config/plexstuff/app.db`` if they don't already exist.

    """
    Base.metadata.create_all( _engine )
    session.commit( )

if not os.environ.get('READTHEDOCS'): create_all( )
