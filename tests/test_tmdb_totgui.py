#!/usr/bin/env python3

import signal, logging
from . import signal_handler
signal.signal( signal.SIGINT, signal_handler )
from optparse import OptionParser
from plexcore import plexcore
from plextmdb import plextmdb_totgui

def main(debug = False, doLocal = True, doLarge = False,
         verify = True ):
    app = test_tmdbgui.get_app_standalone( )
    movie_data_rows = test_tmdbgui.get_movie_data_rows_standalone( )
    if debug: logging.basicConfig( level = logging.DEBUG )
    fullURL, token = plexcore.checkServerCredentials(
        doLocal = doLocal, verify = verify )
    tmdb_totgui = plextmdb_totgui.TMDBTotGUI(
        fullURL, token, movie_data_rows = movie_data_rows,
        doLarge = doLarge, verify = verify )
    result = app.exec_( )

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('--local', dest='do_local', action='store_true',
                      default = False, help = 'Check for locally running plex server.')
    parser.add_option('--debug', dest='do_debug', action='store_true',
                      default = False, help = 'Run debug mode if chosen.')
    parser.add_option('--noverify', dest='do_verify', action='store_false',
                      default = True, help = 'Do not verify SSL transactions if chosen.')    
    opts, args = parser.parse_args( )
    main( debug = opts.do_debug, doLocal = opts.do_local, verify = opts.do_verify )
