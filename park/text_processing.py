#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Puneeth Chaganti <punchagan@muse-amuse.in>
""" Utilities for processing text messages. """


def chunk_text(text, limit=512, messages=None):
    """ Chunk a text message into a messages of length less than limit. """

    if messages is None:
        messages = []

    if len(text) > limit:
        idx = (
            (text.rfind('\n', 0, limit) + 1) or (text.rfind(' ', 0, limit) + 1)
        )
        if idx == 0:
            idx = limit

        chunk_text(text[idx:], limit=limit, messages=messages)
        messages.append(text[:idx])

    else:
        messages.append(text)

    return messages[::-1]
