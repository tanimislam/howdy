import imp, sys, os, pkg_resources, subprocess, shlex

def _choose_install_local( requirements ):
    print('YOU NEED TO INSTALL THESE PACKAGES: %s.' % ' '.join( sorted( requirements ) ) )
    print('I WILL INSTALL THEM INTO YOUR USER DIRECTORY.')
    print('DO YOU ACCEPT?')
    choicedict = { 1 : 'YES, INSTALL THESE PACKAGES.',
                   2 : 'NO, DO NOT INSTALL THESE PACKAGES.' }
    iidx = input( '\n'.join([ 'MAKE OPTION:', '%s\n' %
                              '\n'.join(map(lambda key: '%d: %s' % ( key, choicedict[key] ),
                                            sorted( choicedict.keys( ) ) ) ) ] ) )
    try:
        if iidx not in choicedict:
            print('YOU HAVE CHOSEN NEITHER 1 (YES) OR 2 (NO). EXITING...')
            sys.exit( 0 )
        if iidx == 2:
            print('YOU HAVE CHOSEN NOT TO INSTALL THESE PACKAGES. EXITING...')
            sys.exit( 0 )
    except ValueError:
        print('YOU HAVE CHOSEN NEITHER 1 (YES) OR 2 (NO). EXITING...')
        sys.exit( 0 )
    _install_packages_local( requirements )
    print('FINISHED INSTALLING EVERYTHING. RESTART YOUR APP.')
    sys.exit( 0 )

def _install_packages_local( requirements ):
    import pip
    try:
        pip.main( [ 'install', '--user', '--upgrade' ] + requirements +
                  [ '--trusted-host', 'pypi.python.org' ] )
    except:
        pip.main( [ 'install', '--user', '--upgrade' ] + requirements )

def _choose_install_pip( ):
    print('COULD NOT FIND pip MODULE ON YOUR MACHINE.')
    sortdict = { 1 : 'YES, INSTALL pip.',
                 2 : 'NO, DO NOT INSTALL pip.' }
    iidx = input( '\n'.join([ 'MAKE OPTION:', '%s\n' %
                              '\n'.join(map(lambda key: '%d: %s' % ( key, sortdict[key] ),
                                            sorted( sortdict.keys( ) ) ) ) ] ) )
    try:
        # iidx = int( iidx.strip( ) )
        if iidx not in sortdict:
            print('ERROR, DID NOT CHOOSE 1 (YES) OR 2 (NO). EXITING...')
            sys.exit( 0 )
        if iidx == 1:
            _bootout_pip( )
    except ValueError:
        print('ERROR, DID NOT CHOOSE 1 (YES) OR 2 (NO). EXITING...')
        sys.exit( 0 )

def _bootout_pip( ):
    import shutil, tempfile
    import urllib, pkgutil
    #
    tmpdir0 = tempfile.mkdtemp( )
    with open( os.path.join( tmpdir0, 'get_pip.py' ), 'wb' ) as openfile:
        openfile.write( urllib.urlopen(
            'https://bootstrap.pypa.io/get-pip.py' ).read( ) )
    sys.path.append( tmpdir0 )
    from get_pip import b85decode, DATA
    #
    tmpdir = tempfile.mkdtemp()
    pip_zip = os.path.join(tmpdir, "pip.zip")
    with open(pip_zip, "wb") as fp:
        fp.write(b85decode(DATA.replace(b"\n", b"")))
    shutil.rmtree( tmpdir0 )

    val = sys.path.pop( )
    sys.path.append( pip_zip )
    import pip

    cert_path = os.path.join(tmpdir, "cacert.pem")
    with open( cert_path, 'wb' ) as cert:
        cert.write(pkgutil.get_data("pip._vendor.requests", "cacert.pem"))
    
    #
    ## also put other packages in there..
    pip.main([ 'install', '--user', '--upgrade', '--cert', cert_path,
               'pip', 'setuptools', 'wheel' ])
    shutil.rmtree( tmpdir )
    print('INSTALLED pip AND NECESSARY DEPENDENCIES.')
    print('RERUN THIS APP TO INSTALL REST OF DEPENDENCIES.')
    sys.exit( 0 )

class PlexInitialization( object ):
    class __PlexInitialization( object ):
        def __init__( self ):
            #
            ## first see if we have PyQt4
            #try:
            #    val = imp.find_module( 'PyQt4' )
            #except ImportError:
            #    print('ERROR, YOU NEED TO INSTALL PyQt4 ON YOUR MACHINE.')
            #    sys.exit( 0 )
            
            #
            ## first see if we have pip on this machine
            try:
                val = imp.find_module( 'pip' )
            except ImportError:
                _choose_install_pip( )
            
            #
            ## now go through all the dependencies in the requirements packages
            mainDir = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
            reqs = sorted( set( map(lambda line: line.replace('\n', '').strip(),
                                    open( os.path.join( mainDir, 'resources',
                                                        'requirements.txt' ), 'r' ).readlines( ) ) ) )
            reqs_remain = [ ]
            for req in reqs:
                try: 
                    val = imp.find_module( req )
                except ImportError: 
                    try:
                        val = pkg_resources.require([ req ])
                    except pkg_resources.DistributionNotFound:
                        reqs_remain.append( req )
            #
            if len( reqs_remain ) != 0:
                _choose_install_local( reqs_remain )
    
    _instance = None

    def __new__( cls ):
        if not PlexInitialization._instance:
            PlexInitialization._instance = PlexInitialization.__PlexInitialization( )
        return PlexInitialization._instance

if __name__=='__main__':
    os.chdir( os.path.dirname( __file__ ) )
    pi = PlexInitialization( )
