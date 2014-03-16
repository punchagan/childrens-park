#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2011 Puneeth Chaganti <punchagan@gmail.com>
""" Utilites to work with plugins for bot. """

# Standard library
from glob import glob
from os.path import basename, join, splitext
import sys


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
