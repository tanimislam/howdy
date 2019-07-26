#!/usr/bin/env python3

import signal, sys
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import os, glob
from optparse import OptionParser

from plexmusic import plexmusic

def _files_from_commas(fnames_string):
    return set(filter(lambda fname: os.path.isfile(fname),
                      map(lambda tok: tok.strip( ), fnames_string.split(',') ) ) )

def _files_from_glob(fnames_string):
    return set(filter(lambda fname: os.path.isfile(fname), glob.glob(fnames_string)))

if __name__=='__main__':
    parser = OptionParser()
    parser.add_option('-f', '--filenames', dest='filenames', action='store', type=str,
                      help = 'Give the list of filenames to put into the Google Music Player.')
    parser.add_option('-P', dest='do_push', action='store_true', default = False,
                      help = 'If chosen, then push Google Music credentials into configuration database.' )
    parser.add_option('-e', dest='email', action='store', type=str,
                      help = 'Google Music email.' )
    parser.add_option('-p', dest='password', action='store', type=str,
                      help = 'Google Music password.' )
    opts, args = parser.parse_args()
    if not opts.do_push:
        if opts.filenames is None:
            raise ValueError("Error, must give a list of file names.")
        if '*' in opts.filenames:
            fnames = _files_from_glob(opts.filenames)
        else:
            fnames = _files_from_commas(opts.filenames)
        plexmusic.upload_to_gmusic(fnames)
    else:
        if any( map(lambda tok: tok is not None, ( opts.email, opts.password ) ) ):
            raise ValueError( "Error, must define both Google Music email and password." )
        plexmusic.save_gmusic_creds( opts.email.strip( ), opts.password.strip( ) )
        
