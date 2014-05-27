#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2011 Puneeth Chaganti <punchagan@gmail.com>
""" Miscellaneous utilites. """
# fixme: move them to their proper homes!

# Standard library
import ast
from functools import wraps
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import logging
from logging.handlers import TimedRotatingFileHandler
from StringIO import StringIO
import smtplib
import sys
from urlparse import urlparse
from urllib2 import unquote, urlopen, HTTPError

# 3rd party library
from jinja2 import Template

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


def install_log_handler(filename, debug=False):
    """ Install a log handler. """

    if debug:
        handler = logging.StreamHandler()

    else:
        handler = TimedRotatingFileHandler(filename, when='W0')

    # create formatter
    fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(fmt)

    # add formatter to handler
    handler.setFormatter(formatter)

    # add handler to logger
    log = logging.getLogger()
    log.addHandler(handler)

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
        result = '%s -- %s' % (top['title'], unquote(top['url']))

    else:
        result = None

    return result


def render_template(path, context):
    """  Render the given template using the given context. """

    with open(path) as f:
        template = Template(f.read())

    return template.render(**context)


def requires_invite(f):
    """ Decorator to ensure that a user is at least invited

    Can be subscribed, obviously!

    """

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        message = args[0]
        user = self.get_sender_username(message)

        name = getattr(f, '_jabberbot_command_name', None)
        if name is not None:
            self.log.info('%s called %s with %s' % (user, name, args[1:]))

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

        name = getattr(f, '_jabberbot_command_name', None)
        if name is not None:
            self.log.info('%s called %s with %s' % (user, name, args[1:]))

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

    msg['To'] = ', '.join(to) if isinstance(to, list) else to
    msg['From'] = fro
    msg['Subject'] = subject

    if not debug:
        s = smtplib.SMTP()
        s.connect()
        s.sendmail(fro, to, msg.as_string())
        s.quit()

    else:
        print msg.as_string()

    return msg

#### EOF ######################################################################
