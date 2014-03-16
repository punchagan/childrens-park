#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2011 Puneeth Chaganti <punchagan@gmail.com>
""" Utilites to work with plugins for bot. """

# Standard library
from functools import wraps
from glob import glob
from inspect import getargspec
from os.path import basename, join, splitext
import sys

# 3rd party library
from jabberbot import botcmd

# Project library
from park.util import requires_subscription

class PluginLoader(object):
    """ A class to load plugins from a plugin directory. """

    def __init__(self, plugin_dir):
        self.plugin_dir = plugin_dir
        self._plugins = None
        return

    @property
    def plugins(self):
        """ The list of discovered plugins. """

        if self._plugins is None:
            sys.path.insert(0, self.plugin_dir)
            modules = glob(join(self.plugin_dir, '*.py'))
            self._plugins = [
                __import__(splitext(basename(module))[0]) for module in modules
            ]

        return self._plugins


def wrap_as_bot_command(function, name):
    """ Wrap the given function as a bot command. """

    is_bot_command = getattr(function, '_jabberbot_command', False)

    if is_bot_command:
       command = function

    else:
        @wraps(function)
        @requires_subscription
        def wrapper(bot, message, args):
            f_args = getargspec(function).args
            allowed_args = [bot, message, args]
            n = len(f_args)

            if n <= 3:
                args = allowed_args[3-n:]
                result = function(*args)

            else:
                result = None

            return result

        command = botcmd(wrapper, name=name)

    return command

#### EOF ######################################################################
