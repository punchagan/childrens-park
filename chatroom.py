#!/usr/bin/python

# Copyright (c) 2011 Puneeth Chaganti <punchagan@gmail.com> 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# A portion of this code is from the code of JabberBot copyrighted by
# Thomas Perl the copyright of which is included below. 
# JabberBot: A simple jabber/xmpp bot framework
#
# Copyright (c) 2007-2011 Thomas Perl <thp.io/about>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Commentary:
#
# This bot is written to behave like a chatroom, where all the
# messages are sent to all the users subscribed to this bot.
#
# You are required to have a file settings.py with the variables,
# JID, PASSWORD, CHANNEL, RES
#
# Depends: python-jabberbot, xmpppy
#

from jabberbot import JabberBot, botcmd

import xmpp

import threading
import time 
import logging
import traceback

from settings import * 

class ChatRoomJabberBot(JabberBot):
    """A bot based on JabberBot and broadcast example given in there."""

    def __init__( self, jid, password, res = None):
        super( ChatRoomJabberBot, self).__init__( jid, password, res)
        # create console handler
        chandler = logging.StreamHandler()
        # create formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        # add formatter to handler
        chandler.setFormatter(formatter)
        # add handler to logger
        self.log.addHandler(chandler)
        # set level to INFO
        self.log.setLevel(logging.INFO)

        try:
            from users import USERS
            self.users = USERS
        except:
            self.users = {}

        self.invited = {}
        
        self.message_queue = []
        self.thread_killed = False

    def connect(self):
        if not self.conn:
            conn = xmpp.Client(self.jid.getDomain(), debug = [])

            conres = conn.connect(server=('talk.google.com', 5223))
            
            if not conres:
                self.log.error('unable to connect to server %s.' % self.jid.getDomain())
                return None
            if conres<>'tls':
                self.log.warning('unable to establish secure connection - TLS failed!')

            authres = conn.auth(self.jid.getNode(), self._JabberBot__password, self.res)
            if not authres:
                self.log.error('unable to authorize with server.')
                return None
            if authres<>'sasl':
                self.log.warning("unable to perform SASL auth os %s. Old authentication method used!" % self.jid.getDomain())

            conn.sendInitPresence()
            self.conn = conn
            self.roster = self.conn.Roster.getRoster()
            self.log.info('*** roster ***')
            for contact in self.roster.getItems():
                self.log.info('  %s' % contact)
            self.log.info('*** roster ***')
            self.conn.RegisterHandler('message', self.callback_message)
            self.conn.RegisterHandler('presence', self.callback_presence)

        return self.conn

    
    def save_users(self):
        try:
            f = open('users.py', 'w')
            f.write('USERS = {\n')
            for u in users:
                f.write("'    %s': '%s', \n" %(u, users[u]))
            f.write('}\n')
            f.close()
            self.log.info("Saved user data")
        except:
            self.log.info("Couldn't save user data")

    def shutdown(self):
        self.save_users()

    def unknown_command(self, mess, cmd, args):
        user = self.get_sender_username(mess)
        if user in self.users:
            self.message_queue.append('[%s]: %s %s' % (self.users[user], cmd, args))
            self.log.info("%s sent: %s %s" %(user, cmd, args))
        return ''


    def callback_message( self, conn, mess):
        """Messages sent to the bot will arrive here. Command handling + routing is done in this function."""

        jid      = mess.getFrom()
        props    = mess.getProperties()
        text     = mess.getBody()
        username = self.get_sender_username(mess)

        if username not in self.users.keys() + self.invited.keys(): return

        self.log.debug("*** props = %s" % props)
        self.log.debug("*** jid = %s" % jid)
        self.log.debug("*** username = %s" % username)
        self.log.debug("*** type = %s" % type)
        self.log.debug("*** text = %s" % text)

        # Ignore messages from before we joined
        if xmpp.NS_DELAY in props: return

        # If a message format is not supported (eg. encrypted), txt will be None
        if not text: return

        # Remember the last-talked-in thread for replies
        self._JabberBot__threads[jid] = mess.getThread()

        if ' ' in text:
            command, args = text.split(' ', 1)
        else:
            command, args = text, ''
        cmd = command.lower()
        self.log.debug("*** cmd = %s" % cmd)

        if self.commands.has_key(cmd):
            try:
                reply = self.commands[cmd](mess, args)
            except Exception, e:
                reply = traceback.format_exc(e)
                self.log.exception('An error happened while processing a message ("%s") from %s: %s"' % (text, jid, reply))
        else:
            # In private chat, it's okay for the bot to always respond.
            # In group chat, the bot should silently ignore commands it
            # doesn't understand or aren't handled by unknown_command().
            default_reply = 'Unknown command: "%s". Type "help" for available commands.<b>blubb!</b>' % cmd
            if type == "groupchat": default_reply = None
            reply = self.unknown_command( mess, cmd, args)
            if reply is None:
                reply = default_reply
        if reply:
            self.send_simple_reply(mess,reply)

    
    @botcmd(name=',subscribe')
    def subscribe( self, mess, args):
        """Subscribe to the broadcast list"""
        user = self.get_sender_username(mess)
        if user in self.users:
            return 'You are already subscribed.'
        else:
            self.users[user] = user
            self.invited.pop(user)
            self.message_queue.append('_%s has joined the channel_' % user)
            self.log.info('%s subscribed to the broadcast.' % user)
            self.save_users()
            return 'You are now subscribed.'

    @botcmd(name=',unsubscribe')
    def unsubscribe( self, mess, args):
        """Unsubscribe from the broadcast list"""
        user = self.get_sender_username(mess)
        if not user in self.users:
            return 'You are not subscribed!'
        else:
            user = self.users.pop(user)
            self.message_queue.append('_%s has left the channel_' % user)
            self.log.info( '%s unsubscribed from the broadcast.' % user)
            self.save_users()
            return 'You are now unsubscribed.'


    @botcmd(name=',alias')
    def alias( self, mess, args):
        """Change your nick"""
        user = self.get_sender_username(mess)
        args = args.strip().replace(' ', '_')
        if user in self.users:
            if 0 < len(args) < 24:
                self.message_queue.append('_%s is now known as %s_' %(self.users[user], args))
                self.users[user] = args
                self.log.info( '%s changed alias.' % user)
                self.log.info('%s' %self.users)
                self.save_users()
                return 'You are now known as %s' % args
            else:
                return 'Your nick is too short or too long'


    @botcmd(name=',topic')
    def topic( self, mess, args):
        """Change the topic/status"""
        user = self.get_sender_username(mess)
        if user in self.users:
            self._JabberBot__set_status(args)
            self.message_queue.append('_%s changed topic to %s_' %(self.users[user], args))
            self.log.info( '%s changed topic.' % user)


    @botcmd(name=',list')
    def list( self, mess, args):
        """List all the members of the list"""
        user = self.get_sender_username(mess)
        args = args.replace(' ', '_')
        if user in self.users:
            user_list = 'All these users are subscribed - \n'
            user_list += '\n'.join(['%s :: %s' %(u, self.users[u]) for u in sorted(self.users)])
            if self.invited.keys():
                user_list += '\n The following users are invited - \n'
                user_list += '\n'.join(self.invited.keys())
            self.log.info( '%s checks list of users.' % user)
            return user_list

    @botcmd(name=',me')
    def myself(self, mess, args):
        """Send message in third person"""
        user = self.get_sender_username(mess)
        if user in self.users:
            self.message_queue.append('_%s %s_' % (self.users[user], args))
            self.log.info( '%s says %s in third person.' % (user, args))


    @botcmd(name=',invite')
    def invite(self, mess, args):
        """Invite a person to join the room. Works only if the person has added the bot as a friend, as of now."""
        user = self.get_sender_username(mess)
        if user in self.users:
            self.send(args, '%s invited you to join %s. Say "help" to see how to join.' % (user, CHANNEL))
            self.invited[xmpp.JID(args).getNode()] = ''
            self.log.info( '%s invited %s.' % (user, args))
            return 'You invited %s' % args

    @botcmd(name=',whois')
    def whois( self, mess, args):
        """Check who has a particular nick"""
        user = self.get_sender_username(mess)
        args = args.strip().replace(' ', '_')
        if user in self.users:
            self.log.info('%s queried whois %s.' % (user, args))
            if args in self.users.values():
                return filter(lambda u: self.users[u] == args, self.users)[0]
            else:
                return 'Nobody!'

    def idle_proc( self):
        if not len(self.message_queue):
            return

        # copy the message queue, then empty it
        messages = self.message_queue
        self.message_queue = []

        for message in messages:
            if len(self.users):
                self.log.info('sending "%s" to %d user(s).' % ( message, len(self.users), ))
            for user in self.users:
                if not message.startswith("[%s]:" % self.users[user]):
                    self.send(user+"@gmail.com", message)

    def thread_proc( self):
        while not self.thread_killed:
            self.message_queue.append('')
            for i in range(300):
                time.sleep(1)
                if self.thread_killed:
                    return


bc = ChatRoomJabberBot(JID, PASSWORD, RES)

th = threading.Thread(target = bc.thread_proc)
bc.serve_forever(connect_callback = lambda: th.start())
bc.thread_killed = True

