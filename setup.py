from setuptools import setup, find_packages
#
## requirements are in "requirements.txt"
reqs = sorted(set(map(lambda line: line.strip(),
                      filter(lambda line: len( line.strip( ) ) != 0 and not line.strip( ).startswith('git+'),
                             open( 'requirements.txt', 'r').readlines()))))
dependency_links = sorted(set(map(lambda line: line.strip( ),
                                  filter(lambda line: line.strip( ).startswith('git+'),
                                         open( 'requirements.txt', 'r' ).readlines( ) ) ) ) )

setup(
    name = 'plexstuff',
    version = '1.0',
    #
    ## following advice on find_packages excluding tests from https://setuptools.readthedocs.io/en/latest/setuptools.html#using-find-packages
    packages = find_packages( exclude = ["*.tests", "*.tests.*", "tests" ] ),
    # package_dir = { "": "nprstuff" },
    url = 'https://github.com/tanimislam/plexstuff',
    license = 'BSD-2-Clause',
    author = 'Tanim Islam',
    author_email = 'tanim.islam@gmail.com',
    description = 'This is a collection of a bunch of tools, and APIs, to access media within my Plex server.',
    #
    ## classification: where in package space does "nprstuff live"?
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
            # plextmdb stuff
            'get_mov_tor = plexstuff.plextmdb.cli.get_mov_tor:main',
            'plex_tmdb_totgui = plexstuff.plextmdb.gui.plex_tmdb_totgui:main',
            # plexcore stuff
            'plex_core_cli = plexstuff.plexcore.cli.plex_core_cli:main',
            'plex_deluge_console = plexstuff.plexcore.cli.plex_deluge_console:main',
            'plex_resynclibs = plexstuff.plexcore.cli.plex_resynclibs:main',
            'plex_store_credentials = plexstuff.plexcore.cli.plex_store_credentials:main',
            'rsync_subproc = plexstuff.plexcore.cli.rsync_subproc:main',
            'plex_config_gui = plexstuff.plexcore.gui.plex_config_gui:main',
            'plex_core_gui = plexstuff.plexcore.gui.plex_core_gui:main',
            'plex_create_texts = plexstuff.plexcore.gui.plex_create_texts:main',
            # plexemail stuff
            'plex_email_notif = plexstuff.plexemail.cli.plex_email_notif:main',
            'plex_email_gui = plexstuff.plexemail.gui.plex_email_gui:main',
            # plexmusic stuff
            'plex_music_album = plexstuff.plexmusic.cli.plex_music_album:main',
            'plex_music_metafill = plexstuff.plexmusic.cli.plex_music_metafill:main',
            'plex_music_songs = plexstuff.plexmusic.cli.plex_music_songs:main',
            'upload_to_gmusic = plexstuff.plexmusic.cli.upload_to_gmusic:main',
            # plextvdb stuff
            'get_plextvdb_batch = plexstuff.plextvdb.cli.get_plextvdb_batch:main',
            'get_tv_tor = plexstuff.plextvdb.cli.get_tv_tor:main',
            'plex_tvdb_epinfo = plexstuff.plextvdb.cli.plex_tvdb_epinfo:main',
            'plex_tvdb_epname = plexstuff.plextvdb.cli.plex_tvdb_epname:main',
            'plex_tvdb_futureshows = plexstuff.plextvdb.cli.plex_tvdb_futureshows:main',
            'plex_tvdb_plots = plexstuff.plextvdb.cli.plex_tvdb_plots:main',
            'plex_tvdb_gui = plexstuff.plextvdb.gui.plex_tvdb_gui:main',
            ]
    },
    #entry_points = {
    #     'console_scripts' : [
    #         "music_to_m4a = nprstuff.cli.music_to_m4a:_main",
    #         "freshair = nprstuff.cli.freshair:_freshair",
    #         "freshair_crontab = nprstuff.cli.freshair:_freshair_crontab",
    #         "freshair_by_year = nprstuff.cli.freshair:_freshair_by_year",
    #         "freshair_fix_crontab = nprstuff.cli.freshair:_freshair_fix_crontab",
    #         "github_md_2_html = nprstuff.cli.github_md_2_html:_main",
    #         "autoCropImage = nprstuff.cli.autoCropImage:_main",
    #         "convertImage = nprstuff.cli.convertImage:_main",
    #         "changedates = nprstuff.cli.changedates:_main",
    #         "display = nprstuff.cli.display:_main",
    #         "download_surahs = nprstuff.cli.download_surahs:_main",
    #         "imageFromURL = nprstuff.cli.imageFromURL:_main",
    #         "thisamericanlife = nprstuff.cli.thisamericanlife:_main",
    #         "thisamericanlife_crontab = nprstuff.core.thisamericanlife:thisamericanlife_crontab",
    #         "waitwait = nprstuff.cli.waitwait:_waitwait",
    #         "waitwait_crontab = nprstuff.core.waitwait:waitwait_crontab",
    #         "waitwait_by_year = nprstuff.cli.waitwait:_waitwait_by_year",
    #         #
    #         ## now gui stuff
    #         "nprstuff_gui_maingui = nprstuff.cli.gui:_maingui",
    #         "nprstuff_gui_lightspeed = nprstuff.cli.gui:_lightspeed",
    #         "nprstuff_gui_medium = nprstuff.cli.gui:_medium",
    #         "nprstuff_gui_newyorker = nprstuff.cli.gui:_newyorker",
    #         "nprstuff_gui_nytimes = nprstuff.cli.gui:_nytimes",
    #         "nprstuff_gui_vqronline = nprstuff.cli.gui:_vqronline",
    #         #
    #         ## gui2 stuff, superseded by what's in plexstuff project
    #         "nprstuff_gui2_loginwindow = nprstuff.cli.gui2:_loginwindow",
    #         "nprstuff_gui2_mainapp = nprstuff.cli.gui2:_mainapp",
    #     ]
    # },
    #
    ## big fatass WTF because setuptools is unclear about whether I can give a directory that can then be resolved by
    ## other resources
    ## here is the link to the terrible undocumented documentation: https://setuptools.readthedocs.io/en/latest/setuptools.html#including-data-files
    package_data = {
        "plexstuff" : [
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
