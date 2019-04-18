#!/usr/bin/env python3

import logging
from plexcore import mainDir
from plexcore.plexcore_gui import returnToken, returnEmailAuthentication
from PyQt4.QtGui import QApplication
from optparse import OptionParser

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option( '--debug', dest='do_debug', action = 'store_true', default = False,
                       help = 'If chosen, run in DEBUG logging mode.')
    parser.add_option( '--remote', dest='do_remote', action = 'store_true', default = False,
                       help = 'If chosen, do not check localhost for running plex server.')
    parser.add_option( '--emailauth', dest='do_emailauth', action='store_true', default = False,
                       help = 'If chosen, set up gmail oauth2 authentication.' )
    opts, args = parser.parse_args( )
    if opts.do_debug:
        logging.basicConfig( level = logging.DEBUG )
    app = QApplication([])
    if not opts.do_emailauth:
        fullurl, token = returnToken( shouldCheckLocal = not opts.do_remote )
        print 'token = %s' % token
        print 'url = %s' % fullurl
    else:
        val = returnEmailAuthentication( )
