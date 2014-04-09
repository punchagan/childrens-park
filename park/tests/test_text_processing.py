#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Puneeth Chaganti <punchagan@muse-amuse.in>
""" Tests for the text processing utilities. """

# Standard library
import unittest

# Project library
from park.text_processing import chunk_text, highlight_word, strip_tags


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

    def test_should_highlight_exact_word(self):
        # Given
        word = 'foo'
        text = 'this is foo bar'

        # When
        text = highlight_word(text, word)

        # Then
        self.assertEqual(text, 'this is *foo* bar')

        return

    def test_should_highlight_word_at_ends(self):
        # Given
        word = 'foo'
        text = 'foo this is foo'

        # When
        text = highlight_word(text, word)

        # Then
        self.assertEqual(text, '*foo* this is *foo*')

        return

    def test_should_highlight_punctuated_word(self):
        # Given
        word = 'foo'
        text = "foo's bar or foo?"

        # When
        text = highlight_word(text, word)

        # Then
        self.assertEqual(text, "*foo*'s bar or *foo*?")

        return

    def test_should_strip_tags_should_not_barf_on_plain_text(self):
        # Given
        text = 'this is plain text'

        # When
        result = strip_tags(text)

        # Then
        self.assertEqual(text, result)

        return

    def test_should_strip_tags_from_html(self):
        # Given
        text = 'this is plain text'
        html = '<a>%s</a>' % text

        # When
        result = strip_tags(html)

        # Then
        self.assertEqual(text, result)

        return

    def test_should_strip_tags_from_broken_html(self):
        # Given
        text = 'this is plain text'
        html = '<a>%s' % text

        # When
        result = strip_tags(html)

        # Then
        self.assertEqual(text, result)

        return


if __name__ == '__main__':
    unittest.main()
