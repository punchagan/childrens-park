#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Puneeth Chaganti <punchagan@muse-amuse.in>
""" Tests for the utilities to work with plugins. """

# Standard library
import os
from os.path import exists, join
import shutil
import tempfile
from textwrap import dedent
import unittest

# 3rd party
import xmpp

# Project library
from park.plugin import PluginLoader


class TestPlugins(unittest.TestCase):
    """ Tests for the utilities to work with plugins. """

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.plugin_dir = join(self.tempdir, 'plugins')
        os.makedirs(self.plugin_dir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_should_be_silent_when_no_plugins(self):
        # When
        plugin_loader = PluginLoader(self.plugin_dir)

        # Then
        self.assertEqual([], plugin_loader.plugins)

        return

    def test_should_load_hello_world(self):
        # Given
        code = dedent(
            """
            def main():
                return 'hello world'
            """
        )

        with open(join(self.plugin_dir, 'hello_world.py'), 'w') as f:
            f.write(code)

        # When
        plugin_loader = PluginLoader(self.plugin_dir)
        plugins = plugin_loader.plugins

        # Then
        self.assertEqual(1, len(plugins))
        self.assertEqual('hello world', plugins[0].main())

        return


if __name__ == "__main__":
    unittest.main()

#### EOF ######################################################################
