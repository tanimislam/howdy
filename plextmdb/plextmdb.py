import logging, glob, os, requests, datetime, fuzzywuzzy.fuzz, time, sys
import pathos.multiprocessing as multiprocessing
from itertools import chain

from plextmdb import get_tmdb_api, TMDBEngine, TMDBEngineSimple, tmdb_apiKey
from plexcore import return_error_raw

def get_tv_ids_by_series_name( series_name, verify = True ):
    """
    Returns a :py:class:`list` of TMDB_ series IDs that match to a given TV show name.
    
    :param str series_name: the name of the TV series.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :returns: a :py:class:`list` of TMDB_ series IDs..
    :rtype: list
    """
    response = requests.get( 'https://api.themoviedb.org/3/search/tv',
                                 params = { 'api_key' : tmdb_apiKey,
                                            'append_to_response': 'images',
                                            'include_image_language': 'en',
                                            'language': 'en',
                                            'sort_by': 'popularity.desc',
                                            'query' : '+'.join( series_name.split( ) ),
                                            'page' : 1 }, verify = verify )
    if response.status_code != 200: return [ ]
    data = response.json( )
    valid_results = list(filter(
        lambda result: 'name' in result and
        result['name'] == series_name and
        'id' in result, data[ 'results' ] ) )
    return list(map(lambda result: result[ 'id' ], valid_results ) )

def get_tv_info_for_series( tv_id, verify = True ):
    """
    Finds TMDB_ database information for the TV show.
    
    :param int tv_id: the TMDB_ series ID for the TV show.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :returns: a comprehensive :py:class:`dict` of TMDB_ information on the TV show. Example nicely formatted JSON representation for `The Simpsons`_ is located in :download:`tmdb_simpsons_info.json </_static/tmdb_simpsons_info.json>`. Otherwise returns ``None`` if TV show cannot be found.
    :rtype: dict

    .. _`The Simpsons`: https://en.wikipedia.org/wiki/The_Simpsons
    """
    response = requests.get( 'https://api.themoviedb.org/3/tv/%d' % tv_id,
                             params = { 'api_key' : tmdb_apiKey,
                                        'append_to_response': 'images',
                                        'language': 'en' }, verify = verify )
    if response.status_code != 200:
        print( response.content )
        return None
    return response.json( )

def get_tv_info_for_season( tv_id, season, verify = True ):
    """
    Finds TMDB_ database information for the TV show and a specific season.
    
    :param int tv_id: the TMDB_ series ID for the TV show.
    :param int season: the season on the TV show.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :returns: a comprehensive :py:class:`dict` of TMDB_ information on the TV show and the given season. Example nicely formatted JSON representation for `The Simpsons Season 10`_ is located in :download:`tmdb_simpsons_info.json </_static/tmdb_simpsons_season10_info.json>`. Otherwise returns ``None`` if TV show cannot be found.
    :rtype: dict

    .. _`The Simpsons Season 10`: https://en.wikipedia.org/wiki/The_Simpsons_(season_10)
    """
    response = requests.get(
        'https://api.themoviedb.org/3/tv/%d/season/%d' % ( tv_id, season ),
        params = { 'api_key' : tmdb_apiKey,
                   'append_to_response': 'images',
                   'language': 'en' }, verify = verify )
    if response.status_code != 200:
        print( response.content )
        return None
    return response.json( )

def get_tv_imdbid_by_id( tv_id, verify = True ):
    """
    Returns the IMDb_ ID for a TV show.

    :param int tv_id: the TMDB_ series ID for the TV show.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :returns: the IMDB_ ID for that TV show. Otherwise returns ``None`` if cannot be found.
    :rtype: str

    .. _IMDb: https://www.imdb.com
    """
    response = requests.get(
        'https://api.themoviedb.org/3/tv/%d/external_ids' % tv_id,
        params = { 'api_key' : tmdb_apiKey }, verify = verify )
    if response.status_code != 200:
        print( 'problem here, %s.' % response.content )
        return None
    data = response.json( )
    if 'imdb_id' not in data: return None
    return data['imdb_id']

#
## right now do not show specials
def get_episodes_series_tmdb( tv_id, verify = True ):
    """
    Returns a :py:class:`list` of episodes from the TMDB_ database for a TV show. Otherwise returns ``None`` if cannot be found.
    
    :param int tv_id: the TMDB_ series ID for the TV show.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :returns: a :py:class:`list` of episodes for this TV show, ordered by air date. Each element is a summary of an episode with the following keys.
      
      * ``airedSeason`` is the season the episode aired.
      * ``airedEpisodeNumber`` is the order in the season that the episode aired.
      * ``firstAired`` is a :py:class:`str` representation, in the format "YYYY-MM-DD", when the episode aired.
      * ``overview`` is a plot summary of the episode.

      For example, for `The Simpsons`_,

      .. code-block:: python

        [{'airedSeason': 1,
          'airedEpisodeNumber': 1,
          'firstAired': '1989-12-17',
          'episodeName': 'Simpsons Roasting on an Open Fire',
          'overview': "When his Christmas bonus is cancelled, Homer becomes a department-store Santa--and then bets his meager earnings at the track. When all seems lost, Homer and Bart save Christmas by adopting the losing greyhound, Santa's Little Helper."},
         {'airedSeason': 1,
          'airedEpisodeNumber': 2,
          'firstAired': '1990-01-14',
          'episodeName': 'Bart the Genius',
          'overview': "After switching IQ tests with Martin, Bart is mistaken for a child genius. When he's enrolled in a school for gifted students, a series of embarrassments and mishaps makes him long for his old life."},
         {'airedSeason': 1,
          'airedEpisodeNumber': 3,
          'firstAired': '1990-01-21',
          'episodeName': "Homer's Odyssey",
          'overview': 'Homer is fired for nearly causing a meltdown at the nuclear plant. When he finds a new calling as a public safety advocate, he finds himself facing off against Mr. Burns.'},
         {'airedSeason': 1,
          'airedEpisodeNumber': 4,
          'firstAired': '1990-01-28',
          'episodeName': "There's No Disgrace Like Home",
          'overview': 'After an embarrassing experience at the company picnic, Homer pawns the TV and uses the proceeds to take the family to therapy sessions.'}
         ...
        ]

    :rtype: list
    
    .. seealso:: :py:meth:`get_tot_epdict_tmdb <plextvdb.plextvdb_attic.get_tot_epdict_tmdb>`
    """
    tmdb_tv_info = get_tv_info_for_series( tv_id, verify = verify )
    if tmdb_tv_info is None: return None
    valid_seasons = sorted(filter(lambda seasno: seasno != 0,
                                  map(lambda season: season['season_number'],
                                      tmdb_tv_info[ 'seasons' ] ) ) )
    def _process_tmdb_epinfo( seasno ):
        #
        # must define 'airedSeason', 'airedEpisodeNumber', 'firstAired', 'overview', 'imageURL', 'episodeName'
        seasinfo = get_tv_info_for_season( tv_id, seasno, verify = verify )
        epelems = [ ]
        for epinfo in seasinfo[ 'episodes']:
            if len( set([ 'air_date', 'name', 'episode_number' ]) -
                    set( epinfo.keys( ) ) ) != 0:
                continue
            epelem = {
                'airedSeason' : seasno,
                'airedEpisodeNumber' : epinfo[ 'episode_number' ],
                'firstAired' : epinfo[ 'air_date' ],
                'episodeName' : epinfo[ 'name' ]
            }
            #'imageURL' : 'https://image.tmdb.org/t/p/w500%s' % epinfo['profile_path'] }
            if 'overview' in epinfo: epelem['overview'] = epinfo[ 'overview' ]
            if 'profile_path' in epinfo:
                epelem[ 'imageURL' ] = 'https://image.tmdb.org/t/p/w500%s' % epinfo['profile_path']
            epelems.append( epelem )
        return epelems
    #
    with multiprocessing.Pool( processes = multiprocessing.cpu_count( ) ) as pool:
        return list( chain.from_iterable(
            map( _process_tmdb_epinfo, valid_seasons ) ) )

def get_movie_info( tmdb_id, verify = True ):
    """
    Gets movie information for a movie.
    
    :param int tmdb_id: the TMDB_ movie ID.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :returns: a comprehensive :py:class:`dict` of summary information for the movie. For example, for `Star Wars`_,
    
      .. code-block:: python

        {'adult': False,
         'backdrop_path': '/4iJfYYoQzZcONB9hNzg0J0wWyPH.jpg',
         'belongs_to_collection': {'id': 10,
          'name': 'Star Wars Collection',
          'poster_path': '/iTQHKziZy9pAAY4hHEDCGPaOvFC.jpg',
          'backdrop_path': '/d8duYyyC9J5T825Hg7grmaabfxQ.jpg'},
         'budget': 11000000,
         'genres': [{'id': 12, 'name': 'Adventure'},
          {'id': 28, 'name': 'Action'},
          {'id': 878, 'name': 'Science Fiction'}],
         'homepage': 'http://www.starwars.com/films/star-wars-episode-iv-a-new-hope',
         'id': 11,
         'imdb_id': 'tt0076759',
         'original_language': 'en',
         'original_title': 'Star Wars',
         'overview': 'Princess Leia is captured and held hostage by the evil Imperial forces in their effort to take over the galactic Empire. Venturesome Luke Skywalker and dashing captain Han Solo team together with the loveable robot duo R2-D2 and C-3PO to rescue the beautiful princess and restore peace and justice in the Empire.',
         'popularity': 50.48,
         'poster_path': '/btTdmkgIvOi0FFip1sPuZI2oQG6.jpg',
         'production_companies': [{'id': 1,
           'logo_path': '/o86DbpburjxrqAzEDhXZcyE8pDb.png',
           'name': 'Lucasfilm',
           'origin_country': 'US'},
          {'id': 25,
           'logo_path': '/qZCc1lty5FzX30aOCVRBLzaVmcp.png',
           'name': '20th Century Fox',
           'origin_country': 'US'}],
         'production_countries': [{'iso_3166_1': 'US',
           'name': 'United States of America'}],
         'release_date': '1977-05-25',
         'revenue': 775398007,
         'runtime': 121,
         'spoken_languages': [{'iso_639_1': 'en', 'name': 'English'}],
         'status': 'Released',
         'tagline': 'A long time ago in a galaxy far, far away...',
         'title': 'Star Wars',
         'video': False,
         'vote_average': 8.2,
         'vote_count': 12125}

    :rtype: dict

    .. _`Star Wars`: https://en.wikipedia.org/wiki/Star_Wars_(film)
    """
    response = requests.get(
        'https://api.themoviedb.org/3/movie/%d' % tmdb_id,
        params = { 'api_key' : tmdb_apiKey },
        verify = verify )
    if response.status_code != 200:
        return None
    return response.json( )

def get_actor_ids_dict( actor_names, verify = True ):
    """
    Returns a :py:class:`dict` of actor names to their TMDB_ actor ID.
    
    :param iterable actor_names: an iterable collection (:py:class:`list`, :py:class:`set`, etc.) of actor names.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :returns: a :py:class:`dict`, where the key is the actor name and its value is the TMDB_ actor ID. For example, if we want to get the ids for `Steve Martin`_ and `Richard Pryor`_,
    
      .. code-block:: bash

         {'Richard Pryor': 9309, 'Steve Martin': 67773}

      If no actors can be found, then returns an empty dictionary.

    .. _`Steve Martin`: https://en.wikipedia.org/wiki/Steve_Martin
    .. _`Richard Pryor`: https://en.wikipedia.org/wiki/Richard_Pryor

    .. seealso:: :py:meth:`get_movies_by_actors <plextmdb.plextmdb.get_movies_by_actors>`
    """
    actor_name_dict = { }
    for actor_name in set(actor_names):
        actor_ids = [ ]
        params = { 'api_key' : tmdb_apiKey,
                   'query' : '+'.join( actor_name.split( ) ), }
        response = requests.get(
            'https://api.themoviedb.org/3/search/person',
            params = params, verify = verify )
        if response.status_code != 200:
            continue
        data = response.json()
        total_pages = data['total_pages']
        actor_ids = list( map(lambda result: result['id'], data['results'] ) )
        if total_pages >= 2:
            for pageno in range(2, total_pages + 1 ):
                params =  { 'api_key' : tmdb_apiKey,
                            'query' : '+'.join( actor_name.split( ) ),
                            'page' : pageno }
            response = requests.get( 'https://api.themoviedb.org/3/search/person',
                                     params = params, verify = verify )
            if response.status_code != 200: continue
            data = response.json( )
            actor_ids += list( map(lambda result: result['id'], data['results'] ) )
        if len( set( actor_ids ) ) != 0:
            actor_name_dict[ actor_name ] = min(set( actor_ids ) )
    return actor_name_dict

def get_movies_by_actors( actor_name_dict, verify = True ):
    """
    Finds the movies where a set of actors have acted together.

    :param dict actor_name_dict: the :py:class:`dict`, of format returned by :py:meth:`get_actor_ids_dict <plextmdb.plextmdb.get_actor_ids_dict>`, of the collection of actors.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :returns: a :py:class:`list` of movies in which these actors have acted. For example, here are the three movies that TMDB_ found in which `Steve Martin`_ and `Richard Pryor`_ acted together.

      .. code-block:: python

            [{'title': 'The Muppet Movie',
              'release_date': datetime.datetime(1979, 6, 22, 0, 0),
              'popularity': 7.743,
              'vote_average': 7.1,
              'overview': 'Kermit the Frog is persuaded by agent Dom DeLuise to pursue a career in Hollywood. Along the way, Kermit picks up Fozzie Bear, Miss Piggy, Gonzo, and a motley crew of other Muppets with similar aspirations. Meanwhile, Kermit must elude the grasp of a frog-leg restaurant magnate.',
              'poster_path': 'https://image.tmdb.org/t/p/w500/48Ve7uLDcPJFGaDnmYYdcV3Ve1M.jpg',
              'isFound': False,
              'tmdb_id': 11176,
              'imdb_id': 'tt0079588'},
             {'title': 'And the Oscar Goes To...',
              'release_date': datetime.datetime(2014, 2, 2, 0, 0),
              'popularity': 4.188,
              'vote_average': 7.0,
              'overview': 'The story of the gold-plated statuette that became the film industry\'s most coveted prize, AND THE OSCAR GOES TO... traces the history of the Academy itself, which began in 1927 when Louis B. Mayer, then head of MGM, led other prominent members of the industry in forming this professional honorary organization. Two years later the Academy began bestowing awards, which were nicknamed "Oscar," and quickly came to represent the pinnacle of cinematic achievement.',
              'poster_path': 'https://image.tmdb.org/t/p/w500/kgH49kPNNtel04HPVGQLS63coRF.jpg',
              'isFound': False,
              'tmdb_id': 253639,
              'imdb_id': 'tt3481232'},
             {'title': "Cutting Edge Comedians of the '60s & '70s",
              'release_date': datetime.datetime(2007, 4, 10, 0, 0),
              'popularity': 0.842,
              'vote_average': 0.0,
              'overview': 'In the late 1950s, a fresh, unconventional style of standup comedy emerged in sharp contrast to the standard "Take my wife, please" approach. It tackled such previously taboo subjects as sex, religion, drugs, and politics, and ushered in an avant-garde era of comedy that was decidedly more cerebral, satirical, and improvisational than before. Here are many of the maverick comedians who took those big risks years ago and paved the way for today’s current crop of outrageous, in-your-face comics. Many of these rare television performances have not been seen in 30 or 40 years. Carl Reiner &amp; Mel Brooks (1966) Jackie Mason (1961) Bob Newhart (1966) Shelly Berman (1966) Bill Cosby (1965) Jonathan Winters (1961) Smothers Brothers (1974) Steve Martin (1977) Rowan &amp; Martin (1964) Lily Tomlin (1975) George Carlin (1967 &amp; 1975) Richard Pryor (1967 &amp; 1974) Andy Kaufman (1977) Hendra &amp; Ullett (1966) Billy Crystal (1976) Jay Leno (1978) David Letterman (1979)',
              'poster_path': 'https://image.tmdb.org/t/p/w500/iRHXAdDXwcuKGLH6MmvOUBrhotT.jpg',
              'isFound': False,
              'tmdb_id': 78710,
              'imdb_id': 'tt1002564'}]
    
      If no common movies can be found, then returns an empty list.

    :rtype: list
    """
    if len( actor_name_dict ) == 0: return [ ]
    for idx in range( 50 ):
        response = requests.get(
            'https://api.themoviedb.org/3/discover/movie',
            params = { 'api_key' : tmdb_apiKey,
                       'append_to_response': 'images',
                       'include_image_language': 'en',
                       'language': 'en',
                       'page': 1,
                       'sort_by': 'popularity.desc',
                       'with_cast' : ','.join(map(lambda num: '%d' % num,
                                                  actor_name_dict.values( ) ) ) },
            verify = verify )
        if response.status_code != 429: break
        time.sleep( 2.5 )
    if response.status_code != 200: return [ ]
    data = response.json( )
    total_pages = data['total_pages']
    results = data['results']
    if total_pages >= 2:
        for pageno in range( 2, total_pages + 1 ):
            for idx in range( 50 ):
                response = requests.get(
                    'https://api.themoviedb.org/3/discover/movie',
                    params = { 'api_key' : tmdb_apiKey,
                               'append_to_response': 'images',
                               'include_image_language': 'en',
                               'language': 'en',
                               'sort_by': 'popularity.desc',
                               'with_cast' : ','.join(map(lambda num: '%d' % num,
                                                          actor_name_dict.values( ) ) ),
                               'page' : pageno },
                    verify = verify )
                if response.status_code != 429: break
                time.sleep( 2.5 )
            if response.status_code != 200:
                continue
            data = response.json( )
            results += data[ 'results' ]
    # return results
    return createProcessedMovieData( results, verify = verify )

def get_movies_by_title( title, verify = True, apiKey = None ):
    """
    Gets a collection of movies that the TMDB_ database finds that matches a movie name.

    :param str title: the movie name.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :param str apiKey: optional argument, the TMDB_ API key.
    :returns: a :py:class:`list` of movies that match ``title`` according to TMDB_. For example, 128 movies are a "match" for `Star Wars`_, according to TMDB_. Here is the top match (all movies have the same :py:class:`dict` format).

      .. code-block:: python

            {'title': 'Star Wars',
             'release_date': datetime.datetime(1997, 1, 31, 0, 0),
             'popularity': 50.48,
             'vote_average': 8.2,
             'overview': 'Princess Leia is captured and held hostage by the evil Imperial forces in their effort to take over the galactic Empire. Venturesome Luke Skywalker and dashing captain Han Solo team together with the loveable robot duo R2-D2 and C-3PO to rescue the beautiful princess and restore peace and justice in the Empire.',
             'poster_path': 'https://image.tmdb.org/t/p/w500/btTdmkgIvOi0FFip1sPuZI2oQG6.jpg',
             'isFound': False,
             'tmdb_id': 11,
             'imdb_id': 'tt0076759'}
    
      If no matches can be found, then this method returns an empty list.

    :rtype: list

    .. seealso:: :py:meth:`get_movie_tmdbids <plextmdb.plextmdb.get_movie_tmdbids>`
    """
    if apiKey is None: apiKey = tmdb_apiKey
    for idx in range( 50 ):
        response = requests.get(
            'https://api.themoviedb.org/3/search/movie',
            params = { 'api_key' : apiKey,
                       'append_to_response': 'images',
                       'include_image_language': 'en',
                       'language': 'en',
                       'sort_by': 'popularity.desc',
                       'query' : '+'.join( title.split( ) ),
            'page' : 1 }, verify = verify )
        if response.status_code != 429: break
        time.sleep( 2.5 ) # sleep 2.5 seconds
    if response.status_code != 200: return [ ]
    data = response.json( )
    total_pages = data['total_pages']
    results = list( filter(lambda result: fuzzywuzzy.fuzz.ratio( result['title'], title ) >= 10.0,
                           data['results'] ) )
    results = sorted( results, key = lambda result: -fuzzywuzzy.fuzz.ratio( result['title'], title ) )
    if total_pages >= 2:
        for pageno in range( 2, max( 5, total_pages + 1 ) ):
            for idx in range( 50 ):
                response = requests.get(
                    'https://api.themoviedb.org/3/search/movie',
                    params = { 'api_key' : apiKey,
                               'append_to_response': 'images',
                               'include_image_language': 'en',
                               'language': 'en',
                               'sort_by': 'popularity.desc',
                               'query' : '+'.join( title.split( ) ),
                               'page' : pageno }, verify = verify )
                if response.status_code != 429: break
                time.sleep( 2.5 )
            if response.status_code != 200:
                continue
            data = response.json( )
            newresults = list(
                filter(lambda result: fuzzywuzzy.fuzz.ratio( result['title'], title ) >= 10.0,
                       data['results'] ) )
            if len( newresults ) > 0:
                results += sorted( newresults, key = lambda result: -fuzzywuzzy.fuzz.ratio( result['title'], title ) )
    # return results
    return createProcessedMovieData( results, verify = verify )

# Followed advice from https://www.themoviedb.org/talk/5493b2b59251416e18000826?language=en
def get_imdbid_from_id( tmdb_id, verify = True ):
    """
    Finds the IMDB_ ID for a movie from its TMDB_ ID.
    
    :param int tmdb_id: the TMDB_ movie ID.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``True``.
    :returns: the IMDB_ movie ID. If cannot be found, returns ``None``.
    :rtype: str
    """
    for idx in range( 50 ):
        response = requests.get(
            'https://api.themoviedb.org/3/movie/%d' % tmdb_id,
            params = { 'api_key' : tmdb_apiKey }, verify = verify )
        if response.status_code != 429: break
        time.sleep( 2.5 )
    if response.status_code != 200:
        print( 'problem here, %s.' % response.content )
        return None
    data = response.json( )
    if 'imdb_id' not in data: return None
    return data['imdb_id']

def get_movie( title, year = None, checkMultiple = True,
               getAll = False, verify = True ):
    movieSearchMainURL = 'https://api.themoviedb.org/3/search/movie'
    params = { 'api_key' : tmdb_apiKey,
               'append_to_response': 'images',
               'include_image_language': 'en',
               'language': 'en',
               'sort_by': 'popularity.desc',
               'query' : '+'.join( title.split( ) ),
               'page' : 1 }
    if year is not None:
        params[ 'primary_release_year' ] = int( year )
    response = requests.get(
        movieSearchMainURL, params = params,
        verify = verify )
    data = response.json( )
    if 'total_pages' in data:
        total_pages = data['total_pages']
        results = list(
            filter(lambda result: fuzzywuzzy.fuzz.ratio( result['title'], title ) >= 90.0,
                   data['results'] ) )
        results = sorted( results, key = lambda result: -fuzzywuzzy.fuzz.ratio( result['title'], title ) )
    else: return None
    if len(results) == 0:
        if checkMultiple:
            indices = range(len(title.split()))
            for idx in indices:
                split_titles = title.split()
                split_titles[idx] = split_titles[idx].upper( )
                newtitle = ' '.join( split_titles )
                val = get_movie( newtitle, year = year, checkMultiple = False )
                if val is not None:
                    return val
        return None
    if not getAll:
        first_movie = results[0]
        return 'https://www.themoviedb.org/movie/%d' % first_movie['id']
    else:
        return results

def get_movie_tmdbids( title, year = None, getAll = False, verify = True ):
    """
    Gets either a :py:class:`list` of TMDB_ movie IDs that match a movie name, or a single best TMDB_ movie ID.
    
    :param str title: the movie name.
    :param int year: optional argument. If defined, check only on movies released that year.
    :param bool getAll: optional argument. If ``True``, then find all matches. If ``False``, only return the best match. Default is ``False``.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``False``.
    :returns: If ``getAll` is ``True``, then return a :py:class:`list` of all TMDB_ movie IDs that match ``title``. If `it is `False``, then return a single (:py:class:`int`) best TMDB_ movie ID match to ``title``. If there are no matches, return ``None``.
    :rtype: If ``getAll`` is ``True``, a :py:class:`list`. If ``getAll`` is ``False``, an :py:class:`int`.
    """
    results = get_movie( title, year = year, checkMultiple = True, getAll = True,
                         verify = verify )
    if results is None: return None
    ids = list(map(lambda result: result['id'], results ) )
    if not getAll: return ids[0]
    else: return ids                   

#
## funky logic needed here...
def get_genre_movie( title, year = None, checkMultiple = True, verify = True ):
    """
    Gets the main genre of a movie.
    
    :param str title: the movie name.
    :param int year: optional argument. If defined, check only on movies released that year.
    :param bool checkMultiple: optional argument. If ``True``, then do an involved search where each word in the ``title`` is individually capitalized. This functionality was developed to make TMDB_ movie searches more robust. Default is ``True``.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``False``.
    :returns: the main movie genre, which can be one of action, animation, comedy, documentary, drama, hindi, horror, horror, science fiction.
    :rtype: str
    """
    movieSearchMainURL = 'http://api.themoviedb.org/3/search/movie'
    params = { 'api_key' : tmdb_apiKey,
               'query' : '+'.join( title.split( ) ),
               'page' : 1 }
    if year is not None:
        params[ 'primary_release_year' ] = int( year )
    response = requests.get(
        movieSearchMainURL, params = params,
        verify = verify )
    data = response.json( )
    if 'total_pages' in data:
        total_pages = data['total_pages']
        results = list( filter(lambda result: fuzzywuzzy.fuzz.ratio( result['title'], title ) >= 90.0,
                               data['results'] ) )
        results = sorted( results, key = lambda result: -fuzzywuzzy.fuzz.ratio( result['title'], title ) )
    else: results = [ ]
    if len(results) == 0:
        if checkMultiple:
            indices = range(len(title.split()))
            for idx in indices:
                split_titles = title.split()
                split_titles[idx] = split_titles[idx].upper( )
                newtitle = ' '.join( split_titles )
                val = get_genre_movie( newtitle, year = year, checkMultiple = False )
                if val is not None:
                    return val
        return None
    first_movie = results[0]
    genre_ids = first_movie['genre_ids']
    for genre_id in genre_ids:
        val = TMDBEngineSimple( verify ).getGenreFromGenreId( genre_id ).lower( )
        if val in ( 'horror', 'comedy', 'animation', 'documentary', 'drama',
                    'action', 'hindi', 'horror', 'science fiction' ):
            return val
        if val == 'fantasy':
            return 'science fiction'
        if val == 'family':
            return 'drama'

def getMovieData( year, genre_id, verify = True ):
    """
    This returns all the movies found by TMDB_ in a given year, of a given TMDB_ genre ID.
    
    :param int year: the year on which to search.
    :param int genre_id: the TMDB_ genre ID. The mapping of TMDB_ genre ID to genre is,

      .. code-block:: python

            {12: 'Adventure',
             14: 'Fantasy',
             16: 'Animation',
             18: 'Drama',
             27: 'Horror',
             28: 'Action',
             35: 'Comedy',
             36: 'History',
             37: 'Western',
             53: 'Thriller',
             80: 'Crime',
             99: 'Documentary',
             878: 'Science Fiction',
             9648: 'Mystery',
             10402: 'Music',
             10749: 'Romance',
             10751: 'Family',
             10752: 'War',
             10770: 'TV Movie'}
      
      If ``genre_id`` is ``-1``, then **ALL** movies (of all genres) are chosen.
    
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``False``.
    :returns: a :py:class:`list` of TMDB_ movie data released that year in that genre.
    :rtype: list

    .. warning::
    
       This method can take an arbitrary long time to run. The author has seen this method take :math:`\ge 600` seconds in some instances. One should be careful when testing this functionality.
    """
    moviePosterMainURL = 'https://image.tmdb.org/t/p/w500'
    movieListMainURL = 'https://api.themoviedb.org/3/discover/movie'
    params = { 'api_key' : tmdb_apiKey,
               'append_to_response': 'images',
               'include_image_language': 'en',
               'language': 'en',
               'page': 1,
               'primary_release_year': year,
               'sort_by': 'popularity.desc',
               'with_genres': genre_id }
    if genre_id == -1: params.pop( 'with_genres' )
    for idx in range( 50 ):
        response = requests.get(
            movieListMainURL, params = params,
            verify = verify )
        if response.status_code != 429: break
        time.sleep( 2.5 )
    logging.debug('RESPONSE STATUS FOR %s = %s.' % ( str(params), str(response) ) )
    logging.debug('KEYS IN RESPONSE: %s.' % response.json( ).keys( ) )
    total_pages = response.json()['total_pages']
    results = list( filter(lambda datum: datum['title'] is not None and
                           datum['release_date'] is not None and
                           datum['popularity'] is not None,
                           response.json( )['results'] ) )
    for pageno in range( 2, total_pages + 1 ):
        params['page'] = pageno
        for idx in range( 50 ):
            response = requests.get(
                movieListMainURL, params = params, verify = verify )
            if response.status_code != 429: break
            time.sleep( 2.5 )
        if response.status_code != 200: continue
        logging.debug('RESPONSE STATUS FOR %s = %s.' % ( str(params), str(response) ) )
        results += list( filter(lambda datum: datum['title'] is not None and
                                datum['release_date'] is not None and
                                datum['popularity'] is not None,
                                response.json( )['results'] ) )
        
    # return results
    return createProcessedMovieData( results, year = year, verify = verify )

def createProcessedMovieData( results, year = None, verify = True ):
    """
    Takes the :py:class:`list` of raw movie data (one row per movie) produced by TMDB_, and then processes each row in the following way.
    
    * If a year is specified in this method, then reject any movie that has not been aired that year.
    * Takes the :py:class:`str` release date that TMDB_ produces by default, and converts that into a :py:class:`date <datetime.date>`.
    * Fixes up the ``vote_average`` value for the movie.
    * Tries to find the IMDB_ ID for a movie.

    :param list results: the pre-processed :py:class:`list` of movies that the TMDB_ database produces through its API.
    :param int year: optional argument. If defined, then reject any movie not produced that year.
    :param bool verify: optional argument, whether to verify SSL connections. Default is ``False``.
    :returns: the post-processed and filtered :py:class:`list` of movies with fixed and extra data.
    :rtype: list
    """
    moviePosterMainURL = 'https://image.tmdb.org/t/p/w500'
    movieListMainURL = 'https://api.themoviedb.org/3/discover/movie'
    def processIndividualDatum( datum ):
        if 'poster_path' not in datum or datum['poster_path'] is None:
            poster_path = None
        else:
            poster_path = moviePosterMainURL + datum['poster_path']
        if 'vote_average' not in datum:
            vote_average = 0.0
        else:
            if 'vote_count' not in datum or int( datum[ 'vote_count' ] ) <= 10:
                vote_average = 0.0
            else:
                vote_average = float( datum[ 'vote_average' ] )
        try:
            rd = datetime.datetime.strptime( datum['release_date'], '%Y-%m-%d' )
            if year is not None and rd.year != year: return None
            row = {
                'title' : datum[ 'title' ],
                'release_date' : rd,
                'popularity' : datum[ 'popularity' ],
                'vote_average' : vote_average,
                'overview' : datum[ 'overview' ],
                'poster_path' : poster_path,
                'isFound' : False
            }
            if 'id' in datum:
                row[ 'tmdb_id' ] = datum[ 'id' ]
                imdb_id = get_imdbid_from_id( row[ 'tmdb_id' ], verify = verify )
                if imdb_id is not None: row[ 'imdb_id' ] = imdb_id
            return row
        except Exception as e:
            return None

    return list(filter(None, map( processIndividualDatum, results ) ) )
