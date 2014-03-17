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


# fixme: this should be contributed via a hook, too.
# currently, we don't have a hook for processing all messages before sending...
def dump_message_with_url(user, text, target_dir):
    """ Dump a message to the db in the target dir, if it has a url. """

    tokens = text.split()
    urls = [token for token in tokens if is_url(token)]

    if len(urls) == 0:
        return

    path = join(target_dir, DB_NAME)

    for url in urls:
        data = read_state(path)
        if not data:
            data = []
        entry = {
            'user': user,
            'url': url,
            'timestamp': datetime.datetime.now().isoformat()
        }
        data.append(entry)
        save_state(path, data)

    return


# fixme: possibly could live in it's own plugin, once we do more than urls
def idle_hook(bot):
    """ Check if it is time to send the newsletter, and send it. """

    db = join(bot.ROOT, DB_NAME)
    data = bot.read_state()
    last_newsletter = data.get('last_newsletter', None)

    if last_newsletter is None or _time_since(last_newsletter).days >= 7:
        urls = serialize.read_state(db)
        if len(urls) > 0:
            _send_newsletter(bot, urls)
            _clear_urls(db)

    return


def main(bot, user, args):
    """ Show URLs posted by buddies. The ones since I last checked """

    path = join(bot.ROOT, DB_NAME)
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


def _send_newsletter(bot, urls):
    """ Send the newsletter and save the timestamp to the state. """

    fro = bot.username
    subject = 'Parkly Newsletter'
    context = {
        'entries': _get_email_content(bot, urls[:]), 'title': subject
    }
    body = _get_email(context)
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
