from urlparse import urlparse
from urllib2 import urlopen, HTTPError
from inspect import getargs
from itertools import combinations
from functools import wraps


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
