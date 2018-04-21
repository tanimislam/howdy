#!/usr/bin/env python3

import os, glob
from optparse import OptionParser
from plexmusic import plexmusic

def _files_from_commas(fnames_string):
    return set(filter(lambda fname: os.path.isfile(fname), [ tok.strip() for tok in fnames_string.split(',') ] ) )

def _files_from_glob(fnames_string):
    return set(filter(lambda fname: os.path.isfile(fname), glob.glob(fnames_string)))

if __name__=='__main__':
    parser = OptionParser()
    parser.add_option('--filenames', dest='filenames', action='store', type=str,
                      help = 'Give the list of filenames to put into the Google Music Player.')
    opts, args = parser.parse_args()
    if opts.filenames is None:
        raise ValueError("Error, must give a list of file names.")
    if '*' in opts.filenames:
        fnames = _files_from_glob(opts.filenames)
    else:
        fnames = _files_from_commas(opts.filenames)
    plexmusic.upload_to_gmusic(fnames)
