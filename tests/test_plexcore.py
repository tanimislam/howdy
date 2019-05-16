import os, sys, pytest, logging, warnings
from plexcore import plexcore

def get_token_fullURL_standalone( ):
    fullURL, token = plexcore.checkServerCredentials(
        doLocal = False, verify = True )
    return fullURL, token
    
@pytest.fixture(scope="module")
def get_token_fullURL( ):
    logging.basicConfig( level = logging.INFO )
    print( 'getting fullURL and token, nonLocal and verify SSL' )
    fullURL, token = plexcore.checkServerCredentials( doLocal = False, verify = True )
    yield fullURL, token
    print( 'after tests, finished giving out tokens, fullURL = %s, token = %s.' % (
        fullURL, token ) )

@pytest.fixture(scope="module")
def get_libraries_dict( get_token_fullURL ):
    fullURL, token = get_token_fullURL
    libraries_dict = plexcore.get_libraries(
        fullURL = fullURL, token = token, do_full = True )
    print( 'here are the libraries on the PLEX server:')
    for key in sorted( libraries_dict ):
        print( '%d: %s, %s' % ( key, libraries_dict[ key ][ 0 ],
                                libraries_dict[ key ][ 1 ] ) )
    yield libraries_dict

@pytest.mark.dependency
def test_have_libraries( get_libraries_dict ):
    libraries_dict = get_libraries_dict
    assert( libraries_dict is not None )

@pytest.mark.dependency(depends=["test_have_libraries"])
def test_have_tv( get_token_fullURL, get_libraries_dict ):
    fullURL, token = get_token_fullURL
    libraries_dict = get_libraries_dict
    key = list(filter(lambda k: libraries_dict[k][-1] == 'show',
                      libraries_dict))
    assert( len( key ) != 0 )
    key = max( key )
    library_name = libraries_dict[ key ][ 0 ]
    tvdata = plexcore.get_library_data( library_name, token = token, fullURL = fullURL )
    assert( tvdata is not None )

@pytest.mark.dependency(depends=["test_have_libraries"])
def test_have_movies( get_token_fullURL, get_libraries_dict ):
    fullURL, token = get_token_fullURL
    libraries_dict = get_libraries_dict
    key = list(filter(lambda k: libraries_dict[k][-1] == 'movie',
                      libraries_dict))
    assert( len( key ) != 0 )
    key = max( key )
    library_name = libraries_dict[ key ][ 0 ]
    moviedata = plexcore.get_library_data( library_name, token = token, fullURL = fullURL )
    assert( moviedata is not None )

@pytest.mark.dependency(depends=["test_have_libraries"])
def test_have_music( get_token_fullURL, get_libraries_dict ):
    fullURL, token = get_token_fullURL
    libraries_dict = get_libraries_dict
    key = list(filter(lambda k: libraries_dict[k][-1] == 'artist',
                      libraries_dict))
    assert( len( key ) != 0 )
    key = min( key )
    library_name = libraries_dict[ key ][ 0 ]
    musicdata = plexcore.get_library_data( library_name, token = token, fullURL = fullURL )
    assert( musicdata is not None )
