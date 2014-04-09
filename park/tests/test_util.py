#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Puneeth Chaganti <punchagan@muse-amuse.in>
""" Tests for the miscellaneous utilities. """

# Standard library
from os.path import abspath, dirname

# Project library
from park.util import send_email

HERE = dirname(abspath(__file__))


def test_send_html_email():
    # Given
    body = """<html><body> foo </body></html>"""
    fro = 'foo@foo.com'
    to = 'bar@bar.com'
    subject = 'test email'

    # When
    msg = send_email(fro, to, subject, body, typ_='html', debug=True)

    # Then
    assert to in msg.as_string()
    assert fro in msg.as_string()
    assert body in msg.as_string()

    return


def test_send_plain_email():
    # Given
    body = 'foo'
    fro = 'foo@foo.com'
    to = 'bar@bar.com'
    subject = 'test email'

    # When
    msg = send_email(fro, to, subject, body, debug=True)

    # Then
    assert to in msg.as_string()
    assert fro in msg.as_string()
    assert body in msg.as_string()

    return


#### EOF ######################################################################
