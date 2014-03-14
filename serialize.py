#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Puneeth Chaganti <punchagan@muse-amuse.in>
""" Utilities for serializing and de-serializing the bot. """

# Standard library.
import json
from os.path import exists


def read_state(path):
    """ Return the saved info from the given path. """

    state = {}

    if exists(path):
        with open(path) as f:
            try:
                state.update(json.load(f))
                # fixme: log
            except ValueError:
                pass

    return state


def save_state(path, state):
    """ Save the given state to the given path. """

    with open(path, 'w') as f:
        json.dump(state, f, indent=2)

    return
