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
# You are required to have a file settings.py with the variables,
# JID, PASSWORD, CHANNEL, RES
#
# Depends: python-jabberbot, xmpppy
#

# standard library imports
from datetime import datetime
import json
import logging
from os.path import abspath, dirname, join, exists
from os import execl
import re
from subprocess import Popen, PIPE, call
import sys
import threading
import time
import traceback
import urllib

from jabberbot import JabberBot, botcmd
import xmpp


# local imports
from util import get_code_from_url, is_url, is_wrappable, possible_signatures
from cric_info import CricInfo


class ChatRoomJabberBot(JabberBot):
    """A bot based on JabberBot and broadcast example given in there."""

    #: Maximum allowed length of nick
    NICK_LEN = 24

    ROOT = dirname(abspath(__file__))

    def __init__(self, jid, password, res=None):
        super(ChatRoomJabberBot, self).__init__(jid, password, res)

        self._read_state()

        self.users = self._state.get('users', dict())
        self.invited = self._state.get('invited', dict())
        self.ideas = self._state.get('ideas', [])
        self.topic = self._state.get('topic', '')
        self.gist_urls = self._state.get('gist_urls', [])
        self._protected = [',addbotcmd', ',restart']
        self.started = time.time()
        self.message_queue = []
        self.thread_killed = False
        self.cric_bot = CricInfo(self, SCORECARD, SCORECARD_URL)

        self._install_log_handler()

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

            # Fetch all code from the gist urls and make commands
            self._add_gist_commands()
            ### Send a -- we are online -- message
            self.message_queue.append('_We are up and running!_')

        return self.conn

    def shutdown(self):
        self._save_state()

    def get_sender_username(self, mess):
        """ Extract the sender's user name (along with domain) from a message.
        """
        jid = mess.getFrom()
        typ = mess.getType()
        username = jid.getNode()
        domain = jid.getDomain()
        if typ == "chat":
            return "%s@%s" % (username, domain)
        else:
            return ""

    def get_sender_nick(self, mess):
        """ Get the nick of the user from a message.
        """
        username = self.get_sender_username(mess)
        return self.users[username]

    def thread_proc(self):
        while not self.thread_killed:
            self.message_queue.append('')
            self._save_state()
            for i in range(300):
                time.sleep(1)
                if self.thread_killed:
                    return

    def idle_proc(self):
        if not len(self.message_queue):
            return

        # copy the message queue, then empty it
        messages = self.message_queue
        self.message_queue = []

        for message in messages:
            # If an object in the message queue is not a string, make it one.
            if not isinstance(message, basestring):
                message = unicode(message)
            if len(self.users):
                self.log.info('sending "%s" to %d user(s).',
                              message, len(self.users))
            for user in self.users:
                if not message.startswith("[%s]:" % self.users[user]):
                    self._chunk_message(user,
                                       self._highlight_name(message, user))

    #### Bot Commands #########################################################

    @botcmd(name=',restart')
    def restart(self, mess, args):
        """Restart the bot. Use resource name as PASSWORD.

        To avoid accidental restarts, resource name is used as argument.
        """
        user = self.get_sender_username(mess)

        if user in self.users and args.strip() == self.res:
            self.message_queue.append('_%s restarted me! brb!_'
                                       % (self.users[user]))
            self.log.info('%s is restarting me.' % user)
            self.shutdown()
            self.idle_proc()
            self.conn.sendPresence(typ='unavailable')
            self._attempt_reconnect()

    @botcmd(name=',subscribe')
    def subscribe(self, mess, args):
        """Subscribe to the broadcast list"""
        user = self.get_sender_username(mess)
        if user in self.users:
            return 'You are already subscribed.'
        else:
            self.users[user] = user.split('@')[0][:self.NICK_LEN]
            self.invited.pop(user)
            self.message_queue.append('_%s has joined the channel_' % user)
            self.log.info('%s subscribed to the broadcast.' % user)
            return 'You are now subscribed.'

    @botcmd(name=',unsubscribe')
    def unsubscribe(self, mess, args):
        """Unsubscribe from the broadcast list"""
        user = self.get_sender_username(mess)
        if not user in self.users:
            return 'You are not subscribed!'
        else:
            user = self.users.pop(user)
            self.message_queue.append('_%s has left the channel_' % user)
            self.log.info('%s unsubscribed from the broadcast.' % user)
            return 'You are now unsubscribed.'

    @botcmd(name=',dnd')
    def dnd(self, mess, args):
        """Switch to do-not-disturb mode. Use ,dnd to switch back."""
        user = self.get_sender_username(mess)
        if user not in self.users and user not in self.invited:
            return 'You are not subscribed!'
        elif user in self.users:
            name = self.users.pop(user)
            self.invited[user] = name
            self.message_queue.append('_%s entered NO PARKING ZONE here_' % name)
            self.log.info('%s entered NO PARKING ZONE here.' % name)
            return 'NO PARKING ZONE entered.Happy riding!'
        elif user in self.invited:
            name = self.invited.pop(user)
            self.users[user] = name
            self.message_queue.append('_%s came out of NO PARKING ZONE_' % name)
            self.log.info('%s came out of NO PARKING ZONE.' % name)
            return 'PARKING ZONE entered. Hey %s!' % name

    @botcmd(name=',alias')
    def alias(self, mess, args):
        """Change your nick"""
        user = self.get_sender_username(mess)
        args = args.strip().replace(' ', '_')
        if user in self.users:
            if args in self.users.values():
                return 'Nick already taken.'
            elif len(args) == 0:
                return 'Nick needs to be atleast one character long'
            elif len(args) > self.NICK_LEN:
                return 'Nick cannot be longer than %s characters' % (self.NICK_LEN,)
            else:
                self.message_queue.append('_%s is now known as %s_' % (self.users[user], args))
                self.users[user] = args
                self.log.info('%s changed alias.' % user)
                self.log.info('%s' % self.users)
                return 'You are now known as %s' % args

    @botcmd(name=',topic')
    def topic(self, mess, args):
        """Change the topic/status"""
        user = self.get_sender_username(mess)
        if user in self.users:
            self.topic = args
            self._JabberBot__set_status(self.topic)
            self.message_queue.append('_%s changed topic to %s_' % (self.users[user], args))
            self.log.info('%s changed topic.' % user)

    @botcmd(name=',list')
    def list(self, mess, args):
        """List all the members of the list"""
        user = self.get_sender_username(mess)
        args = args.replace(' ', '_')
        if user in self.users or user in self.invited:
            user_list = 'All these users are subscribed - \n'
            user_list += '\n'.join(['%s :: %s' % (u, self.users[u]) for u in sorted(self.users)])
            if self.invited.keys():
                user_list += '\n The following users are invited - \n'
                user_list += '\n'.join(self.invited.keys())
            self.log.info('%s checks list of users.' % user)
            return user_list

    @botcmd(name=',me')
    def myself(self, mess, args):
        """Send message in third person"""
        user = self.get_sender_username(mess)
        if user in self.users:
            self.message_queue.append('*%s %s*' % (self.users[user], args))
            self.log.info('%s says %s in third person.' % (user, args))

    @botcmd(name=',invite')
    def invite(self, mess, args):
        """Invite a person to join the room. Works only if the person has added the bot as a friend, as of now."""
        user = self.get_sender_username(mess)
        if user in self.users:
            email = '%s@%s' % (xmpp.JID(args).getNode(), xmpp.JID(args).getDomain())
            if email in self.roster.getItems():
                self.send(args, '%s invited you to join %s. Say ",help" to see how to join.' % (user, CHANNEL))
                self.roster.Authorize(email)
                self.invited[email] = ''
                self.log.info('%s invited %s.' % (user, args))
                self.message_queue.append('_%s invited %s_' % (self.users[user], args))
            else:
                return 'User needs to add me to friend list before they can be invited.'

    @botcmd(name=',ideas')
    def ideas(self, mess, args):
        """Maintain a list of ideas/items. Use ,ideas help."""
        user = self.get_sender_username(mess)
        if user in self.users:
            if args.startswith('show'):
                txt = '\n_%s is ideating_\n' % (self.users[user])
                for i, idea in enumerate(self.ideas):
                    txt += '_%s - %s_\n' % (i, idea)
                self.message_queue.append(txt)
            elif args.startswith('add'):
                text = ' '.join(args.split()[1:]).strip()
                if text == '':
                    return "Sorry. Cannot add empty idea."
                self.ideas.append(text)
                self.message_queue.append('_%s added "%s" as an idea_' % (self.users[user], text))
            elif args.startswith('del'):
                try:
                    num = int(args.split()[1])
                    if num in range(len(self.ideas)):
                        self.message_queue.append('_%s deleted "%s" from ideas_' % (self.users[user], self.ideas[num]))
                        del self.ideas[num]
                except:
                    return "Invalid option to delete."
            elif args.startswith('edit'):
                try:
                    num = int(args.split()[1])
                    if num in range(len(self.ideas)):
                        txt = ' '.join(args.split()[2:]).strip()
                        if txt == '':
                            return "Sorry. Cannot add empty idea."
                        self.message_queue.append('_%s changed idea %s to %s_' % (self.users[user], num, txt))
                        self.ideas[num] = txt
                except:
                    return "Invalid option to edit."
            elif not args:
                return '\n'.join(['_%s - %s_' % (i, t) \
                                  for i, t in enumerate(self.ideas)])
            else:
                return """add - Adds a new idea
                del n - Deletes n^{th} idea
                edit n txt - Replace n^{th} idea with 'txt'
                show - Show ideas in chatroom
                no arguments - Show ideas to you"""

    @botcmd(name=',whois')
    def whois(self, mess, args):
        """Check who has a particular nick"""
        user = self.get_sender_username(mess)
        args = args.strip().replace(' ', '_')
        if user in self.users:
            self.log.info('%s queried whois %s.' % (user, args))
            if args in self.users.values():
                return filter(lambda u: self.users[u] == args, self.users)[0]
            else:
                return 'Nobody!'

    @botcmd(name=',uptime')
    def uptime(self, mess, args):
        """Check the uptime of the bot."""
        user = self.get_sender_username(mess)
        if user in self.users:
            t = datetime.fromtimestamp(time.time()) - \
                   datetime.fromtimestamp(self.started)
            hours = t.seconds / 3600
            mins = (t.seconds / 60) % 60
            secs = t.seconds % 60
            self.log.info('%s queried uptime.' % (user,))
            self.message_queue.append("Harbouring conversations, and what's more, memories, relentlessly since %s day(s) %s hour(s) %s min(s) and %s sec(s) for %s & friends" % (t.days, hours, mins, secs, self.users[user]))

    @botcmd(name=',g')
    def google_fetch(self, mess, args):
        """Fetch the top-most result from Google"""
        user = self.get_sender_username(mess)
        if user in self.users:
            self.log.info('%s queried %s from Google.' % (user, args))
            query = urllib.urlencode({'q': args})
            url = 'http://ajax.googleapis.com/ajax/' + \
                  'services/search/web?v=1.0&%s' % (query)
            results = urllib.urlopen(url)
            data = json.loads(results.read())
            self.message_queue.append('%s googled for %s ... and here you go'
                                      % (self.users[user], args))
            try:
                top = data['responseData']['results'][0]
                self.message_queue.append('%s -- %s' % (top['title'], top['url']))
            except:
                self.message_queue.append('%s' % "Oops! Nothing found!")

    @botcmd(name=',sc')
    def soundcloud_fetch(self, mess, args):
        """Fetch the top-most result from Google for site:soundcloud.com"""
        user = self.get_sender_username(mess)
        if user in self.users:
            self.log.info('%s queried %s from Google.' % (user, args))
            query = urllib.urlencode({'q': "site:soundcloud.com " + args})
            url = 'http://ajax.googleapis.com/ajax/' + \
                  'services/search/web?v=1.0&%s' % (query)
            results = urllib.urlopen(url)
            data = json.loads(results.read())
            top = data['responseData']['results'][0]
            self.message_queue.append('%s googled for %s ... and here you go'
                                      % (self.users[user], args))
            self.message_queue.append('%s -- %s' % (top['title'], top['url']))

    @botcmd(name=',cric')
    def cric(self, mess, args):
        """ A bunch of Cricinfo commands. Say ,cric help for more info. """
        cric_th = threading.Thread(target=self.cric_bot, args=(mess, args))
        cric_th.start()

    @botcmd(name=",stats")
    def stats(self, mess, args):
        "Simple statistics with message count for each user."
        user = self.get_sender_username(mess)
        self.log.info('Starting analysis... %s requested' % user)
        stats_th = threading.Thread(target=self._analyze_logs)
        stats_th.start()
        return 'Starting analysis... will take a while!'

    @botcmd(name=',see')
    def bot_see(self, mess, args):
        """ Look at bot's public attributes.

        You can past a list of attributes separated by spaces.
        """
        output = ''
        for arg in args.split():
            value = getattr(self, arg, None)
            if value is not None and not arg.startswith('_'):
                output += '%s is %s\n' %(arg, value)
            else:
                output += "%s - No such attribute\n" % arg
        return output

    @botcmd(name=',see-friends')
    def show_roster(self, mess, args):
        """ Return the roster of friends.
        """
        return '\n'.join([contact for contact in self.roster.getItems()])

    @botcmd(name=',help')
    def help_alias(self, mess, args):
        """An alias to help command."""
        return self.help(mess, args)

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
        if not(args):
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

    def _attempt_reconnect(self):
        self.log.info('Restarting...')
        self.log.info('Pulling changes from GitHub...')
        call(["git", "pull"])
        execl('/usr/bin/nohup', sys.executable, sys.executable,
                abspath(__file__))

    def _save_state(self):
        """ Persists the state of the bot.
        """
        with open(join(self.ROOT, 'state.json'), 'w') as f:
            state = dict(users=self.users,
                         invited=self.invited,
                         topic=self.topic,
                         ideas=self.ideas,
                         gist_urls=self.gist_urls)
            json.dump(state, f, indent=2)
        self.log.info('Persisted state data')

    def _read_state(self):
        """ Reads persisted state from state.json
        """
        state_file = join(self.ROOT, 'state.json')
        if not exists(state_file):
            self._state = dict()
        with open(state_file) as f:
            self._state = json.load(f)
        self.log.info('Obtained saved state from state.json')

    def _analyze_logs(self):
        self.log.info('Starting analysis...')
        logs = Popen(["grep", "sent:", "nohup.out"], stdout=PIPE)
        logs = logs.stdout
        people = {}
        for line in logs:
            log = line.strip().split()
            if not log or len(log) < 10:
                continue
            person = log[7]
            if '@' in person:
                person = person.split('@')[0]
            message = ' '.join(log[9:])
            if person not in people:
                people[person] = [message]
            else:
                people[person].append(message)
        stats = ["%-15s -- %s" % (dude, len(people[dude])) for dude in people]
        stats = sorted(stats, key=lambda x: int(x.split()[2]), reverse=True)
        stats = ["%-15s -- %s" % ("Name", "Message count")] + stats

        stats = 'the stats ...\n' + '\n'.join(stats) + '\n'

        self.log.info('Sending analyzed info')
        self.message_queue.append(stats)

    def _highlight_name(self, msg, user):
        """Emphasizes your name, when sent in a message.
        """
        nick = re.escape(self.users[user])
        msg = re.sub("(\W|\A)(%s)(\W|\Z)" % nick, "\\1 *\\2* \\3", msg)
        return msg

    def _add_gist_commands(self):
        """ Adds persisted gists as commands (on startup)
        """
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

    def _create_cmd_from_code(self, code, extra_doc=None):
        """ exec code, and make it a new bot cmd, if possible
        """
        from inspect import isfunction

        # Evaluate the code and get the function
        d = dict()
        exec(code) in globals(), d
        # XXX: Should let people define arbit global functions?
        if len(d) != 1:
            return False, 'You need to define one callable'
        f = d.values()[0]

        if not (isfunction(f) and f.__doc__):
            return (False, 'You can only add functions, with doc-strings')
        elif not is_wrappable(f):
            possible = possible_signatures()
            return (False, '%s are the only supported signatures' % possible)

        name = ',' + f.__name__
        f.__doc__ += "\n%s" % extra_doc or ''

        # Prevent over-riding protected commands
        if name in self._protected:
            return False, "Sorry, this function can't be over-written."

        # Wrap the function, as required and register it.
        self.commands[name] = self._wrap_function(f, code)

        return True, name

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

    def _chunk_message(self, user, msg):
        LIM_LEN = 512
        if len(msg) <= LIM_LEN:
            self.send(user, msg)
        else:
            idx = (msg.rfind('\n', 0, LIM_LEN) + 1) or (msg.rfind(' ', 0, LIM_LEN) + 1)
            if not idx:
                idx = LIM_LEN
            self.send(user, msg[:idx])
            time.sleep(0.1)
            self._chunk_message(user, msg[idx:])

    def _install_log_handler(self):
        # create console handler
        chandler = logging.StreamHandler()
        # create formatter
        format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        formatter = logging.Formatter(format)
        # add formatter to handler
        chandler.setFormatter(formatter)
        # add handler to logger
        self.log.addHandler(chandler)
        # set level to INFO
        self.log.setLevel(logging.INFO)

    def _callback_message(self, conn, mess):
        """Messages sent to the bot will arrive here. Command handling +
        routing is done in this function.
        """

        jid = mess.getFrom()
        props = mess.getProperties()
        text = mess.getBody()
        username = self.get_sender_username(mess)

        if username not in self.users.keys() + self.invited.keys():
            self.log.info("Ignored message from %s." % username)
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
        self.log.debug("*** cmd = %s" % cmd )

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

    def _unknown_command(self, mess, cmd, args):
        user = self.get_sender_username(mess)
        if user in self.users:
            self.message_queue.append('[%s]: %s %s' % (self.users[user], cmd, args))
            self.log.info("%s sent: %s %s" % (user, cmd, args))
        return ''

    def __getattr__(self, name):
        "Overridden to allow easier writing of user commands"
        return None


if __name__ == "__main__":
    PATH = dirname(abspath(__file__))
    sys.path = [PATH] + sys.path

    from settings import JID, PASSWORD, RES, SCORECARD, SCORECARD_URL, CHANNEL

    bc = ChatRoomJabberBot(JID, PASSWORD, RES)

    th = threading.Thread(target=bc.thread_proc)
    bc.serve_forever(connect_callback=lambda: th.start())
    bc.thread_killed = True
