from BeautifulSoup import BeautifulSoup
import time
from textwrap import dedent
import urllib2

class CricInfo(object):
    """ A class for all the cric info stuff.
    """

    def __init__(self, parent, scorecard='scorecard.html',
        scorecard_url='scorecard.html', url='http://www.espncricinfo.com'):
        self.parent = parent
        self.matches = None
        self.match = None
        self.url = url
        self.scorecard = scorecard
        self.scorecard_url = scorecard_url

    def _soupify_url(self, url):
        """ Open a url and return it's soup."""
        opener = urllib2.build_opener()
        opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
        data = opener.open(self.url + url)
        soup = BeautifulSoup(data)
        return soup

    def cric_summary(self):
        """ Fetches the minimal scoreboard """
        url = self.matches[self.match][1]
        soup = self._soupify_url(url)
        title, = soup.findAll('title')
        score = title.text.split('|')[0]

        msg = score
        log = 'Obtained minimal scoreboard'
        return msg, log, True

    def cric_recent(self):
        """ Fetches the recent overs
        """
        url = self.matches[self.match][1]
        view = '?view=live'
        soup = self._soupify_url(url + view)
        recent, = soup.findAll('p', 'liveDetailsText', limit=1)

        msg = recent.getText(' ')
        log = 'Obtained recent overs score'
        return msg, log, True

    def cric_score(self):
        """ Fetch the score-card.
        """
        url = self.matches[self.match][1]
        view = '?view=scorecard'
        soup = self._soupify_url(url + view)
        scorecard = soup.findAll("table", "inningsTable")
        scorecard = '\n'.join([str(tag) for tag in scorecard])
        f = open(self.scorecard, 'w')
        f.write('Scorecard last updated -- %s<br><br>\n' % time.ctime())
        f.write(str(scorecard))
        f.close()

        log = "Obtained live scorecard url"
        msg = 'Scores written to %s' % self.scorecard_url
        return msg, log, True

    def cric_matches(self, args):
        """ Fetches currently relevant matches. """
        if not self.matches or not args:
            soup = self._soupify_url('/')
            matches, = soup.findAll('table', id='international', limit=1)
            self.matches = [[match.getText(' '), match.attrs[0][1], '0', '1'] \
                            for match in matches.findAll('a')]
            if len(self.matches) > 1:
                msg = 'Now obtained, matches - '
                for i, match in enumerate(self.matches):
                    msg += '\n[%s] - %s' % (i, match[0])
                msg += '\nSelect a match'
                log = "Obtained list of matches."
                return msg, log, False
            else:
                args = '0'
        try:
            n = int(args)
            if n < len(self.matches):
                self.match = n
            else:
                self.match = 0
            msg = 'Match set to %s' % self.matches[self.match][0]
            return msg, msg, True
        except:
            msg = 'Behave yourelf'
            return msg

    def _caller(self, func_name, args):
        if func_name == 'matches':
            return self.cric_matches(args)
        elif self.match is None:
            msg = 'Use matches command to obtain and set matches.'
            log = 'Use matches'
            return msg, log
        command = getattr(self, 'cric_' + func_name, self._help)
        return command()

    def __call__(self, mess, args):
        """An entry point to the cric info stuff.
        """
        user = self.parent.get_sender_username(mess)
        user = self.parent.users[user]

        if not args:
            args = 'summary'

        args_list = args.split()
        result = self._caller(args_list[0], ' '.join(args_list[1:]))

        if len(result) == 3:
            msg, log, group = result
        elif len(result) == 2:
            msg, log = result
            group = False
        else:
            msg = log = result
            group = False

        self.parent.log.info('%s -- %s' % (log, user))
        if group:
            self.parent.message_queue.append(msg)
        else:
            self.parent.send_simple_reply(mess, msg)

    def _help(self):
        help = dedent("""
        ,cric matches -- Get list of matches
        ,cric matches n -- Set match number to n
        ,cric -- Brief summary of the match
        ,cric recent -- Recent Overs
        ,cric score -- Full scorecard
        """)
        log = 'Sending help'
        return help, log
