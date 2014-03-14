#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Puneeth Chaganti <punchagan@muse-amuse.in>
""" Tests for the ChatRoom. """

# Standard library
from os.path import exists, join
import shutil
import tempfile
import unittest

# Project library
from chatroom import ChatRoomJabberBot
import serialize


class TestChatRoom(unittest.TestCase):
    """ Tests for the ChatRoom. """

    def setUp(self):
        self.jid = 'test@example.com'
        self.password = '********'
        self.tempdir = ChatRoomJabberBot.ROOT = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_should_read_state_file(self):
        # Given
        state_file = join(ChatRoomJabberBot.ROOT, 'state.json')
        state = {
            'users': {
                'foo': 'foo@example.com',
                'bar': 'bar@bazooka.com'
            }
        }
        serialize.save_state(state_file, state)

        # When
        bot = ChatRoomJabberBot(self.jid, self.password)

        # Then
        self.assertDictEqual(bot.users, state['users'])

    def test_should_save_state_on_shutdown(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        bot.users = {
            'foo': 'foo@foo.com'
        }

        # When
        bot.shutdown()

        # Then
        path = join(bot.ROOT, 'state.json')
        self.assertTrue(exists(path))
        self.assertDictEqual(bot.users, serialize.read_state(path)['users'])


if __name__ == "__main__":
    unittest.main()
