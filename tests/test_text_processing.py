#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Puneeth Chaganti <punchagan@muse-amuse.in>
""" Tests for the text processing utilities. """

# Standard library
import unittest

# Project library
from park.text_processing import chunk_text


class TestTextProcessing(unittest.TestCase):
    """ Tests for the text processing utilities. """

    def test_should_not_chunk_small_messages(self):
        # Given
        limit = 500

        # When
        messages = chunk_text('ab cd ef ', limit)

        # Then
        self.assertEqual(1, len(messages))
        self.assertEqual(9, len(messages[0]))

        return

    def test_should_chunk_message_at_spaces(self):
        # Given
        limit = 3

        # When
        messages = chunk_text('ab cd ef ', limit)

        # Then
        self.assertEqual(3, len(messages))
        self.assertEqual('ab ', messages[0])
        self.assertEqual('cd ', messages[1])
        self.assertEqual('ef ', messages[2])

        return

    def test_should_chunk_message_at_limit(self):
        # Given
        limit = 500

        # When
        messages = chunk_text('x' * 1400, limit)

        # Then
        self.assertEqual(3, len(messages))
        self.assertEqual(500, len(messages[0]))
        self.assertEqual(500, len(messages[1]))
        self.assertEqual(400, len(messages[2]))

        return


if __name__ == '__main__':
    unittest.main()
