# resource file
import os, sys, base64
mainDir = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
sys.path.append( mainDir )
from plexcore import plexcore

def send_email_lowlevel( msg ):
    data = { 'raw' : base64.urlsafe_b64encode(
        msg.as_bytes( ) ).decode('utf-8') }
    #
    credentials = plexcore.oauthGetGoogleCredentials( )
    assert( credentials is not None )
    email_service = build('gmail', 'v1', credentials = credentials,
                          cache_discovery = False )
    try: message = email_service.users( ).messages( ).send(
            userId='me', body = data ).execute( )
    except: print('problem with %s' % msg['To'] )

    
def send_email_localsmtp( msg ):
    smtp_conn = smtplib.SMTP('localhost', 25 )
    smtp_conn.ehlo( 'test' )
    smtp_conn.sendmail( msg['From'], [ msg["To"], ], msg.as_string( ) )
    smtp_conn.quit( )
