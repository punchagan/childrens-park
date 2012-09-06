from urlparse import urlparse
from urllib2 import urlopen, HTTPError

def get_code_from_gist(url):
    """ Return the code as a string, given a gist's url.
    """
    parsed_url = urlparse(url)
    if parsed_url.netloc != 'gist.github.com':
        return ''
    gist_id = parsed_url.path.strip('/')
    raw_url = 'https://raw.github.com/gist/%s' %gist_id
    try:
        code = urlopen(raw_url).read()
    except HTTPError:
        code = ''
    return code