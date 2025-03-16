import os, datetime, logging, time, json, sys
from pathlib import Path
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
        return rst2html.create_rfc5322_email({
            'email' : email })
    return rst2html.create_rfc5322_email({
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

def exclude_name_emails( excl_set, name_emails ):
    if len( excl_set ) == 0: return name_emails
    #
    ##
    def is_excluded_match( name_email ):
        name, email = name_email
        if name is not None:
          if any(map(lambda excl: excl in name.lower( ), excl_set ) ): return True
        if email is not None:
          if any(map(lambda excl: excl in email.lower( ), excl_set ) ): return True
        return False
    return list(filter(lambda name_email: not is_excluded_match( name_email ), name_emails) )

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
        help = 'Body of the email to be sent, in reStructuredText format. Default is "This is a test."')
    parser.add_argument(
        '-F', '--bodyFile', dest='bodyFile', action='store', type=str, default = 'This is a test.',
        help = 'Body of the email to be sent, in reStructuredText format. Default is "This is a test."')
    parser.add_argument(
        '-E', '--exclude', dest = 'excluded_contact_fragments', action='store', default = [ ], nargs = "*",
        help = 'The name or email contacts to exclude. Needs to only be first few characters that match.' )
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
    #
    ## do we get the reStructuredText email body as a body string -B or as an -F
    if args.bodyFile is not None and os.path.exists( os.path.expanduser( args.bodyFile ) ):
        bodyFile = os.path.expanduser( args.bodyFile )
        try:
            bodyString = open( bodyFile, 'r' ).read( )
        except Exception as e:
            print( "Error trying to read input reStructuredText file = %s. Reason = %s." % (
                bodyFile, str( e ) ) )
            return
    else:
        bodyString = args.body
    
    finalString = create_final_restructuredtext_body( bodyString )
    if finalString is None:
        print( 'Error, %s could not be converted into email.' % bodyString )
        return

    excl_set = set( map(lambda elem: elem.lower().strip(), args.excluded_contact_fragments ) )
    logging.info( 'excluded contact fragments = %s.' % excl_set )
    name_emails = exclude_name_emails( excl_set, name_emails )
    logging.info( 'LIST OF NAME_EMAILS: %s.' % name_emails )
    #
    ## now do the email sending out
    print( 'processed all checks in %0.3f seconds.' % ( time.perf_counter( ) - time0 ) )
    time0 = time.perf_counter( )
    if args.do_test:
        finalString = create_final_restructuredtext_body( bodyString, name = emailName )
        msg = rst2html.create_collective_email_full(
            rst2html.convert_string_RST( finalString ),
            args.subject,
            { 'email' : emailAddress, 'full name' : emailName },
            [ { 'email' : emailAddress, 'full name' : emailName }, ] )
        send_email_lowlevel( msg, verify = False )
        logging.info( 'processed test email in %0.3f seconds.' %
                     ( time.perf_counter( ) - time0 ) )
        return
    
    email_service = get_email_service( verify = False )
    def _send_email_perproc( input_tuple ):
        name, fullEmail = input_tuple
        finalString = create_final_restructuredtext_body( bodyString, name = name )
        msg = rst2html.create_collective_email_full(
            rst2html.convert_string_RST( finalString ),
            args.subject,
            { 'email' : emailAddress, 'full name' : emailName },
            [ { 'email' : fullEmail, 'full name' : name }, ] )
        send_email_lowlevel( msg, email_service = email_service, verify = False )
    arrs = list( map( _send_email_perproc, name_emails + [ ( emailName, emailAddress ), ] ) )
    logging.info( 'processed %d emails in %0.3f seconds.' % (
        len(arrs), time.perf_counter( ) - time0 ) )
