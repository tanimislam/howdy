import imp, sys, os, pkg_resources, logging
import subprocess, shlex, glob, socket
from distutils.spawn import find_executable

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
        iidx = int( iidx.strip( ) )
        if iidx not in choicedict:
            print( 'YOU HAVE CHOSEN NEITHER 1 (YES) OR 2 (NO). EXITING...' )
            sys.exit( 0 )
        if iidx == 2:
            print( 'YOU HAVE CHOSEN NOT TO INSTALL THESE PACKAGES. EXITING...' )
            sys.exit( 0 )
    except ValueError:
        print( 'YOU HAVE CHOSEN NEITHER 1 (YES) OR 2 (NO). EXITING...' )
        sys.exit( 0 )
    _install_packages_local( requirements )
    print( 'FINISHED INSTALLING EVERYTHING. RESTART YOUR APP.' )
    sys.exit( 0 )

def _install_packages_local( requirements ):
    try:
        from pip._internal.main import main
    except:
        try: from pip._internal import main
        except: raise ValueError("could not find main method in pip." )
    try:
        main( [ 'install', '--user', '--upgrade' ] + requirements +
              [ '--trusted-host', 'pypi.python.org' ] +
              [ '--trusted-host', 'pypi.org' ] +
              [ '--trusted-host', 'files.pythonhosted.org' ] )
    except:
        main( [ 'install', '--user', '--upgrade' ] + requirements )
        
def _choose_install_pip( ):
    print('COULD NOT FIND pip MODULE ON YOUR MACHINE.')
    sortdict = { 1 : 'YES, INSTALL pip.',
                 2 : 'NO, DO NOT INSTALL pip.' }
    iidx = input( '\n'.join([ 'MAKE OPTION:', '%s\n' %
                              '\n'.join(map(lambda key: '%d: %s' % ( key, sortdict[key] ),
                                            sorted( sortdict.keys( ) ) ) ) ] ) )
    try:
        iidx = int( iidx.strip( ) )
        if iidx not in sortdict:
            print('ERROR, DID NOT CHOOSE 1 (YES) OR 2 (NO). EXITING...')
            sys.exit( 0 )
        if iidx == 1: _bootout_pip( )
    except ValueError:
        print('ERROR, DID NOT CHOOSE 1 (YES) OR 2 (NO). EXITING...')
        sys.exit( 0 )

def _bootout_pip( ):
    import shutil, tempfile, pkgutil
    from urllib.request import urlopen
    from pip._internal import main
    #
    tmpdir0 = tempfile.mkdtemp( )
    with open( os.path.join( tmpdir0, 'get_pip.py' ), 'wb' ) as openfile:
        openfile.write( urlopen(
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
    main([ 'install', '--user', '--upgrade', '--cert', cert_path,
           'pip', 'setuptools', 'wheel' ])
    shutil.rmtree( tmpdir )
    print('INSTALLED pip AND NECESSARY DEPENDENCIES.')
    print('RERUN THIS APP TO INSTALL REST OF DEPENDENCIES.')
    sys.exit( 0 )

class PlexInitialization( object ):
    """
    The singleton class that, once called, initializes to perform the following checks:

    1. Force Python to use ipv4 connections.

    2. are PyQt4, sshpass, and pandoc installed on the machine? If not, then exits.

    3. If they are installed, then installs missing Python packages and modules as enumerated in the ``resources/requirements.txt`` resource file.
    
    """

    version = 1.0
    
    class __PlexInitialization( object ):
        def __init__( self ):
            #
            ## I have to do this in order to explicitly use ipv4 in instances where ipv6 is used but does not work.
            logging.info('HAVE TO DO THIS IN ORDER TO USE IPV4 WHEN IPV6 DOES NOT WORK')
            _old_getaddrinfo = socket.getaddrinfo
            def _new_getaddrinfo(*args, **kwargs):
                responses = _old_getaddrinfo(*args, **kwargs)
                return [
                    response
                    for response in responses
                if response[0] == socket.AF_INET]
            socket.getaddrinfo = _new_getaddrinfo
            
            if not os.environ.get( 'READTHEDOCS' ): # more and more contortions to get read the docs to work...
                #
                ## first see if we have PyQt4
                try:
                    val = imp.find_module( 'PyQt4' )
                    from PyQt4.QtGui import QFontDatabase
                except ImportError:
                    print( 'ERROR, YOU NEED TO INSTALL PyQt4 ON YOUR MACHINE.' )
                    sys.exit( 0 )
                #
                ## now see if we have sshpass
                sshpass = find_executable( 'sshpass' )
                if sshpass is None:
                    print( 'ERROR, YOU NEED TO INSTALL sshpass ON YOUR MACHINE.' )
                    sys.exit( 0 )
                #
                ## now see if we have pandoc
                pandoc = find_executable( 'pandoc' )
                if pandoc is None:
                    print( 'ERROR, YOU NEED TO INSTALL pandoc ON YOUR MACHINE.' )
                    sys.exit( 0 )
            
            #
            ## first see if we have pip on this machine, install if don't
            try: val = imp.find_module( 'pip' )
            except ImportError: _choose_install_pip( )
            
            #
            ## now go through all the dependencies in the requirements packages
            mainDir = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
            reqs = sorted( set( map(lambda line: line.replace('\n', '').strip(),
                                    open( os.path.join( mainDir, 'resources',
                                                        'requirements.txt' ), 'r' ).readlines( ) ) ) )
            #
            ## TODO -- ignore any requirements that start with git+
            ## WILL HAVE TO FIGURE OUT HOW TO GET THE REQUIREMENTS INFORMATION
            ## 1. what package name corresponds to git module (take git+https:// URL -- how to get the package name)?
            ## 2. may have to make YET ANOTHER table in the database called, "here is row where download git+https://. value is package name
            ## 3. OR, contract is the standard "here is a git/svn/etc repository containing the python package that pip tries to install."
            ##   a. Meaning, contains EGG info as in git+https://<GIT-URL>#egg=<package-name>, for example git+https://github.com/sphinx-contrib/youtube.git#egg=sphinxcontrib.youtube
            ##   b. package name comes after reqs = sorted(filter(lambda req: not req.startswith('git+'), reqs ) )
            ##   c. of course, the thing installed with git+https://<GIT-URL> MUST have <package-name>, or process will not work.
            reqs_remain = [ ]
            for req in reqs:
                if not req.startswith( 'git+' ): req_act = req
                else:
                    req_act_string = req.split('#')[-1].strip( )
                    if not req_act_string.lower( ).startswith('egg='):
                        raise ValueError("Error, requirement line = %s is missing an #egg= definition")
                    req_act = req_act_string.split('=')[1].strip( )
                #
                ## first use imp.find_module to find module
                try:
                    val = imp.find_module( req_act )
                    continue
                except ImportError:
                    pass
                #
                ## otherwise use pkg_resources.require to find module
                try:
                    val = pkg_resources.require([ req_act ])
                    continue
                except pkg_resources.DistributionNotFound as err:
                    reqs_remain.append( req )
            #
            if len( reqs_remain ) != 0:
                _choose_install_local( reqs_remain )

    _instance = None

    def __new__( cls ):
        if not PlexInitialization._instance:
            PlexInitialization._instance = PlexInitialization.__PlexInitialization( )
        return PlexInitialization._instance
