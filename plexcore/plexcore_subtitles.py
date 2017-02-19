"""
This module uses the SubDB API to get subtitles
"""
import os, sys, numpy, hashlib

def get_hash(filename):
    assert( os.path.isfile( filename ) )
    readsize = 64 * 1024
    with open( filename, 'rb') as openfile:
        size = os.path.getsize( name )
        data = openfile.read( readsize )
        openfile.seek( -readsize, os.SEEK_END )
        data += openfile.read( readsize )
    return hashlib.md5(data).hexdigest( )
