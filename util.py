from urlparse import urlparse
from urllib2 import urlopen, HTTPError
from inspect import getargs
from itertools import combinations

def is_gist_url(url):
    parsed_url = urlparse(url)
    if parsed_url.netloc != 'gist.github.com':
        return False
    else:
        return parsed_url

def get_code_from_gist(url):
    """ Return the code as a string, given a gist's url.
    """
    parsed_url = is_gist_url(url)
    if not parsed_url:
        return ''
    gist_id = parsed_url.path.strip('/')
    raw_url = 'https://raw.github.com/gist/%s' % gist_id
    try:
        code = urlopen(raw_url).read()
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
    if len(args) not in (1, 2, 3):
        return False
    possible = possible_signatures()
    return args in possible
