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
from os.path import basename, join, splitext
import sys

# 3rd party library
from jabberbot import botcmd

# Project library
from park.util import captured_stdout, requires_subscription


class PluginLoader(object):
    """ A class to load plugins from a plugin directory. """

    def __init__(self, plugin_dir):
        self.plugin_dir = plugin_dir
        self._plugins = None
        return

    @property
    def plugins(self):
        """ The list of discovered plugins. """

        self.clean_compiled_files()
        sys.path.insert(0, self.plugin_dir)

        if self._plugins is None:
            modules = glob(join(self.plugin_dir, '*.py'))
            self._plugins = [
                imp.load_source(splitext(basename(module))[0], module, )
                for module in modules
            ]

        sys.path = sys.path[1:]

        return self._plugins

    def clean_compiled_files(self):
        """ Remove all the .pyc and .pyo files. """

        for f in glob(join(self.plugin_dir, '*.py[oc]')):
            os.unlink(f)

        return


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

#### EOF ######################################################################
