import requests, plextmdb, os, re
import sys, zipfile, codecs
from urlparse import urljoin
from bs4 import BeautifulSoup
from io import BytesIO
from plexcore import subscene

def get_subtitles_subscene2( title, extra_strings = [ ] ):
    film = subscene.search( title )
    subtitles = filter(lambda subtitle: subtitle.language == 'English', film.subtitles )
    if len( extra_strings ) != 0:
        subtitles = filter(lambda subtitle: any(map(lambda tok: tok.lower( ) in subtitle.title.lower( ),
                                                    set( extra_strings) ) ), subtitles )
    if len( subtitles ) == 0:
        return None
    subtitles_map = { }
    for subtitle in subtitles:
        title = subtitle.title
        if title not in subtitles_map:
            subtitles_map[ title ] = subtitle
    return subtitles_map
    
def get_subtitles_subscene( title ):
    response = requests.get( 'https://subscene.com/subtitles/title',
                             params = { 'q' : title, 'l' : 'english' } )
    if response.status_code != 200:
        return None
    html = BeautifulSoup( response.content, 'lxml' )
    header = filter(lambda elem: elem.get_text( ) == 'Exact', html.find('div', 'search-result').find_all('h2') )
    if len( header ) != 1:
        return None
    header = max( header )

    film_url = urljoin( 'https://subscene.com',
                        header.findNext('ul').find('li').div.a.get('href') )
    #
    ## now load this url
    response2 = requests.get( film_url )
    if response2.status_code != 200:
        return None
    html2 = BeautifulSoup( response2.content, 'lxml' )
    content = html2.find('div', 'subtitles')
    header = content.find('div', 'box clearfix')
    cover = header.find('div', 'poster').img.get('src')
    title = header.find('div', 'header').h2.text
    def from_rows( rows ):
        subtitles = filter(None, map(from_row, filter(lambda row: row.td.a is not None, rows ) ) )
        return subtitles

    def from_row( row ):
        try:
            title = row.find('td', 'a1').a.find_all('span')[1].text
        except:
            title = ''
        title = title.strip()
        
        try:
            page = urljoin( 'https://subscene.com', row.find('td', 'a1').a.get('href') )
        except:
            page = ''
        if page == '':
            return None
        
        try:
            language = row.find('td', 'a1').a.find_all('span')[0].text
        except:
            language = ''
        language = language.strip()
        if language != '':
            if language.lower( ) != 'english':
                return None

        owner = {}
        try:
            owner_username = row.find('td', 'a5').a.text
        except:
            owner_username = ''
        owner['username'] = owner_username.strip()
        try:
            owner_page = row.find('td', 'a5').a.get('href')
            owner['page'] = urljoin( 'https://subscene.com', owner_page.strip() )
        except:
            owner['page'] = ''
            
        try:
            comment = row.find('td', 'a6').div.text
        except:
            comment = ''
        comment = comment.strip()
        #
        ## now get the name, and SRT file, for this subtitle
        response = requests.get( page )
        if response.status_code != 200:
            return None
        html = BeautifulSoup( response.content, 'lxml' )
        zipurl = urljoin( 'https://subscene.com', html.find('div', 'download').a.get('href') )
        try:
            with zipfile.ZipFile( BytesIO( requests.get( zipurl ).content ), 'r' ) as zf:
                name = max( zf.namelist( ) )
                srtdata = zf.read( name )
                return { 'title' : title, 'name' : name, 'owner' : owner,
                         'comment' : comment, 'srtdata' : srtdata }
        except:
            return None
        
    
    imdb = header.find('div', 'header').h2.find('a', 'imdb').get('href')    
    year = header.find('div', 'header').ul.li.text
    year = int(re.findall(r'[0-9]+', year)[0])

    rows = content.find('table').tbody.find_all('tr')    
    subtitles = from_rows( rows )
    names_exact = [ ]
    subtitles_unique = [ ]
    for subtitle in subtitles:
        name = subtitle[ 'name' ]
        if name not in names_exact:
            names_exact.append( name )
            subtitles_unique.append( subtitle )
    return { 'title' : title, 'year' : year, 'imdb' : imdb, 'cover' : cover,
             'subtitles' : subtitles_unique }

def get_subtitles_yts( title ):
    tmdbid = plextmdb.get_movie_tmdbids( title )
    if tmdbid is None:
        return None
    imdbid = plextmdb.get_imdbid_from_id( int( tmdbid ) )
    if imdbid is None:
        return None
    #
    ## now get the main page for the YTS subtitles
    ## code inspired by https://github.com/kartouch/yts/blob/master/lib/yts.rb
    response = requests.get('http://www.yifysubtitles.com/movie-imdb/%s' % imdbid )
    if response.status_code != 200:
        return None
    html = BeautifulSoup( response.content, 'lxml' )
    def is_english_subtitle( elem ):
        if 'data-id' not in elem.attrs:
            return False
        #
        ## language elem
        lang_elems = filter(lambda elm: 'class' in elm.attrs and max(elm.attrs['class']) == 'sub-lang', elem.find_all('span'))
        if len( lang_elems ) != 1:
            return False
        lang_elem = max( lang_elems )
        language = lang_elem.get_text( ).lower( )
        return language == 'english'

    valid_st_elems = filter( is_english_subtitle, html.find_all('tr') )[:5]
    if len( valid_st_elems ) == 0:
        return None
    valid_subs = [ ]
    for subtitle_elem in valid_st_elems:
        first_href = filter(lambda elm: elm.text.strip().startswith('subtitle'), subtitle_elem.find_all('a'))
        if len( first_href ) != 1:
            continue
        first_href = max( first_href )
        name = ' '.join( first_href.text.strip( ).split( )[1:] )
        last_href = filter(lambda elm: 'class' in elm.attrs and max(elm.attrs['class']) == 'subtitle-download',
                           subtitle_elem.find_all('a'))
        if len( last_href ) != 1:
            continue
        last_href = max( last_href )
        pageurl = urljoin( 'http://www.yifysubtitles.com', last_href.attrs['href'] )
        resp2 = requests.get( pageurl )
        if resp2.status_code != 200:
            continue
        html2 = BeautifulSoup( resp2.content, 'lxml' )
        button_elem = filter(lambda elm: 'href' in elm.attrs and elm.attrs['href'].endswith('.zip'), html2.find_all('a'))
        if len( button_elem ) != 1:
            continue
        button_elem = max( button_elem )
        url = button_elem.attrs['href']
        if not url.endswith('zip'):
            continue
        valid_subs.append({ 'name' : name, 'url' : url })
    if len( valid_subs ) == 0:
        return None
    return valid_subs

def download_yts_sub( url, srtfilename = 'eng.srt' ):
    assert( srtfilename.endswith( '.srt' ) )
    assert( url.endswith( '.zip' ) )
    response = requests.get( url )
    if response.status_code != 200:
        raise ValueError("Error, could not download %s." % url )
    with zipfile.ZipFile( BytesIO( response.content ), 'r' ) as zf:
        name = max( zf.namelist( ) )
        if not name.endswith('.srt'):
            raise ValueError("Error, name = %s does not end with srt." % name )
        #with codecs.open( srtfilename, 'w', 'utf-8' ) as openfile:
        with open( srtfilename, 'w') as openfile:
            openfile.write( zf.read( name ) )
