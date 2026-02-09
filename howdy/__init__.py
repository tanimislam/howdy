__author__ = 'Tanim Islam'
__email__ = 'tanim.islam@gmail.com'

import sys, os, requests, urllib3

# disable insecure request warnings, because do not recall how to get the name of the certificate for a given plex server
requests.packages.urllib3.disable_warnings( )
urllib3.disable_warnings( )

_mainDir = os.path.dirname( os.path.abspath( __file__ ) )
resourceDir = os.path.join( _mainDir, 'resources' )
"""
the directory where Howdy_ stores its resources.

.. _Howdy: https://howdy.readthedocs.io
"""

assert( os.path.isdir( resourceDir ) )
#
# from howdy import plexinitialization
# _ = plexinitialization.PlexInitialization( )
# resource file and stuff
baseConfDir = os.path.abspath( os.path.expanduser( '~/.config/howdy' ) )
"""
the directory where Howdy_ user data is stored -- ``~/.config/howdy``.
"""
#
## don't do anything if in READTHEDOCS
if not os.path.isdir( baseConfDir ) and not os.environ.get('READTHEDOCS'):
    os.mkdir( baseConfDir )

# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    """
    This is a convenience method that ``kills`` a Python execution when ``Ctrl+C`` is pressed. Its usage is fairly straightforward, shown in the code block below.

    .. code-block:: python

       import signal
       signal.signal( signal.SIGINT, howdy.signal_handler )

    This block of code at the top of the executable will capture ``Ctrl+C`` and then hard kill the executable by invoking ``sys.exit( 0 )``.

    :param dict signal: the POSIX_ signal to capture. See `the Python 3 signal high level overview <signal_high_level_overview_>`_ to begin to understand what POSIX_ signals are, and how Python can expose functionality to interact with them.
    :param frame: the stack frame. I don't know what it is, or why it's necessary in this context, when trying to capture a ``Ctrl+C`` and cleanly exit. It is of type :py:class:`frame`.
    
    .. _signal_high_level_overview: https://docs.python.org/3/library/signal.html
    .. _POSIX: https://en.wikipedia.org/wiki/POSIX
    """
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )

class HowdyPostgreSQLConfig( object ):
    """
    This class contains configuration information one needs to access the PostgreSQL_ database that contains all the Howdy_ configuration data. We previously stored this data within a SQLite_ on-disk database.

    If the access credentials to the PostgreSQL_ database do not exist, then Howdy_ will revert to the SQLite_ on-disk database.
    
    .. _PostgreSQL: https://en.wikipedia.org/wiki/PostgreSQL
    .. _SQLite: https://en.wikipedia.org/wiki/SQLite
    .. _Howdy: https://tanimislam.github.io/howdy
    """
    
    @classmethod
    def _checkConnection( cls, data_to_load, timeout = 5 ):
        import logging, pg8000.dbapi
        try:
            conn = pg8000.dbapi.connect(
                data_to_load[ 'howdy pgsql username' ],
                host     = data_to_load[ 'howdy pgsql hostname' ],
                database = data_to_load[ 'howdy pgsql database' ],
                password = data_to_load[ 'howdy pgsql password' ],
                port     = data_to_load[ 'howdy pgsql port'     ],
                timeout = timeout )
            return True
        except Exception as e:
            logging.error("ERROR, COULD NOT CONNECT TO POSTGRESQL DATABASE")
            return False
    
    def __init__( self ):
        import yaml, logging
        
        self.howdy_pgsql_username = ''
        self.howdy_pgsql_password = ''
        self.howdy_pgsql_hostname = ''
        self.howdy_pgsql_port     = 0
        self.howdy_pgsql_database = ''

        pgsqlConfigFile = os.path.realpath(
            os.path.join( baseConfDir, 'pgsql_config.yaml' ) )
        if not os.path.isfile( pgsqlConfigFile ):
            data_to_dump = {
                'howdy pgsql username' : self.howdy_pgsql_username,
                'howdy pgsql password' : self.howdy_pgsql_password,
                'howdy pgsql hostname' : self.howdy_pgsql_hostname,
                'howdy pgsql port'     : self.howdy_pgsql_port,
                'howdy pgsql database' : self.howdy_pgsql_database }
            yaml.safe_dump(
                data_to_dump, open( pgsqlConfigFile, 'w' ) )
            os.chmod( pgsqlConfigFile, 0o600 )
            logging.info( "NO POSTGRESQL CONFIGURATION INFORMATION FOUND IN CONFIG FILE = %s." % os.path.basename( pgsqlConfigFile ) )
            logging.info( "CREATED IT WITH EMPTY INFORMATION AND 600 PERMISSIONS." )
            logging.info( "PLEASE POPULATE THIS INFORMATION OR HOWDY TOOLING WILL USE THE SQLITE ON-DISK DATABASE." )
            return
        #
        ## now read it in, first check that it exists, has permission 600
        if oct( os.stat( pgsqlConfigFile ).st_mode )[-3:] != '600':
            logging.error( "ERROR, PERMISSION ON CONFIG FILE = %s IS %s." % (
                os.path.basename( pgsqlConfigFile ), os.stat( pgsqlConfigFile ).st_mode )[-3:] )
            logging.error( "YOU NEED TO FIX PERMISSION OF CONFIG FILE = %s TO BE 600." % 
                           os.path.basename( pgsqlConfigFile ) )
            logging.error( "EXITING..." )
            sys.exit( 0 )
        #
        ## now get at the data
        data_to_load = yaml.safe_load( open( pgsqlConfigFile, 'rt' ) )
        missing_values = sorted( set( [
            'howdy pgsql username',
            'howdy pgsql password',
            'howdy pgsql hostname',
            'howdy pgsql port',
            'howdy pgsql database' ] ) - set( data_to_load.keys( ) ) )
        if len( missing_values ) != 0:
            logging.error( "ERROR, MISSING %d POSTGRESQL CONFIG SETTINGS: %s." % (
                len( missing_values ), missing_values ) )
            logging.error( "PLEASE FIX BEFORE USING." )
            return
        #
        ## now check if it is a valid connection
        if not HowdyPostgreSQLConfig._checkConnection( data_to_load, timeout = 5 ):
            logging.error("ERROR, POSTGRESQL DATABASE CREDENTIALS DO NOT WORK. PLEASE FIX." )
            return
        #
        ## store into database
        self.howdy_pgsql_username = data_to_load[ 'howdy pgsql username' ]
        self.howdy_pgsql_password = data_to_load[ 'howdy pgsql password' ]
        self.howdy_pgsql_hostname = data_to_load[ 'howdy pgsql hostname' ]
        self.howdy_pgsql_port     = data_to_load[ 'howdy pgsql port'     ]
        self.howdy_pgsql_database = data_to_load[ 'howdy pgsql database' ]

    def getConfig( self ):
        data_to_dump = {
            'howdy pgsql username' : self.howdy_pgsql_username,
            'howdy pgsql password' : self.howdy_pgsql_password,
            'howdy pgsql hostname' : self.howdy_pgsql_hostname,
            'howdy pgsql port'     : self.howdy_pgsql_port,
            'howdy pgsql database' : self.howdy_pgsql_database }
        return data_to_dump

    def setConfig(
        self,
        howdy_pgsql_username = None,
        howdy_pgsql_password = None,
        howdy_pgsql_hostname = None,
        howdy_pgsql_port     = None,
        howdy_pgsql_database = None ):
        import logging, yaml
        #
        data_to_set = {
            'howdy pgsql username' : self.howdy_pgsql_username,
            'howdy pgsql password' : self.howdy_pgsql_password,
            'howdy pgsql hostname' : self.howdy_pgsql_hostname,
            'howdy pgsql port'     : self.howdy_pgsql_port,
            'howdy pgsql database' : self.howdy_pgsql_database }
        if all(map(lambda entry: entry is None, (
                howdy_pgsql_username,
                howdy_pgsql_password,
                howdy_pgsql_hostname,
                howdy_pgsql_port,
                howdy_pgsql_database ) ) ):
            return # do nothing

        if howdy_pgsql_username is not None:
            data_to_set[ 'howdy pgsql username' ] = howdy_pgsql_username
        if howdy_pgsql_password is not None:
            data_to_set[ 'howdy pgsql password' ] = howdy_pgsql_password
        if howdy_pgsql_hostname is not None:
            data_to_set[ 'howdy pgsql hostname' ] = howdy_pgsql_hostname
        if howdy_pgsql_port is not None:
            data_to_set[ 'howdy pgsql port'     ] = howdy_pgsql_port
        if howdy_pgsql_database is not None:
            data_to_set[ 'howdy pgsql database' ] = howdy_pgsql_database
        #
        ## if valid connection, update connection settings, store to config file
        if HowdyPostgreSQLConfig._checkConnection( data_to_set, timeout = 5 ):
            logging.info( "VALID SETTINGS TO CONNECT TO POSTGRESQL DATABASE." )
            #
            self.howdy_pgsql_username = data_to_set[ 'howdy pgsql username' ]
            self.howdy_pgsql_password = data_to_set[ 'howdy pgsql password' ]
            self.howdy_pgsql_hostname = data_to_set[ 'howdy pgsql hostname' ]
            self.howdy_pgsql_port     = data_to_set[ 'howdy pgsql port'     ]
            self.howdy_pgsql_database = data_to_set[ 'howdy pgsql database' ]
            #
            pgsqlConfigFile = os.path.realpath(
                os.path.join( baseConfDir, 'pgsql_config.yaml' ) )
            yaml.safe_dump( data_to_set, open( pgsqlConfigFile, 'w' ) )
            os.chmod( pgsqlConfigFile, 0o600 )

    def getEngineString( self ):
        # follow directions for postgresql from AI on 20260208
        return "postgresql+pg8000://%s:%s@%s:%d/%s" % (
            self.howdy_pgsql_username,
            self.howdy_pgsql_password,
            self.howdy_pgsql_hostname,
            self.howdy_pgsql_port,
            self.howdy_pgsql_database )
            
#
## now the single class
howdy_pgsql_config = HowdyPostgreSQLConfig( )
