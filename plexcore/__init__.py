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
from PyQt5.QtWidgets import QAction, QApplication, QDialog, QFileDialog, QLabel, QMenu, QTextEdit, QVBoxLayout
from PyQt5.QtGui import QColor, QPixmap, QFontDatabase
from PyQt5.QtCore import pyqtSignal, QTimer, QThread

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

def get_lastupdated_string( dt = datetime.datetime.now( ) ):
    """
    Returns a string representation of a :py:class:`datetime <datetime.datetime>` object.

    :param :py:class:`datetime <datetime.datetime>` dt: the date and time.
    
    :returns: a :py:class:`str` with this format, ``Saturday, 28 September 2019, at 3:41 AM``.
    :rtype: str

    .. seealso:: :py:meth:`get_summary_body <plexemail.plexemail.get_summary_body>`
    """
    return dt.strftime('%A, %d %B %Y, at %-I:%M %p')

def return_error_raw( msg ):
    """Returns a default ``tuple`` of type ``None, msg``, where ``msg`` is a :py:class:`str`.

    :param str msg: the error message.
    
    :returns: a ``tuple`` with structure ``(None, msg)``. ``msg`` should NEVER be ``SUCCESS``.
    :rtype: tuple
    """
    return None, msg
    
    
def get_popularity_color( hpop, alpha = 1.0 ):
    """Get a color that represents some darkish cool looking color interpolated between 0 and 1.

    :param float hpop: the value (between 0 and 1) of the color.
    :param float alpha: The alpha value of the color (between 0 and 1).
    :returns: a :class:`QColor <PyQt5.QtGui.QColor>` object to put into a :class:`QWidget <PyQt5.QtWidgets.QWidget>`.
    :rtype: :class:`QColor <PyQt5.QtGui.QColor>`

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
    A convenient PyQt5_ widget that inherits from :py:class:`QLabel <PyQt5.QtWidgets.QLabel>`, but allows screen shots.

    .. _PyQt5: https://www.riverbankcomputing.com/static/Docs/PyQt5
    """
    
    def screenGrab( self ):
        """
        take a screen shot of itself and save to a PNG file through a :py:class:`QFileDialog <PyQt5.QtWidgets.QFileDialog>` widget.

        .. seealso:: :py:meth:`QDialogWithPrinting.screenGrab <plexcore.QDialogWithPrinting.screenGrab>`
        """
        fname, _ = QFileDialog.getSaveFileName(
            self, 'Save Pixmap', os.path.expanduser( '~' ),
            filter = '*.png' )
        if len( os.path.basename( fname.strip( ) ) ) == 0: return
        if not fname.lower( ).endswith( '.png' ):
            fname = '%s.png' % fname
        qpm = self.grab( )
        qpm.save( fname )

    def __init__( self, parent = None ):
        super( QLabel, self ).__init__( parent )

    def contextMenuEvent( self, event ):
        """Constructs a `context menu`_ with a single action, *Save Pixmap*, that takes a screen shot of this widget, using :py:meth:`screenGrab <plexcore.QLabelWithSave.screenGrab>`.

        :param QEvent event: default :py:class:`QEvent <PyQt5.QtCore.QEvent>` argument needed to create a context menu. Is not used in this reimplementation.

        .. _`context menu`: https://en.wikipedia.org/wiki/Context_menu

        """
        menu = QMenu( self )
        savePixmapAction = QAction( 'Save Pixmap', menu )
        savePixmapAction.triggered.connect( self.screenGrab )
        menu.addAction( savePixmapAction )
        menu.popup( QCursor.pos( ) )

class QDialogWithPrinting( QDialog ):
    """
    A convenient PyQt5_ widget, inheriting from :py:class:`QDialog <PyQt5.QtWidgets.QDialog>`, that allows for screen grabs and keyboard shortcuts to either hide this dialog window or quit the underlying program. This PyQt5_ widget is also resizable, in relative increments of 5% larger or smaller, to a maximum of :math:`1.05^5` times the initial size, and to a minimum of :math:`1.05^{-5}` times the initial size.
    
    Args:
        parent (:py:class:`QWidget <PyQt5.QtWidgets.QWidget>`): the parent :py:class:`QWidget <PyQt5.QtWidgets.QWidget>` to this dialog widget.
        isIsolated (bool): If ``True``, then this widget is detached from its parent. If ``False``, then this widget is embedded into a layout in the parent widget.
        doQuit (bool): if ``True``, then using the quit shortcuts (``Esc`` or ``Ctrl+Shift+Q``) will cause the underlying program to exit. Otherwise, hide the progress dialog.

     
    :var indexScalingSignal: a :py:class:`pyqtSignal <PyQt5.QtCore.pyqtSignal>` that can be connected to other PyQt5_ events or methods, if resize events want to be recorded.
    :type indexScalingSignal: :py:class:`pyqtSignal <PyQt5.QtCore.pyqtSignal>`

    :var int initWidth: the initial width of the GUI in pixels.
    :var int initHeight: the initial heigth of the GUI in pixels.    
    """
    
    indexScalingSignal = pyqtSignal( int )
    
    def screenGrab( self ):
        """
        take a screen shot of itself and saver to a PNG file through a :py:class:`QFileDialog <PyQt5.QtGui.QFileDialog>` widget.
        
        .. seealso:: :py:meth:`QLabelWithSave.screenGrab <plexcore.QLabelWithSave.screenGrab>`
        """
        fname, _ = QFileDialog.getSaveFileName(
            self, 'Save Screenshot', os.path.expanduser( '~' ),
            filter = '*.png' )
        if len( os.path.basename( fname.strip( ) ) ) == 0: return
        if not fname.lower( ).endswith( '.png' ):
            fname = '%s.png' % fname
        qpm = self.grab( )
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

        #
        ## make bigger
        makeBiggerAction = QAction( self )
        makeBiggerAction.setShortcut( 'Ctrl+|' )
        makeBiggerAction.triggered.connect( self.makeBigger )
        self.addAction( makeBiggerAction )
        #
        ## make smaller
        makeSmallerAction = QAction( self )
        makeSmallerAction.setShortcut( 'Ctrl+_' )
        makeSmallerAction.triggered.connect( self.makeSmaller )
        self.addAction( makeSmallerAction )
        #
        ## reset to original size
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

class ProgressDialogThread( QThread ):
    """
    This subclassing of :py:class:`QThread <PyQt5.QtCore.QThread>` provides a convenient scaffolding to run, in a non-blocking fashion, some long-running processes with an asssociated :py:class:`ProgressDialog <plexcore.ProgressDialog>` widget.

    Subclasses of this object need to have a particular structure for their ``__init__`` method. The first three arguments MUST be ``self``, ``parent``, ``self`` is a reference to this object. ``parent`` is the parent :py:class:`QWidget <PyQt5.QtWidgets.QWidget>` to which the :py:class:`ProgressDialog <plexcore.ProgressDialog>` attribute, named ``progress_dialog``, is the child. ``title`` is the title of ``progress_dialog``. Here is an example, where an example class named ``ProgressDialogThreadChildClass`` inherits from  :py:class:`ProgressDialogThread <plexcore.ProgressDialogThread>`.

    .. code-block:: python

       def __init__( self, parent, *args, **kwargs ):
           super( ProgressDialogThreadChildClass, self ).__init__( parent, title )

           # own code to initialize based on *args and **kwargs

    This thing has an associated :py:meth:`run <ProgressDialogThread.run>` method that is expected to be partially implemented in the following manner for subclasses of :py:class:`ProgressDialogThread <plexstuff.ProgressDialogThread>`.

    * It must start with ``self.progress_dialog.show( )`` to show the progress dialog widget.

    * It must end with this command, ``self.stopDialog.emit( )`` to hide the progress dialog widget.

    Here is an example.

    .. code-block:: python

       def run( self ):
           self.progress_dialog.show( )
           # run its own way
           self.stopDialog.emit( )

    In the :py:meth:`run <plexstuff.ProgressDialogThread.run>` method, if one wants to print out something into ``progess_dialog``, then there should be these types of commands in ``run``: ``self.emitString.emit( mystr )``, where ``mystr`` is a :py:class:`str` message to show in ``progress_dialog``, and ``emitString`` is a :py:class:`pyqtsignal <PyQt5.QtCore.pyqtSignal>` connected to the ``progress_dialog`` object's :py:meth:`addText( ) <plexcore.ProgressDialog.addText>`.
    
    :param parent: the parent widget for which this long-lasting process will pop up a progress dialog.
    :param str title: the title for the ``progress_dialog`` widget.
    :type parent: :py:class:`QWidget <PyQt5.QtWidgets.QWidget>`

    :var emitString: the signal, with :py:class:`str` signature, that is triggered to send progress messages into ``progress_dialog``.
    :var stopDialog: the signal that is triggered to stop the ``progress_dialog``, calling :py:meth:`stopDialog <plexcore.ProgressDialog.stopDialog>`.
    :var startDialog: the signal, with :py:class:`str` signature, that is triggered to restart the ``progress_dialog`` widget, calling :py:class:`startDialog <plexcore.ProgressDialog.startDialog>`.
    :var progress_dialog: the GUI that shows, in a non-blocking fashion, the progress on some longer-running method.
    :var int time0: a convenience attribute, the UTC time at which the ``progress_dialog`` object was first instantiated. Can be used to determine the time each submethod takes (for example, ``time.time( ) - self.time0``).
    :type emitString: :py:class:`pyqtSignal <PyQt5.QtCore.pyqtSignal>`
    :type stopDialog: :py:class:`pyqtSignal <PyQt5.QtCore.pyqtSignal>`
    :type startDialog: :py:class:`pyqtSignal <PyQt5.QtCore.pyqtSignal>`
    :type progress_dialog: :py:class:`ProgressDialog <plexcore.ProgressDialog>`
    
    .. seealso:: :py:class:`ProgressDialog <plexcore.ProgressDialog>`
    """
    emitString = pyqtSignal( str )
    stopDialog = pyqtSignal( )
    startDialog= pyqtSignal( str )
    
    def __init__( self, parent, title ):
        super( ProgressDialogThread, self ).__init__( )
        self.progress_dialog = ProgressDialog( parent, title )
        #
        ## must do these things because unsafe to manipulate this thing from separate thread
        self.emitString.connect( self.progress_dialog.addText )
        self.stopDialog.connect( self.progress_dialog.stopDialog )
        self.startDialog.connect( self.progress_dialog.startDialog )
        self.progress_dialog.hide( )
        self.time0 = self.progress_dialog.t0
            
class ProgressDialog( QDialogWithPrinting ):
    """
    A convenient PyQt5_ widget, inheriting from :py:class:`QDialogWithPrinting <plexcore.QDialogWithPrinting>`, that acts as a GUI blocking progress window for longer lasting operations. Like its parent class, this dialog widget is also resizable. This shows the passage of the underlying slow process in 5 second increments.

    This progress dialog exposes three methods -- :py:meth:`addText <plexcore.ProgressDialog.addText>`, :py:meth:`stopDialog <plexcore.ProgressDialog.stopDialog>`, and :py:meth:`startDialog <plexcore.ProgressDialog.startDialog>` -- to which a custom :py:class:`QThread <PyQt5.QtCore.QThread>` object can connect.
    
    * :py:meth:`startDialog <plexcore.ProgressDialog.startDialog>` is triggered on long operation start, sometimes with an initial message.
    
    * :py:meth:`addText <plexcore.ProgressDialog.addText>` is triggered when some intermediate progress text must be returned.
    
    * :py:meth:`stopDialog <plexcore.ProgressDialog.stopDialog>` is triggered on process end.

    :param parent: the parent :py:class:`QWidget <PyQt5.QtWidgets.QWidget>` on which this dialog widget blocks.
    :param str windowTitle: the label to put on this progress dialog in an internal :py:class:`QLabel <PyQt5.QtWidgets.QLabel>`.
    :param bool doQuit: if ``True``, then using the quit shortcuts (``Esc`` or ``Ctrl+Shift+Q``) will cause the underlying program to exit. Otherwise, hide the progress dialog.
    :type parent: :py:class:`QWidget <PyQt5.QtWidgets.QWidget>`

    :var mainDialog: the main dialog widget in this GUI.
    :var parsedHTML: the :py:class:`BeautifulSoup <bs4.BeautifulSoup>` structure that contains the indexable tree of progress dialogs.
    :var elapsedTime: the bottom :py:class:`QLabel <PyQt5.QtWidgets.QLabel>` widget that displays how much time (in seconds) has passed.
    :var timer: the :py:class:`QTimer <PyQt5.QtCore.QTimer>` sub-thread that listens every 5 seconds before emitting a signal.
    :var float t0: the UNIX time, in seconds with resolution of microseconds.
    
    :vartype mainDialog: :py:class:`QTextEdit <PyQt5.QtWidgets.QTextEdit>`
    :vartype parsedHTML: :py:class:`BeautifulSoup <bs4.BeautifulSoup>`
    :vartype elapsedTime: :py:class:`QLabel <PyQt5.QtWidgets.QLabel>`
    :vartype timer: :py:class:`QTimer <PyQt5.QtCore.QTimer>`
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
        """
        method connected to the internal :py:attr:`timer` that prints out how many seconds have passed, on the underlying :py:attr:`elapsedTime` :py:class:`QLabel <PyQt5.QtWidgets.QLabel>`.
        """
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
        """
        stops running, and hides, this progress dialog.
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
        self.timer.stop( ) # if not already stopped
        self.t0 = time.time( )
        self.timer.start( 5000 )
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
        if dt.year - 1970 == 1:
            durstringsplit.append('%d year' % ( dt.year - 1970 ) )
        else:
            durstringsplit.append('%d years' % ( dt.year - 1970 ) )
        month_off = 0
    if dt.month != month_off:
        if dt.month - month_off == 1:
            durstringsplit.append('%d month' % ( dt.month - month_off ) )
        else:
            durstringsplit.append('%d months' % ( dt.month - month_off ) )
        day_off = 0
    if dt.day != day_off:
        if dt.day - day_off == 1:
            durstringsplit.append('%d day' % ( dt.day - day_off ) )
        else:
            durstringsplit.append('%d days' % ( dt.day - day_off ) )
        hour_off = 0
    if dt.hour != hour_off:
        if dt.hour - hour_off == 1:
            durstringsplit.append('%d hour' % ( dt.hour - hour_off ) )
        else:
            durstringsplit.append('%d hours' % ( dt.hour - hour_off ) )
        min_off = 0
    if dt.minute != min_off:
        if dt.minute - min_off == 1:
            durstringsplit.append('%d minute' % ( dt.minute - min_off ) )
        else:
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
    if totsizebytes >= 1024**4:
        size_in_tb = totsizebytes * 1.0 / 1024**4
        sizestring = '%0.3f TB' % size_in_tb
    elif totsizebytes >= 1024**3:
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
    returns a customized :py:class:`QApplication <PyQt5.QtWidgets.QApplication>` with all custom fonts loaded.
    """
    app = QApplication([])
    fontNames = sorted(glob.glob( os.path.join( mainDir, 'resources', '*.tff' ) ) )
    for fontName in fontNames: QFontDatabase.addApplicationFont( fontName )
    return app

# follow directions in http://pythoncentral.io/introductory-tutorial-python-sqlalchemy/
_engine = create_engine( 'sqlite:///%s' % os.path.join( baseConfDir, 'app.db') )
Base = declarative_base( )
if not os.environ.get( 'READTHEDOCS' ):
    Base.metadata.bind = _engine
    session = sessionmaker( bind = _engine )( )
else: session = sessionmaker( )

#
## this will be used to replace all the existing credentials stored in separate tables
class PlexConfig( Base ):
    """
    This SQLAlchemy_ ORM class contains the configuration data used for running all the plexstuff tools. Stored into the ``plexconfig`` table in the SQLite3_ configuration database.

    :var Column service: the name of the configuration service we store. Index on this unique key. This is a :py:class:`Column <sqlalchemy.Column>` containing a :py:class:`String <sqlalchemy.String>` of size 65536.
    :var Column data: the JSON formatted information on the data stored here. For instance, username and password can be stored in the following way

    .. code-block:: python

       { 'username' : USERNAME,
         'password' : PASSWORD }

    This is a :py:class:`Column <sqlalchemy.Column>` containing a :py:class:`JSON <sqlalchemy.JSON>` object.

    .. _SQLAlchemy: https://www.sqlalchemy.org
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
        
    :var Column date: the :py:class:`datetime <datetime.datetime>` when the last newsletter was sent. This is a :py:class:`Column <sqlalchemy.Column>` containing a :py:class:`Date <sqlalchemy.Date>` object.

    .. _Tautulli: https://tautulli.com
    """
    #
    ## create the table using Base.metadata.create_all( _engine )
    __tablename__ = 'lastnewsletterdate'
    __table_args__ = {'extend_existing': True}
    date = Column( Date, onupdate = datetime.datetime.now,
                   index = True, primary_key = True )
    
class PlexGuestEmailMapping( Base ):
    """
    This SQLAlchemy_ ORM class contains mapping of emails of Plex_ server users, to other email addresses. This is used to determine other email addresses to which Plexstuff one-off or newsletter emails are delivered. Stored in the ``plexguestemailmapping`` table in the SQLite3_ configuration database. The structure of each row in this table is straightforward. Each column in the table is a member of the object in this ORM class. 
    
    :var Column plexemail: this is the main column, which must be the email of a Plex_ user who has access to the Plex_ server. This is a :py:class:`Column <sqlalchemy.Column>` containing a :py:class:`String <sqlalchemy.String>`.
    
    :var Column plexmapping: this is a collection of **different** email addresses, to which the Plexstuff emails are sent. For example, if a Plex_ user with email address ``A@email.com`` would like to send email to ``B@mail.com`` and ``C@mail.com``, the *plexmapping* column would be ``B@mail.com,C@mail.com``. NONE of the mapped emails will match *plexemail*. This is a :py:class:`Column <sqlalchemy.Column>` containing a :py:class:`String <sqlalchemy.String>` of size 65536.
    
    :var Column plexreplaceexisting: this is a boolean that determines whether Plexstuff email also goes to the Plex_ user's email address. From the example above, if ``True`` then a Plex_ user at ``A@mail.com`` will have email delivered ONLY to ``B@mail.com`` and ``C@mail.com``. If ``False``, then that same Plex_ user will have email delivered to all three email addresses (``A@mail.com``, ``B@mail.com``, and ``C@mail.com``).  This is a :py:class:`Column <sqlalchemy.Column>` containing a :py:class:`Boolean <sqlalchemy.Boolean>`.
    
    .. _Plex: https://plex.tv
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
    creates the necessary SQLite3_ tables into the database file ``~/.config/plexstuff/app.db`` if they don't already exist, but only if not building documentation in `Read the docs`_.

    .. _`Read the docs`: https://www.readthedocs.io
    """
    if os.environ.get( 'READTHEDOCS' ): return # do nothing if in READTHEDOCS
    Base.metadata.create_all( _engine )
    session.commit( )

create_all( ) # OK, now create the missing tables
