#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Puneeth Chaganti <punchagan@muse-amuse.in>
""" Tests for the ChatRoom. """

# Standard library
from datetime import datetime, timedelta
from email import message_from_string
from os.path import abspath, dirname, exists, join
import shutil
import tempfile
import threading
import time
import unittest

# 3rd party
import xmpp

# Project library
from park import serialize
from park.chatroom import ChatRoomJabberBot
from park.util import captured_stdout

HERE = dirname(abspath(__file__))


class TestChatRoom(unittest.TestCase):
    """ Tests for the ChatRoom. """

    def setUp(self):
        self.jid = 'test@example.com'
        self.password = '********'
        self.tempdir = tempfile.mkdtemp()
        self.plugin_dir = join(self.tempdir, 'plugins')
        shutil.copytree(join(HERE, '..', 'plugins'), self.plugin_dir)
        shutil.copy(
            join(HERE, '..', '..', 'sample-settings.py'),
            join(HERE, '..', 'sample-settings.py')
        )

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_should_read_state_file(self):
        # Given
        _bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
        state = {
            'users': {
                'foo': 'foo@example.com',
                'bar': 'bar@bazooka.com'
            }
        }
        serialize.save_state(_bot.db, state)

        # When
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)

        # Then
        self.assertDictEqual(bot.users, state['users'])

        return

    def test_should_save_state_on_shutdown(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
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
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
        message = xmpp.Message(frm='foo@foo.com', typ='chat')
        text = 'this is my message'

        # When
        bot.commands[',me'](message, text)

        # Then
        self.assertEqual(0, len(bot.message_queue))

        return

    def test_should_send_message_in_third_person(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
        foo = 'foo@foo.com'
        bot.users = {foo: 'foo'}
        message = xmpp.Message(frm=foo, typ='chat')
        text = 'this is my message'

        # When
        bot.commands[',me'](message, text)

        # Then
        self.assertIn(text, bot.message_queue[0])

        return

    def test_should_not_unsubscribe_unknown_user(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
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
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
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
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
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
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
        foo = 'foo@foo.com'
        bot.users = {foo: 'foo'}
        message = xmpp.Message(frm=foo, typ='chat')

        # When
        bot.alias(message, 'bazooka')

        # Then
        self.assertEqual(bot.users[foo], 'bazooka')
        self.assertIn('bazooka', bot.message_queue[0])

        return

    def test_should_not_allow_empty_nick(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
        foo = 'foo@foo.com'
        bot.users = {foo: 'foo'}
        message = xmpp.Message(frm=foo, typ='chat')

        # When
        bot.alias(message, '  ')

        # Then
        self.assertEqual(bot.users[foo], 'foo')

        return

    def test_should_show_help_to_unknown_user(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
        message = xmpp.Message(frm='', typ='chat')

        # When
        help_text = bot.help(message, '')

        # Then
        self.assertIn(bot.help.__doc__.strip(), help_text)

        return

    def test_should_show_attributes(self):
        # Given
        attributes = 'users topic'
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
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
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
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
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
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
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
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
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
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
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
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
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
        bar = 'bar@bar.com'
        message = xmpp.Message(frm=bar, typ='chat')

        # When
        buzz_off = bot.subscribe(message, '')

        # Then
        self.assertIn('need to be invited', buzz_off)

        return

    def test_should_not_subscribe_already_subscribed_user(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
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
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
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
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
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
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
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
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
        bar = 'bar@bar.com'
        bot.users = {bar: 'bar'}
        message = xmpp.Message(frm=bar, typ='chat', body='foo')

        # When
        result = bot.callback_message(None, message)

        # Then
        self.assertIsNone(result)
        self.assertIn('[bar]: foo', bot.message_queue[0].strip())

        return

    def test_should_not_broadcast_unknown_cmd(self):
        # Given
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
        bar = 'bar@bar.com'
        bot.users = {bar: 'bar'}
        message = xmpp.Message(frm=bar, typ='chat', body=',foo bar')
        # patching since we are not connected!
        self.result = ''
        def reply(x, y): self.result = y
        bot.send_simple_reply = reply

        # When
        bot.callback_message(None, message)

        # Then
        self.assertIn('unknown command', self.result)
        self.assertEqual(0, len(bot.message_queue))

        return

    def test_should_add_hello_world_as_bot_command(self):
        # Given
        shutil.copy(join(HERE, 'data', 'hello_world.py'), self.plugin_dir)
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
        bar = 'bar@bar.com'
        bot.users = {bar: 'bar'}
        message = xmpp.Message(frm=bar, typ='chat', body=',hello_world')

        # When
        result = bot.commands[',hello_world'](message, '')
        help = bot.help(message, ',hello_world')

        # Then
        self.assertEqual('hello world', result)
        self.assertIn('hello world', help)

        return

    def test_should_add_hello_name_as_bot_command(self):
        # Given
        shutil.copy(join(HERE, 'data', 'hello_name.py'), self.plugin_dir)
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
        bar = 'bar@bar.com'
        bot.users = {bar: 'bar'}
        message = xmpp.Message(frm=bar, typ='chat', body=',hello_name foo')

        # When
        result = bot.commands[',hello_name'](message, 'foo')

        # Then
        self.assertEqual('hello, foo', result)

        return

    def test_should_add_hello_custom_as_bot_command(self):
        # Given
        shutil.copy(join(HERE, 'data', 'hello_custom.py'), self.plugin_dir)
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
        bar = 'bar@bar.com'
        bot.users = {bar: 'bar'}
        message = xmpp.Message(
            frm=bar, typ='chat', body=',hello_custom namaste'
        )

        # When
        result = bot.commands[',hello_custom'](message, 'namaste')

        # Then
        self.assertEqual('%s, namaste' % bar, result)

        return

    def test_should_add_hello_all_as_bot_command(self):
        # Given
        shutil.copy(join(HERE, 'data', 'hello_all.py'), self.plugin_dir)
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
        bar = 'bar@bar.com'
        bot.users = {bar: 'bar'}
        message = xmpp.Message(frm=bar, typ='chat', body=',hello_all')

        # When
        bot.commands[',hello_all'](message, '')

        # Then
        self.assertEqual(1, len(bot.message_queue))
        self.assertEqual('%s says namaste' % bar, bot.message_queue[0].strip())

        return

    def test_should_update_hello_world_command(self):
        # Given
        shutil.copy(join(HERE, 'data', 'hello_world.py'), self.plugin_dir)
        bot = ChatRoomJabberBot(self.jid, self.password, root=self.tempdir)
        bar = 'bar@bar.com'
        bot.users = {bar: 'bar'}
        message = xmpp.Message(frm=bar, typ='chat', body=',hello_world')

        # When
        with open(join(HERE, 'data', 'hello_all.py')) as f:
            code = f.read()
        text = 'hello_world %s' % code
        bot.add(xmpp.Message(frm=bar, typ='chat', body=',hello_world'), text)
        bot.commands[',hello_world'](message, '')

        # Then
        self.assertEqual(
            '%s says namaste' % bar, bot.message_queue[-1].strip()
        )

        return

    def test_should_show_urls(self):
        # Given
        from park.plugins.urls import DB_NAME
        bot = ChatRoomJabberBot(
            self.jid, self.password, debug=True, root=self.tempdir
        )
        bar = 'bar@bar.com'
        bot.users = {bar: 'bar'}
        url = 'http://muse-amuse.in'
        text = 'this is %s' % url
        db_path = join(bot.root, DB_NAME)
        bot.callback_message(
            None,  xmpp.Message(frm=bar, typ='chat', body=text)
        )
        self._wait_while(lambda: not exists(db_path))

        # When
        message = xmpp.Message(frm=bar, typ='chat', body=',urls')
        bot.commands[',urls'](message, '')

        # Then
        # Any prints in bot commands are sent as messages. In debug mode,
        # send_email prints out the email.
        self.assertIn(url, bot.message_queue[0])

        return

    def test_should_send_newsletter(self):
        # Given
        from park.plugins.urls import DB_NAME
        bot = ChatRoomJabberBot(
            self.jid, self.password, debug=True, root=self.tempdir
        )
        bar = 'bar@bar.com'
        bot.users = {bar: 'bar'}
        url = 'http://muse-amuse.in'
        text = 'this is %s' % url
        db_path = join(bot.root, DB_NAME)
        bot.callback_message(
            None,  xmpp.Message(frm=bar, typ='chat', body=text)
        )
        self._wait_while(lambda: not exists(db_path))
        extra_state = {
            'last_newsletter': (datetime.now() - timedelta(10)).isoformat()
        }
        bot.save_state(extra_state=extra_state)

        # When
        with captured_stdout() as captured:
            self._run_bot(bot, lambda: captured.output)

        # Then
        message = message_from_string(captured.output)
        for payload in message.get_payload():
            self.assertIn(url, payload.get_payload(decode=True))

    def test_should_capture_prints_in_hooks(self):
        # Given
        shutil.copy(join(HERE, 'data', 'my_hook.py'), self.plugin_dir)
        bot = ChatRoomJabberBot(
            self.jid, self.password, debug=True, root=self.tempdir
        )
        foo = 'foo@foo.com'
        bot.users = {foo: 'foo'}
        text = 'this is my message'
        message = xmpp.Message(frm=foo, typ='chat', body=text)
        expected = 'New message!'

        # When
        bot.callback_message(None, message)

        # Then
        self.assertIn(expected, bot.message_queue)

        return

    #### Private protocol #####################################################

    def _run_bot(self, bot, condition, timeout=5):
        """ Run the bot until the condition returns True. """
        thread = threading.Thread(target=bot.thread_proc)
        thread.daemon = True
        thread.start()
        self._wait_while(lambda: not condition(), timeout=timeout)
        bot.thread_killed = True
        thread.join()

        return

    def _wait_while(self, condition, timeout=10):
        """ Wait while the condition is True. """
        started = time.time()
        while condition():
            time.sleep(0.1)
            if time.time() - started > timeout:
                raise RuntimeError('Timed out')

        return


if __name__ == "__main__":
    unittest.main()

#### EOF ######################################################################
