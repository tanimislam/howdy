#!/usr/bin/env python

import os, sys, glob
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from optparse import OptionParser

sys.path.append( os.path.dirname( os.path.dirname(
    os.path.abspath( __file__ ) ) ) )
from plexstuff import plextmdb_gui, plexcore_gui

parser = OptionParser( )
parser.add_option('--movie', dest='movie', type=str, action='store',
                  default = 'Big Hero 6', help =
                  ' '.join([ 'Name of movie to do torrent for.',
                             'Default is Big Hero 6.' ]) )
parser.add_option('--bypass', dest='do_bypass', action='store_true',
                  default = False, help = 'If chosen, then bypass using Kickass.' )
opts, args = parser.parse_args( )

app = QApplication([])
_, token = plexcore_gui.returnClientToken( )
tmdbt = plextmdb_gui.TMDBTorrents( None, token, opts.movie,
                                   bypass = opts.do_bypass )
result = tmdbt.exec_( )
