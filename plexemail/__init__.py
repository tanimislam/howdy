import os, sys
from functools import reduce
_mainDir = reduce(lambda x,y: os.path.dirname( x ), range( 2 ),
                  os.path.abspath(__file__) )
sys.path.append( _mainDir )
import base64, httplib2, numpy, glob
import hashlib, requests, io, datetime
import pathos.multiprocessing as multiprocessing
from apiclient.discovery import build
from PyQt4.QtGui import *
from PIL import Image

from plexcore import plexcore

def send_email_lowlevel( msg, verify = True ):
    """
    Sends out an email using the _`Google Contacts API`. If process is unsuccessfull, prints out an error message, ``"problem with <TO-EMAIL>"``, where ``<TO-EMAIL>`` is the recipient's email address.

    :param MIMEMultiPart msg: the :py:class:`MIMEMultiPart <email.mime.multipart.MIMEMultiPart>` email message to send. At a high level, this is an email with body, sender, recipients, and optional attachments.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.

    .. _`Google Contacts API` https://developers.google.com/contacts/v3
    """
    
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
    """
    Sends the email using the :py:class:`SMTP <smtplib.SMTP>` Python functionality to send through a local SMTP_ server. `This blog post`_ describes how I set up a GMail relay using my local SMTP_ server on my Ubuntu_ machine.

    :param MIMEMultiPart msg: the :py:class:`MIMEMultiPart <email.mime.multipart.MIMEMultiPart>` email message to send. At a high level, this is an email with body, sender, recipients, and optional attachments.
    
    .. _SMTP: https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol
    .. _`This blog post`: https://tanimislamblog.wordpress.com/2018/11/19/sendmail-relay-setup-and-implementation
    """
    smtp_conn = smtplib.SMTP('localhost', 25 )
    smtp_conn.ehlo( 'test' )
    smtp_conn.sendmail( msg['From'], [ msg["To"], ], msg.as_string( ) )
    smtp_conn.quit( )


def get_email_contacts_dict( emailList, verify = True ):
    if len( emailList ) == 0: return [ ]
    credentials = plexcore.oauthGetOauth2ClientGoogleCredentials( )
    http_auth = credentials.authorize( httplib2.Http(
        disable_ssl_certificate_validation = not verify ) )
    people_service = build( 'people', 'v1', http = http_auth,
                            cache_discovery = False )
    # credentials = plexcore.oauthGetGoogleCredentials( verify = verify )
    # people_service = build( 'people', 'v1', credentials = credentials,
    #                        cache_discovery = False )
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

class PlexIMGClient( object ):
    def __init__( self, verify = True ):
        #
        ## https://api.imgur.com/oauth2 advice on using refresh tokens
        self.verify = verify
        data_imgurl = plexcore.get_imgurl_credentials( )
        clientID = data_imgurl[ 'clientID' ]
        clientSECRET = data_imgurl[ 'clientSECRET' ]
        clientREFRESHTOKEN = data_imgurl[ 'clientREFRESHTOKEN' ]
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
            imgMD5 = imgurl_img[ 'name' ]
            imgID = imgurl_img[ 'id' ]
            imgLINK = imgurl_img[ 'link' ]
            imgName = imgurl_img[ 'title' ]
            imgDateTime = datetime.datetime.fromtimestamp(
                imgurl_img[ 'datetime' ] )
            self.imghashes[ imgMD5 ] = [ imgName, imgID, imgLINK, imgDateTime ]

    def refreshImages( self ):
        response = requests.get( 'https://api.imgur.com/3/album/%s/images' % self.albumID,
                                 headers = { 'Authorization' : 'Bearer %s' % self.access_token },
                                 verify = self.verify )
        if response.status_code != 200:
            raise ValueError("ERROR, COULD NOT ACCESS ALBUM IMAGES." )
        self.imghashes = { }        
        all_imgs = response.json( )[ 'data' ]
        for imgurl_img in all_imgs:
            imgMD5 = imgurl_img[ 'name' ]
            imgID = imgurl_img[ 'id' ]
            imgLINK = imgurl_img[ 'link' ]
            imgName = imgurl_img[ 'title' ]
            imgDateTime = datetime.datetime.fromtimestamp(
                imgurl_img[ 'datetime' ] )
            self.imghashes[ imgMD5 ] = [ imgName, imgID, imgLINK, imgDatetime ]
            
    def upload_image( self, b64img, name, imgMD5 = None ):
        if imgMD5 is None:
            imgMD5 = hashlib.md5( b64img ).hexdigest( )
        if imgMD5 in self.imghashes:
            return self.imghashes[ imgMD5 ]
        #
        ## upload and add to the set of images
        data = {
            'image' : b64img,
            'type' : 'base64',
            'name' : imgMD5,
            'album' : self.albumID,
            'title' : name }
        response = requests.post( 'https://api.imgur.com/3/image', data = data,
                                  headers = { 'Authorization' : 'Bearer %s' % self.access_token },
                                  verify = self.verify )
        if response.status_code != 200:
            print('ERROR, COULD NOT UPLOAD IMAGE.')
            return False
        responseData = response.json( )[ 'data' ]
        link = responseData[ 'link' ]
        imgID = responseData[ 'id' ]
        imgDateTime = datetime.datetime.fromtimestamp( responseData[ 'datetime' ] )
        self.imghashes[ imgMD5 ] = [ name, imgID, link, imgDateTime ]
        return ( name, imgID, link, imgDateTime )

    def delete_image( self, b64img, imgMD5 = None ):
        if imgMD5 is None:
            imgMD5 = hashlib.md5( b64img ).hexdigest( )
        if imgMD5 not in self.imghashes:
            return False

        _, imgID, _, _ = self.imghashes[ imgMD5 ]
        response = requests.delete( 'https://api.imgur.com/3/image/%s' % imgID,
                                    headers = { 'Authorization' : 'Bearer %s' % self.access_token },
                                    verify = self.verify )
        self.imghashes.pop( imgMD5 )
        return True

    def change_name( self, imgMD5, new_name ):
        assert( os.path.basename( new_name ).endswith('.png') )
        if imgMD5 not in self.imghashes:
            return False
        _, imgID, _, _ = self.imghashes[ imgMD5 ]
        response = requests.post(  'https://api.imgur.com/3/image/%s' % imgID,
                                 headers = { 'Authorization' : 'Bearer %s' % self.access_token },
                                 data = { 'title' : os.path.basename( new_name ) }, verify = self.verify )
        if response.status_code != 200: return False
        self.imghashes[ imgMD5 ][ 0 ] = new_name
        return True

class PNGPicObject( object ):
    
    @classmethod
    def createPNGPicObjects( cls, pImgClient ):
        pngPICObjects = [ ]
        def _create_object( imgMD5 ):
            imgName, imgID, imgurlLink, imgDateTime = pImgClient.imghashes[ imgMD5 ]
            try:
                newObj = PNGPicObject( {
                    'initialization' : 'SERVER',
                    'imgurlLink' : imgurlLink,
                    'imgName' : imgName,
                    'imgMD5' : imgMD5,
                    'imgDateTime' : imgDateTime }, pImgClient )
                return newObj
            except: return None

        with multiprocessing.Pool( processes = multiprocessing.cpu_count( ) ) as pool:
            pngPICObjects = list( filter(
                None, map( _create_object, pImgClient.imghashes ) ) )
            return pngPICObjects
                
    def __init__( self, initdata, pImgClient ):
        dpi = 300.0

        if 'initialization' not in initdata or initdata['initialization'] not in ( 'FILE', 'SERVER' ):
            raise ValueError( "ERROR, initialization key must be one of 'FILE' or 'SERVER'" )
        
        # filename, actName
        if initdata[ 'initialization' ] == 'FILE':
            filename = initdata[ 'filename' ]
            actName = initdata[ 'actName' ]
            assert( os.path.isfile( filename ) )
            assert( actName.endswith('.png') )
            self.actName = os.path.basename( actName )
            self.img = QImage( filename )
            self.originalImage = Image.open( filename )
            self.originalWidth = self.originalImage.size[0] * 2.54 / dpi # current width in cm
            self.currentWidth = self.originalWidth
            #
            ## do this from http://stackoverflow.com/questions/31826335/how-to-convert-pil-image-image-object-to-base64-string
            buf = io.BytesIO( )
            self.originalImage.save( buf, format = 'PNG' )
            self.b64string = base64.b64encode( buf.getvalue( ) )
            self.imgMD5 = hashlib.md5( self.b64string ).hexdigest( )
            _, _, link, imgDateTime = pImgClient.upload_image(
                self.b64string, self.actName, imgMD5 = self.imgMD5 )
            self.imgurlLink = link
            self.imgDateTime = imgDateTime

        # imgurlLink, imgName, imgMD5, imgDatetime
        elif initdata[ 'initialization' ] == 'SERVER':
            imgurlLink = initdata[ 'imgurlLink' ]
            imgName = initdata[ 'imgName' ]
            imgMD5 = initdata[ 'imgMD5' ]
            imgDateTime = initdata[ 'imgDateTime' ]
            self.imgurlLink = imgurlLink
            self.actName = imgName
            self.imgMD5 = imgMD5
            self.imgDateTime = imgDateTime
            cnt = requests.get( self.imgurlLink, verify = False ).content
            self.originalImage = Image.open( io.BytesIO( cnt ) )
            self.img = QImage( )
            self.img.loadFromData( cnt )
            self.originalWidth = self.originalImage.size[ 0 ] * 2.54 / dpi
            self.currentWidth = self.originalWidth
            buf = io.BytesIO( )
            self.originalImage.save( buf, format = 'PNG' )
            self.b64string = base64.b64encode( buf.getvalue( ) )
        
    def getInfoGUI( self, parent ):
        qdl = QDialog( parent )
        qdl.setModal( True )
        myLayout = QVBoxLayout( )
        mainColor = qdl.palette().color( QPalette.Background )
        qdl.setWindowTitle( 'PNG IMAGE: %s.' % self.actName )
        qdl.setLayout( myLayout )
        myLayout.addWidget( QLabel( 'ACTNAME: %s' % self.actName ) )
        myLayout.addWidget( QLabel( 'URL: %s' % self.imgurlLink ) )
        myLayout.addWidget( QLabel(
            'UPLOADED AT: %s' %
            self.imgDateTime.strftime( '%B %d, %Y @ %I:%M:%S %p' ) ) )
        qpm = QPixmap.fromImage( self.img ).scaledToWidth( 450 )
        qlabel = QLabel( )
        qlabel.setPixmap( qpm )
        myLayout.addWidget( qlabel )
        qdl.setFixedWidth( 1.1 * qpm.width( ) )
        qdl.setFixedHeight( qdl.sizeHint( ).height( ) )
        result = qdl.exec_( )

    def b64String( self ):
        #assert( self.currentWidth > 0 )
        #buffer = StringIO( )
        #reldif = abs( 2 * ( self.originalWidth - self.currentWidth ) / ( self.originalWidth + self.currentWidth ) )
        #self.originalImage.save( buffer, format = 'PNG' )
        #return base64.b64encode( buffer.getvalue( ) ), self.currentWidth, self.imgurlLink
        return self.b64string, self.currentWidth, self.imgurlLink

    def changeName( self, new_name, pImgClient ):
        assert( new_name.endswith( '.png' ) )
        status = pImgClient.change_name( self.imgMD5, os.path.basename( new_name ) )
        if not status: return
        self.actName = os.path.basename( new_name )


if not os.environ.get( 'READTHEDOCS' ):
    dat = plexcore.getCredentials( verify = False, checkWorkingServer = False )
    if dat is not None:
        emailAddress = dat[0]
        try:
            emailName = get_email_contacts_dict( [ emailAddress ], verify = False )[0][0]
        except: emailName = None
    else:
        emailAddress = None
        emailName = None
else:
    emailAddress = None
    emailName = None
