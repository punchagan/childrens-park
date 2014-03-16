#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Puneeth Chaganti <punchagan@muse-amuse.in>
""" Tests for the utilities to work with plugins. """

# Standard library
import os
from os.path import abspath, dirname, join
import shutil
import tempfile
import unittest

# 3rd party

# Project library
from park.plugin import load_file

HERE = dirname(abspath(__file__))


class TestPlugins(unittest.TestCase):
    """ Tests for the utilities to work with plugins. """

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.plugin_dir = join(self.tempdir, 'plugins')
        os.makedirs(self.plugin_dir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_should_load_hello_world(self):
        # Given
        hello_world = join(HERE, 'data', 'hello_world.py')

        # When
        plugin = load_file(hello_world)

        # Then
        self.assertEqual('hello world', plugin.main())

        return


if __name__ == "__main__":
    unittest.main()

#### EOF ######################################################################
