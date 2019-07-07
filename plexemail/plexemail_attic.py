from plexcore import session, plexcore
from plexcore import get_formatted_size, get_formatted_duration
from . import mainDir, send_email_lowlevel, send_email_localsmtp, emailAddress, emailName

def get_summary_data_freshair_remote( token, fullURLWithPort = 'http://localhost:32400' ):
    libraries_dict = plexcore.get_libraries( token = token, fullURL = fullURLWithPort )
    keynum = max([ key for key in libraries_dict if libraries_dict[key] == 'NPR Fresh Air' ])
    sinceDate = plexcore.get_current_date_newsletter( )
    key, num_songs, _, _, totdur, totsizebytes = plexcore._get_library_stats_artist(
        keynum, token, fullURL = fullURLWithPort )
    mainstring = 'There are %d episodes of NPR Fresh Air.'  % num_songs
    sizestring = 'The total size of Fresh Air media is %s.' % get_formatted_size( totsizebytes )
    durstring = 'The total duration of Fresh Air media is %s.' % get_formatted_duration( totdur )
    if sinceDate is not None:
        key, num_songs_since, _, _, \
            totdur_since, totsizebytes_since = plexcore._get_library_stats_artist(
                keynum, token, fullURL = fullURLWithPort, sinceDate = sinceDate )
        if num_songs_since > 0:
            mainstring_since = ' '.join([
                'Since %s, I have added %d new Fresh Air episodes.' %
                ( sinceDate.strftime('%B %d, %Y'), num_songs_since ),
                'The total size of Fresh Air media I have added is %s.' %
                get_formatted_size( totsizebytes_since ),
                'The total duration of Fresh Air media I have added is %s.' %
                get_formatted_duration( totdur_since ) ] )
            return ' '.join([ mainstring, sizestring, durstring, mainstring_since ])
    return ' '.join([ mainstring, sizestring, durstring ])

def get_summary_data_thisamericanlife_remote( token, fullURLWithPort = 'http://localhost:32400' ):
    libraries_dict = plexcore.get_libraries( token = token, fullURL = fullURLWithPort )
    keynum = max([ key for key in libraries_dict if libraries_dict[key] == 'This American Life' ])
    sinceDate = plexcore.get_current_date_newsletter( )
    key, song_data = plexcore._get_library_data_artist( keynum, token, fullURL = fullURLWithPort )
    num_episodes = 0
    totdur = 0.0
    totsizebytes = 0.0
    for key in song_data:
        for key2 in song_data[key]:
            num_episodes += len( song_data[ key ][ key2 ] )
            for track in song_data[ key ][ key2 ]:
                name, dt, dur, sizebytes = track
                totdur += dur
                totsizebytes += sizebytes
    mainstring = 'There are %d episodes in %d series in This American Life.' % (
        num_episodes, len( song_data ) )
    sizestring = 'The total size of This American Life media is %s.' % \
        get_formatted_size( totsizebytes )
    durstring = 'The total duration of This American Life media is %s.' % \
        get_formatted_duration( totdur )
    if sinceDate is None:
        pristrings = [ ' '.join([ mainstring, sizestring, durstring ]), ]
    else:
        key, song_data_since = plexcore._get_library_data_artist(
            keynum, token, fullURL = fullURLWithPort, sinceDate = sinceDate )
        num_episodes_since = 0
        totdur_since = 0.0
        totsizebytes_since = 0.0
        for key in song_data_since:
            for key2 in song_data_since[key]:
                num_episodes_since += len( song_data_since[ key ][ key2 ] )
                for track in song_data_since[ key ][ key2 ]:
                    name, dt, dur, sizebytes = track
                    totdur_since += dur
                    totsizebytes_since += sizebytes
        if num_episodes_since > 0:        
            mainstring_since = ' '.join([
                'Since %s, I have added %d new This American Life episodes.' %
                ( sinceDate.strftime( '%B %d, %Y' ), num_episodes_since ),
                'The total size of This American Life media I added is %s.' %
                get_formatted_size( totsizebytes_since ),
                'The total duration of This American Life media I added is %s.' %
                get_formatted_duration( totdur_since ) ])
            pristrings = [ ' '.join([ mainstring, sizestring, durstring, mainstring_since ]), ]
        else:
            pristrings = [ ' '.join([ mainstring, sizestring, durstring ]), ]           
    #
    catpristrings = {}
    for album in song_data:
        if album == 'Ira Glass': actalbum = 'This American Life'
        else: actalbum = album
        totdur = 0.0
        totsizebytes = 0.0
        num_episodes = 0
        for key2 in song_data[ album ]:
            num_episodes += len( song_data[ album ][ key2 ] )
            for track in song_data[ album ][ key2 ]:
                name, dt, dur, sizebytes = track
                totdur += dur
                totsizebytes += sizebytes
        mainstring = 'There are %d episodes in this category.' % num_episodes
        sizestring = 'The total size of media here is %s.' % get_formatted_size( totsizebytes )
        durstring = 'The total duration of media here is %s.' % get_formatted_duration( totdur )
        if sinceDate is None:
            mystring = ' '.join([ mainstring, sizestring, durstring ])
        else:
            if album not in song_data_since:
                mystring = ' '.join([ mainstring, sizestring, durstring ])
            else:
                totdur_since = 0.0
                totsizebytes_since = 0.0
                num_episodes_since = 0
                for key2 in song_data_since[ album ]:
                    num_episodes_since += len( song_data_since[ album ][ key2 ] )
                    for track in song_data_since[ album ][ key2 ]:
                        name, dt, dur, sizebytes = track
                        totdur_since += dur
                        totsizebytes_since += sizebytes
                if num_episodes_since > 0:
                    mainstring_since = ' '.join([
                        'Since %s, I have added %d new episodes in this category.' %
                        ( sinceDate.strftime( '%B %d, %Y' ), num_episodes_since ),
                        'The total size of media I added here is %s.' %
                        get_formatted_size( totsizebytes_since ),
                        'The total duration of media I added here is %s.' %
                        get_formatted_duration( totdur_since ) ])
                    mystring = ' '.join([ mainstring, sizestring, durstring, mainstring_since ])
                else:
                    mystring = ' '.join([ mainstring, sizestring, durstring ])
        catpristrings[ actalbum ] = mystring
    pristrings.append( catpristrings )
    return pristrings
