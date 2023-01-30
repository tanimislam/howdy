import os, datetime, logging, time
from email.utils import formataddr
from argparse import ArgumentParser
from jinja2 import Environment, FileSystemLoader, Template
#
from howdy import resourceDir
from howdy.core import core
from howdy.email import (
    email, get_email_contacts_dict, emailAddress, emailName, get_email_service, send_email_lowlevel )
from ive_tanim.core import rst2html

def return_nameemail_string( name, email ):
    if name is None:
        return rst2html.create_rfc2047_email({
            'email' : email })
    return rst2html.create_rfc2047_email({
        'email' : email,
        'full name' : name })

def create_final_restructuredtext_body( bodyString, name = None ):
    email = { 'body' : bodyString }
    env = Environment( loader = FileSystemLoader( resourceDir ) )
    template = env.get_template( 'email_notif_template.rst' )
    
    if name is None: email[ 'recipient_name' ] = 'Friend'
    else: email[ 'recipient_name' ] = name.split( )[ 0 ].strip( )
    finalString = template.render( email = email )
    if not rst2html.check_valid_RST( finalString ):
        logging.error("ERROR, final RST string = %s." % finalString )
        logging.error("COULD NOT BE PARSED.")
        return None
    return finalString

def main( ):
    time0 = time.perf_counter( )
    date_now = datetime.datetime.now( ).date( )
    parser = ArgumentParser( )
    parser.add_argument(
        '-I', '--info', dest='do_info', action='store_true',
        default = False, help = 'Run INFO logging mode if chosen.')
    parser.add_argument(
        '-T', '--test', dest='do_test', action='store_true',
        default = False, help = 'Send a test notification email if chosen.')
    parser.add_argument(
        '-S', '--subject', dest='subject', action='store', type=str,
        default = 'Plex notification for %s.' % date_now.strftime( '%B %d, %Y' ),
        help = 'Subject of notification email. Default is "%s".' %
        ( 'Plex notification for %s.' % date_now.strftime( '%B %d, %Y' ) ) )
    parser.add_argument(
        '-B', '--body', dest='body', action='store', type=str, default = 'This is a test.',
        help = 'Body of the email to be sent. Default is "This is a test."')
    #
    args = parser.parse_args( )
    logger = logging.getLogger( )
    if args.do_info: logger.setLevel( level = logging.INFO )
    status, _ = core.oauthCheckGoogleCredentials( )
    if not status:
        print( "Error, do not have correct Google credentials." )
        return
    val = core.checkServerCredentials( doLocal = False, verify = False )
    if val is None:
        print( "Error, could not get an instance of a running Plex server on this machine." )
        return
    _, token = val
    #
    ## get mapped emails
    emails = core.get_mapped_email_contacts( token, verify = False )
    name_emails = get_email_contacts_dict( emails, verify = False )
    items = sorted(list(map(lambda name_email: return_nameemail_string( name_email[0], name_email[1] ),
                            name_emails)))
    finalString = create_final_restructuredtext_body( args.body )
    if finalString is None:
        print( 'Error, %s could not be converted into email.' % args.body )
        return

    #
    ## now do the email sending out
    print( 'processed all checks in %0.3f seconds.' % ( time.time( ) - time0 ) )
    time0 = time.perf_counter( )
    if args.do_test:
        finalString = create_final_restructuredtext_body( args.body, name = emailName )
        msg = rst2html.create_collective_email_full(
            rst2html.convert_string_RST( finalString ),
            args.subject,
            { 'email' : emailAddress, 'full name' : emailName },
            [ { 'email' : emailAddress, 'full name' : emailName }, ] )
        send_email_lowlevel( msg, verify = False )
        logging.info( 'processed test email in %0.3f seconds.' %
                     ( time.perf_counter( ) - time0 ) )
        return
    #
    # email_service = get_email_service( verify = False )
    # def _send_email_perproc( input_tuple ):
    #     name, fullEmail = input_tuple
    #     email.send_individual_email_full(
    #         htmlString, args.subject, fullEmail, name = name,
    #         email_service = email_service )
    #     return True
    # arrs = list( map(
    #     _send_email_perproc, name_emails +
    #     [ ( emailName, emailAddress ) ] ) )
    # logging.info( 'processed %d emails in %0.3f seconds.' % (
    #     len(arrs), time.perf_counter( ) - time0 ) )
