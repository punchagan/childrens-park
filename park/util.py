#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2011 Puneeth Chaganti <punchagan@gmail.com>
""" Miscellaneous utilites. """
# fixme: move them to their proper homes!

# Standard library
import ast
from functools import wraps
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import logging
from StringIO import StringIO
import smtplib
import sys
from urlparse import urlparse
from urllib2 import urlopen, HTTPError

# Project library
from park.text_processing import strip_tags


class captured_stdout(object):
    """ A context manager to capture anything written to stdout. """

    #### 'contextmanager' protocol ############################################

    def __enter__(self):
        self.stream = StringIO()
        self._output = None
        self.old = sys.stdout
        sys.stdout = self.stream

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._output = self.stream.getvalue()
        sys.stdout = self.old

    #### 'captured_stdout' protocol ###########################################

    @property
    def output(self):
        if self._output is None:
            output = self.stream.getvalue()

        else:
            output = self._output

        return output


# fixme: this should be contributed via a hook, too.
# currently, we don't have a hook for processing all messages before sending...
def dump_message_with_url(path, user, text):
    """ Dump a message to shit.json if it has a url. """

    tokens = text.split()
    urls = [token for token in tokens if is_url(token)]

    if len(urls) == 0:
        return

    from park.serialize import read_state, save_state

    for url in urls:
        data = read_state(path)
        if not data:
            data = []
        entry = {
            'user': user,  # fixme: do we want nick or email?
            'url': url,
            'timestamp': datetime.now().isoformat()
        }
        data.append(entry)
        save_state(path, data)

    return


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


def make_function_main(code):
    """ Rename first function as main, and return (original name, code). """

    functions = [
        element for element in ast.parse(code.strip(), 'string').body
        if isinstance(element, ast.FunctionDef)
    ]

    name = functions[0].name
    code = code.replace('def %s' % name, 'def main')

    return name, code


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


def send_email(fro, to, subject, body, typ_='text', debug=False):
    """ Send an email. """

    if typ_ == 'text':
        msg = MIMEText(body)

    else:
        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(strip_tags(body), 'plain'))
        msg.attach(MIMEText(body, 'html'))

    msg['To'] = to
    msg['From'] = fro
    msg['Subject'] = subject

    if not debug:
        s = smtplib.SMTP()
        s.connect()
        s.sendmail(fro, to, msg.as_string())
        s.quit()

    return msg

#### EOF ######################################################################
