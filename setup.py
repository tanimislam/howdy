import os, sys
from setuptools import setup, find_packages
from distutils.spawn import find_executable
#
## requirements are in "requirements.txt"

#
## ones that live on PyPI
reqs = sorted(set(map(lambda line: line.strip(),
                      filter(lambda line: len( line.strip( ) ) != 0 and not line.strip( ).startswith('git+'),
                             open( 'requirements.txt', 'r').readlines()))))

#
## git+https modules
dependency_links = sorted(set(map(lambda line: line.strip( ),
                                  filter(lambda line: line.strip( ).startswith('git+'),
                                         open( 'requirements.txt', 'r' ).readlines( ) ) ) ) )
#
## need pandoc
if find_executable( 'pandoc' ) is None:
    print( "Error, cannot find pandoc executable. Exiting..." )
    sys.exit( 0 )

#
## need sshpass
if find_executable( 'sshpass' ) is None:
    print( "Error, cannot find sshpass executable. Exiting..." )
    sys.exit( 0 )

setup(
    name = 'howdy',
    version = '1.0',
    #
    ## following advice on find_packages excluding tests from https://setuptools.readthedocs.io/en/latest/setuptools.html#using-find-packages
    packages = find_packages( exclude = ["*.tests", "*.tests.*", "tests" ] ),
    # package_dir = { "": "nprstuff" },
    url = 'https://github.com/tanimislam/howdy',
    license = 'BSD-2-Clause',
    author = 'Tanim Islam',
    author_email = 'tanim.islam@gmail.com',
    description = 'This is a collection of a bunch of tools, and APIs, to access media within my Plex server.',
    #
    ## classification: where in package space does "howdy live"?
    ## follow (poorly) advice I infer from https://blog.ionelmc.ro/2014/05/25/python-packaging/#the-setup-script
    classifiers=[
    # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX',
        'Environment :: Console',
        'Environment :: X11 Applications :: Qt',
        'Programming Language :: Python :: 3',
    # uncomment if you test on these interpreters:
    # 'Programming Language :: Python :: Implementation :: IronPython',
    # 'Programming Language :: Python :: Implementation :: Jython',
    # 'Programming Language :: Python :: Implementation :: Stackless',
        'Topic :: Utilities',
        'Topic :: Multimedia',
    ],
    #
    ## requirements
    install_requires = reqs,
    dependency_links = dependency_links,
    python_requires = '>=3',
    #
    ## the executables I am creating
    entry_points = {
        'console_scripts' : [
            # movie stuff
            'get_mov_tor = howdy.movie.cli.get_mov_tor:main',
            'howdy_movie_totgui = howdy.movie.gui.howdy_tmdb_totgui:main',
            # plexcore stuff
            ## cli
            'howdy_core_cli = howdy.plexcore.cli.howdy_core_cli:main',
            'howdy_deluge_console = howdy.plexcore.cli.howdy_deluge_console:main',
            'howdy_resynclibs = howdy.plexcore.cli.howdy_resynclibs:main',
            'howdy_store_credentials = howdy.plexcore.cli.howdy_store_credentials:main',
            'rsync_subproc = howdy.plexcore.cli.rsync_subproc:main',
            'get_book_tor = howdy.plexcore.cli.get_book_tor:main',
            ## gui
            'howdy_config_gui = howdy.plexcore.gui.howdy_config_gui:main',
            'howdy_core_gui = howdy.plexcore.gui.howdy_core_gui:main',
            'howdy_create_texts = howdy.plexcore.gui.howdy_create_texts:main',
            # email stuff
            'howdy_email_notif = howdy.email.cli.howdy_email_notif:main',
            'howdy_email_gui = howdy.email.gui.howdy_email_gui:main',
            # music stuff
            'howdy_music_album = howdy.music.cli.howdy_music_album:main',
            'howdy_music_metafill = howdy.music.cli.howdy_music_metafill:main',
            'howdy_music_songs = howdy.music.cli.howdy_music_songs:main',
            'upload_to_gmusic = howdy.music.cli.upload_to_gmusic:main',
            # tv stuff
            ## cli
            'get_tv_batch = howdy.tv.cli.get_tv_batch:main',
            'get_tv_tor = howdy.tv.cli.get_tv_tor:main',
            'howdy_tv_epinfo = howdy.tv.cli.howdy_tv_epinfo:main',
            'howdy_tv_epname = howdy.tv.cli.howdy_tv_epname:main',
            'howdy_tv_futureshows = howdy.tv.cli.howdy_tv_futureshows:main',
            'howdy_tv_plots = howdy.tv.cli.howdy_tv_plots:main',
            'howdy_tv_excludes = howdy.tv.cli.howdy_tv_excludes:main',
            ## gui
            'howdy_tv_gui = howdy.tv.gui.howdy_tv_gui:main',
            ]
    },
    #
    ## big fatass WTF because setuptools is unclear about whether I can give a directory that can then be resolved by
    ## other resources
    ## here is the link to the terrible undocumented documentation: https://setuptools.readthedocs.io/en/latest/setuptools.html#including-data-files
    package_data = {
        "howdy" : [
            "resources/*.ttf",
            "resources/*.tex",
            "resources/*.qss",
            "resources/*.json",
            "resources/*.tex",
            "resources/*.html",
            "resources/icons/*.png",
            "resources/icons/*.key" ]
    }
)
