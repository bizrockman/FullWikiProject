from __future__ import unicode_literals

import requests
import time
import mwparserfromhell
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from wikipedia.exceptions import (HTTPTimeoutError, WikipediaException, PageError, DisambiguationError,
                                  RedirectError, ODD_ERROR_MESSAGE)
from wikipedia.util import cache, stdout_encode
from wikipedia import wikipedia

API_URL = 'http://en.wikipedia.org/w/api.php'
RATE_LIMIT = False
RATE_LIMIT_MIN_WAIT = timedelta(milliseconds=50)
RATE_LIMIT_LAST_CALL = None
USER_AGENT = 'wikipedia (https://github.com/goldsmith/Wikipedia/)'


def set_lang(prefix):
    """
      Change the language of the API being requested.
      Set `prefix` to one of the two letter prefixes found on the `list of all Wikipedias <http://meta.wikimedia.org/wiki/List_of_Wikipedias>`_.

      After setting the language, the cache for ``search``, ``suggest``, and ``summary`` will be cleared.

      .. note:: Make sure you search for page titles in the language that you have set.
    """

    global API_URL
    API_URL = 'http://' + prefix.lower() + '.wikipedia.org/w/api.php'

    #for cached_func in (search):
    #    cached_func.clear_cache()


def set_user_agent(user_agent_string):
    """
      Set the User-Agent string to be used for all requests.

      Arguments:

      * user_agent_string - (string) a string specifying the User-Agent header
    """
    global USER_AGENT
    USER_AGENT = user_agent_string


def set_rate_limiting(rate_limit, min_wait=timedelta(milliseconds=50)):
    """
      Enable or disable rate limiting on requests to the Mediawiki servers.
      If rate limiting is not enabled, under some circumstances (depending on
      load on Wikipedia, the number of requests you and other `wikipedia` users
      are making, and other factors), Wikipedia may return an HTTP timeout error.

      Enabling rate limiting generally prevents that issue, but please note that
      HTTPTimeoutError still might be raised.

      Arguments:

      * rate_limit - (Boolean) whether to enable rate limiting or not

      Keyword arguments:

      * min_wait - if rate limiting is enabled, `min_wait` is a timedelta describing the minimum time to wait before requests.
             Defaults to timedelta(milliseconds=50)
    """
    global RATE_LIMIT
    global RATE_LIMIT_MIN_WAIT
    global RATE_LIMIT_LAST_CALL

    RATE_LIMIT = rate_limit
    if not rate_limit:
        RATE_LIMIT_MIN_WAIT = None
    else:
        RATE_LIMIT_MIN_WAIT = min_wait

    RATE_LIMIT_LAST_CALL = None


def search(query, results=10, suggestion=False):
    """
      Do a Wikipedia search for `query`.

      Keyword arguments:

      * results - the maxmimum number of results returned
      * suggestion - if True, return results and suggestion (if any) in a tuple
    """

    search_params = {
        'list': 'search',
        'srprop': '',
        'srlimit': results,
        'limit': results,
        'srsearch': query
    }
    if suggestion:
        search_params['srinfo'] = 'suggestion'
    print("Current API URL: ", API_URL, " using query ", query  )
    raw_results = _wiki_request(search_params)
    print(raw_results)
    if 'error' in raw_results:
        if raw_results['error']['info'] in ('HTTP request timed out.', 'Pool queue is full'):
            raise HTTPTimeoutError(query)
        else:
            raise WikipediaException(raw_results['error']['info'])

    search_results = (d['title'] for d in raw_results['query']['search'])

    if suggestion:
        if raw_results['query'].get('searchinfo'):
            return list(search_results), raw_results['query']['searchinfo']['suggestion']
        else:
            return list(search_results), None

    return list(search_results)


def page(title=None, pageid=None, auto_suggest=True, redirect=True, preload=False):
    """
      Get a WikipediaPage object for the page with title `title` or the pageid
      `pageid` (mutually exclusive).

      Keyword arguments:

      * title - the title of the page to load
      * pageid - the numeric pageid of the page to load
      * auto_suggest - let Wikipedia find a valid page title for the query
      * redirect - allow redirection without raising RedirectError
      * preload - load content, summary, images, references, and links during initialization
    """

    if title is not None:
        if auto_suggest:
            results, suggestion = search(title, results=1, suggestion=True)
            try:
                title = suggestion or results[0]
            except IndexError:
                # if there is no suggestion or search results, the page doesn't exist
                raise PageError(title)
        return WikipediaPage(title, redirect=redirect, preload=preload)
    elif pageid is not None:
        return WikipediaPage(pageid=pageid, preload=preload)
    else:
        raise ValueError("Either a title or a pageid must be specified")


def _wiki_request(params):
    """
      Make a request to the Wikipedia API using the given search parameters.
      Returns a parsed dict of the JSON response.
    """
    global RATE_LIMIT_LAST_CALL
    global USER_AGENT

    params['format'] = 'json'
    if not 'action' in params:
        params['action'] = 'query'

    headers = {
        'User-Agent': USER_AGENT
    }

    if RATE_LIMIT and RATE_LIMIT_LAST_CALL and \
            RATE_LIMIT_LAST_CALL + RATE_LIMIT_MIN_WAIT > datetime.now():
        # it hasn't been long enough since the last API call
        # so wait until we're in the clear to make the request

        wait_time = (RATE_LIMIT_LAST_CALL + RATE_LIMIT_MIN_WAIT) - datetime.now()
        time.sleep(int(wait_time.total_seconds()))

    r = requests.get(API_URL, params=params, headers=headers)

    if RATE_LIMIT:
        RATE_LIMIT_LAST_CALL = datetime.now()

    return r.json()


@cache
def get_image_url(filename):
    params = {
        "prop": "imageinfo",
        "titles": f"File:{filename}",
        "iiprop": "url"
    }

    raw_results = _wiki_request(params)

    page = next(iter(raw_results['query']['pages'].values()))
    image_info = page['imageinfo'][0]
    image_url = image_info['url']
    return image_url


class WikipediaPage(object):
    """
      Contains data from a Wikipedia page.
      Uses property methods to filter data from the raw HTML.
    """

    def __init__(self, title=None, pageid=None, redirect=True, preload=False, original_title=''):
        if title is not None:
            self.title = title
            self.original_title = original_title or title
        elif pageid is not None:
            self.pageid = pageid
        else:
            raise ValueError("Either a title or a pageid must be specified")

        self.__load(redirect=redirect, preload=preload)

        self._extract = None
        self._content = None
        self._image_name = None

        if preload:
            self.load_content()

    def __repr__(self):
        return stdout_encode(u'<WikipediaPage \'{}\'>'.format(self.title))

    def __eq__(self, other):
        try:
            return (
                    self.pageid == other.pageid
                    and self.title == other.title
                    and self.url == other.url
            )
        except:
            return False

    def __load(self, redirect=True, preload=False):
        """
        Load basic information from Wikipedia.
        Confirm that page exists and is not a disambiguation/redirect.

        Does not need to be called manually, should be called automatically during __init__.
        """

        query_params = {
            'prop': 'info|pageprops',
            'inprop': 'url',
            'ppprop': 'disambiguation',
            'redirects': '',
        }
        if not getattr(self, 'pageid', None):
            query_params['titles'] = self.title
        else:
            query_params['pageids'] = self.pageid

        request = _wiki_request(query_params)

        query = request['query']
        pageid = list(query['pages'].keys())[0]
        page = query['pages'][pageid]

        # missing is present if the page is missing
        if 'missing' in page:
            if hasattr(self, 'title'):
                raise PageError(self.title)
            else:
                raise PageError(pageid=self.pageid)

        # same thing for redirect, except it shows up in query instead of page for
        # whatever silly reason
        elif 'redirects' in query:
            if redirect:
                redirects = query['redirects'][0]

                if 'normalized' in query:
                    normalized = query['normalized'][0]
                    assert normalized['from'] == self.title, ODD_ERROR_MESSAGE

                    from_title = normalized['to']

                else:
                    from_title = self.title

                assert redirects['from'] == from_title, ODD_ERROR_MESSAGE

                # change the title and reload the whole object
                self.__init__(redirects['to'], redirect=redirect, preload=preload)

            else:
                raise RedirectError(getattr(self, 'title', page['title']))

        # since we only asked for disambiguation in ppprop,
        # if a pageprop is returned,
        # then the page must be a disambiguation page
        elif 'pageprops' in page:
            query_params = {
                'prop': 'revisions',
                'rvprop': 'content',
                'rvparse': '',
                'rvlimit': 1
            }
            if hasattr(self, 'pageid'):
                query_params['pageids'] = self.pageid
            else:
                query_params['titles'] = self.title

            request = _wiki_request(query_params)
            html = request['query']['pages'][pageid]['revisions'][0]['*']

            lis = BeautifulSoup(html, features="html.parser").find_all('li')
            filtered_lis = [li for li in lis if not 'tocsection' in ''.join(li.get('class', []))]
            may_refer_to = [li.a.get_text() for li in filtered_lis if li.a]
            #if may_refer_to[0]:
            #    return WikipediaPage(may_refer_to[0], redirect=redirect, preload=preload)

            raise DisambiguationError(getattr(self, 'title', page['title']), may_refer_to)

        else:
            self.pageid = pageid
            self.title = page['title']
            self.url = page['fullurl']

    def load_content(self):
        """
            Plain text content of the page, excluding images, tables, and other data.
        """

        if not getattr(self, '_content', False):
            query_params = {
                'prop': 'extracts|revisions|pageimages',
                'explaintext': '',
                "rvprop": "content",
                "rvslots": "main",
                "formatversion": "2",
                "format": "json"
            }
            if not getattr(self, 'title', None) is None:
                query_params['titles'] = self.title
            else:
                query_params['pageids'] = self.pageid
            print(query_params)
            request = _wiki_request(query_params)

            self._extract = request['query']['pages'][0]['extract']
            self._content = request['query']['pages'][0]['revisions'][0]['slots']['main']['content']
            print(request['query']['pages'][0].keys())
            print(request['query']['pages'][0].get('pageimage'))
            self._image_name = request['query']['pages'][0]['pageimage']

    @property
    def content(self):
        if not self._content:
            self.load_content()

        return self._content

    @property
    def extract(self):
        if not self._extract:
            self.load_content()

        return self._extract

    @property
    def image_name(self):
        if not self._image_name:
            self.load_content()

        return self._image_name

    @property
    def infobox(self):
        page_content = self.content
        wikicode = mwparserfromhell.parse(page_content)

        infoboxes = wikicode.filter_templates(matches="Infobox")

        if not infoboxes:
            return None

        infobox = infoboxes[0]  # Nehmen wir die erste gefundene Infobox
        # print(infobox)
        infobox_data = {}

        for param in infobox.params:
            param_name = str(param.name).strip()
            param_value = str(param.value).strip()
            # Bereinigen und Entfernen von übermäßigem Wikitext
            param_value_clean = mwparserfromhell.parse(param_value).strip_code()
            infobox_data[param_name] = param_value_clean

        return infobox_data
