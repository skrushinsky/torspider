#!/usr/bin/env python

'''
urlnorm.py - URL normalisation routines
This is clone of http://github.com/jehiah/urlnorm library adapted to Python 3.
'''

from urllib.parse import urlparse, urlunparse, unquote
import re
import idna
import logging
from pprint import pformat

_collapse = re.compile('([^/]+/\.\./?|/\./|//|/\.$|/\.\.$|^\.)')
_server_authority = re.compile('^(?:([^\@]+)\@)?([^\:]+)(?:\:(.+))?$')
_default_port = {
    'http': 80,
    'https': 443,
    'gopher': 70,
    'news': 119,
    'snews': 563,
    'nntp': 119,
    'snntp': 563,
    'ftp': 21,
    'telnet': 23,
    'prospero': 191,
}
_relative_schemes = [
    'http', 'https', 'news', 'snews', 'nntp', 'snntp', 'ftp', 'file', '']
_server_authority_schemes = ['http', 'https', 'news', 'snews', 'ftp',]


def norm(url, domain=None):
    (scheme, authority, path, parameters, query, fragment) = urlparse(url, scheme='http')
    if authority:
        userinfo, host, port = _server_authority.match(authority).groups()
        if host[-1] == '.':
            host = host[:-1]
        authority = host.lower()
        if userinfo:
            authority = "%s@%s" % (userinfo, authority)
        if port and int(port) != _default_port.get(scheme, None):
            authority = "%s:%s" % (authority, port)
    else:
        authority = domain.lower()
    assert authority, '%s: No authority!' % url

    if scheme in _relative_schemes:
        last_path = path
        while 1:
            path = _collapse.sub('/', path, 1)
            if last_path == path:
                break
            last_path = path

    path = unquote(path)
    try:
        authority = idna.decode(authority)
    except Exception as ex:
        logging.warn(ex)

    parts = (scheme, authority, path, parameters, query, "")
    assert not join_parts(parts).startswith('http://http://'), 'Error parsing <%s> (%s)' % (url, pformat(parts))
    return parts

def join_parts(url):
    return urlunparse(url)


def first_level_domain(full_domain):
    return '.'.join(full_domain.split('.')[-2:])

def get_domain(url):
    return urlparse(url)[1]

def get_first_level_domain(url):
    return first_level_domain(get_domain(url))
