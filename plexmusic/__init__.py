import os, sys, datetime, re, isodate, mutagen.mp4
from dateutil.relativedelta import relativedelta
from functools import reduce
_mainDir = reduce(lambda x,y: os.path.dirname( x ), range( 2 ),
                  os.path.abspath( __file__ ) )
sys.path.append( _mainDir )

_dt0 = datetime.datetime.strptime("00", "%S")

def parse_youtube_date( duration_string ):
    dstring = duration_string.upper( )
    timedelta = isodate.parse_duration( dstring )
    return _dt0 + timedelta

def format_youtube_date( dt_duration ):
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
    if not os.path.basename( filename ).endswith( '.m4a' ):
        return None

    mp4tag = mutagen.mp4.MP4( filename )
    if not all([ key in mp4tag for key in ( '\xa9alb', '\xa9ART' ) ]):
        return filename

    return None
