#!/usr/bin/env python3

import os, datetime, logging
import time, multiprocessing
from optparse import OptionParser
from plexcore import plexcore
from plexemail import plexemail

def main( ):
    time0 = time.time( )
    date_now = datetime.datetime.now( ).date( )
    parser = OptionParser( )
    parser.add_option('--debug', dest='do_debug', action='store_true',
                      default = False, help = 'Run debug mode if chosen.')
    parser.add_option('--test', dest='do_test', action='store_true',
                      default = False, help = 'Send a test notification email if chosen.')
    parser.add_option('--subject', dest='subject', action='store', type=str,
                      default = 'Plex notification for %s.' % date_now.strftime( '%B %d, %Y' ),
                      help = 'Subject of notification email. Default is "%s".' %
                      ( 'Plex notification for %s.' % date_now.strftime( '%B %d, %Y' ) ) )
    parser.add_option('--body', dest='body', action='store', type=str, default = 'This is a test.',
                      help = 'Body of the email to be sent. Default is "This is a test."')
    opts, args = parser.parse_args( )
    if opts.do_debug:
        logging.basicConfig( level = logging.DEBUG )
    status, _ = plexcore.oauthCheckEmailCredentials( )
    if not status:
        print( "Error, do not have correct email credentials." )
        return
    status, _ = plexcore.oauthCheckContactCredentials( )
    if not status:
        print( "Error, do not have correct contact credentials." )
        return
    val = plexcore.checkServerCredentials( )
    if val is None:
        print( "Error, could not get an instance of a running Plex server on this machine." )
        return
    _, token = val
    #
    ## get mapped emails
    emails = plexcore.get_mapped_email_contacts( token )
    name_emails = plexemail.get_email_contacts_dict( emails )
    def return_nameemail_string( name, email ):
        if name is not None:
            return "%s <%s>" % ( name, email )
        return email
    items = sorted(list(map(lambda name_email: return_nameemail_string( name_email[0], name_email[1] ),
                            name_emails)))
    finalString = '\n'.join([ 'Hello Friend,', '', opts.body ])
    htmlString = plexcore.latexToHTML( finalString )
    if htmlString is None:
        print( 'Error, %s could not be converted into email.' % opts.body )
        return

    #
    ## now do the email sending out
    access_token = plexcore.oauth_get_access_token( )
    if access_token is None:
        print( 'Error, could not authorize email sending.' )
        return
    print( 'processed all checks in %0.3f seconds.' % ( time.time( ) - time0 ) )
    time0 = time.time( )
    if opts.do_test:
        plexemail.send_individual_email_full( htmlString, opts.subject, access_token,
                                              'tanim.islam@gmail.com', 'Tanim Islam' )
        print( 'processed test email in %0.3f seconds.' % ( time.time( ) - time0 ) )
    else:
        def _send_email_perproc( input_tuple ):
            name, email = input_tuple
            plexemail.send_individual_email_full( htmlString, opts.subject, access_token,
                                                  email, name )
            return True
        pool = multiprocessing.Pool( processes = multiprocessing.cpu_count( ) )
        arrs = pool.map( _send_email_perproc, name_emails + [ ( 'Tanim Islam', 'tanim.islam@gmail.com' ) ])
        print( 'processed %d emails in %0.3f seconds.' % ( len(arrs), time.time( ) - time0 ) )
        
if __name__=='__main__':
    main( )
