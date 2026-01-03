import signal
from howdy import signal_handler
signal.signal( signal.SIGINT, signal_handler )
from argparse import ArgumentParser
import requests, tabulate
#
from howdy.core import core, session
from howdy.email import get_email_contacts_dict

def _print_format_names( plex_emails, header_name = 'PLEX' ):
    print( '\n'.join([
                      'YOU HAVE %d %s FRIENDS' % ( len( plex_emails ), header_name.upper( ) ),
                      '---' ] ) )
    if len( plex_emails ) == 0: return
    email_contacts_dict = get_email_contacts_dict( plex_emails )
    num_with_names = len( list( filter( lambda tup: tup[0] is not None, email_contacts_dict ) ) )
    num_wo_names = len( email_contacts_dict ) - num_with_names
    print ('\n'.join([ '%d HAVE FOUND NAMES, %d DO NOT HAVE FOUND NAMES' % (
        num_with_names, num_wo_names ), '' ]) )
    if num_with_names != 0:
        if num_with_names == 1:
            print( '\n'.join([ '%d %s FRIEND WITH NAMES' % ( num_with_names, header_name.upper( ) ), '' ]))
        else:
            print( '\n'.join([ '%d %s FRIENDS WITH NAMES' % ( num_with_names, header_name.upper( ) ), '' ]))
        #
        names_emails = sorted(filter(lambda tup: tup[0] is not None, email_contacts_dict),
                              key = lambda tup: tup[0].split( )[-1] )
        print( '%s\n' % tabulate.tabulate( names_emails, headers = [ 'NAME', 'EMAIL' ] ) )
        if num_wo_names != 0: print('\n')
        
    if num_wo_names != 0:
        if num_wo_names == 1:
            print( '\n'.join([ '%d %s FRIEND WITHOUT NAMES' % ( num_wo_names, header_name.upper( ) ), '' ]))
        else:
            print( '\n'.join([ '%d %s FRIENDS WITHOUT NAMES' % ( num_wo_names, header_name.upper( ) ), '' ]))
        emails_only = sorted(map(lambda tup: tup[1], filter(lambda tup: tup[0] is None, email_contacts_dict ) ) )
        print( '%s\n' % tabulate.tabulate(list(map(lambda eml: [ eml ], emails_only)), headers = [ 'EMAIL' ] ) )

def main( ):
    parser = ArgumentParser( )
    parser.add_argument(
        '-u', '--username', dest='username', type=str, action='store',
        help = 'Your plex username.' )
    parser.add_argument(
        '-p', '--password', dest='password', type=str, action='store',
        help = 'Your plex password.' )
    parser.add_argument(
        '-C', '--choice', dest='choice', action='store', type=str, choices = [ 'friends', 'mappedfriends' ], default = 'friends',
        help = ' '.join([
            'Two choices on what to visualize. If choose "friends", then get a list of guests of your Plex server.',
            'If choose "mappedfriends", get list of guests with mapping, of your Plex server.'
            'Default is "friends".' ] ) )
    #
    subparsers = parser.add_subparsers(
        help = 'Optionally choose to add mapping.',
        dest = 'choose_option' )
    parser_addmapping = subparsers.add_parser( 'addmapping',    help = 'Add extra friends from Plex friends.' )
    parser_addmapping.add_argument(
        '-G', '--guestemail', dest='parser_addmapping_guest_email',
        metavar = 'GUEST_EMAIL', action = 'store', type=str, required = True, help = 'Name of the Plex guest email.' )
    parser_addmapping.add_argument(
        '-N', '--newemails', dest='parser_addmapping_new_emails', metavar = 'NEW_EMAILS', action = 'store', nargs = '+', default = [ ],
        help = 'Name of the new emails associated with the Plex guest email.')
    parser_addmapping.add_argument(
        '-R', '--replace_existing', dest='parser_addmapping_do_replace_existing',
        action = 'store_true', default = False,
        help = 'If chosen, replace existing email to send newsletter.')
    #
    args = parser.parse_args( )
    if any(map(lambda tok: tok is None, ( args.username, args.password ) ) ):
        var = core.checkServerCredentials(
            doLocal = False, verify = False, checkWorkingServer = False )
        # var = core.checkServerCredentials( doLocal = True ) # seems to now only work with local
        if var is None:
            print( 'COULD NOT FIND PLEX SERVER CREDENTIALS OR INVALID USERNAME/PASSWORD COMBO' )
            return
        fullURL, token = var
    else:
        assert(all(map(lambda tok: tok is not None, ( args.username, args.password ) ) ) ), "must have both username and password"
        token = core.getTokenForUsernamePassword( args.username, args.password, verify = False )
        if token is None:
            print( 'INVALID USERNAME/PASSWORD COMBO.' )
            return
    
    if args.choose_option == 'addmapping':
        plex_emails = sorted( set( core.get_email_contacts( token, verify = False ) ) )
        assert( args.parser_addmapping_guest_email in plex_emails )
        new_emails = sorted( set( args.parser_addmapping_guest_email ) )
        if len( new_emails ) == 0:
            return
        assert( len( set( new_emails ) & set( plex_emails ) ) == 0 )
        core.add_mapping(
            args.parser_addmapping_guest_email, plex_emails, new_emails,
            args.do_replace_existing )
        return
            
    if args.choice.strip( ).lower( ) == 'friends':
        plex_emails = sorted( set( core.get_email_contacts( token, fullURL = fullURL, verify = False ) ) )
        _print_format_names( plex_emails, header_name = 'PLEX' )
        return

    if args.choice.strip( ).lower( ) == 'mappedfriends':
        mapped_emails = sorted( set( core.get_mapped_email_contacts( token, fullURL = fullURL, verify = False ) ) )
        _print_format_names( mapped_emails, header_name = 'MAPPED PLEX' )
        return

