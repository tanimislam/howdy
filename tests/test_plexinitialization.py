import os, sys, pytest
from . import mainDir

def test_requirements_exist( ):
    resourceFile = os.path.join(
        mainDir, 'resources', 'requirements.txt' )
    assert( os.path.isfile( resourceFile ) )

def test_plex_initialization( ):
    from plexcore import plexinitialization    
    pi = plexinitialization.PlexInitialization( )

