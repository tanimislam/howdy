#!/usr/bin/env python3

import tabulate, os

def _create_cell( execs ):
    assert( all(map(lambda exc: exc.endswith( '.py' ), execs ) ) )
    return '\n'.join(
        map(lambda exc: '- :ref:`%s <%s>`' % ( exc, '%s_label' % exc ), execs ) )
                         

_table = [
    ( "``plexcore``",
      _create_cell([ 'plex_core_cli.py', 'plex_deluge_console.py', 'plex_resynclibs.py', 'plex_store_credentials.py', 'rsync_subproc.py' ]),
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

      
      
        
