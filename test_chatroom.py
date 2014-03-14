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
        message = xmpp.Message(frm='foo@foo.com', typ='chat')
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
        message = xmpp.Message(frm=foo, typ='chat')
        text = 'this is my message'

        # When
        bot.myself(message, text)

        # Then
        self.assertIn(text, bot.message_queue[0])

        return

    def test_should_not_unsubscribe_unknown_user(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        foo = 'foo@foo.com'
        # bot.users = {foo: 'foo'}
        message = xmpp.Message(frm=foo, typ='chat')

        # When
        result = bot.unsubscribe(message, '')

        # Then
        self.assertIn('You are not subscribed', result)

        return

    def test_should_unsubscribe_user(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        foo = 'foo@foo.com'
        bot.users = {foo: 'foo'}
        message = xmpp.Message(frm=foo, typ='chat')

        # When
        result = bot.unsubscribe(message, '')

        # Then
        self.assertIn('You are now un-subscribed', result)
        self.assertEqual(0, len(bot.users))

        return

    def test_should_not_allow_duplicate_alias(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        foo = 'foo@foo.com'
        bar = 'bar@bar.com'
        users = {foo: 'foo', bar: 'bar'}
        bot.users = users
        message = xmpp.Message(frm=foo, typ='chat')

        # When
        bot.alias(message, 'bar')

        # Then
        self.assertDictEqual(users, bot.users)

        return

    def test_should_change_alias(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        foo = 'foo@foo.com'
        bot.users = {foo: 'foo'}
        message = xmpp.Message(frm=foo, typ='chat')

        # When
        bot.alias(message, 'bazooka')

        # Then
        self.assertEqual(bot.users[foo], 'bazooka')
        self.assertIn('bazooka', bot.message_queue[0])

        return

    def test_should_show_help_to_unknown_user(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        message = xmpp.Message(frm='', typ='chat')

        # When
        help_text = bot.help(message, '')

        # Then
        self.assertIn(bot.help.__doc__.strip(), help_text)

        return

    def test_should_show_attributes(self):
        # Given
        attributes = 'users topic'
        bot = ChatRoomJabberBot(self.jid, self.password)
        foo = 'foo@foo.com'
        bot.users = {foo: 'foo'}
        bot.topic = 'bazooka'
        message = xmpp.Message(frm=foo, typ='chat')

        # When
        output = bot.see(message, attributes)

        # Then
        self.assertIn('topic: bazooka', output)
        self.assertIn(foo, output)

        return

    def test_should_not_show_private_attributes(self):
        # Given
        attributes = '_state'
        bot = ChatRoomJabberBot(self.jid, self.password)
        foo = 'foo@foo.com'
        bot.users = {foo: 'foo'}
        bot.topic = 'bazooka'
        message = xmpp.Message(frm=foo, typ='chat')

        # When
        output = bot.see(message, attributes)

        # Then
        self.assertEqual('_state is private', output)

        return

    def test_should_google(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        foo = 'foo@foo.com'
        bot.users = {foo: 'foo'}
        message = xmpp.Message(frm=foo, typ='chat')

        # When
        bot.google(message, 'punchagan')

        # Then
        self.assertEqual(2, len(bot.message_queue))
        self.assertIn('punchagan', bot.message_queue[1])

        return

    def test_should_find_subscribed_user(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        foo = 'foo@foo.com'
        bot.users = {foo: 'foo'}
        message = xmpp.Message(frm=foo, typ='chat')

        # When
        who = bot.whois(message, 'foo')

        # Then
        self.assertEqual(who, foo)

        return

    def test_should_not_find_unknown_user(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        foo = 'foo@foo.com'
        bot.users = {foo: 'foo'}
        message = xmpp.Message(frm=foo, typ='chat')

        # When
        who = bot.whois(message, 'fox')

        # Then
        self.assertEqual(who, 'Nobody!')

        return

    def test_should_list_users(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        foo = 'foo@foo.com'
        bar = 'bar@bar.com'
        bot.users = {foo: 'foo'}
        bot.invited = {bar: 'bar'}
        message = xmpp.Message(frm=foo, typ='chat')

        # When
        user_list = bot.list(message, '')

        # Then
        self.assertIn(foo, user_list)
        self.assertIn(bar, user_list)

        return

    def test_should_not_subscribe_uninvited_user(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        bar = 'bar@bar.com'
        message = xmpp.Message(frm=bar, typ='chat')

        # When
        buzz_off = bot.subscribe(message, '')

        # Then
        self.assertIn('need to be invited', buzz_off)

        return

    def test_should_not_subscribe_already_subscribed_user(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        bar = 'bar@bar.com'
        bot.users = {bar: 'bar'}
        message = xmpp.Message(frm=bar, typ='chat')

        # When
        buzz_off = bot.subscribe(message, '')

        # Then
        self.assertIn('already subscribed', buzz_off)

        return

    def test_should_subscribe_invited_user(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        bar = 'bar@bar.com'
        bot.invited = {bar: 'bar'}
        message = xmpp.Message(frm=bar, typ='chat')

        # When
        welcome = bot.subscribe(message, '')

        # Then
        self.assertIn('Welcome', welcome)

        return

    def test_should_disable_dnd(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        bar = 'bar@bar.com'
        bot.invited = {bar: 'bar'}
        message = xmpp.Message(frm=bar, typ='chat')

        # When
        welcome = bot.dnd(message, '')

        # Then
        self.assertIn('Welcome', welcome)

        return

    def test_should_enable_dnd(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        bar = 'bar@bar.com'
        bot.users = {bar: 'bar'}
        message = xmpp.Message(frm=bar, typ='chat')

        # When
        bye = bot.dnd(message, '')

        # Then
        self.assertIn('Bye', bye)

        return

    def test_should_broadcast_non_cmd_messages(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        bar = 'bar@bar.com'
        bot.users = {bar: 'bar'}
        message = xmpp.Message(frm=bar, typ='chat', body='foo')

        # When
        result = bot._callback_message(None, message)

        # Then
        self.assertIsNone(result)
        self.assertIn('[bar]: foo', bot.message_queue[0].strip())

        return

    def test_should_not_broadcast_unknown_cmd(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password)
        bar = 'bar@bar.com'
        bot.users = {bar: 'bar'}
        message = xmpp.Message(frm=bar, typ='chat', body=',foo bar')
        # patching since we are not connected!
        self.result = ''
        def reply(x, y): self.result = y
        bot.send_simple_reply = reply

        # When
        bot._callback_message(None, message)

        # Then
        self.assertIn('unknown command', self.result)
        self.assertEqual(0, len(bot.message_queue))

        return


if __name__ == "__main__":
    unittest.main()

#### EOF ######################################################################
