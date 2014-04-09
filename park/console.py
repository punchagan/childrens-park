#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Puneeth Chaganti <punchagan@muse-amuse.in>
""" A Console based ChatRoom. """

# Standard library.
from cmd import Cmd
from os.path import join, dirname, abspath
import shutil
import tempfile
import threading

# 3rd party library.
from xmpp import Client, DBG_CLIENT

# Project library.
from park.chatroom import ChatRoomJabberBot

TEST_EMAIL = 'console@example.com'
TEST_USER = 'you'
HERE = dirname(abspath(__file__))


class StreamClient(Client):

    Namespace = 'jabber:client'
    DBG = DBG_CLIENT

    def __init__(self, server, port=5222, debug=[], stream=None):
        Client.__init__(self, server, port, debug)
        self.stream = stream

    def Process(self, x):
        pass

    def send(self, message):
        text = message.getBody() or ''
        self.stream.write('%s\n' % text)
        self.stream.flush()


class ChatRoomCmd(Cmd):
    prompt = 'park> '

    def __init__(self, completekey='tab', stdin=None, stdout=None):
        Cmd.__init__(self, completekey, stdin, stdout)
        root = tempfile.mkdtemp()
        self._copy_plugins(root)
        self.bot = self._create_bot(root)

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

    def _copy_plugins(self, dst):
        """ Copy plugin directories to the given destination. """

        for name in ('plugins', 'gist_plugins'):
            shutil.copytree(join(HERE, name), join(dst, name))

    def _create_bot(self, root=None):
        bot = ChatRoomJabberBot(
            'foo@example.com', '*******', debug=True, root=root
        )
        bot.conn = StreamClient(bot.username, stream=self.stdout)
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
