#!/usr/bin/env python3

import logging, PyQt4.QtGui, sys, pickle, gzip, os
if sys.version_info.major == 2: from ConfigParser import RawConfigParser
else: from configparser import RawConfigParser
from optparse import OptionParser
#
##
sip.setapi( 'QVariant', 1 )
from plexcore import plexcore_gui, mainDir
from plextmdb import plextmdb_gui

def main(debug = False, checkLocal = True):
    app = PyQt4.QtGui.QApplication([])
    if debug:
        logging.basicConfig( level = logging.DEBUG )
    fullurl, token = plexcore_gui.returnToken( shouldCheckLocal = checkLocal )
    movie_data_rows = pickle.load( gzip.open( os.path.join( mainDir, 'resources', 'movie_data_rows.pkl.gz', 'rb' ) ) )
    tmdbgui = plextmdb_gui.TMDBGUI( movie_data_rows )
    result = app.exec_( )
    return tmdbgui

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('--local', dest='do_local', action='store_true',
                      default = False, help = 'Check for locally running plex server.')
    parser.add_option('--debug', dest='do_debug', action='store_true',
                      default = False, help = 'Run debug mode if chosen.')
    opts, args = parser.parse_args( )
    main( debug = opts.do_debug, checkLocal = opts.do_local )
