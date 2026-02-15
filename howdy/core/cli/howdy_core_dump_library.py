import os, sys, time, datetime, yaml, gzip, warnings, logging, tabulate
from multiprocessing import cpu_count
from howdy.core import core
from bs4.builder import XMLParsedAsHTMLWarning
from argparse import ArgumentParser
from nprstuff import logging_dict, nprstuff_logger as logger

warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)

def get_server_listing( ):
    _, token = core.checkServerCredentials( doLocal = True )
    all_servers = core.get_all_servers( token )
    #
    ## now make a printout
    all_data = list(map(lambda servername: (
        servername,
        all_servers[ servername ][ 'owned' ] ), sorted( all_servers ) ) )
    print( 'FOUND %d PLEX SERVERS TO WHICH YOU HAVE ACCESS.' % ( len( all_servers ) ) )
    print( '---' )
    print( '%s\n' % tabulate.tabulate(
        all_data, headers = [ 'PLEX SERVER NAME', 'OWNED' ] ) )

def get_server_libraries( servername ):
    _, token = core.checkServerCredentials( doLocal = True )
    all_servers = core.get_all_servers( token )
    assert( servername in all_servers )
    server_access = all_servers[ servername ]
    #
    library_dict = core.get_libraries(
        server_access[ 'access token' ],
        fullURL = server_access[ 'url' ],
        do_full = True )
    print( 'found %d libraries in PLEX SERVER = %s.' % (
        len( library_dict ), servername ) )
    print( '---' )
    library_data = list(map(lambda key: ( library_dict[ key ][ 0 ], library_dict[ key ][ 1 ] ),
                            library_dict ) )
    print( '%s\n' % tabulate.tabulate( library_data, headers = [ 'LIBRARY NAME', 'TYPE' ] ) )

def get_server_data( servername, library_name ):
    time0 = time.perf_counter( )
    dnow = datetime.datetime.now( ).date( )
    _, token = core.checkServerCredentials( doLocal = True )
    all_servers = core.get_all_servers( token )
    assert( servername in all_servers )
    server_access = all_servers[ servername ]
    #
    library_dict = core.get_libraries(
        server_access[ 'access token' ],
        fullURL = server_access[ 'url' ],
        do_full = True )
    assert( library_name in set(map(lambda key: library_dict[key][0], library_dict ) ) )
    libdata = core.get_library_data(
        library_name,
        token = server_access[ 'access token' ],
        fullURL = server_access[ 'url' ],
        num_threads = 2 * cpu_count( ) )
    time_to_collect = time.perf_counter( ) - time0
    logging.info( 'took %0.3f seconds to get %s LIBRARY DATA on %s PLEX SERVER.' % (
        time_to_collect, library_name, servername ) )
    return {
        'library data'          : libdata,
        'date snapshot created' : dnow.strftime('%Y%m%d' ),
        'time to collect (s)'   : time_to_collect,
        'server'                : servername,
        'library'               : library_name,
    }

def main( ):
    parser = ArgumentParser( )
    parser.add_argument(
        '--info', dest='do_info', action='store_true', default = False,
        help = 'If chosen, then print out INFO level logging statements.' )
    #
    subparsers = parser.add_subparsers(
        help = '\n'.join([
            'Choose one of three options:',
            '(S) shows the Plex servers to which you have access;',
            '(L) given a chosen Plex server, shows the libraries in that Plex server;',
            '(D) dumps the plex server library into a YAML gzipped file.' ] ),
        dest = 'choose_option' )
    #
    ## show plex servers
    parser_showservers = subparsers.add_parser( 'S', help = 'Just show the Plex servers to which you have access.' )
    #
    ## show the libraries on a specific plex server
    parser_showlibraries = subparsers.add_parser( 'L', help = 'Show the accessible libraries on a chosen Plex server to which you have access.' )
    parser_showlibraries.add_argument( '-s', '--server', dest = 'showlibraries_server', type = str, action = 'store', required = True,
                                       help = 'The name of the Plex server.' )
    #
    ## dump the libraries to a file
    parser_dumplibrary = subparsers.add_parser( 'D', help = 'Dump the library data, from a Plex server, into a YAML gzipped file.' )
    parser_dumplibrary.add_argument( '-s', '--server', dest = 'dumplibrary_server', type = str, action = 'store', required = True,
                                     help = 'Name of the Plex server to dump library data.' )
    parser_dumplibrary.add_argument( '-L', '--library', dest = 'dumplibrary_library', type = str, action = 'store', required = True,
                                     help = 'Name of the Plex library, on the Plex server, to dump into a YAML gzipped file.' )
    parser_dumplibrary.add_argument( '-Y', '--yaml', dest = 'dumplibrary_yaml_prefix', type = str, action = 'store', required = True,
                                     help = 'Name of the prefix of the YAML gzipped file containing the library dump.' )
    #
    args = parser.parse_args( )
    logger = logging.getLogger( )
    if args.do_info: logger.setLevel( logging.INFO )
    #
    ## just show the servers
    if args.choose_option == 'S':
        get_server_listing( )
        return
    #
    ## library info
    if args.choose_option == 'L':
        servername = args.showlibraries_server
        get_server_libraries( servername )
        return
    #
    ## dump data
    if args.choose_option == 'D':
        servername = args.dumplibrary_server
        library    = args.dumplibrary_library
        yamldump   = args.dumplibrary_yaml_prefix
        dumpdata   = get_server_data(
            servername, library )
        dtnow_str  = dumpdata[ 'date snapshot created' ]
        yaml.safe_dump( dumpdata, gzip.open( '%s_%s.yml.gz' % ( yamldump, dtnow_str ), 'wt' ) )
