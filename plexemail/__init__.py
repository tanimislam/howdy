import os, sys, base64, httplib2
from functools import reduce
_mainDir = reduce(lambda x,y: os.path.dirname( x ), range( 2 ),
                  os.path.abspath(__file__) )
sys.path.append( _mainDir )
from apiclient.discovery import build

from plexcore import plexcore

def send_email_lowlevel( msg, verify = True ):
    data = { 'raw' : base64.urlsafe_b64encode(
        msg.as_bytes( ) ).decode('utf-8') }
    #
    #credentials = plexcore.oauthGetGoogleCredentials(
    #    verify = verify )
    #email_service = build('gmail', 'v1', credentials = credentials,
    #                      cache_discovery = False )
    credentials = plexcore.oauthGetOauth2ClientGoogleCredentials( )
    assert( credentials is not None )
    http_auth = credentials.authorize( httplib2.Http(
        disable_ssl_certificate_validation = not verify ) )
    email_service = build('gmail', 'v1', http = http_auth,
                          cache_discovery = False )
    try: message = email_service.users( ).messages( ).send(
            userId='me', body = data ).execute( )
    except: print('problem with %s' % msg['To'] )
    
def send_email_localsmtp( msg ):
    smtp_conn = smtplib.SMTP('localhost', 25 )
    smtp_conn.ehlo( 'test' )
    smtp_conn.sendmail( msg['From'], [ msg["To"], ], msg.as_string( ) )
    smtp_conn.quit( )


def get_email_contacts_dict( emailList, verify = True ):
    if len( emailList ) == 0: return [ ]
    #credentials = plexcore.oauthGetGoogleCredentials( verify = verify )
    credentials = plexcore.oauthGetOauth2ClientGoogleCredentials( )
    http_auth = credentials.authorize( httplib2.Http(
        disable_ssl_certificate_validation = not verify ) )
    # credentials = plexcore.oauthGetGoogleCredentials( verify = verify )
    # people_service = build( 'people', 'v1', credentials = credentials,
    #                        cache_discovery = False )
    people_service = build( 'people', 'v1', http = http_auth,
                            cache_discovery = False )
    connections = people_service.people( ).connections( ).list(
        resourceName='people/me', personFields='names,emailAddresses',
        pageSize = 2000 ).execute( )
    emails_dict = { }
    for conn in filter(lambda conn: 'names' in conn and 'emailAddresses' in conn,
                       connections['connections']):
        name = conn['names'][0]['displayName']
        emails = set(map(lambda eml: eml['value'], conn['emailAddresses'] ) )
        if name not in emails_dict:
            emails_dict[ name ] = emails
        else:
            new_emails = emails | emails_dict[ name ]
            emails_dict[ name ] = new_emails
    while 'nextPageToken' in connections: 
        connections = people_service.people( ).connections( ).list(
            resourceName='people/me', personFields='names,emailAddresses',
            pageToken = connections['nextPageToken'], pageSize = 2000 ).execute( )
        for conn in filter(lambda conn: 'names' in conn and 'emailAddresses' in conn,
                           connections['connections']):
            name = conn['names'][0]['displayName']
            emails = set(map(lambda eml: eml['value'], conn['emailAddresses'] ) )
            if name not in emails_dict:
                emails_dict[ name ] = emails
            else:
                new_emails = emails | emails_dict[ name ]
                emails_dict[ name ] = new_emails
    #
    emails_dict_rev = {}
    for contact in emails_dict:
        for email in emails_dict[contact]:
            emails_dict_rev[ email ] = contact
    emails_array = []
    for email in emailList:
        if email in emails_dict_rev:
            emails_array.append((emails_dict_rev[ email ], email) )
        else:
            emails_array.append( (None, email) )
    return emails_array


dat = plexcore.getCredentials( verify = False )
if dat is not None:
    emailAddress = dat[0]
    try:
        emailName = get_email_contacts_dict( [ emailAddress ], verify = False )[0][0]
    except: emailName = None
else:
    emailAddress = None
    emailName = None
