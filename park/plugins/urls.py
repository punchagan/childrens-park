# Standard library
import datetime
import hashlib
from lxml import html
import os
from os.path import abspath, dirname, join
import shutil
from urllib import urlopen

# 3rd party library
from premailer import transform

# Project library
from park import serialize
from park.serialize import read_state, save_state
from park.util import is_url, render_template, send_email

HERE = dirname(abspath(__file__))
DB_NAME = 'newsletter.json'


def message_processor(bot, user, text):
    """ Dump a message to the db in the bot's root, if it has a url. """

    urls = [token for token in text.split() if is_url(token)]

    if len(urls) == 0:
        return

    entries = []

    for url in urls:
        entry = {
            'url': url,
            'title': _get_title(url),
            'user': user,
            'timestamp': datetime.datetime.now().isoformat()
        }
        entries.append(entry)

    path = join(bot.root, DB_NAME)
    bot.lock.acquire()
    _save_entries(path, entries)
    bot.lock.release()

    return


# fixme: possibly could live in it's own plugin, once we do more than urls
def idle_hook(bot):
    """ Check if it is time to send the newsletter, and send it. """

    db = join(bot.root, DB_NAME)
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

    path = join(bot.root, DB_NAME)

    bot.lock.acquire()
    data = serialize.read_state(path)
    bot.lock.release()

    if len(data) == 0:
        message = 'No new urls.'

    else:
        fro = bot.username
        subject = 'Park updates since last newsletter'
        body = _get_email(bot, data, subject)
        send_email(fro, user, subject, body, typ_='html', debug=bot.debug)
        message = 'Sent email to %s' % user

    return message


#### Private protocol #########################################################

_TIMESTAMP_FMT = '%Y-%m-%dT%H:%M:%S.%f'


def _clear_urls(path):
    """ Move the db file to a name with the time stamp. """

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    new_path = join(dirname(path), 'newsletter-%s.json' % timestamp)
    shutil.copy(path, new_path)
    os.unlink(path)

    return


def _get_email_content(bot, urls):
    """" Return the content section of the email. """

    for entry in urls:
        email = entry['user']
        entry['name'] = bot.users.get(email) or bot.invited.get(email, email)
        entry['hash'] = hashlib.md5(email).hexdigest()
        if 'title' not in entry:
            entry['title'] = entry['url']

    return urls


def _get_email(bot, urls, subject):
    """ Return the content to be used for the newsletter. """

    context = {
        'entries': _get_email_content(bot, urls[:]), 'title': subject
    }

    template = join(HERE, 'data', 'newsletter_template.html')
    return transform(render_template(template, context))


def _get_title(url):
    """ Get the title of the page for a given url. """

    return html.parse(urlopen(url)).find('.//title').text or url


def _save_entries(path, entries):
    """ Save the url data to the db. """

    data = read_state(path)
    data = [] if not data else data
    data.extend(entries)
    save_state(path, data)

    return


def _save_timestamp(bot):
    """ Save the current time to the bot's state db. """

    bot.save_state(
        {'last_newsletter': datetime.datetime.now().strftime(_TIMESTAMP_FMT)}
    )

    return


def _send_newsletter(bot, urls, last_sent):
    """ Send the newsletter and save the timestamp to the state. """

    last_sent = last_sent.strftime('%b %d')
    now = datetime.datetime.now().strftime('%b %d')
    subject = 'Parkly Newsletter for %s to %s' % (last_sent, now)
    body = _get_email(bot, urls, subject)
    fro = bot.username
    to = bot.users.keys() + bot.invited.keys()

    send_email(fro, to, subject, body, typ_='html', debug=bot.debug)

    return


def _time_since(timestamp):
    """ Return a timedelta of current time and the given timestamp. """

    return datetime.datetime.now() - timestamp

#### EOF ######################################################################
