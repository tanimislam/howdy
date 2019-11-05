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
    Sends out an email using the `Google Contacts API`_. If process is unsuccessfull, prints out an error message, ``"problem with <TO-EMAIL>"``, where ``<TO-EMAIL>`` is the recipient's email address.

    :param MIMEMultiPart msg: the :py:class:`MIMEMultiPart <email.mime.multipart.MIMEMultiPart>` email message to send. At a high level, this is an email with body, sender, recipients, and optional attachments.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.

    .. _`Google Contacts API`: https://developers.google.com/contacts/v3
    .. _Ubuntu: https://www.ubuntu.com
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
    """
    Returns the Google contacts given a set of emails, all using the `Google Contacts API`_.

    :param list emailList: the :py:class:`list` of emails, used to determine to whom it belongs.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :returns: a :py:class:`list` of two-element :py:class:`tuple`. The first element is the Google conatct name. The second element is a primary email associated with that contact.
    :rtype: list
    """
    if len( emailList ) == 0: return [ ]
    credentials = plexcore.oauthGetOauth2ClientGoogleCredentials( )
    assert( credentials is not None )
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
    """
    This object contains and implements the collection of images located in a single main album in the Imgur_ account. This uses the Imgur_ API to peform all operations. This object is constructed using Imgur_ credentials -- the client ID, secret, and refresh token -- stored in the SQLite3_ configuration database, and stores the following attributes: the client ID, secret, refresh token, and the *access token* used for API access to your Imgur_ album and images.

    If the Imgur_ albums cannot be accessed, or there are no albums, then ``self.albumID = None``, the ``self.imgHashes`` is an empty :py:class:`dict`.

    The main album ID is stored as a :py:class:`string <str>` in the Imgur_ configuration under the ``mainALBUMID`` key, if it exists; otherwise the Imgur_ configuration dictionary does not have a ``mainALBUMID`` key.

    * If there is no main album ID defined, or if there is no album with that ID, then we choose the first album found, and reset the Imgur_ configuration data into the SQLite3_ database with this album ID and name.

    * If the configured album exists in our Imgur_ library, then continue with this the main album.

    Once the main album is found, populate ``self.imghashes`` with all the pictures in this album. The pictures in an album in our Imgur_ account are expected to be filled through methods in this object.

    * The key is the MD5_ hash of the image in that library.
    
    * The value is a four element :py:class:`tuple`: image name, image ID, the URL link to this image, and the :py:class:`datetime <datetime.datetime>` at which the image was uploaded.

    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    
    :var bool verify: whether to verify SSL connections.
    :var str access_token: the persistent API access token to the user's Imgur_ account.
    :var str clientID: the Imgur_ client ID.
    :var str clientSECRET: the Imgur_ client secret.
    :var str albumID: the hashed name of the main album.
    :var dict imghashes: the structure of images stored in the main album.

    :raise ValueError: if images in the new album cannot be accessed.

    .. seealso:: :py:meth:`refreshImages <plexemail.PlexIMGClient.refreshImages>`
    
    .. _Imgur: https://imgur.com
    .. _SQLite3: https://www.sqlite.org/index.html
    .. _MD5: https://en.wikipedia.org/wiki/MD5
    """    
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
        data = response.json( )
        self.access_token = data[ 'access_token' ]
        self.clientID = clientID
        self.clientSECRET = clientSECRET
        self.imghashes = { }
        #
        ## now first see if there are any albums
        response = requests.get( 'https://api.imgur.com/3/account/me/albums',
                                 headers = { 'Authorization' : 'Bearer %s' % self.access_token },
                                 verify = self.verify )

        #
        ## error state #1: cannot access my own albums
        if response.status_code != 200:
            self.albumID = None
            return

        #
        ## error state #2: do not have any albums
        imgDatas = response.json( )[ 'data' ]
        if len( imgDatas ) == 0:
            self.albumID = None
            return

        #
        ## three possible situations
        ## #1: if mainALBUMID not defined OR album name not defined, use first img hash
        if 'mainALBUMID' not in data_imgurl or data_imgurl[ 'mainALBUMID' ] not in set(map(lambda imgData: imgData['title'], imgDatas)):
            self.albumID = imgDatas[ 0 ][ 'id' ]
            albumName = imgDatas[ 0 ][ 'title' ]
            #
            ## put new information into database
            plexcore.store_imgurl_credentials(
                clientID, clientSECRET, clientREFRESHTOKEN, 
                mainALBUMID = self.albumID,
                mainALBUMNAME = albumName,
                verify = self.verify )
        else:
            self.albumID = data_imgurl['mainALBUMID']
        #
        ## now get all the images in that album
        ## remember: Authorization: Bearer YOUR_ACCESS_TOKEN
        self.refreshImages( )

    def set_main_album( self, new_album_name ):
        """
        Sets or changes the main Imgur_ album used for storing and displaying images to a new album name. If ``new_album_name`` exists in the Imgur_ account, then sets that name. If ``new_album_name`` does not exist, then creates this new Imgur_ album.

        Once this album is set or created,

        * sets the new Imgur_ credentials using :py:meth:`store_imgur_credentials <plexcore.plexcore.store_imgurl_credentials>`.

        * populates ``self.imghashes`` with all the images found in this library. Of course, if the album does not exist, then ``self.imghashes`` is an empty :py:class:`dict`.
        
        :param str new_album_name: the new name of the Imgur_ album to use for images.
        :raise ValueError: if images in the new album cannot be accessed.

        .. seealso:: :py:meth:`refreshImages <plexemail.PlexIMGClient.refreshImages>`
        """

        #
        ## if nothing there, then make new album
        response = requests.get( 'https://api.imgur.com/3/account/me/albums',
                                 headers = { 'Authorization' : 'Bearer %s' % self.access_token },
                                 verify = self.verify )
        if response.status_code != 200:
            return

        imgDatas = response.json( )[ 'data' ]
        imgNames = dict(map(lambda imgData: ( imgData[ 'title' ], imgData[ 'id' ] ), imgDatas ) )
        if new_album_name in imgNames:
            self.albumID = imgNames[ new_album_name ]
            
        else: # create this album
            response = requests.post( 'https://api.imgur.com/3/album',
                                      headers = { 'Authorization' : 'Bearer %s' % self.access_token },
                                      data = { 'title' : new_album_name, 'privacy' : 'public' },
                                      verify = self.verify )
            if response.status_code != 200: return
            data = response.json( )[ 'data' ]
            self.albumID = data[ 'id' ]

        #
        ## put new information into database
        plexcore.store_imgurl_credentials(
            self.clientID, self.clientSECRET, self.clientREFRESHTOKEN, 
            mainALBUMID = self.albumID,
            mainALBUMNAME = new_album_name,
            verify = self.verify )
            
        #
        ## now get all the images in that album
        ## remember: Authorization: Bearer YOUR_ACCESS_TOKEN
        self.refreshImages( )

    def get_candidate_album_names( self ):
        """
        :returns: a :py:class:`list` of album names in the Imgur_ account. :py:meth:`set_main_album <plexemail.PlexIMGClient.set_main_album>` can use this method to determine the valid album name to choose.
        """
        response = requests.get( 'https://api.imgur.com/3/account/me/albums',
                                 headers = { 'Authorization' : 'Bearer %s' % self.access_token },
                                 verify = self.verify )
        if response.status_code != 200:
            return [ ]

        imgDatas = response.json( )[ 'data' ]
        imgNames = dict(map(lambda imgData: ( imgData[ 'title' ], imgData[ 'id' ] ), imgDatas ) )
        return sorted( imgNames )
            
    def refreshImages( self ):
        """
        Refreshes the collection of images in the main Imgur_ album, by filling out ``self.imghashes``. The pictures in an album in our Imgur_ account are expected to be filled through methods in this object.

        * The key is the MD5_ hash of the image in that library.
    
        * The value is a four element :py:class:`tuple`: image name, image ID, the URL link to this image, and the :py:class:`datetime <datetime.datetime>` at which the image was uploaded.
        """
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
        """
        Uploads a Base64_ encoded file into the main Imgur_ album. If the image exists, then returns information (from ``self.imghashes``) about the file. If not, create it, put it into ``self.imghashes``, and then return its information.

        :param str b64img: the Base64_ representation of the image.
        :param str name: name of the image.
        :param str imgMD5: optional argument. This is the MD5_ hash of the image. If not provided, this is calculated for that image represented by ``b64img``.

        :returns: a 4-element :py:class:`tuple`: image name, image ID, the URL link to this image, and the :py:class:`datetime <datetime.datetime>` at which the image was uploaded.
        :rtype: tuple

        .. seealso::

           * :py:meth:`refreshImages <plexemail.PlexIMGClient.refreshImages>`
           * :py:meth:`delete_image <plexemail.PlexIMGClient.delete_image>`
           * :py:meth:`change_name <plexemail.PlexIMGClient.change_name>`

        .. _Base64: https://en.wikipedia.org/wiki/Base64
        """
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
        """
        Removes an image from the main Imgur_ library.

        :param str b64img: the Base64_ representation of the image.
        :param str imgMD5: optional argument. This is the MD5_ hash of the image. If not provided, this is calculated for that image represented by ``b64img``.

        :returns: ``True`` if image can be found and returned. Otherwise returns ``False``.
        :rtype: bool

        .. seealso::

           * :py:meth:`upload_image <plexemail.PlexIMGClient.upload_image>`
           * :py:meth:`change_name <plexemail.PlexIMGClient.change_name>`
        """
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
        """
        Changes the name of an image in the main Imgur_ library.

        :param str imgMD5: this is the MD5_ hash of the image in the main Imgur_ library.
        :param str new_name: the new name to give this image.
        :returns: ``True`` if image could be found and its name changed. Otherwise returns ``False``.
        :rtype: bool

        .. seealso::

           * :py:meth:`upload_image <plexemail.PlexIMGClient.upload_image>`
           * :py:meth:`delete_image <plexemail.PlexIMGClient.delete_image>`
        """
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
    """
    This provides a GUI widget to the Imgur_ interface implemented in :py:class:`PlexIMGClient <plexemail.PlexIMGClient>`. Initializaton of the image can either upload this image to the Imgur_ account, or retrieve the image from the main Imgur_ album. This object can also launch a GUI dialog window through :py:meth:`getInfoGUI <plexemail.PNGPicObject.getInfoGUI>`.

    :param dict initdata: the low-level dictionary that contains important information on the image, located in a file, that will either be uploaded into the main Imgur_ album or merely kept in memory. The main key that determines operation is ``initialization``. It can be one of ``"FILE"`` or ``"SERVER"``.

      If ``initialization`` is ``"FILE"``, then upload the the image to the main album in the Imgur_ account. Here are the required keys in ``initdata``.

      * ``filename`` is the location of the image file on disk.
    
      * ``actName`` is the PNG filename to be used. It must end in ``png``.

      If ``initialization`` is ``"SERVER"``, then retrieve this image from the main album in the Imgur_ account. Here are the required keys in ``initdata``.

      * ``imgurlink`` is the URL link to the image.
    
      * ``imgName`` is the name of the image.

      * ``imgMD5`` is the MD5_ hash of the image.
    
      * ``imgDateTime`` is the :py:class:`datetime <datetime.datetime>` at which the image was initially uploaded into the main Imgur_ album.

    :param PlexIMGClient pImgClient: the :py:class:`PlexIMGClient <plexemail.PlexIMGClient>` used to access and manipulate (add, delete, rename) images in the main Imgur_ album.

    :var str actName: the file name without full path, which must end in ``png``.
    :var QImage img: the :py:class:`QImage <PyQt4.QtGui.QImage>` representation of this image.
    :var Image originalImage: the :py:class:`Image <PIL.Image>` representation of this image.
    :var float originalWidth: the inferred width in cm.
    :var float currentWidth: the current image width in cm. It starts off as equal to ``originalWidth``
    :var str b64string: the Base64_ encoded representation of this image as a PNG file.
    :var str imgurlLink: the URL link to the image.
    :var datetime imgDateTime: the :py:class:`datetime <datetime.datetime>` at which this image was first uploaded to the main album in the Imgur_ account.

    :raise ValueError: if ``initdata['initialization']`` is neither ``"FILE"`` nor ``"SERVER"``.
    """
    
    @classmethod
    def createPNGPicObjects( cls, pImgClient ):
        """
        :param PlexIMGClient pImgClient: the :py:class:`PlexIMGClient <plexemail.PlexIMGClient>` used to access and manipulate (add, delete, rename) images in the main Imgur_ album.
        :returns: a :py:class:`list` of :py:class:`PNGPicObject <plexemail.PNGPicObject>` representing the images in the main Imgur_ album.
        :rtype: list
        """
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
        """
        Launches a :py:class:`QDialog <PyQt4.QtGui.QDialog>` that contains the underlying image and some other labels: ``ACTNAME`` is the actual PNG file name, ``URL`` is the image's Imgur_ link, and ``UPLOADED AT`` is the date and time at which the file was uploaded. An example image is shown below,

        .. image:: /_static/plexemail_pngpicobject_infogui.png
           :width: 100%
        
        :param QWidget parent: the parent :py:class:`QWidget <PyQt4.QtGui.QWidget>` that acts as the :py:class:`QDialog <PyQt4.QtGui.QDialog>` window's parent. Can be ``None``.
        """
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
        """
        :returns: a 3-element :py:class:`tuple` on the image incorporated into this object: its Base64_ string, its width in pixels, and the Imgur_ link.
        :rtype: tuple
        """
        #assert( self.currentWidth > 0 )
        #buffer = StringIO( )
        #reldif = abs( 2 * ( self.originalWidth - self.currentWidth ) / ( self.originalWidth + self.currentWidth ) )
        #self.originalImage.save( buffer, format = 'PNG' )
        #return base64.b64encode( buffer.getvalue( ) ), self.currentWidth, self.imgurlLink
        return self.b64string, self.currentWidth, self.imgurlLink

    def changeName( self, new_name, pImgClient ):
        """
        changes the filename into a new name.

        :param str new_name: the new name of the image file to be changed in the main album on the Imgur_ account. This must end in ``png``.
        :param PlexIMGClient pImgClient: the :py:class:`PlexIMGClient <plexemail.PlexIMGClient>` used to access and manipulate (add, delete, rename) images in the main Imgur_ album.
        """
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
