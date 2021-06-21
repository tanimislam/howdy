import signal, sys
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import titlecase
from argparse import ArgumentParser
#
from howdy.tv import tv, tv_attic

def main( ):
    parser = ArgumentParser( )
    parser.add_argument('-s', '--series', dest = 'series', type=str, action='store',
                        help = 'The name of the series', required = True )
    parser.add_argument('-e', '--epstring', dest='epstring', type=str, action='store',
                        help = 'The episode string, in the form S%%02dE%%02d.' )
    parser.add_argument('-S', '--season', dest='season', action='store', type=int,
                        help = 'If chosen, get a list of all episode titles for this season of the SERIES.')
    parser.add_argument('-f', '--firstyear', dest='firstyear', action='store', type=int,
                        help = 'Optional argument, because of TMDB ambiguities, we can specify a year in which the first episode aired to get the SPECIFIC TMDB id on the show.' )
    parser.add_argument('--summary', dest='do_summary', action='store_true', default = False,
                        help = 'If chosen, get a summary of all the seasons and episodes for the SERIES.')
    #
    ## big option
    #parser.add_option('--add', dest='do_add', action='store_true', default = False,
    #help = ' '.join([
    #                      'BIG CHANGE. If chosen, allows you to choose and download',
    #                       'an episode given a valid series name and episode name.' ]))
    args = parser.parse_args( )
    if args.do_summary:
        seriesName = args.series.strip( )
        epdicts = tv_attic.get_tot_epdict_tmdb( seriesName, showFuture = True, minmatch = 10.0, firstAiredYear = args.firstyear )
        if epdicts is None:
            print('Error, could not find %s' % seriesName)
            return
        seasons = set( range( 1, max( epdicts.keys( ) ) + 1 ) ) & set( epdicts.keys( ) )
        print( '%d episodes for %s' % ( sum(map(lambda seasno: len( epdicts[ seasno ] ), seasons ) ),
                                        seriesName ) )
        for seasno in sorted( seasons ):
            print('SEASON %02d: %d episodes' % ( seasno, len( epdicts[ seasno ] ) ) )
    elif args.season is not None:
        seriesName = args.series.strip( )
        epdicts = tv_attic.get_tot_epdict_tmdb( seriesName, showFuture = True, minmatch = 10.0, firstAiredYear = args.firstyear )
        if epdicts is None:
            print( 'Error, could not find %s' % seriesName )
            return
        if args.season not in epdicts:
            print( 'Error, season %02d not in %s.' % ( args.season, seriesName ) )
            return
        print('%d episodes in SEASON %02d of %s.' % ( len( epdicts[ args.season ] ), args.season, seriesName ) )
        for epnum in sorted( epdicts[ args.season ] ):
            title, airedDate = epdicts[ args.season ][ epnum ]
            print( 'Episode %02d/%02d: %s (%s)' % (
                epnum, len( epdicts[ args.season ] ),
                title, airedDate.strftime( '%A, %d %B %Y' ) ) )
    else:
        assert( args.epstring is not None )
        seriesName = args.series.strip( )
        token = tv.get_token( verify = args.do_verify )
        series_id = tv.get_series_id( seriesName, token, verify = args.do_verify )
        if series_id is None:
            print( 'Error, could not find %s' % seriesName )
            return
        seasepstring = args.epstring.strip( ).upper( )
        if not seasepstring[0] == 'S':
            print( 'Error, first string must be an s or S.' )
            return
        seasepstring = seasepstring[1:]
        splitseaseps = seasepstring.split('E')[:2]
        if len( splitseaseps ) != 2:
            print( 'Error, string must have a SEASON and EPISODE part.' )
            return
        try:
            seasno = int( splitseaseps[0] )
        except:
            print( 'Error, invalid season number.' )
            return
        try:
            epno = int( splitseaseps[1] )
        except:
            print( 'Error, invalid episode number.' )
            return
        data = tv.get_episode_name( series_id, seasno, epno, token,
                                          verify = args.do_verify )
        if data is None:
            print( 'Error, could not find SEASON %02d, EPISODE %02d, in %s.' % (
                seasno, epno, seriesName ) )
            return
        epname, fa = data
        print('%s (%s)' % ( titlecase.titlecase( epname ), fa.strftime('%A, %d %B %Y' ) ) )
        # not yet implemented
        #if do_add:
        #    tv.download_single_episode_to_folder( series_id, seasno, epno data )
