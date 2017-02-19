# resource file
import os, sys, datetime, re
from dateutil.relativedelta import relativedelta
mainDir = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
sys.path.append( mainDir )

_dt0 = datetime.datetime.strptime("00", "%S")

def parse_youtube_date( duration_string ):
    dstring = duration_string.upper( )
    if dstring.startswith('PT'):
        dstring_sub = dstring[2:]
        hms_split = re.sub( r"([A-Z])", r" ", dstring_sub).split()
        if all(map(lambda tok: tok in dstring_sub, ('H', 'M', 'S' ) ) ):
            hours = int( hms_split[ 0 ] )
            mins = int( hms_split[ 1 ] )
            secs = int( hms_split[ 2 ] )
            return datetime.datetime.strptime("%02d:%02d:%02d" % ( hours, mins, secs ),
                                              "%H:%M:%S" )
        elif all(map(lambda tok: tok in dstring_sub, ('M', 'S' ) ) ):
            mins = int( hms_split[ 0 ] )
            secs = int( hms_split[ 1 ] )
            return datetime.datetime.strptime("%02d:%02d" % ( mins, secs ), "%M:%S" )
        elif all(map(lambda tok: tok in dstring_sub, ('S' ) ) ):
            secs = int( hms_split[ 0 ] )
            return datetime.datetime.strptime("%02d" % secs, "%S" )
        else:
            raise ValueError("Error, datetime string %s cannot be parsed." % dstring )
    elif dstring.startswith('P'):
        dstring_sub = dstring[1:]
        dhms_split = re.sub( r"([A-Z])", r" \1", dstring_sub).split()
        assert( all(map(lambda tok: tok in dtsring_sub, ( 'DT', 'H', 'M', 'S' ) ) ) )
        assert( len( dhms_split ) == 4 )
        days = int( dhms_split[ 0 ] )
        hours = int( dhms_split[ 1 ] )
        mins = int( dhms_split[ 2 ] )
        secs = int( dhms_split[ 3 ] )
        return datetime.datetime.strptime(
            "%02d:%02d:%02d:%02d" % ( days, hours, mins, secs ),
            "%d:%H:%M:%S" )
    else:
        raise ValueError("Error, datetime string %s cannot be parsed." % dstring )

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
