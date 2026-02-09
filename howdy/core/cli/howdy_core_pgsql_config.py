import signal
from howdy import signal_handler
signal.signal( signal.SIGINT, signal_handler )
#
import os, sys, tabulate, logging
from howdy import howdy_pgsql_config
from argparse import ArgumentParser

def main( ):
    parser = ArgumentParser( )
    parser.add_argument(
        '-u', '--username', dest = 'username', type = str, action = 'store',
        help = 'The username setting to access the PostgreSQL config database.' )
    parser.add_argument(
        '-H', '--hostname', dest = 'hostname', type = str, action = 'store',
        help = 'The hostname setting to access the PostgreSQL config database.' )
    parser.add_argument(
        '-p', '--port', dest = 'port', type = int, action = 'store',
        help = 'The port setting to access the PostgreSQL config database.' )
    parser.add_argument(
        '-d', '--database', dest = 'database', type = str, action = 'store', 
        help = 'The name of the PostgreSQL config database that stores all the Howdy configuration.' )
    parser.add_argument(
        '-P', '--password', dest = 'password', type = str, action = 'store',
        help = 'The password setting to access the PostgreSQL config database.' )
    #
    args = parser.parse_args( )
    #
    howdy_pgsql_config.setConfig(
        howdy_pgsql_username = args.username,
        howdy_pgsql_password = args.password,
        howdy_pgsql_hostname = args.hostname,
        howdy_pgsql_port     = args.port,
        howdy_pgsql_database = args.database )
