import json
import logging
from urlparse import urlparse
from urllib2 import urlopen, HTTPError
from inspect import getargs
from itertools import combinations
from functools import wraps


def install_log_handler():
    """ Install a log handler. """

    # create console handler
    chandler = logging.StreamHandler()

    # create formatter
    fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(fmt)

    # add formatter to handler
    chandler.setFormatter(formatter)

    # add handler to logger
    log = logging.getLogger()
    log.addHandler(chandler)

    # set level to INFO
    log.setLevel(logging.INFO)

    return


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


def google(query):
    """ Query the string on google and return the top most result. """

    url = 'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&%s'

    results = urlopen(url % query)
    data = json.loads(results.read())
    top = data.get('responseData', {}).get('results', [{}])[0]

    if 'title' in top and 'url' in top:
        result = '%s -- %s' % (top['title'], top['url'])

    else:
        result = None

    return result


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


def requires_invite(f):
    """ Decorator to ensure that a user is atleast invited

    Can be subscribed, obviously!

    """

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        message = args[0]
        user = self.get_sender_username(message)
        if user not in self.users and user not in self.invited:
            message = 'You atleast need to be invited!'

        else:
            message = f(self, user, *args[1:], **kwargs)

        return message

    return wrapper


def requires_subscription(f):
    """ Decorator to ensure that a user is subscribed. """

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        message = args[0]
        user = self.get_sender_username(message)
        if user not in self.users:
            message = (
                'You are not subscribed! Use %s to subscribe' %
                self.subscribe._jabberbot_command_name
            )

        else:
            message = f(self, user, *args[1:], **kwargs)

        return message

    return wrapper
