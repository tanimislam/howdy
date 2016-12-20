#!/usr/bin/env python2

import logging, PyQt4.QtGui, sys, pickle, gzip
from plexcore import plexcore_gui
from plextmdb import plextmdb_totgui
from optparse import OptionParser

def main(debug = False, checkLocal = True):
    app = PyQt4.QtGui.QApplication([])
    if debug:
        logging.basicConfig( level = logging.DEBUG )
    fullurl, token = plexcore_gui.returnClientToken( )
    tmdb_mygui = plextmdb_totgui.TMDBTotGUI( fullurl, token )
    result = app.exec_( )
    return tmdb_mygui

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('--local', dest='do_local', action='store_true',
                      default = False, help = 'Check for locally running plex server.')
    parser.add_option('--debug', dest='do_debug', action='store_true',
                      default = False, help = 'Run debug mode if chosen.')
    opts, args = parser.parse_args( )
    main( debug = opts.do_debug, checkLocal = opts.do_local )
