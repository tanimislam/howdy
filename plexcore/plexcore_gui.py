import xdg.BaseDirectory, os, requests, logging, sys, webbrowser
try:
    from ConfigParser import RawConfigParser
except:
    from configparser import RawConfigParser
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from . import plexcore

#
## check to see if we have a local plex server
def _checkForLocal( ):
    try:
        response = requests.get( 'http://localhost:32400' )
        if response.status_code == 200:
            return 'http://localhost:32400', None
        else:
            return None
    except requests.exceptions.ConnectionError:
        return None

def returnToken( shouldCheckLocal = True ):
    #
    ## now check local
    if shouldCheckLocal:
        val = _checkForLocal( )
        if val is None:
            pass
        else:
            fullurl, token = val
            return fullurl, token
    #
    ## now check if we have server credentials
    val = plexcore.checkServerCredentials( )
    if val is not None:
        fullurl, token = val
        return fullurl, token
    #
    ## now check if we have client credentials
    val = plexcore.checkClientCredentials( )
    if val is not None:
        fullurl, token = val
        return fullurl, token
    
    dlg = UsernamePasswordDialog( )
    result = dlg.exec_( )
    if result != QDialog.Accepted:
        sys.exit( 0 )
    return dlg.fullurl, dlg.token

def returnServerToken( ):
    val = plexcore.checkServerCredentials( )
    if val is not None:
        fullurl, token = val
        return fullurl, token
    
    dlg = UsernamePasswordServerDialog( )
    result = dlg.exec_( )
    if result != QDialog.Accepted:
        sys.exit( 0 )
    return dlg.fullurl, dlg.token

def returnClientToken( ):
    val = plexcore.checkClientCredentials( )
    if val is not None:
        fullurl, token = val
        return fullurl, token
    
    dlg = UsernamePasswordClientDialog( )
    result = dlg.exec_( )
    if result != QDialog.Accepted:
        sys.exit( 0 )
    return dlg.fullurl, dlg.token

def returnEmailAuthentication( ):
    status, message = plexcore.oauthCheckEmailCredentials( )
    if status:
        return status
    dlg = GMailOauth2Dialog( )
    result = dlg.exec_( )
    if result != QDialog.Accepted:
        sys.exit( 0 )
    return True

def returnContactAuthentication( ):
    status, message = plexcore.oauthCheckContactCredentials( )
    if status:
        return status
    dlg = ContactsOauth2Dialog( )
    result = dlg.exec_( )
    if result != QDialog.Accepted:
        sys.exit( 0 )
    return True

class UsernamePasswordServerDialog( QDialog ):
    def __init__( self ):
        super( UsernamePasswordServerDialog, self ).__init__( )
        self.fullurl = ''
        self.token = None
        self.setModal( True )
        self.setWindowTitle( 'PLEX SERVER USERNAME/PASSWORD' )
        mainLayout = QGridLayout( )
        self.setLayout( mainLayout )
        #
        self.server_usernameBox = QLineEdit( )
        self.server_passwordBox = QLineEdit( )
        self.server_statusLabel = QLabel( "" )
        self.server_passwordBox.setEchoMode( QLineEdit.Password )
        mainLayout.addWidget( QLabel( "USERNAME" ), 0, 0, 1, 1 )
        mainLayout.addWidget( self.server_usernameBox, 0, 1, 1, 2 )
        mainLayout.addWidget( QLabel( "PASSWORD" ), 1, 0, 1, 1 )
        mainLayout.addWidget( self.server_passwordBox, 1, 1, 1, 2 )
        mainLayout.addWidget( self.server_statusLabel, 2, 0, 1, 3 )
        self.server_usernameBox.returnPressed.connect( self.server_checkUsernamePassword )
        self.server_passwordBox.returnPressed.connect( self.server_checkUsernamePassword )
        #
        ##
        self.setFixedWidth( self.sizeHint().width() )
        self.setFixedHeight( self.sizeHint().height() )
    
    #
    ## clear all credential information
    def clearCreds( self ):
        self.server_usernameBox.setText( '' )
        self.server_passwordBox.setText( '' )
    #
    ## do plex server checking
    def server_checkUsernamePassword( self ):        
        self.server_usernameBox.setText( str( self.server_usernameBox.text( ) ).strip( ) )
        self.server_passwordBox.setText( str( self.server_passwordBox.text( ) ).strip( ) )
        #
        ## now check that this is a valid username and password
        username = str( self.server_usernameBox.text( ) ).strip( )
        password = str( self.server_passwordBox.text( ) ).strip( )
        token = plexcore.getTokenForUsernamePassword( username, password )
        if token is None:
            self.server_statusLabel.setText( 'ERROR: wrong credentials.' )
            return
        self.token = token
        _, fullurl = max( plexcore.get_owned_servers( token ).items( ) )
        self.fullurl = 'https://%s' % fullurl
        plexcore.pushCredentials( username, password, name = 'SERVER' )
        self.clearCreds( )
        self.accept( )

class UsernamePasswordClientDialog( QDialog ):
    def __init__( self ):
        super( UsernamePasswordClientDialog, self ).__init__( )
        self.fullurl = ''
        self.token = None
        self.setModal( True )
        self.setWindowTitle( 'PLEX CLIENT USERNAME/PASSWORD' )
        mainLayout = QGridLayout( )
        self.setLayout( mainLayout )
        #
        self.client_usernameBox = QLineEdit( )
        self.client_passwordBox = QLineEdit( )
        self.client_statusLabel = QLabel( "" )
        self.client_passwordBox.setEchoMode( QLineEdit.Password )
        mainLayout.addWidget( QLabel( "USERNAME" ), 0, 0, 1, 1 )
        mainLayout.addWidget( self.client_usernameBox, 0, 1, 1, 2 )
        mainLayout.addWidget( QLabel( "PASSWORD" ), 1, 0, 1, 1 )
        mainLayout.addWidget( self.client_passwordBox, 1, 1, 1, 2 )
        mainLayout.addWidget( self.client_statusLabel, 2, 0, 1, 3 )
        self.client_usernameBox.returnPressed.connect( self.client_checkUsernamePassword )
        self.client_passwordBox.returnPressed.connect( self.client_checkUsernamePassword )
        #
        ##
        self.setFixedWidth( self.sizeHint().width() )
        self.setFixedHeight( self.sizeHint().height() )

    #
    ## clear all credential information
    def clearCreds( self ):
        self.client_usernameBox.setText( '' )
        self.client_passwordBox.setText( '' )
        
    #
    ## do plex client checking
    def client_checkUsernamePassword( self ):
        self.client_usernameBox.setText( str( self.client_usernameBox.text( ) ).strip( ) )
        self.client_passwordBox.setText( str( self.client_passwordBox.text( ) ).strip( ) )
        #
        ## now check that this is a valid username and password
        username = str( self.client_usernameBox.text( ) ).strip( )
        password = str( self.client_passwordBox.text( ) ).strip( )
        response = requests.get( 'https://tanimislam.ddns.net/flask/plex/tokenurl',
                                 auth = ( username, password ) )
        if response.status_code != 200:
            self.client_statusLabel.setText( 'ERROR: wrong credentials.' )
            return
        self.token = response.json( )['token']
        self.fullurl = response.json( )['url']
        plexcore.pushCredentials( username, password, name = 'CLIENT' )
        self.clearCreds( )
        self.accept( )

class UsernamePasswordDialog( QDialog ):
    def __init__( self ):
        super( UsernamePasswordDialog, self ).__init__( )
        self.fullurl = ''
        self.token = None
        self.setModal( True )
        self.setWindowTitle( 'PLEX ACCOUNT USERNAME/PASSWORD' )
        mainWidget = QTabWidget( self )
        mainLayout = QVBoxLayout( )
        self.setLayout( mainLayout )
        mainLayout.addWidget( mainWidget )
        #
        leftWidget = QWidget( self )
        leftLayout = QGridLayout( )
        leftWidget.setLayout( leftLayout )
        self.server_usernameBox = QLineEdit( )
        self.server_passwordBox = QLineEdit( )
        self.server_statusLabel = QLabel( "" )
        self.server_passwordBox.setEchoMode( QLineEdit.Password )
        leftLayout.addWidget( QLabel( "USERNAME" ), 0, 0, 1, 1 )
        leftLayout.addWidget( self.server_usernameBox, 0, 1, 1, 2 )
        leftLayout.addWidget( QLabel( "PASSWORD" ), 1, 0, 1, 1 )
        leftLayout.addWidget( self.server_passwordBox, 1, 1, 1, 2 )
        leftLayout.addWidget( self.server_statusLabel, 2, 0, 1, 3 )
        self.server_usernameBox.returnPressed.connect( self.server_checkUsernamePassword )
        self.server_passwordBox.returnPressed.connect( self.server_checkUsernamePassword )
        mainWidget.addTab( leftWidget, 'PLEX SERVER CREDS' )
        #
        rightWidget = QWidget( self )
        rightLayout = QGridLayout( )
        rightWidget.setLayout( rightLayout )
        self.client_usernameBox = QLineEdit( )
        self.client_passwordBox = QLineEdit( )
        self.client_statusLabel = QLabel( "" )
        self.client_passwordBox.setEchoMode( QLineEdit.Password )
        rightLayout.addWidget( QLabel( "USERNAME" ), 0, 0, 1, 1 )
        rightLayout.addWidget( self.client_usernameBox, 0, 1, 1, 2 )
        rightLayout.addWidget( QLabel( "PASSWORD" ), 1, 0, 1, 1 )
        rightLayout.addWidget( self.client_passwordBox, 1, 1, 1, 2 )
        rightLayout.addWidget( self.client_statusLabel, 2, 0, 1, 3 )
        self.client_usernameBox.returnPressed.connect( self.client_checkUsernamePassword )
        self.client_passwordBox.returnPressed.connect( self.client_checkUsernamePassword )
        mainWidget.addTab( rightWidget, 'PLEX CLIENT CREDS' )
        #
        ##
        self.setFixedWidth( self.sizeHint().width() )
        self.setFixedHeight( self.sizeHint().height() )

    #
    ## clear all credential information
    def clearCreds( self ):
        self.client_usernameBox.setText( '' )
        self.client_passwordBox.setText( '' )
        self.server_usernameBox.setText( '' )
        self.server_passwordBox.setText( '' )

    #
    ## do plex server checking
    def server_checkUsernamePassword( self ):        
        self.server_usernameBox.setText( str( self.server_usernameBox.text( ) ).strip( ) )
        self.server_passwordBox.setText( str( self.server_passwordBox.text( ) ).strip( ) )
        #
        ## now check that this is a valid username and password
        username = str( self.server_usernameBox.text( ) ).strip( )
        password = str( self.server_passwordBox.text( ) ).strip( )
        token = plexcore.getTokenForUsernamePassword( username, password )
        if token is None:
            self.server_statusLabel.setText( 'ERROR: wrong credentials.' )
            return
        self.token = token
        _, fullurl = max( plexcore.get_owned_servers( token ).items( ) )
        self.fullurl = 'https://%s' % fullurl
        plexcore.pushCredentials( username, password, name = 'SERVER' )
        self.clearCreds( )
        self.accept( )
        
    #
    ## do plex client checking
    def client_checkUsernamePassword( self ):
        self.client_usernameBox.setText( str( self.client_usernameBox.text( ) ).strip( ) )
        self.client_passwordBox.setText( str( self.client_passwordBox.text( ) ).strip( ) )
        #
        ## now check that this is a valid username and password
        username = str( self.client_usernameBox.text( ) ).strip( )
        password = str( self.client_passwordBox.text( ) ).strip( )
        response = requests.get( 'https://tanimislam.ddns.net/flask/plex/tokenurl',
                                 auth = ( username, password ) )
        if response.status_code != 200:
            self.client_statusLabel.setText( 'ERROR: wrong credentials.' )
            return
        self.token = response.json( )['token']
        self.fullurl = response.json( )['url']
        plexcore.pushCredentials( username, password, name = 'CLIENT' )
        self.clearCreds( )
        self.accept( )

class GMailOauth2Dialog( QDialog ):
    def __init__( self ):
        super( GMailOauth2Dialog, self ).__init__( )
        self.setModal( True )
        self.setWindowTitle( 'PLEX ACCOUNT GMAIL OAUTH2 CREDENTIALS' )
        mainLayout = QVBoxLayout( )
        self.setLayout( mainLayout )
        #
        mainLayout.addWidget( QLabel( 'TOOL TO STORE GMAIL ACCOUNT SETTINGS AS OAUTH2 TOKENS.' ) )
        #
        authWidget = QWidget( )
        authLayout = QGridLayout( )
        authWidget.setLayout( authLayout )
        self.authCredentials = QLineEdit( )
        self.authCredentials.setEchoMode( QLineEdit.Password )
        authLayout.addWidget( QLabel( 'CREDENTIALS:' ), 0, 0, 1, 1 )
        authLayout.addWidget( self.authCredentials, 0, 1, 1, 4 )
        mainLayout.addWidget( authWidget )
        #
        self.statusLabel = QLabel( )
        mainLayout.addWidget( self.statusLabel )
        #
        self.authCredentials.returnPressed.connect( self.check_authCredentials )
        self.setFixedWidth( 550 )
        self.setFixedHeight( self.sizeHint( ).height( ) )
        webbrowser.open_new_tab( plexcore.oauth_generate_permission_url( ) )
        
    def check_authCredentials( self ):
        self.statusLabel.setText( '' )
        self.authCredentials.setText( str( self.authCredentials.text( ) ).strip( ) )
        authorization_code = str( self.authCredentials.text( ) )
        tokens = plexcore.oauth_authorize_tokens( authorization_code )
        if 'refresh_token' not in tokens:
            self.statusLabel.setText( 'ERROR: INVALID AUTHORIZATION CODE.' )
            self.authCredentials.setText( '' )
            return
        #
        ## otherwise is valid
        plexcore.oauth_push_new_gmailauthentication( tokens[ 'refresh_token' ] )
        self.authCredentials.setText( '' )
        self.accept( )

class ContactsOauth2Dialog( QDialog ):
    def __init__( self ):
        super( ContactsOauth2Dialog, self ).__init__( )
        self.setModal( True )
        self.setWindowTitle( 'PLEX ACCOUNT GMAIL OAUTH2 CREDENTIALS' )
        mainLayout = QVBoxLayout( )
        self.setLayout( mainLayout )
        #
        mainLayout.addWidget( QLabel( 'TOOL TO STORE GOOGLE CONTACT SETTINGS AS OAUTH2 TOKENS.' ) )
        #
        authWidget = QWidget( )
        authLayout = QGridLayout( )
        authWidget.setLayout( authLayout )
        self.authCredentials = QLineEdit( )
        self.authCredentials.setEchoMode( QLineEdit.Password )
        authLayout.addWidget( QLabel( 'CREDENTIALS:' ), 0, 0, 1, 1 )
        authLayout.addWidget( self.authCredentials, 0, 1, 1, 4 )
        mainLayout.addWidget( authWidget )
        #
        self.statusLabel = QLabel( )
        mainLayout.addWidget( self.statusLabel )
        #
        self.authCredentials.returnPressed.connect( self.check_authCredentials )
        self.setFixedWidth( 550 )
        self.setFixedHeight( self.sizeHint( ).height( ) )
        #
        self.flow, url = plexcore.oauth_generate_contacts_permission_url( )
        webbrowser.open_new_tab( url )
        
    def check_authCredentials( self ):
        self.statusLabel.setText( '' )
        self.authCredentials.setText( str( self.authCredentials.text( ) ).strip( ) )
        authorization_code = str( self.authCredentials.text( ) )
        try:
            credentials = self.flow.step2_exchange( authorization_code )
            plexcore.oauth_store_contacts_credentials( credentials )
            self.authCredentials.setText( '' )
            self.accept( )
        except:
            self.statusLabel.setText( 'ERROR: INVALID AUTHORIZATION CODE.' )
            self.authCredentials.setText( '' )
            return
