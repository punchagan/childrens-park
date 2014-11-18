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
""" A chatroom bot that uses the XMPP protocol. """

# Standard library
from datetime import datetime
import glob
import logging
from os.path import abspath, basename, dirname, exists, join
from os import execl, makedirs
from subprocess import call, STDOUT
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
from park.plugin import load_file, wrap_as_bot_command
from park.text_processing import chunk_text, highlight_word
from park.util import (
    captured_stdout, get_code_from_url, google, install_log_handler, is_url,
    requires_invite, requires_subscription
)

HERE = dirname(abspath(__file__))
LOG_FILE_NAME = join(HERE, 'park.log')


class ChatRoomJabberBot(JabberBot):
    """ A chatroom bot that uses the XMPP protocol.

    Based on JabberBot and the broadcast example in the jabberbot package.

    """

    #: Maximum allowed length of nick
    NICK_LEN = 24

    def __init__(self, username, password, server=None, res=None, debug=False, root=None):
        super(ChatRoomJabberBot, self).__init__(
            username, password, res, debug=debug
        )

        # Root directory
        if root is None:
            root = HERE
        self.root = root

        self.debug = debug
        self.username = username
        self.server = server if server is not None else self.jid.getDomain()
        self.lock = threading.RLock()

        self._state = self.read_state()

        self.users = self._state.get('users', dict())
        self.invited = self._state.get('invited', dict())
        self.storytellers = self._state.get('storytellers', dict())
        self.ideas = self._state.get('ideas', [])
        self.topic = self._state.get('topic', '')
        self.gist_urls = self._state.get('gist_urls', [])
        self._protected = [',add', ',restart']
        self.started = time.time()
        self.message_queue = []
        self.thread_killed = False

        # Plugins
        self._command_plugins = []
        self._idle_hooks = []
        self._message_processors = []

        # Fetch all code from the gist urls and make commands
        self._add_gist_commands()

        # Load local commands.
        self._load_plugins()

        return

    @property
    def db(self):
        """ Returns the path to the persistence file. """

        return join(self.root, 'state.json')

    #### JabberBot interface ##################################################

    def callback_message(self, conn, mess):
        """ Command handling + routing.

        All messages sent to the bot will arrive here.

        """

        jid = mess.getFrom()
        props = mess.getProperties()
        text = mess.getBody()
        username = self.get_sender_username(mess)

        if username not in self.users.keys() + self.invited.keys():
            self.log.info(
                'Ignored %s type message - %s - from %s',
                mess.getType(), text, username
            )
            return

        self.log.debug("*** props = %s" % props)
        self.log.debug("*** jid = %s" % jid)
        self.log.debug("*** username = %s" % username)
        self.log.debug("*** type = %s" % type)
        self.log.debug("*** text = %s" % text)

        # Ignore messages from before we joined
        if xmpp.NS_DELAY in props:
            return

        # Ignore messages from myself
        if self.jid.bareMatch(jid):
            return

        # If message format is not supported (eg. encrypted), txt will be None
        if not text:
            return

        self._process_message_via_hooks(username, text)

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
                self.log.exception(
                    "An error happened while processing a message "
                    "('%s') from %s: %s", text, jid, reply
                )
        else:
            reply = self._unknown_command(mess, cmd, args)

        if reply:
            self.send_simple_reply(mess, unicode(reply))

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

            for (handler, callback) in self.handlers:
                self.conn.RegisterHandler(handler, callback)
                self.log.debug('Registered handler: %s' % handler)

            self.conn.RegisterDisconnectHandler(self._attempt_reconnect)
            self.conn.UnregisterDisconnectHandler(conn.DisconnectHandler)
            self._JabberBot__set_status(self.topic)

            ### Send a -- we are online -- message
            self.message_queue.append('_We are up and running!_')

        return self.conn

    def get_email_from_nick(self, nick):
        """ Return the email of the user with the given nick.

        Returns None, if no such nick exists.

        """

        for email, alias in self.users.iteritems():
            if nick == alias:
                break
        else:
            email = None

        return email

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
                    self.send(user, highlight_word(message, self.users[user]))

        return

    def read_state(self):
        """ Reads the persisted state. """

        self.lock.acquire()
        data = serialize.read_state(self.db)
        self.lock.release()

        return data

    def thread_proc(self):
        while not self.thread_killed:

            # fixme: do we need this?
            self.message_queue.append('')

            # fixme: prints in idle hooks are not captured as messages.
            # this may be good?
            for hook in self._idle_hooks:
                self._run_hook_in_thread(hook, self)

            self.save_state()

            for i in range(300):
                time.sleep(1)
                if self.thread_killed:
                    return

    def save_state(self, extra_state=None):
        """ Persists the state of the bot. """

        self.lock.acquire()
        old_state = self.read_state()
        new_state = dict(
            users=self.users,
            invited=self.invited,
            storytellers=self.storytellers,
            topic=self.topic,
            ideas=self.ideas,
            gist_urls=self.gist_urls
        )
        old_state.update(new_state)
        if extra_state is not None:
            old_state.update(extra_state)

        serialize.save_state(self.db, old_state)

        self.lock.release()

        return

    def shutdown(self):
        self.save_state()

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

        if nick in self.users.values():
            message = 'Nick already taken.'

        elif len(nick) == 0:
            message = 'Nick needs to be at least one character long'

        elif len(nick) > self.NICK_LEN:
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
                % (user, self.jid, self.subscribe._jabberbot_command_name)
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

    @botcmd(name=',add')
    @requires_subscription
    def add(self, user, args):
        """ Define a bot command, or other hooks from chat.

        This command lets extend the bot, by adding bot commands, or other
        hooks through the chat interface. New commands can be added as shown
        below ::

            ,add command_name
            def main():
                ''' Clears the screen!

                This command is intended to be used when you want to
                divert attention of the users from the previous
                discussion.
                '''

                print '\\n' * 80

        The commands can be added to a gist and the *raw* url can be passed
        to this command, like so ::

            ,add <raw-gist-url>

        For more information, look at
        http://punchagan.github.io/childrens-park/plugins.html#plugins

        """

        if not args:
            return "Didn't get any arguments for the command!"

        # Check if first word in args is a URL.
        first_arg = args.split()[0]

        if is_url(first_arg):
            url = first_arg
            code = get_code_from_url(url)
            name = basename(url)

        else:
            name = first_arg
            code = args[len(name):].strip()

        path = self._save_code_to_plugin(name, code)
        if path is not None:
            self._load_plugin_from_path(path)

        self.message_queue.append('%s registered command %s' % (user, name))

        return

    #### Private interface ####################################################

    def _add_command_from_plugin(self, plugin):
        """ Add the given plugin's main as a command. """

        if hasattr(plugin, 'main'):
            command = wrap_as_bot_command(
                self, plugin.main, ',%s' % plugin.__name__
            )

        else:
            command = None

        if command is not None:
            name = getattr(command, '_jabberbot_command_name')
            self.commands[name] = command

        else:
            self.log.info('Ignoring plugin %s' % plugin.__name__)

        return

    def _add_gist_commands(self):
        """ Adds persisted gists as commands (on startup). """

        for url in self.gist_urls[:]:
            code = get_code_from_url(url)
            name = basename(url)
            path = self._save_code_to_plugin(name, code)
            for requirement in self._get_requirements(path):
                self._install(requirement)
            if path is not None:
                self._load_plugin_from_path(path)

        return

    def _attempt_reconnect(self):
        """ Attempt to reconnect. """

        self.log.info('Restarting...')
        self.log.info('Pulling changes from GitHub...')
        call(
            ["git", "pull"],
            stdout=self.log.root.handlers[0].stream,
            stderr=STDOUT
        )
        logging.shutdown()
        execl(sys.executable, sys.executable, abspath(__file__))

        return

    def _get_requirements(self, path):
        """ Read requirements from the file. """

        with open(path) as f:
            for line in f:
                if line.startswith('REQUIREMENTS'):
                    ns = {}
                    exec line in ns
                    requirements = ns['REQUIREMENTS']
                    break
            else:
                requirements = []

        return requirements

    def _install(self, requirement):
        """ Pip install the given requirement. """

        import pip

        self.log.debug('Installing %s' % requirement)

        if pip.main(['install', requirement]) == 0:
            self.log.debug('Successfully installed %s' % requirement)

        else:
            self.log.debug('Failed to "pip install %s"' % requirement)

    def _load_plugin_from_path(self, path):
        """ Load the plugin at the given path. """

        plugin = load_file(path)

        if getattr(plugin, 'main', None) is not None:
            self._add_command_from_plugin(plugin)

        if getattr(plugin, 'idle_hook', None) is not None:
            self._idle_hooks.append(plugin.idle_hook)

        if getattr(plugin, 'message_processor', None) is not None:
            self._message_processors.append(plugin.message_processor)

        return

    def _load_plugins(self):
        """ Load all the plugins from the plugin directory. """

        plugins = glob.glob(join(self.root, 'plugins', '*.py'))

        for path in plugins:
            for requirement in self._get_requirements(path):
                self._install(requirement)

        for path in plugins:
            self._load_plugin_from_path(path)

        return

    def _process_message_via_hooks(self, username, text):
        """ Call the message processors on the text. """
        # fixme: how do we handle hooks that modify the text?
        def capture_output_from_hooks():
            with captured_stdout() as captured:
                threads = [
                    self._run_hook_in_thread(hook, self, username, text)

                    for hook in self._message_processors
                ]
                [thread.join() for thread in threads]

            self.message_queue.extend(captured.output.splitlines())

        # fixme: probably should be self.no_threading?
        # or may be capturing stdout isn't the best thing to do?
        # or in console mode, captured_stdout does different things?
        # the problem is captured_stdout, really! not threading.
        if self.debug:
            capture_output_from_hooks()

        else:
            thread = threading.Thread(target=capture_output_from_hooks)
            thread.daemon = True
            thread.start()

    def _run_hook_in_thread(self, hook, *args, **kwargs):
        """ Run the given hook in a new thread. """

        thread = threading.Thread(target=hook, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()

        return thread

    def _save_code_to_plugin(self, name, code):
        """ Save the given code as a plugin file. """

        # fixme: the directory should be called something meaningful.
        gist_plugin_dir = join(self.root, 'gist_plugins')
        if not exists(gist_plugin_dir):
            makedirs(gist_plugin_dir)

        if not name.endswith('.py'):
            name += '.py'

        if code:
            path = join(gist_plugin_dir, name)
            with open(path, 'w') as f:
                f.write(code)

        else:
            path = None

        return path

    @requires_subscription
    def _unknown_command(self, user, cmd, args):
        """ Handle everything that is not a known command.

        Currently, just sends it to all the other users as a message.

        """

        if not cmd.startswith(','):
            text = '%s %s' % (cmd, args)
            self.message_queue.append('[%s]: %s' % (self.users[user], text))
            message = ''

        else:
            message = 'unknown command: %s' % cmd

        return message


def main():
    try:
        from park.settings import USERNAME, PASSWORD, RES, SERVER
    except ImportError:
        print('Please copy sample-settings.py to settings.py and edit it!')
        sys.exit(1)

    debug = True if '--debug' in sys.argv else False
    install_log_handler(LOG_FILE_NAME, debug=debug)

    bc = ChatRoomJabberBot(USERNAME, PASSWORD, SERVER, RES, debug=debug)

    th = threading.Thread(target=bc.thread_proc)
    bc.serve_forever(connect_callback=lambda: th.start())
    bc.thread_killed = True


if __name__ == "__main__":
    main()

#### EOF ######################################################################
