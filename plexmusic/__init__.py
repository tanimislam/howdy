# resource file
import os, sys, datetime, re, isodate
from dateutil.relativedelta import relativedelta
mainDir = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
sys.path.append( mainDir )

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
