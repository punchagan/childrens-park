#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Puneeth Chaganti <punchagan@muse-amuse.in>
""" Tests for the ChatRoom. """

# Standard library
import shutil
import tempfile
import unittest

# Project library
from chatroom import ChatRoomJabberBot


class TestChatRoom(unittest.TestCase):
    """ Tests for the ChatRoom. """

    def setUp(self):
        self.tempdir = ChatRoomJabberBot.ROOT = tempfile.mkdtemp()
        self.bot = ChatRoomJabberBot(
            jid='test@example.com',
            password='**********'
        )

    def tearDown(self):
        shutil.rmtree(self.tempdir)


if __name__ == "__main__":
    unittest.main()
