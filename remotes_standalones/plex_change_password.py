#!/usr/bin/env python3

import os, sys, requests, datetime
from optparse import OptionParser

parser = OptionParser( )
parser.add_option('--email', dest='email', type=str,
                  action = 'store', help = 'Plex email address.')
parser.add_option('--password', dest='password', type=str,
                  action = 'store', help = 'Password on Plex server.')
parser.add_option('--newpassword', dest='newpassword', type=str,
                  action = 'store', help = ' '.join([ 'New password on Plex server.',
                                                      'If you forget it, you have to email',
                                                      '***REMOVED***.islam@gmail.com to reset your password.' ]))
opts, args = parser.parse_args( )
assert( opts.email is not None )
assert( opts.password is not None )
assert( opts.newpassword is not None )
#
response = requests.post( 'https://***REMOVED***islam.ddns.net/flask/accounts/modify', auth = ( opts.email, opts.password ),
                          json = { 'newpassword' : opts.newpassword } )
if response.status_code not in ( 400, 200 ):
    print('%s. You have probably given the wrong email/password combo.' % response.content)
elif response.status_code == 400:
    print('%s.' % response.json()['message'])
else:
    print(' '.join([ 'Changed password at %s.' % datetime.datetime.now( ),
                     'Remember your password!' ]))
