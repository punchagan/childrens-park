#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Puneeth Chaganti <punchagan@muse-amuse.in>
""" Tests for the ChatRoom. """

# Standard library
from os.path import exists
import shutil
import tempfile
import unittest

# 3rd party
import xmpp

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
        _bot = ChatRoomJabberBot(self.jid, self.password)
        state = {
            'users': {
                'foo': 'foo@example.com',
                'bar': 'bar@bazooka.com'
            }
        }
        serialize.save_state(_bot.db, state)

        # When
        bot = ChatRoomJabberBot(self.jid, self.password)

        # Then
        self.assertDictEqual(bot.users, state['users'])

        return

    def test_should_save_state_on_shutdown(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        bot.users = {
            'foo': 'foo@foo.com'
        }

        # When
        bot.shutdown()

        # Then
        self.assertTrue(exists(bot.db))
        self.assertDictEqual(bot.users, serialize.read_state(bot.db)['users'])

        return

    #### Test bot commands ####################################################

    def test_should_not_send_message_from_unsubscribed_user(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        message = xmpp.Protocol(frm='foo@foo.com', typ='chat')
        text = 'this is my message'

        # When
        bot.myself(message, text)

        # Then
        self.assertEqual(0, len(bot.message_queue))

        return

    def test_should_send_message_in_third_person(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        foo = 'foo@foo.com'
        bot.users = {foo: 'foo'}
        message = xmpp.Protocol(frm=foo, typ='chat')
        text = 'this is my message'

        # When
        bot.myself(message, text)

        # Then
        self.assertIn(text, bot.message_queue[0])

        return


if __name__ == "__main__":
    unittest.main()
