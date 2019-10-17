#!/usr/bin/env python3

import tabulate, os, logging

logger = logging.getLogger( )
logger.setLevel( logging.INFO )

_coverage_dict = {
    'plex_core_cli.py' : True,
    'plex_deluge_console.py' : True,
    'plex_resynclibs.py' : True,
    'plex_store_credentials.py' : False,
    'rsync_subproc.py' : False,
    #
    'plex_config_gui.py' : True,
    'plex_core_gui.py' : False,
    'plex_create_texts.py' : False,
    #
    'get_plextvdb_batch.py' : False,
    'get_tv_tor.py' : False,
    'plex_tvdb_epinfo.py' : False,
    'plex_tvdb_epname.py' : False,
    'plex_tvdb_futureshows.py' : False,
    'plex_tvdb_plots.py' : False,
    #
    'plex_tvdb_totgui.py' : False,
    #
    'get_mov_tor.py' : False,
    #
    'plex_tmdb_totgui.py' : False,
    #
    'plex_music_album.py' : False,
    'plex_music_metafill.py' : False,
    'plex_music_songs.py' : False,
    'upload_to_gmusic.py' : False,
    #
    'plex_email_notif.py' : False,
    #
    'plex_email_gui.py' : False }

def _create_cell( execs ):
    assert( len(set(execs) - set( _coverage_dict ) ) == 0 )
    assert( all(map(lambda exc: exc.endswith( '.py' ), execs ) ) )
    def _make_str( exc ):
        if _coverage_dict[ exc ]:
            return '- :ref:`%s <%s>` |cbox|' % ( exc, '%s_label' % exc )
        else:
            return '- :ref:`%s <%s>`' % ( exc, '%s_label' % exc )
    return '\n'.join( map(_make_str, execs ) )
                         

_table = [
    ( "``plexcore``",
      _create_cell([ 'plex_core_cli.py', 'plex_deluge_console.py', 'plex_resynclibs.py',
                     'plex_store_credentials.py', 'rsync_subproc.py' ]),
      _create_cell([ 'plex_config_gui.py', 'plex_core_gui.py', 'plex_create_texts.py' ] ) ),
    ( "``plextvdb``",
      _create_cell([ 'get_plextvdb_batch.py', 'get_tv_tor.py', 'plex_tvdb_epinfo.py', 'plex_tvdb_epname.py',
                     'plex_tvdb_futureshows.py', 'plex_tvdb_plots.py' ]),
      _create_cell([ 'plex_tvdb_totgui.py' ] ) ),
    ( "``plextmdb``",
      _create_cell([ 'get_mov_tor.py' ]),
      _create_cell([ 'plex_tmdb_totgui.py' ]) ),
    ( "``plexmusic``",
      _create_cell([ 'plex_music_album.py', 'plex_music_metafill.py', 'plex_music_songs.py', 'upload_to_gmusic.py' ]),
      _create_cell([ ]) ),
    ( "``plexemail``",
      _create_cell([ 'plex_email_notif.py' ]), _create_cell([ 'plex_email_gui.py' ]) )
]

print( tabulate.tabulate( _table, [ 'Functionality', 'CLI', 'GUI' ], tablefmt = 'rst' ) )
