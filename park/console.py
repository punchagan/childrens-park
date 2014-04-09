#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Puneeth Chaganti <punchagan@muse-amuse.in>
""" Tests for the ChatRoom. """

# Standard library.
from cmd import Cmd
import tempfile
import threading
import sys

# 3rd party library.
from xmpp import Client

# Project library.
from park.chatroom import ChatRoomJabberBot

TEST_EMAIL = 'console@example.com'
TEST_USER = 'you'


class ChatRoomCmd(Cmd):
    prompt = 'park> '

    def __init__(self, completekey='tab', stdin=None, stdout=None):
        Cmd.__init__(self, completekey, stdin, stdout)
        self.bot = self._create_bot()

    def default(self, line):
        if line == 'EOF':
            self.stdout.write('Exiting ...\n')
            sys.exit(0)

        else:
            message = self.bot.build_message(line)
            message.setType('chat')
            message.setFrom(TEST_EMAIL)
            self.bot.callback_message(self.bot.conn, message)
            self.bot.idle_proc()

    def _create_bot(self):
        bot = ChatRoomJabberBot('foo@example.com', '*******', debug=True)
        # fixme: the root should be an argument to constructor!
        bot.ROOT = tempfile.mkdtemp()
        bot.conn = Client(bot.username, debug=[])
        bot.conn.Process = lambda x: None

        def send(message):
            text = message.getBody() or ''
            self.stdout.write('%s\n' % text)
            self.stdout.flush()

        bot.conn.send = send
        bot.users = {TEST_EMAIL: TEST_USER}
        bot.save_state()

        thread = threading.Thread(target=bot.thread_proc)
        thread.daemon = True
        thread.start()

        return bot

    def emptyline(self):
        pass

if __name__ == '__main__':
    import sys
    console = ChatRoomCmd(stdout=sys.stderr)
    console.cmdloop('Welcome!')
