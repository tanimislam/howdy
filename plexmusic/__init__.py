import os, sys, datetime, re, isodate, mutagen.mp4
from dateutil.relativedelta import relativedelta
from functools import reduce
_mainDir = reduce(lambda x,y: os.path.dirname( x ), range( 2 ),
                  os.path.abspath( __file__ ) )
sys.path.append( _mainDir )

_dt0 = datetime.datetime.strptime("00", "%S")

def parse_youtube_date( duration_string ):
    """
    Parses a duration string that ``isodate`` can recognize, such as ``PT4M33S``, into a :py:class:`datetime <datetime.datetime>`.
    
    :param str duration_string: duration in ``isodate`` format, such as ``PT4M33S`` to represent 4 minutes and 33 seconds.
    :returns: the :py:class:`datetime <datetime.datetime>` that can be used to infer duration using :py:meth:`format_youtube_date <plexmusic.format_youtube_date>`.
    :rtype: :py:class:`datetime <datetime.datetime>`

    .. seealso:: :py:meth:`format_youtube_date <plexmusic.format_youtube_date>`
    """
    dstring = duration_string.upper( )
    timedelta = isodate.parse_duration( dstring )
    return _dt0 + timedelta

def format_youtube_date( dt_duration ):
    """    
    :param datetime dt_duration: the :py:class:`datetime <datetime.datetime>`
    
    :returns: a standard second, or MM:SS (such as 4:33), or so on from a :py:class:`datetime <datetime.datetime>` returned by :py:meth:`parse_youtube_date <plexmusic.parse_youtube_date>`.
    :rtype: str

    .. seealso:: :py:meth:`parse_youtube_date <plexmusic.parse_youtube_date>`
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
