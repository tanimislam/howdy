import pytest

def pytest_addoption( parser ):
    parser.addoption('--local', dest='do_local', action='store_true', default = False,
                     help = 'If chosen, then use local Plex URL address.' )
    parser.addoption('--noverify', dest='do_verify', action='store_false', default = True,
                     help = 'If chosen, then do not verify connections.' )
    parser.addoption('--info', dest='do_info', action='store_true', default = False,
                     help = 'If chosen, then run in INFO mode using the logger.')
    parser.addoption('--bypass', dest='do_bypass', action='store_true',
                     default = False, help = 'If chosen, then bypass using YTS Movies.' )

