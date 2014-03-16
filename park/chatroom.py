#!/usr/bin/python
# -*- coding: utf-8 -*-

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

# Standard library
from datetime import datetime
from os.path import abspath, dirname, join
from os import execl
import re
from subprocess import call
import sys
import threading
import time
import traceback
import urllib

# 3rd-party library
from jabberbot import JabberBot, botcmd
import xmpp

# Project library
from park import serialize
from park.plugin import PluginLoader, wrap_as_bot_command
from park.text_processing import chunk_text
from park.util import (
    get_code_from_url, google, install_log_handler, is_url, is_wrappable,
    possible_signatures, requires_invite, requires_subscription
)


class ChatRoomJabberBot(JabberBot):
    """A bot based on JabberBot and broadcast example given in there."""

    #: Maximum allowed length of nick
    NICK_LEN = 24

    ROOT = dirname(abspath(__file__))

    def __init__(self, jid, password, res=None):
        super(ChatRoomJabberBot, self).__init__(jid, password, res)

        self._state = self._read_state()

        self.users = self._state.get('users', dict())
        self.invited = self._state.get('invited', dict())
        self.ideas = self._state.get('ideas', [])
        self.topic = self._state.get('topic', '')
        self.gist_urls = self._state.get('gist_urls', [])
        self._protected = [',addbotcmd', ',restart']
        self.started = time.time()
        self.message_queue = []
        self.thread_killed = False

        # Fetch all code from the gist urls and make commands
        self._add_gist_commands()

        # Load local commands.
        self._add_local_commands()

        return

    @property
    def db(self):
        """ Returns the path to the persistence file. """

        return join(self.ROOT, 'state.json')

    #### JabberBot interface ##################################################

    def connect(self):
        if not self.conn:
            conn = xmpp.Client(self.jid.getDomain(), debug=[])

            if self.jid.getDomain() == 'gmail.com':
                conres = conn.connect(server=('talk.google.com', 5222))
            else:
                conres = conn.connect()

            if not conres:
                server = self.jid.getDomain()
                self.log.error('unable to connect to %s.' % server)
                return None
            if conres != 'tls':
                self.log.warning('TLS failed! - using unsecure connection')
            else:
                self.log.info('Connected to server')

            authres = conn.auth(self.jid.getNode(), self._JabberBot__password,
                                self.res)
            if not authres:
                self.log.error('unable to authorize with server.')
                self._attempt_reconnect()

            if authres != 'sasl':
                self.log.warning("SASL failed on %s" % self.jid.getDomain())
                self.log.warging("Old authentication method used!")

            conn.sendInitPresence()

            self.conn = conn
            self.roster = self.conn.Roster.getRoster()
            self.log.info('*** roster ***')
            for contact in self.roster.getItems():
                self.log.info('  %s' % contact)
            self.log.info('*** roster ***')
            self.conn.RegisterHandler('message', self._callback_message)
            self.conn.RegisterDisconnectHandler(self._attempt_reconnect)
            self.conn.UnregisterDisconnectHandler(conn.DisconnectHandler)
            self._JabberBot__set_status(self.topic)

            ### Send a -- we are online -- message
            self.message_queue.append('_We are up and running!_')

        return self.conn

    def get_sender_nick(self, mess):
        """ Get the nick of the user from a message. """

        return self.users[self.get_sender_username(mess)]

    def get_sender_username(self, mess):
        """ Extract the sender's user name (along with domain) from a message.

        """

        jid = mess.getFrom()
        typ = mess.getType()

        return (
            '%s@%s' % (jid.getNode(), jid.getDomain()) if typ == 'chat' else ''
        )

    def idle_proc(self):

        if len(self.message_queue) == 0:
            return

        # copy the message queue, then empty it
        queue = self.message_queue
        self.message_queue = []

        messages = []

        for message in queue:
            messages.extend(chunk_text(message))

        for message in messages:
            if len(self.users):
                self.log.info(
                    'sending "%s" to %d user(s).', message, len(self.users)
                )

            for user in self.users:
                if not message.startswith("[%s]:" % self.users[user]):
                    self.send(user, self._highlight_name(message, user))

        return

    def thread_proc(self):
        while not self.thread_killed:
            self.message_queue.append('')
            # fixme: this is ugly.  make everything a property, and changes
            # should trigger a save!
            self._save_state()
            for i in range(300):
                time.sleep(1)
                if self.thread_killed:
                    return

    def shutdown(self):
        self._save_state()

    #### Bot Commands #########################################################

    @botcmd(name=',restart')
    @requires_subscription
    def restart(self, user, args):
        """ Restart the bot: Use resource name as PASSWORD.

        To avoid accidental restarts, resource name is used as argument.

        """

        if not args.strip() == self.res:
            return

        self.message_queue.append(
            '_%s restarted me! brb!_' % (self.users[user])
        )

        self.shutdown()
        self.idle_proc()
        self.conn.sendPresence(typ='unavailable')
        self._attempt_reconnect()

        return

    @botcmd(name=',subscribe')
    @requires_invite
    def subscribe(self, user, args):
        """ Subscribe to the chatroom. """

        if user in self.users:
            message = 'You are already subscribed.'

        else:
            nick = user.split('@')[0][:self.NICK_LEN]
            self.users[user] = nick
            self.invited.pop(user)
            self.message_queue.append('_%s has joined the channel_' % user)
            message = '%s, Welcome! Type %s for help.' % (
                nick, self.help._jabberbot_command_name
            )

        return message

    @botcmd(name=',unsubscribe')
    @requires_subscription
    def unsubscribe(self, user, args):
        """ Un-subscribe from the broadcast list. """

        user = self.users.pop(user)
        self.message_queue.append('_%s has left the channel_' % user)

        return 'You are now un-subscribed.'

    @botcmd(name=',dnd')
    @requires_invite
    def dnd(self, user, args):
        """ Command to toggle do-not-disturb mode. """

        if user in self.users:
            name = self.users.pop(user)
            self.invited[user] = name
            self.message_queue.append('_%s entered NO PARKING ZONE_' % name)
            message = 'NO PARKING ZONE entered. Bye!'

        else:
            name = self.invited.pop(user)
            self.users[user] = name
            self.message_queue.append('_%s is out of NO PARKING ZONE_' % name)
            message = 'PARKING ZONE entered. Welcome, %s!' % name

        return message

    @botcmd(name=',alias')
    @requires_subscription
    def alias(self, user, args):
        """ Allows a user to change their nick/alias. """

        nick = args.strip().replace(' ', '_')

        if args in self.users.values():
            message = 'Nick already taken.'

        elif len(args) == 0:
            message = 'Nick needs to be atleast one character long'

        elif len(args) > self.NICK_LEN:
            message = 'Nick cannot be longer than %s chars' % (self.NICK_LEN,)

        else:
            message = 'You are now known as %s' % nick
            self.message_queue.append(
                '_%s is now known as %s_' % (self.users[user], nick)
            )
            self.users[user] = nick

        return message

    @botcmd(name=',topic')
    @requires_subscription
    def topic(self, user, args):
        """ Change the topic/status. """

        self.topic = args
        self._JabberBot__set_status(self.topic)
        self.message_queue.append(
            '_%s changed topic to %s_' % (self.users[user], args)
        )

        return

    @botcmd(name=',list')
    @requires_subscription
    def list(self, user, args):
        """ List all the subscribed and invited members. """

        user_list = 'All these users are subscribed - \n'
        user_list += '\n'.join(
            ['%s :: %s' % (u, self.users[u]) for u in sorted(self.users)]
        )

        if self.invited.keys():
            user_list += '\n The following users are invited - \n'
            user_list += '\n'.join(self.invited.keys())

        return user_list

    @botcmd(name=',invite')
    @requires_subscription
    def invite(self, user, args):
        """ Invite a person to join the room.

        Works only if the person has added the bot as a friend.

        """

        jid = xmpp.JID(args.strip())
        email = '%s@%s' % (jid.getNode(), jid.getDomain())

        if email in self.roster.getItems():
            self.send(
                args,
                '%s invited you to join %s. '
                'Say %s to join!'
                % (user, CHANNEL, self.subscribe._jabberbot_command_name)
            )
            self.roster.Authorize(email)
            self.invited[email] = email
            self.message_queue.append(
                '_%s invited %s_' % (self.users[user], args)
            )

        else:
            return '%s in not in my friend list. Cannot invite.' % email

    @botcmd(name=',whois')
    @requires_subscription
    def whois(self, user, args):
        """ Check who has a particular nick. """

        query = args.strip().replace(' ', '_')

        for email, nick in self.users.iteritems():
            if nick == query:
                break

        else:
            email = 'Nobody!'

        return email

    @botcmd(name=',uptime')
    @requires_subscription
    def uptime(self, user, args):
        """ Check the up-time of the bot. """

        t = (
            datetime.fromtimestamp(time.time()) -
            datetime.fromtimestamp(self.started)
        )
        hours = t.seconds / 3600
        mins = (t.seconds / 60) % 60
        secs = t.seconds % 60
        uptime = '%s day(s) %s hour(s) %s min(s) and %s sec(s)' % (
            t.days, hours, mins, secs
        )

        self.message_queue.append(
            "Harbouring conversations, and what's more, memories, relentlessly"
            ' since %s for %s & friends' % (uptime, self.users[user])
        )

        return

    @botcmd(name=',g')
    @requires_subscription
    def google(self, user, args):
        """ Fetch the top-most result from Google. """

        query = urllib.urlencode({'q': args})
        result = google(query)

        if result is not None:
            self.message_queue.append(
                '%s googled for %s... and here you go: '
                % (self.users[user], args)
            )
            self.message_queue.append(result)
            message = ''

        else:
            message = 'Oops! nothing found'

        return message

    @botcmd(name=',sc')
    @requires_subscription
    def soundcloud(self, user, args):
        """ Fetch the top-most result from Google for site:soundcloud.com. """

        query = urllib.urlencode({'q': 'site:soundcloud.com ' + args})
        result = google(query)

        if result is not None:
            self.message_queue.append(
                '%s sound-clouded for %s... and here you go: '
                % (self.users[user], args)
            )
            self.message_queue.append(result)
            message = ''

        else:
            message = 'Oops! nothing found'

        return message

    @botcmd(name=',see', hidden=True)
    @requires_subscription
    def see(self, user, args):
        """ Look at bot's public attributes.

        You can pass a list of attributes separated by spaces.

        """

        attributes = [

            '%s: %s' % (attr, getattr(self, attr, None))
            if not attr.startswith('_') else '%s is private' % attr

            for attr in args.split()

        ]

        return '\n'.join(attributes)

    @botcmd(name=',see-friends', hidden=True)
    @requires_subscription
    def show_roster(self, user, args):
        """ Return the roster of friends. """

        return '\n'.join([contact for contact in self.roster.getItems()])

    @botcmd(name=',help')
    def help(self, mess, args):
        """ Show help for all the bot commands, or a given command. """

        return super(ChatRoomJabberBot, self).help(mess, args)

    @botcmd(name=',addbotcmd')
    def add_botcmd(self, mess, args):
        """ Define a bot command on the fly!

        This command lets you add bot commands, during runtime. New
        commands can be added as shown below ::

            ,addbotcmd<space>
            def clear():
                ''' Clears the screen!

                This command is intended to be used when you want to
                divert attention of the users from the previous
                discussion.
                '''
                print '\\n' * 80

        The commands can be added to a gist and the *raw* url can be passed
        to this command, like so ::

            ,addbotcmd <raw-gist-url>

        Commands added using gists are persisted between restarts.

        For more information, look at
        http://punchagan.github.com/childrens-park/#how-to-add-new-bot-commands

        """

        if not args:
            return "Didn't get any arguments for the command!"

        # Check if first word in args is a URL.
        gist_url = args.split()[0]
        if is_url(gist_url):
            code = get_code_from_url(gist_url)
            extra_doc = 'The code is at %s' % gist_url
        else:
            code = args
            gist_url = False
            extra_doc = ''

        is_name, name = self._create_cmd_from_code(code, extra_doc)

        if not is_name:
            # Return the error message
            return name

        # Persist the url, if it's not already persisted
        if gist_url and gist_url not in self.gist_urls:
            self.gist_urls.append(gist_url)

        # Log and celebrate!
        user = self.users[self.get_sender_username(mess)]
        self.log.info('%s registered command %s' % (user, name))
        self.message_queue.append('%s registered command %s' % (user, name))
        self.message_queue.append('Say ,help %s to see the help' % name)
        if extra_doc:
            self.message_queue.append(extra_doc)

    #### Private interface ####################################################

    def _add_gist_commands(self):
        """ Adds persisted gists as commands (on startup). """

        for url in self.gist_urls[:]:
            code = get_code_from_url(url)
            extra_doc = "\nThe code is at %s" % url
            if not code:
                self.gist_urls.remove(url)
                self.log.info('Untracking command at %s' %url)
                continue
            is_name, name = self._create_cmd_from_code(code, extra_doc)
            if not is_name:
                self.gist_urls.remove(url)
                self.log.info('Untracking command at %s' %url)
                continue
            self.log.info('Added new command from %s' %url)

        return

    def _add_local_commands(self):
        """ Add the locally contributed commands to the bot. """

        plugin_loader = PluginLoader(join(self.ROOT, 'plugins'))

        for plugin in plugin_loader.plugins:
            command = wrap_as_bot_command(plugin.main, ',%s' % plugin.__name__)
            if command is not None:
                name = getattr(command, '_jabberbot_command_name')
                self.commands[name] = command
            else:
                self.log('Ignoring plugin %s' % plugin.__name__)

        return

    def _attempt_reconnect(self):
        """ Attempt to reconnect. """

        self.log.info('Restarting...')
        self.log.info('Pulling changes from GitHub...')
        call(["git", "pull"])
        execl(
            '/usr/bin/nohup', sys.executable, sys.executable, abspath(__file__)
        )

        return

    def _callback_message(self, conn, mess):
        """ Command handling + routing.

        All messages sent to the bot will arrive here.

        """

        jid = mess.getFrom()
        props = mess.getProperties()
        text = mess.getBody()
        username = self.get_sender_username(mess)

        if username not in self.users.keys() + self.invited.keys():
            self.log.info('Ignored message from %s.' % username)
            return

        self.log.debug("*** props = %s" % props)
        self.log.debug("*** jid = %s" % jid)
        self.log.debug("*** username = %s" % username)
        self.log.debug("*** type = %s" % type)
        self.log.debug("*** text = %s" % text)

        # Ignore messages from before we joined
        if xmpp.NS_DELAY in props:
            return

        # If a message format is not supported (eg. encrypted), txt will be None
        if not text:
            return

        # Remember the last-talked-in thread for replies
        self._JabberBot__threads[jid] = mess.getThread()

        if ' ' in text:
            command, args = text.split(' ', 1)
        elif '\n' in text:
            command, args = text.split('\n', 1)
        else:
            command, args = text, ''
        cmd = command
        self.log.debug("*** cmd = %s" % cmd)

        if cmd in self.commands and cmd != 'help':
            try:
                reply = self.commands[cmd](mess, args)
            except Exception as e:
                reply = traceback.format_exc(e)
                self.log.exception('An error happened while processing a message ("%s") from %s: %s"' % (text, jid, reply))
        else:
            reply = self._unknown_command(mess, cmd, args)

        if reply:
            self.send_simple_reply(mess, unicode(reply))

    def _create_cmd_from_code(self, code, extra_doc=None):
        """ Execute the code, and make it a new bot cmd, if possible. """

        from inspect import isfunction

        # Evaluate the code and get the function
        d = dict()
        exec(code) in globals(), d
        # XXX: Should let people define arbit global functions?
        if len(d) != 1:
            return False, 'You need to define one callable'
        f = d.values()[0]

        if not (isfunction(f) and f.__doc__):
            return False, 'You can only add functions, with doc-strings'

        elif not is_wrappable(f):
            possible = possible_signatures()
            return False, '%s are the only supported signatures' % possible

        name = ',' + f.__name__
        f.__doc__ += "\n%s" % extra_doc or ''

        # Prevent over-riding protected commands
        if name in self._protected:
            return False, "Sorry, this function can't be over-written."

        # Wrap the function, as required and register it.
        self.commands[name] = self._wrap_function(f, code)

        return True, name

    def _highlight_name(self, msg, user):
        """ Emphasizes your name, when sent in a message. """

        nick = re.escape(self.users[user])
        msg = re.sub("(\W|\A)(%s)(\W|\Z)" % nick, "\\1 *\\2* \\3", msg)

        return msg

    def _read_state(self):
        """ Reads the persisted state. """

        return serialize.read_state(self.db)

    def _save_state(self):
        """ Persists the state of the bot. """

        state = dict(
            users=self.users,
            invited=self.invited,
            topic=self.topic,
            ideas=self.ideas,
            gist_urls=self.gist_urls
        )
        serialize.save_state(self.db, state)

        return

    @requires_subscription
    def _unknown_command(self, user, cmd, args):
        """ Handle everything that is not a known command.

        Currently, just sends it to all the other users as a message.

        """

        if not cmd.startswith(','):
            self.message_queue.append(
                '[%s]: %s %s' % (self.users[user], cmd, args)
            )
            message = ''

        else:
            message = 'unknown command: %s' % cmd

        return message

    def _wrap_function(self, f, code):
        from functools import partial, update_wrapper
        from inspect import getargs
        expected_args = getargs(f.func_code).args

        if 'self' not in expected_args:
            # Redefine the function to add a self argument!
            # XXX this is one heck of a hack!
            # This is done to support print statements
            code = re.sub("((\n|\A)def\s+\w+\()", "\\1self, ", code)

        # Replace print statements with 'self.message_queue.extend([args])
        code = re.sub("(\n\s*)print (.*)",
                      "\\1self.message_queue.extend([\\2])", code)

        # Re-evaluate code to get new function
        d = dict()
        exec(code) in globals(), d
        f_new = d.values()[0]

        # Wrap with first argument as self, to fake as a method
        f_ = partial(f_new, self)

        # Wrap to handle, missing mess or args arguments
        def wrapper(mess, args):
            f_args = dict()
            if 'mess' in expected_args:
                f_args.setdefault('mess', mess)
            if 'args' in expected_args:
                f_args.setdefault('args', args)
            return f_(**f_args)

        # Return a botcmd with the proper doc-string, etc.
        return botcmd(update_wrapper(wrapper, f))

    def __getattr__(self, name):
        """ Overridden to allow easier writing of user commands. """

        return None


def main():
    try:
        from park.settings import JID, PASSWORD, RES, CHANNEL
    except ImportError:
        print('Please copy sample-settings.py to settings.py and edit it!')
        sys.exit(1)

    install_log_handler()

    bc = ChatRoomJabberBot(JID, PASSWORD, RES)

    th = threading.Thread(target=bc.thread_proc)
    bc.serve_forever(connect_callback=lambda: th.start())
    bc.thread_killed = True


if __name__ == "__main__":
    main()


#### EOF ######################################################################
