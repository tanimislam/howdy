#!/usr/bin/env python3

import signal
from . import signal_handler
signal.signal( signal.SIGINT, signal_handler )
from optparse import OptionParser
from plextmdb import plextmdb_gui
from plexcore import plexcore
import test_plexcore, test_tmdbgui

parser = OptionParser( )
parser.add_option('--movie', dest='movie', type=str, action='store',
                  default = 'Big Hero 6', help =
                  ' '.join([ 'Name of movie to do torrent for.',
                             'Default is Big Hero 6.' ]) )
parser.add_option('--bypass', dest='do_bypass', action='store_true',
                  default = False, help = 'If chosen, then bypass using YTS Movies.' )
parser.add_option('--info', dest='do_info', action='store_true', default = False,
                  help = 'If chosen, then run with info mode.' )
opts, args = parser.parse_args( )
#
app = test_tmdbgui.get_app_standalone( )
if opts.do_info: logging.basicConfig( level = logging.INFO )
_, token = test_plexcore.get_token_fullURL_standalone( )
tmdbt = plextmdb_gui.TMDBTorrents( None, token, opts.movie,
                                   bypass = opts.do_bypass )
result = tmdbt.exec_( )
