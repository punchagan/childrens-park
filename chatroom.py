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

from jabberbot import JabberBot, botcmd

import xmpp

import threading
import time 
import logging
import traceback
import codecs
from datetime import timedelta, datetime

from settings import *

import re
import urllib2

try:
    from BeautifulSoup import BeautifulSoup
except:
    self.log.info('You need to have BeautifulSoup for cricinfo')



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

        self.users = self.get_users()
        
        self.invited = self.get_invited()

        self.ideas = self.get_ideas()        

        self.started = time.time()

        self.cric_matches = None
        self.cric_match = None
        self.cric_url = 'http://www.espncricinfo.com'
        self.cric_on = False
        
        self.message_queue = []
        self.thread_killed = False

    def connect(self):
        if not self.conn:
            conn = xmpp.Client(self.jid.getDomain(), debug = [])

            if self.jid.getDomain() == 'gmail.com':
                conres = conn.connect(server=('talk.google.com', 5222))
            else:
                conres = conn.connect()
            
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
            self._JabberBot__set_status(self.get_topic())

        return self.conn

    def save_state(self):
        f = open('state.py', 'w')
        f.write('# -*- coding: utf-8 -*-\n\n')
        self.save_users(f)
        self.save_invited(f)
        self.save_topic(f)
        self.save_ideas(f)
        f.close()

    def get_users(self):
        try:
            from state import USERS
            users = USERS
            for user in users:
                users[user] = users[user].decode('utf-8')
            self.log.info("Obtained user data")
        except:
            users = {}
            self.log.info("No existing user data")
        return users
    
    def save_users(self, file):
        try:
            file.write('USERS = {\n')
            for u in self.users:
                file.write("'%s': '%s',\n"
                           %(u.encode('utf-8'),
                             self.users[u].encode('utf-8')))
            file.write('}\n\n')
            self.log.info("Saved user data")
        except:
            self.log.info("Couldn't save user data")

    def get_invited(self):
        try:
            from state import INVITED
            invited = INVITED
            for user in invited:
                invited[user] = invited[user].decode('utf-8')
            self.log.info("Obtained invited user data")
        except:
            invited = {}
            self.log.info("No existing invited users")
        return invited
    
    def save_invited(self, file):
        try:
            file.write('INVITED = {\n')
            for u in self.invited:
                file.write("'%s': '%s',\n" %(u, self.invited[u].encode('utf-8')))
            file.write('}\n\n')
            self.log.info("Saved invited user data")
        except:
            self.log.info("Couldn't save invited user data")

    def get_topic(self):
        try:
            from state import TOPIC
            TOPIC = TOPIC.decode('utf-8')
            return TOPIC
        except:
            return ''

    def save_topic(self, file):
        try:
            file.write('TOPIC = """%s"""\n\n' %(self._JabberBot__status.encode('utf-8')))
        except:
            return ''

    def get_ideas(self):
        try:
            from state import IDEAS
            ideas = [idea.decode('utf-8') for idea in IDEAS]
        except:
            ideas = []
        return ideas

    def save_ideas(self, file):
        try:
            file.write('IDEAS = [\n')
            for u in self.ideas:
                file.write('"""%s""",\n' % (u.encode('utf-8')))
            file.write(']\n\n')
        except:
            self.log.info("Couldn't save ideas")

    def shutdown(self):
        self.save_state()
        self.cric_on = False

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

        if username not in self.users.keys() + self.invited.keys():
            self.log.info("Ignored message from %s." % username)
            return

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
        cmd = command
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
            self.save_state()
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
            self.save_state()
            return 'You are now unsubscribed.'


    @botcmd(name=',alias')
    def alias( self, mess, args):
        """Change your nick"""
        user = self.get_sender_username(mess)
        args = args.strip().replace(' ', '_')
        if user in self.users:
            if 0 < len(args) < 24 and args not in self.users.values():
                self.message_queue.append('_%s is now known as %s_' %(self.users[user], args))
                self.users[user] = args
                self.log.info( '%s changed alias.' % user)
                self.log.info('%s' %self.users)
                self.save_state()
                return 'You are now known as %s' % args
            else:
                return 'Nick already taken, or too short/long. 1-24 chars allowed.'


    @botcmd(name=',topic')
    def topic( self, mess, args):
        """Change the topic/status"""
        user = self.get_sender_username(mess)
        if user in self.users:
            self._JabberBot__set_status(args)
            self.message_queue.append('_%s changed topic to %s_' %(self.users[user], args))
            self.log.info( '%s changed topic.' % user)
            self.save_state()


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
            self.save_state()
            self.message_queue.append('_%s invited %s_' % (self.users[user], args))

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
                self.save_state()
                self.message_queue.append('_%s added "%s" as an idea_' % (self.users[user], text))
            elif args.startswith('del'):
                try:
                    num = int(args.split()[1])
                    if num in range(len(self.ideas)):
                        self.message_queue.append('_%s deleted "%s" from ideas_' % (self.users[user], self.ideas[num]))
                        del self.ideas[num]
                        self.save_state()
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
                        self.save_state()
                except:
                    return "Invalid option to edit."
            elif not args:
                return '\n'.join(['_%s - %s_' %(i,t) for i,t in enumerate(self.ideas)])
            else:
                return """add - Adds a new idea
                del n - Deletes n^{th} idea
                edit n txt - Replace n^{th} idea with 'txt'
                show - Show ideas in chatroom
                no arguments - Show ideas to you"""

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

    @botcmd(name=',uptime')
    def uptime(self, mess, args):
        """Check the uptime of the bot."""
        user = self.get_sender_username(mess)
        if user in self.users:
            t = datetime.fromtimestamp(time.time()) - \
                   datetime.fromtimestamp(self.started)
            hours = t.seconds/3600
            mins = (t.seconds/60)%60
            secs = t.seconds%60
            self.log.info('%s queried uptime.' % (user))
            self.message_queue.append("Harbouring conversations, and what's more, memories, relentlessly since %s day(s) %s hour(s) %s min(s) and %s sec(s) for %s & friends" % (t.days, hours, mins, secs, self.users[user]))

    @botcmd(name=',yt')
    def youtube_fetch(self, mess, args):
        """Fetch the top-most result from YouTube"""
        user = self.get_sender_username(mess)
        try:
            import gdata.youtube
            import gdata.youtube.service
        except:
            self.log.info('You need to have python-gdata')
            return 'python-gdata needs to be installed!'
        if user in self.users:
            self.log.info('%s queried %s from Youtube.' % (user, args))
            yt_service = gdata.youtube.service.YouTubeService()
            query = gdata.youtube.service.YouTubeVideoQuery()
            query.racy = 'include'
            query.orderby = 'relevance'
            query.max_results = 1
            query.vq = args

            feed = yt_service.YouTubeQuery(query)
            self.message_queue.append('%s searched for %s ...' %(self.users[user], args))

            for entry in feed.entry:
                self.message_queue.append('... and here you go -- %s' % entry.GetHtmlLink().href)

    @botcmd(name=',cric')
    def cric(self, mess, args):
        """ A bunch of Cricinfo commands. Say ,cric help for more info. """
        cric_th = threading.Thread(target=self.cric_parse, args=(mess,args))
        cric_th.start()

    def cric_soupify_url(self, url):
        """ Open a url and return it's soup."""
        opener = urllib2.build_opener()
        opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
        data = opener.open(self.cric_url+url)
        soup = BeautifulSoup(data)
        return soup

    def cric_get_matches(self):
        """ Fetches currently relevant matches. """
        soup = self.cric_soupify_url('/')
        matches, = soup.findAll('table', id='special', limit=1)
        return [[match.getText(' '), match.attrs[0][1], '0', '1'] for match in matches.findAll('a')]

    def cric_get_summary(self, url):
        """ Fetches the minimal scoreboard """
        soup = self.cric_soupify_url(url)
        title, = soup.findAll('title')
        score = title.text.split('|')[0]
        return score
    
    def cric_get_recent(self, url):
        """ Fetches the recent overs"""
        view = '?view=live'
        soup = self.cric_soupify_url(url+view)
        recent, = soup.findAll('p', 'liveDetailsText', limit=1)
        return recent.getText(' ')

    def cric_get_commentary_url(self, url):
        """ Fetches the url of the current innings """
        view = '?view=live'
        soup = self.cric_soupify_url(url+view)
        try: 
            l, = filter(lambda t: 'Commentary' in t.text, soup.findAll('a', "cardMenu"))
            url = l.attrs[0][1]
            self.log.info("Obtained commentary url")
            return url
        except:
            self.log.info("Commentary url not found")
            return

    def cric_get_innings(self, url):
        """ Find out the innings from commentary url"""
        return re.findall(r'innings=(.)', url)[0]

    def cric_get_commentary(self, url):
        """ Fetches the Commentary of current innings"""
        url = self.cric_get_commentary_url(url)
        if not url:
            return
        curr_inn = self.cric_get_innings(url)
        if self.cric_matches[self.cric_match][3] == '1' and curr_inn == '2':
            self.cric_matches[self.cric_match][2] = '0' # reset last ball
            self.cric_matches[self.cric_match][3] = '2' # change innings
            self.log.info("cricinfo: Changed innings")
            return  # Just adding some time delay
        soup = self.cric_soupify_url(url)
        S = soup.find('table', attrs={'class':'commsTable'})
        C = S.findAll('p', 'commsText')
        all_C = []
        for i, comm in enumerate(C):
            for hit in ['FOUR,', 'SIX,', 'OUT,']:
                if hit in comm.text:
                    ball = C[i-1].text
                    if float(ball) > float(self.cric_matches[self.cric_match][2]):
                        all_C.append((ball, comm.text.replace('\n', ' ')))
        self.log.info("Obtained new undisplayed commentary")
        return all_C

    def cric_poll(self, url):
        while self.cric_on:
            self.log.info('Will Poll Cricinfo, if not unset when I sleep')
            for i in range(30):
                time.sleep(1)
                if not self.cric_on:
                    return
            self.log.info('Polling Cricinfo')
            comm = self.cric_get_commentary(url)
            if comm:
                self.cric_matches[self.cric_match][2] = comm[-1][0]
                comm.append(('Score', self.cric_get_summary(self.cric_matches[self.cric_match][1])))
                comm = [' - '.join(c) for c in comm]
                comm = '\n\n'.join(comm)
                self.message_queue.append(comm)
                self.log.info('Sent new commentary')
                    
    def cric_parse(self, mess, args):
        """ A function that is used in a new thread."""
        user = self.get_sender_username(mess)

        if not args:
            if self.cric_match is None or not self.cric_matches:
                self.send_simple_reply(mess, 'Use the matches sub-command')
                return
            summary = self.cric_get_summary(self.cric_matches[self.cric_match][1])
            self.log.info('%s' %(summary))
            self.message_queue.append(summary)

        elif args.startswith('recent'):
            if self.cric_match is None or not self.cric_matches:
                self.send_simple_reply(mess, 'Use the matches sub-command')
                return
            recent = self.cric_get_recent(self.cric_matches[self.cric_match][1])
            self.log.info('%s' %(recent))
            self.message_queue.append(recent)

        elif args.startswith('matches'):
            matches = self.cric_get_matches()
            self.send_simple_reply(mess,'Now obtained, matches - ')
            for i, match in enumerate(matches):
                self.send_simple_reply(mess,'[%s] - %s' %(i, match[0]))
            if '-f' in args or not self.cric_matches:
                self.cric_matches = matches
            else:
                self.send_simple_reply(mess,'Matches *previously* set to - ')
                for i, match in enumerate(self.cric_matches):
                    self.send_simple_reply(mess,'[%s] - %s' %(i, match[0]))
                self.send_simple_reply(mess,'*matches -f* will force change.')
            self.send_simple_reply(mess,'Set the match using ,cric set.')

        elif args.startswith('set'):
            args = args.split()
            if len(args)!=2:
                self.send_simple_reply(mess, 'Behave yourelf, %s' %user)
                return
            try:
                n = int(args[1])
                self.cric_match = n
                self.message_queue.append('Match set to %s by %s'
                                          %(self.cric_matches[n][0], user))
                return 
            except:
                self.send_simple_reply(mess, 'Behave yourelf, %s' %user)
                return
        elif args == 'on':
            # Start a thread to keep polling cricinfo
            self.cric_on = True
            if self.cric_match is None or not self.cric_matches:
                self.send_simple_reply(mess, 'Use the matches sub-command')
                return
            cric_poll_th = threading.Thread(target=self.cric_poll,
                                args=(self.cric_matches[self.cric_match][1],))
            cric_poll_th.start()
            self.message_queue.append('Polling turned on by %s. Match -- %s'
                                      %(user, self.cric_matches[self.cric_match][0]))
        elif args == 'off':
            # Unset variable to stop polling
            self.cric_on = False
            self.message_queue.append('Polling turned off by %s. Match -- %s'
                                      %(user, self.cric_matches[self.cric_match][0]))

        else:
            help = """
            ,cric matches -- Current matches
            ,cric set n -- Set match number to n
            ,cric -- Brief summary of the match
            ,cric on -- Turn 'on' polling 
            ,cric recent -- Recent Overs
            ,cric full -- Full scorecard (MAY NOT IMPLEMENT)
            ,cric live -- Prev 2 overs of commentary? (MAY NOT IMPLEMENT)
            """
            self.send_simple_reply(mess, help)

    @botcmd(name=',see')
    def bot_see(self, mess, args):
        """ Look at bot's attributes.

        May not be a good idea to allow use for all users, but for
        now, I don't care."""
        try:
            return "%s is %s" % (args, bc.__getattribute__(args))
        except AttributeError:
            return "No such attribute"

    @botcmd(name=',help')
    def help_alias(self, mess, args):
        """An alias to help command."""
        return self.help(mess,args)

    def chunk_message(self, user, msg):
        LIM_LEN = 768
        if len(msg) <= LIM_LEN:
            self.send(user+"@gmail.com", msg)
        else:
            idx = msg.rfind('\n', 0, LIM_LEN)
            if idx < 0:
                idx = LIM_LEN
            self.send(user+"@gmail.com", msg[:idx])
            self.chunk_message(user, msg[idx:])

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
                    self.chunk_message(user, message)

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

