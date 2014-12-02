#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Puneeth Chaganti <punchagan@muse-amuse.in>
""" Tests for the miscellaneous utilities. """

# Standard library
import base64
from os.path import abspath, dirname

# Project library
from park.util import send_email

HERE = dirname(abspath(__file__))


def test_send_html_email():
    # Given
    body = """<html><body> foo </body></html>"""
    to = 'bar@bar.com'
    subject = 'test email'

    # When
    msg = send_email(to, subject, body, typ_='html', debug=True)

    # Then
    assert to in msg.as_string()
    assert base64.encodestring(body).strip('=\n') in msg.as_string()

    return


def test_send_plain_email():
    # Given
    body = 'foo'
    to = 'bar@bar.com'
    subject = 'test email'

    # When
    msg = send_email(to, subject, body, debug=True)

    # Then
    assert to in msg.as_string()
    assert base64.encodestring(body).strip('=\n') in msg.as_string()

    return


#### EOF ######################################################################
