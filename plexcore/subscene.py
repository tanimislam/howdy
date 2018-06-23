# -*- coding: utf-8 -*-
# vim: fenc=utf-8 ts=4 et sw=4 sts=4

# This file is part of Subscene-API.
#
# Subscene-API is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Subscene-API is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Python wrapper for Subscene subtitle database.

since Subscene doesn't provide an official API, I wrote
this script that does the job by parsing the website"s pages.
"""

# imports
import re, enum, sys, cfscrape
if sys.version_info.major >= 3: from contextlib import suppress
from bs4 import BeautifulSoup

# constants
HEADERS = {
    "User-Agent": ''.join([ "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWeb",
                            "Kit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safa",
                            "ri/537.36" ])
}
SITE_DOMAIN = "https://subscene.com"
_scraper = cfscrape.create_scraper( )

# utils
def soup_for(url, params):
    response = _scraper.get( url, headers = HEADERS, params = params )
    html = response.content.decode("utf-8")
    return BeautifulSoup(html, "lxml")

class AttrDict( object ):
    def __init__(self, *attrs):
        self._attrs = attrs

        for attr in attrs:
            setattr(self, attr, "")

    def to_dict(self):
        return {k: getattr(self, k) for k in self._attrs}


# models
@enum.unique
class SearchTypes(enum.Enum):
    Exact = 1
    TvSerie = 2
    Popular = 3
    Close = 4


SectionsParts = {
    SearchTypes.Exact: "Exact",
    SearchTypes.TvSerie: "TV-Series",
    SearchTypes.Popular: "Popular",
    SearchTypes.Close: "Close"
}


class Subtitle( object ):
    def __init__(self, title, url, language, owner_username, owner_url,
                 description):
        self.title = title
        self.url = url
        self.language = language
        self.owner_username = owner_username
        self.owner_url = owner_url
        self.description = description

        self._zipped_url = None

    def __str__(self):
        return self.title

    @classmethod
    def from_rows(cls, rows):
        subtitles = []

        for row in rows:
            if row.td.a is not None:
                subtitles.append(cls.from_row(row))

        return subtitles

    @classmethod
    def from_row(cls, row):
        attrs = AttrDict("title", "url", "language", "owner_username",
                         "owner_url", "description")
        if sys.version_info.major >= 3:
            with suppress(Exception):
                attrs.title = row.find("td", "a1").a.find_all("span")[1].text.strip()
                
            with suppress(Exception):
                attrs.url = SITE_DOMAIN + row.find("td", "a1").a.get("href")

            with suppress(Exception):
                attrs.language = row.find("td", "a1").a.find_all("span")[0].text.strip()
                
            with suppress(Exception):
                attrs.owner_username = row.find("td", "a5").a.text.strip()

            with suppress(Exception):
                attrs.owner_page = SITE_DOMAIN + row.find("td", "a5").a.get("href").strip()
                
            with suppress(Exception):
                attrs.description = row.find("td", "a6").div.text.strip()
        else:
            try: attrs.title = row.find("td", "a1").a.find_all("span")[1].text.strip()                
            except: pass
            
            try: attrs.url = SITE_DOMAIN + row.find("td", "a1").a.get("href")
            except: pass

            try: attrs.language = row.find("td", "a1").a.find_all("span")[0].text.strip()
            except: pass

            try: attrs.owner_username = row.find("td", "a5").a.text.strip()
            except: pass

            try: ttrs.owner_page = SITE_DOMAIN + row.find("td", "a5").a.get("href").strip()
            except: pass

            try: attrs.description = row.find("td", "a6").div.text.strip()
            except: pass
            
        return cls(**attrs.to_dict())

    @property
    def zipped_url(self):
        if self._zipped_url:
            return self._zipped_url

        soup = soup_for(self.url)
        self._zipped_url = SITE_DOMAIN + soup.find("div", "download").a \
            .get("href")
        return self._zipped_url


class Film( object ):
    def __init__(self, title, year=None, imdb=None, cover=None,
                 subtitles=None):
        self.title = title
        self.year = year
        self.imdb = imdb
        self.cover = cover
        self.subtitles = subtitles

    def __str__(self):
        return self.title

    @classmethod
    def from_url(cls, url):
        soup = soup_for(url)

        content = soup.find("div", "subtitles")
        header = content.find("div", "box clearfix")

        try:
            cover = header.find("div", "poster").img.get("src")
        except:
            cover = None

        title = header.find("div", "header").h2.text[:-12].strip()

        imdb = header.find("div", "header").h2.find("a", "imdb").get("href")

        year = header.find("div", "header").ul.li.text
        year = int(re.findall(r"[0-9]+", year)[0])

        rows = content.find("table").tbody.find_all("tr")
        subtitles = Subtitle.from_rows(rows)

        return cls(title, year, imdb, cover, subtitles)


# functions
def section_exists(soup, section):
    tag_part = SectionsParts[section]

    try:
        headers = soup.find("div", "search-result").find_all("h2")
    except AttributeError:
        return False

    for header in headers:
        if tag_part in header.text:
            return True
    return False


def get_first_film(soup, section):
    tag_part = SectionsParts[section]
    tag = None

    headers = soup.find("div", "search-result").find_all("h2")
    for header in headers:
        if tag_part in header.text:
            tag = header
            break
    if not tag:
        return

    url = SITE_DOMAIN + tag.findNext("ul").find("li").div.a.get("href")
    return Film.from_url(url)


def search(term, language="", limit_to=SearchTypes.Exact):
    params = { 'q' : re.sub("\s", "+", term),
               'l' : language }
    soup = soup_for("%s/subtitles/title" % SITE_DOMAIN,
                    params = params )
    with open('sub.html', 'w') as openfile:
        openfile.write('%s\n' % soup.prettify( ) )
    
    if "Subtitle search by" in str(soup):
        rows = soup.find("table").tbody.find_all("tr")
        subtitles = Subtitle.from_rows(rows)
        return Film(term, subtitles=subtitles)

    for junk, search_type in SearchTypes.__members__.items():
        if section_exists(soup, search_type):
            return get_first_film(soup, search_type)

        if limit_to == search_type:
            return
