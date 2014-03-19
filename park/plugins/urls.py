# Standard library
import datetime
import hashlib
import os
from os.path import abspath, dirname, join

# 3rd party library
from premailer import transform

# Project library
from park import serialize
from park.serialize import read_state, save_state
from park.util import is_url, render_template, send_email

HERE = dirname(abspath(__file__))
DB_NAME = 'newsletter.json'


def message_processor(bot, user, text):
    """ Dump a message to the db in the bot's ROOT, if it has a url. """

    tokens = text.split()
    urls = [token for token in tokens if is_url(token)]

    if len(urls) == 0:
        return

    path = join(bot.ROOT, DB_NAME)

    bot.lock.acquire()
    data = read_state(path)
    for url in urls:
        if not data:
            data = []
        entry = {
            'user': user,
            'url': url,
            'timestamp': datetime.datetime.now().isoformat()
        }
        data.append(entry)
        save_state(path, data)
    bot.lock.release()

    return


# fixme: possibly could live in it's own plugin, once we do more than urls
def idle_hook(bot):
    """ Check if it is time to send the newsletter, and send it. """

    db = join(bot.ROOT, DB_NAME)
    data = bot.read_state()
    last_newsletter = (
        datetime.datetime.strptime(data['last_newsletter'], _TIMESTAMP_FMT)
        if 'last_newsletter' in data else None
    )

    if last_newsletter is None:
        _save_timestamp(bot)

    elif _time_since(last_newsletter).days >= 7:
        bot.lock.acquire()
        urls = serialize.read_state(db)
        bot.lock.release()
        if len(urls) > 0:
            _send_newsletter(bot, urls, last_newsletter)
            _clear_urls(db)
            _save_timestamp(bot)

    return


def main(bot, user, args):
    """ Show URLs posted by buddies. The ones since I last checked """

    path = join(bot.ROOT, DB_NAME)

    bot.lock.acquire()
    data = serialize.read_state(path)
    bot.lock.release()

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


#### Private protocol #########################################################

_TIMESTAMP_FMT = '%Y-%m-%dT%H:%M:%S.%f'


def _clear_urls(path):
    """ Remove the db file where urls are saved. """

    os.unlink(path)

    return


def _get_email_content(bot, urls):
    """" Return the content section of the email. """

    for entry in urls:
        email = entry['user']
        entry['name'] = bot.users.get(email) or bot.invited.get(email, email)
        entry['hash'] = hashlib.md5(email).hexdigest()
        # fixme: get the url title.

    return urls


def _get_email(context):
    """ Return the content to be used for the newsletter. """

    template = join(HERE, 'data', 'newsletter_template.html')
    return transform(render_template(template, context))


def _save_timestamp(bot):
    """ Save the current time to the bot's state db. """

    bot.save_state(
        {'last_newsletter': datetime.datetime.now().strftime(_TIMESTAMP_FMT)}
    )

    return


def _send_newsletter(bot, urls, last_sent):
    """ Send the newsletter and save the timestamp to the state. """

    fro = bot.username
    last_sent = last_sent.strftime('%b %d')
    now = datetime.datetime.now().strftime('%b %d')
    subject = 'Parkly Newsletter for %s to %s' % (last_sent, now)
    context = {
        'entries': _get_email_content(bot, urls[:]), 'title': subject
    }
    body = _get_email(context)
    to = ', '.join(bot.users.keys() + bot.invited.keys())
    send_email(fro, to, subject, body, typ_='html', debug=bot.debug)

    return


def _time_since(timestamp):
    """ Return a timedelta of current time and the given timestamp. """

    return datetime.datetime.now() - timestamp

#### EOF ######################################################################
