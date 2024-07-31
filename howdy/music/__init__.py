import os, sys, datetime, re, isodate, mutagen.mp4, io, requests
from dateutil.relativedelta import relativedelta
from PIL import Image
from io import BytesIO
#
from howdy.core import core

_dt0 = datetime.datetime.strptime("00", "%S")

def parse_youtube_date( duration_string ):
    """
    Parses a duration string that ``isodate`` can recognize, such as ``PT4M33S``, into a :py:class:`datetime <datetime.datetime>`.
    
    :param str duration_string: duration in ``isodate`` format, such as ``PT4M33S`` to represent 4 minutes and 33 seconds.
    :returns: the :py:class:`datetime <datetime.datetime>` that can be used to infer duration using :py:meth:`format_youtube_date <howdy.music.format_youtube_date>`.
    :rtype: :py:class:`datetime <datetime.datetime>`

    .. seealso:: :py:meth:`format_youtube_date <howdy.music.format_youtube_date>`.
    """
    dstring = duration_string.upper( )
    timedelta = isodate.parse_duration( dstring )
    return _dt0 + timedelta

def format_youtube_date( dt_duration ):
    """    
    :param datetime dt_duration: the :py:class:`datetime <datetime.datetime>`
    
    :returns: a standard second, or MM:SS (such as 4:33), or so on from a :py:class:`datetime <datetime.datetime>` returned by :py:meth:`parse_youtube_date <howdy.music.parse_youtube_date>`.
    :rtype: str

    .. seealso:: :py:meth:`parse_youtube_date <howdy.music.parse_youtube_date>`.
    """
    delta = relativedelta( dt_duration, _dt0 )
    if delta.days >= 20:
        raise ValueError("Error, duration is longer than 20 days!")
    if delta.days > 0:
        dstring = dt_duration.strftime("%d:%H:%M:%S")
    elif delta.hours > 0:
        dstring = dt_duration.strftime("%H:%M:%S")
    elif delta.minutes > 0:
        dstring = dt_duration.strftime("%M:%S")
    else:
        dstring = dt_duration.strftime("%S")
    return dstring


def get_failing_artistalbum( filename ):
    """
    :param str filename: a candidate M4A_ music file name (file must also end in ``".m4a"``).
    :returns: the filename ONLY IF it is missing either album or artist metadata. Otherwise returns ``None``.
    :rtype: str

    .. _M4A: https://en.wikipedia.org/wiki/MPEG-4_Part_14
    """
    if not os.path.basename( filename ).endswith( '.m4a' ):
        return None

    mp4tag = mutagen.mp4.MP4( filename )
    if not all([ key in mp4tag for key in ( '\xa9alb', '\xa9ART' ) ]):
        return filename

    return None

def get_m4a_metadata( filename ):
    """
    Low level method that returns the metadata of an M4A_ music file.

    :param str filename: the M4A_ music file name.
    
    :returns: a :py:class:`dict` of the music metadata that contains as many of these keys: ``song``, ``album``, ``artist``, ``date``, ``tracknumber``, ``total tracks``, ``album cover``.
    :rtype: dict
    """
    #
    ## now start it off
    naming_dict = {
        '\xa9nam' : 'song',
        '\xa9alb' : 'album',
        '\xa9ART' : 'artist',
        '\xa9day' : 'date',
        'aART'    : 'album artist',
        'covr'    : 'album cover',
        'trkn'    : 'trkn' }
    data_dict = dict()
    #
    ##
    assert( os.path.isfile( filename ) )
    assert( os.path.basename( filename ).lower( ).endswith( '.m4a' ) )
    #
    ## open file see what keys we have
    mp4tags = mutagen.mp4.MP4( filename )
    set_of_keys_intersect = set( naming_dict ) & set( mp4tags.keys( ) )
    for key in set_of_keys_intersect:
        if key == 'covr':
            continue
        if key == 'trkn':
            continue
        if key == '\xa9day':
            continue
        data_dict[ naming_dict[ key ] ] = mp4tags[ key ][ 0 ]
    #
    ## now if we have a covr
    if 'covr' in set_of_keys_intersect:
        data_dict[ 'cover' ] = Image.open(
            BytesIO( mp4tags['covr'][0][:-1] ) )
    #
    ## if we have the track number and total number of tracks
    if 'trkn' in set_of_keys_intersect:
        trackno, tottracks = mp4tags[ 'trkn' ][ 0 ][:2]
        data_dict[ 'tracknumber'  ] = trackno
        data_dict[ 'total tracks' ] = tottracks
    #
    ## if have isodate string
    if '\xa9day' in set_of_keys_intersect:
        dstring = mp4tags[ '\xa9day' ][ 0 ].strip( )
        num_dashes = len( dstring.split('-') ) - 1
        assert( num_dashes <= 2 )
        if num_dashes == 0: # just year
            mydate = datetime.datetime.strptime( dstring, '%Y' ).date( )
        elif num_dashes == 1:
            mydate = datetmie.datetime.strptime( dstring, '%Y-%m' ).date( )
        else:
            mydate = datetime.datetime.strptime( dstring, '%Y-%m-%d' ).date( )
        data_dict[ 'date' ] = mydate
    #
    return data_dict    


def fill_m4a_metadata( filename, data_dict, verify = True, image_data = None ):
    """
    Low level method that populates the metadata of an M4A_ music file.

    :param str filename: a candidate M4A_ music file name.
    :param dict data_dict: a dictionary of candidate music metadata with the following obligatory keys: ``song``, ``album``, ``artist``, ``year``, ``tracknumber``, and ``total tracks``. If the URL of the album image, ``album url``, is defined, then also provides the album image into the M4A_ file.
    :param BytesIO image_data: optional argument. If defined, is a :py:class:`BytesIO <io.BytesIO>` binary data representation of *usually* a candidate PNG_ image file.
    
    .. _PNG: https://en.wikipedia.org/wiki/Portable_Network_Graphics
    .. _M4A: https://en.wikipedia.org/wiki/MPEG-4_Part_14
    """
    assert( os.path.isfile( filename ) )
    assert( os.path.basename( filename ).lower( ).endswith( '.m4a' ) )
    #
    ## now start it off
    mp4tags = mutagen.mp4.MP4( filename )
    mp4tags[ '\xa9nam' ] = [ data_dict[ 'song' ], ]
    mp4tags[ '\xa9alb' ] = [ data_dict[ 'album' ], ]
    mp4tags[ '\xa9ART' ] = [ data_dict[ 'artist' ], ]
    mp4tags[ 'aART' ] = [ data_dict[ 'artist' ], ]
    if 'year' in data_dict: mp4tags[ '\xa9day' ] = [ str(data_dict[ 'year' ]), ]
    mp4tags[ 'trkn' ] = [ ( data_dict[ 'tracknumber' ],
                            data_dict[ 'total tracks' ] ), ]

    def _save_image_data( image_data, mp4tags ):
        if image_data is None: return
        with io.BytesIO( ) as csio2:
            try:
                img = Image.open( image_data )
            except Exception as e:
                logging.info( 'problem with filename = %s, and error message = %s.' % (
                    filename, str( e ) ) )
                return str(e)
            try:
                img.save( csio2, format = 'png' )
                mp4tags[ 'covr' ] = [
                    mutagen.mp4.MP4Cover( csio2.getvalue( ),
                                        mutagen.mp4.MP4Cover.FORMAT_PNG ), ]
                return 'SUCCESS'
            except:
                #
                ## had a CMYK colormap for the JPEG file, so just store the JPEG image into the M4A file
                img.save( csio2, format = 'jpeg' )
                mp4tags[ 'covr' ] = [
                    mutagen.mp4.MP4Cover( csio2.getvalue( ),
                                         mutagen.mp4.MP4Cover.FORMAT_JPEG ), ]
                return 'SUCCESS'
        
    if image_data is not None: val = _save_image_data( image_data, mp4tags )
    elif data_dict[ 'album url' ] != '':
        with io.BytesIO( requests.get(
                data_dict[ 'album url' ], verify = verify ).content ) as csio, io.BytesIO( ) as csio2:
            try:
                mp4tags[ 'covr' ] = [
                    mutagen.mp4.MP4Cover( csio2.getvalue( ),
                                        mutagen.mp4.MP4Cover.FORMAT_PNG ), ]
            except:
                #
                ## had a CMYK colormap for the JPEG file, so just store the JPEG image into the M4A file
                img.save( csio2, format = 'jpeg' )
                mp4tags[ 'covr' ] = [
                    mutagen.mp4.MP4Cover( csio2.getvalue( ),
                                         mutagen.mp4.MP4Cover.FORMAT_JPEG ), ]
    mp4tags.save( )
