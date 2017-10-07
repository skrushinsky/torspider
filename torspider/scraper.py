import logging
import re

from tornado import httpclient
from tornado.httputil import HTTPHeaders
from tornado.options import options

from dateutil.parser import parse as parse_datetime
from bs4 import BeautifulSoup as Soup, Comment
from langdetect import detect

from urlnorm import norm, join_parts

ALLOW_SCHEMES = ('http', 'https')
ALLOWED_TYPES = ('text/html')
ALLOWED_LANGS = ('ru', 'en')
SAVE_HEADERS = (
    'Content-Encoding', 'Content-Language', 'Content-Length', 'Content-Location',
    'Content-MD5', 'Content-Type', 'Date', 'ETag', 'Expires', 'Last-Modified',
    'Link', 'Retry-After', 'Server', 'Via', 'Warning', 'Status', 'X-Powered-By',
    'X-UA-Compatible'
)
MAX_CONTENT_SIZE = 1024  # Kb
DEFAULT_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:28.0) Gecko/20100101 Firefox/28.0'
DEFAULT_HEADERS = HTTPHeaders({
    'Accept': ','.join(ALLOWED_TYPES),
    'Accept-Charset': 'utf-8, windows-1251;q=0.5, koi8-r;q=0.3, *;q=0.3',
    'Accept-Language': 'ru, en;q=0.7',
})

httpclient.AsyncHTTPClient.configure(
    "tornado.curl_httpclient.CurlAsyncHTTPClient",
    defaults=dict(user_agent=DEFAULT_AGENT)
)


# remove these tags, complete with contents.
SKIP_TAGS = ("script", "style", "form", "input")

class Page():
    """
    Parse HTML page.
    All page attributes are available as lazily initialized properties.

    Arguments:
        url : target URL (str)
        response : tornado.httpclient.HTTPResponse instance
    """

    def __init__(self, url, response):
        self.url = url
        self.response = response
        self._base = None
        self._soup = None
        self._title = None
        self._meta = None
        self._text = None
        self._language = None
        self._links = None
        self._headers = None

    @property
    def soup(self):
        """BeautifulSoup tree."""
        if self._soup is None:
            self._soup = Soup(self.response.body, 'lxml')
        return self._soup

    @property
    def base(self):
        """<base> header value is any, or response.effective_url domain name.
        """
        if self._base is None:
            if self.soup.base:
                self._base = self.soup.base.get('href')
            if not self._base:
                logging.debug('No <base> header. Using response domain name')
                self._base = norm(self.response.effective_url)[1]
        return self._base

    @property
    def title(self):
        """<title> header, if any, or the first found heading."""
        if not self._title:
            if self.soup.title and self.soup.title.string:
               self._title = self.soup.title.string.strip()
            if not self._title:
                logging.debug('Page title not found. Searching headings...')
                body = self.soup.body
                for i in range(5):
                    h = body.find('h{%d}' % (i+1))
                    if h:
                        self._title = h.string
                        break
        return self._title

    def _iter_meta(self):
        for tag in self.soup.find_all('meta'):
            k = tag.get('property', tag.get('name'))
            if k:
                v = tag.get('content')
                if v:
                    yield k, v

    @property
    def meta(self):
        """Page meta tags as dictionary."""
        if self._meta is None:
            self._meta = {k: v for k, v in self._iter_meta()}
        return self._meta

    def _sanitize(self, soup):
        # now strip HTML we don't like.
        for tag in soup.findAll():
            if tag.name.lower() in SKIP_TAGS:
                # blacklisted tags are removed in their entirety
                tag.extract()

        # scripts can be executed from comments in some cases
        comments = soup.findAll(text=lambda text:isinstance(text, Comment))
        for com in comments:
            com.extract()

    @property
    def text(self):
        """Page text converted to markup format."""
        if self._text is None:
            #doc = Document(str(self.soup.body))
            body = Soup(str(self.soup.body), 'lxml')
            self._sanitize(body)
            self._text = body.get_text(' ')
            self._text = re.sub(r'\s{2,}', ' ', self._text)
            self._text = re.sub(r'\s*\n\s*', '\n', self._text)
            self._text = re.sub(r'\n{2,}', '\n', self._text)
            self._text = re.sub(r'\s+\.\s+', '. ', self._text)
            self._text = self._text.strip()

            #self._text = html2text(str(self.soup.body))
        return self._text

    @property
    def language(self):
        """Detected page language."""
        if self._language is None:
            self._language = detect(self.text)
        return self._language

    def _iter_links(self):
        for a in self.soup.find_all('a', href=True):
            url = norm(a['href'], self.base)
            if not url[0] in ALLOW_SCHEMES:
                logging.warning('Skipping scheme <%s>', url[0])
            else:
                yield join_parts(url)

    @property
    def links(self):
        """Set of normalized links found inside the page <body>."""
        if self._links is None:
            self._links = {url for url in self._iter_links()}
        return self._links

    def _parse_header(self, k, v):
        lk = k.lower()
        if lk in ('date', 'expires', 'last-modified'):
            return parse_datetime(v)
        if lk in ('content-length', 'status'):
            return int(v)
        return v

    @property
    def headers(self):
        """Some usefull data from HTTP response headers"""
        if self._headers is None:
            self._headers = {
                k: self._parse_header(k, v) for (k, v) in sorted(
                    self.response.headers.get_all())
                if k in SAVE_HEADERS
            }
        return self._headers


    def as_dict(self):
        report = {}
        if self.title:
            report['title'] = self.title
        if self.title:
            report['text'] = self.text
        if self.meta:
            report['meta'] = self.meta
        if self.language:
            report['language'] = self.language
        if self.links:
            report['links'] = list(self.links)
        if self.headers:
            report['headers'] = self.headers

        return report

class Client():
    """Asyncroneous HTTP client.
    """
    def __init__(self):
        self.client = httpclient.AsyncHTTPClient()
        self.req_options = dict(
            headers = DEFAULT_HEADERS,
            validate_cert = False,
        )
        if options.proxy:
            logging.debug('Using proxy: %s', options.proxy)
            h, p = options.proxy.split(':')
            self.req_options['proxy_host'] = h
            self.req_options['proxy_port'] = int(p)
        else:
            logging.debug('Working without proxy')

        logging.debug('Using timeout: %.1f', options.timeout)
        self.req_options['connect_timeout'] = options.connect_timeout
        self.req_options['request_timeout'] = options.request_timeout
        self.req_options['validate_cert'] = options.validate_cert

    def _validate_headers(self, headers):
        """If anything is wrong with HTTP headers, raise AssertionError."""
        h = headers.get('Content-Type')
        if h:
            v = h.split(';')[0].strip()
            assert v in ALLOWED_TYPES, 'Illegal  Content-Type: %s' % h

        h = headers.get('Content-Language')
        if h:
            langs = [x.strip().lower() for x in h.split(',')]
            assert set(langs).intersection(ALLOWED_LANGS), 'Illegal Content-Language: %s' % h

        h = headers.get('Content-Length')
        if h:
            v = int(h) / 1024
            assert v <= MAX_CONTENT_SIZE, 'Content size %d exceeds %dKb' % (v, MAX_CONTENT_SIZE)
        logging.debug('Headers OK.')


    async def visit(self, url):
        req = httpclient.HTTPRequest(url, **self.req_options)
        res = await self.client.fetch(req)
        logging.info('%s: %s - %s', res.effective_url, res.code, res.reason)
        self._validate_headers(res.headers)
        return res
