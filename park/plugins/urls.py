# Standard library
import datetime
import os
from os.path import join

# Project library
from park import serialize
from park.util import send_email


def main(bot, user, args):
    """ Show URLs posted by buddies. The ones since I last checked """

    path = join(bot.ROOT, 'shit.json')  # fixme: duplication.
    data = serialize.read_state(path)
    urls = {}

    for entry in data:
        user = entry['user']
        url = entry['url']
        user_urls = urls.setdefault(user, [])
        user_urls.append(url)

    messages = [
        '%s:\n    %s' % (user, '\n    '.join(user_urls))
        for user, user_urls in urls.iteritems()
    ]

    if len(messages) == 0:
        message = 'No new urls.'

    else:
        message = '\n' + '\n'.join(messages)

    return message


def idle_hook(bot):
    """ Check if it is time to send the newsletter, and send it. """

    # fixme: possibly could live in it's own plugin, once we do more than urls
    db = join(bot.ROOT, 'shit.json')
    data = bot.read_state()
    last_newsletter = data.get('last_newsletter', None)

    if last_newsletter is None or _time_since(last_newsletter).days >= 7:
        urls = serialize.read_state(db)
        if len(urls) > 0:
            _send_newsletter(bot, urls)
            _clear_urls(db)

    return

#### Private protocol #########################################################

_TIMESTAMP_FMT = '%Y-%m-%dT%H:%M:%S.%f'


def _clear_urls(path):
    """ Remove the db file where urls are saved. """

    os.unlink(path)

    return


def _send_newsletter(bot, urls):
    """ Send the newsletter and save the timestamp to the state. """

    # fixme: hard-coded values.
    fro = 'park@muse-amuse.in'
    subject = 'Parkly Newsletter'
    body = str(urls)
    to = ', '.join(bot.users.keys() + bot.invited.keys())
    send_email(fro, to, subject, body, typ_='html', debug=bot.debug)

    bot.save_state(
        {'last_newsletter': datetime.datetime.now().strftime(_TIMESTAMP_FMT)}
    )

    return


def _time_since(timestamp):
    """ Return a timedelta of current time and the given timestamp. """

    if timestamp is not None:
        old = datetime.datetime.strptime(timestamp, _TIMESTAMP_FMT)
        now = datetime.datetime.now()
        since = now - old

    else:
        since = None

    return since

#### EOF ######################################################################
