#!/usr/bin/env python3

import signal
from . import signal_handler
signal.signal( signal.SIGINT, signal_handler )
from plextvdb import plextvdb_season_gui, get_token
from plexcore import plexcore
from optparse import OptionParser
import test_plexcore, test_tvdbgui

#
## start the application here
if __name__=='__main__':
    logging.basicConfig( level = logging.INFO )
    parser = OptionParser( )
    parser.add_option('-s', '--series', type=str, dest='series', action='store', default='The Simpsons',
                      help = 'Name of the series to choose. Default is "The Simpsons".' )
    parser.add_option('-S', '--season', type=int, dest='season', action='store', default=1,
                      help = 'Season number to examine. Default is 1.' )
    opts, args = parser.parse_args( )
    app = test_tvdbgui.get_app_standalone( )
    tvdata, toGet, _ = test_tvdbgui.get_tvdata_toGet_didend_standalone( )
    fullURL, token = test_plexcore.get_token_fullURL_standalone( )
    assert( opts.season > 0 )
    assert( opts.series in tvdata )
    assert( opts.season in tvdata[ opts.series ][ 'seasons' ] )
    missing_eps = dict(map(
        lambda seriesName: ( seriesName, toGet[ seriesName ][ 'episodes' ] ),
        toGet ) )#
    tvdb_season_gui = plextvdb_season_gui.TVDBSeasonGUI(
        opts.series, opts.season, tvdata, missing_eps, get_token( True ),
        plex_token, verify = True )
    result = app.exec_( )
