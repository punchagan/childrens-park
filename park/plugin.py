#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2011 Puneeth Chaganti <punchagan@gmail.com>
""" Utilites to work with plugins for bot. """

# Standard library
from functools import partial, update_wrapper
from glob import glob
import imp
from inspect import getargspec
import os
from os.path import basename, dirname, splitext
import sys

# 3rd party library
from jabberbot import botcmd

# Project library
from park.util import captured_stdout, requires_subscription


def load_file(path):
    """  Import the file at the given path. """

    _clean_compiled_file(path)
    sys.path.insert(0, dirname(path))
    module = imp.load_source(splitext(basename(path))[0], path)
    sys.path = sys.path[1:]

    return module


def wrap_as_bot_command(bot, function, name):
    """ Wrap the given function as a bot command. """

    is_bot_command = getattr(function, '_jabberbot_command', False)

    if is_bot_command:
       command = function

    else:

        @requires_subscription
        def wrapper(self, message, args):
            f_args = getargspec(function).args
            allowed_args = [bot, message, args]
            n = len(f_args)

            if n <= 3:
                args = allowed_args[3-n:]
                with captured_stdout() as captured:
                    result = function(*args)

                if captured.output:
                    self.message_queue.append(captured.output)

            else:
                result = None

            return result

        wrapper = update_wrapper(partial(wrapper, bot), function)

        command = botcmd(wrapper, name=name)

    return command


#### Private protocol #########################################################

def _clean_compiled_file(path):
    """ Clean the compiled versions .pyc/.pyo of a given file. """

    for f in glob(path+'[co]'):
        os.unlink(f)

    return



#### EOF ######################################################################
