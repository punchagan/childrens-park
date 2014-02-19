from urlparse import urlparse
from urllib2 import urlopen, HTTPError
from inspect import getargs
from itertools import combinations


def is_url(url):
    """ Return True if a string is a url. """

    parsed_url = urlparse(url)

    return parsed_url.scheme and parsed_url.netloc


def get_code_from_url(url):
    """ Return the code as a string, given a url with raw code.

    For GitHub urls, use the raw url.
    """

    try:
        code = urlopen(url).read()
    except HTTPError:
        code = ''
    return code


def possible_signatures():
    possible = list(combinations(['self', 'mess', 'args'], 0)) + \
               list(combinations(['self', 'mess', 'args'], 1)) + \
               list(combinations(['self', 'mess', 'args'], 2)) + \
               list(combinations(['self', 'mess', 'args'], 3))
    return possible


def is_wrappable(f):
    args = tuple(getargs(f.func_code).args)
    possible = possible_signatures()
    return args in possible
