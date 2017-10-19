#!/usr/bin/env python2

from plexcore import plexcore, session
from optparse import OptionParser
import requests

def main( ):
    parser = OptionParser( )
    parser.add_option( '--username', dest='username', type=str, action='store',
                       help = 'Your plex username.' )
    parser.add_option( '--password', dest='password', type=str, action='store',
                       help = 'Your plex password.' )
    parser.add_option( '--friends', dest='do_friends', action='store_true',
                       default = False,
                       help = 'Get list of guests of your Plex server.')
    parser.add_option( '--addmapping', dest='do_addmapping',
                       action = 'store_true', default = False,
                       help = 'If chosen, then add extra friends from Plex friends.' )
    parser.add_option( '--guestemail', dest='guest_email', action = 'store', type=str,
                       help = 'Name of the Plex guest email.' )
    parser.add_option( '--newemails', dest='new_emails', action = 'store', type = str,
                       help = 'Name of the new emails associated with the Plex guest email.')
    parser.add_option( '--replace_existing', dest='do_replace_existing', action = 'store_true', default = False,
                       help = 'If chosen, replace existing email to send newsletter to.')
    parser.add_option( '--mappedfriends', dest='do_mapped_friends', action='store_true', default = False,
                       help = 'Get list of guests with mapping, of your Plex server.')
    parser.add_option( '--updateflaskcreds', dest='do_updateflaskcreds', action = 'store_true', default = False,
                       help = 'Update flask credentials.' )
    parser.add_option( '--flaskpassword', dest='flaskpassword', action = 'store', type=str,
                       help = 'Password to flask server for Tanim Islam.' )
    parser.add_option( '--justadd', dest='do_justadd', action = 'store_true', default = False,
                       help = 'Just add the set of emails we set with --newemails.' )
    opts, args = parser.parse_args( )
    assert(len(list(filter(lambda tok: tok is True,
                           ( opts.do_friends, opts.do_addmapping,
                             opts.do_mapped_friends, opts.do_updateflaskcreds,
                             opts.do_justadd ) ) ) ) == 1 )
    if any(map(lambda tok: tok is None, ( opts.username, opts.password ) ) ):
        var = plexcore.checkServerCredentials( )
        if var is None:
            print('COULD NOT FIND PLEX SERVER CREDENTIALS OR INVALID USERNAME/PASSWORD COMBO')
            return
        _, token = var
    else:
        assert(all(map(lambda tok: tok is not None,
                       ( opts.username, opts.password ) ) ) )
        token = plexcore.getTokenForUsernamePassword(
            opts.username, opts.password, verify = False )
        if token is None:
            print('INVALID USERNAME/PASSWORD COMBO.')
            return
        
    if opts.do_friends:
        plex_emails = sorted( set( plexcore.get_email_contacts( token, verify = False ) ) )
        print('YOU HAVE %d PLEX FRIENDS' % len( plex_emails ) )
        print('---')
        for email in plex_emails:
            print('%s' % email)

    elif opts.do_addmapping:
        plex_emails = sorted( set( plexcore.get_email_contacts( token, verify = False ) ) )
        assert(all(map(lambda tok: tok is not None, ( opts.guest_email, opts.new_emails ) ) ) )        
        assert( opts.guest_email in plex_emails )
        new_emails = sorted( set( map(lambda tok: tok.strip(), opts.new_emails.split(','))) )
        assert( len( set( new_emails ) & set( plex_emails ) ) == 0 )
        plexcore.add_mapping( opts.guest_email, plex_emails, new_emails,
                              opts.do_replace_existing )
    elif opts.do_mapped_friends:
        mapped_emails = sorted( set( plexcore.get_mapped_email_contacts( token, verify = True ) ) )
        print('YOU HAVE %d MAPPED PLEX FRIENDS' % len( mapped_emails ))
        print('---')
        for email in mapped_emails:
            print('%s' % email)
    elif opts.do_updateflaskcreds:
        assert( opts.flaskpassword is not None )
        response = requests.get( 'https://tanimislam.ddns.net/flask/accounts/checkpassword',
                                 auth = ( 'tanim.islam@gmail.com', opts.flaskpassword ) )
        if response.status_code != 200:
            print('ERROR, WRONG PASSWORD FOR TANIM ISLAM.')
            return
        query = session.query( plexcore.PlexGuestEmailMapping )
        subtracts = [ ]
        adds = [ ]
        for mapping in query.all( ):
            replace_existing = mapping.plexreplaceexisting
            plex_email = mapping.plexemail
            if replace_existing: subtracts.append( plex_email )
            adds += map(lambda tok: tok.strip(), mapping.plexmapping.strip().split(','))
        adds = sorted( set( adds ) )
        response = requests.post( 'https://tanimislam.ddns.net/flask/accounts/adddeleteusersbulk',
                                  json = { 'initialpassword' : 'initialplexserver',
                                           'addemails' : adds, 'deleteemails' : subtracts },
                                  auth = ( 'tanim.islam@gmail.com', opts.flaskpassword ) )
        data = response.json( )
        print(data['deleted'])
        print(data['added'])
    elif opts.do_justadd:
        assert( opts.flaskpassword is not None )
        assert( opts.new_emails is not None )
        response = requests.get( 'https://tanimislam.ddns.net/flask/accounts/checkpassword',
                                 auth = ( 'tanim.islam@gmail.com', opts.flaskpassword ) )
        if response.status_code != 200:
            print('ERROR, WRONG PASSWORD FOR TANIM ISLAM.')
            return
        adds = sorted( set( map(lambda email: email.strip(), opts.new_emails.split(',') ) ) )
        response = requests.post( 'https://tanimislam.ddns.net/flask/accounts/adddeleteusersbulk',
                                  json = { 'initialpassword' : 'initialplexserver',
                                           'addemails' : adds },
                                  auth = ( 'tanim.islam@gmail.com', opts.flaskpassword ) )
        data = response.json( )
        print(data['added'])
        
if __name__=='__main__':
    main( )
