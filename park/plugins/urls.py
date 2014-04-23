REQUIREMENTS = ['ago']

# Standard library
import datetime
import hashlib
import os
from os.path import abspath, dirname, join
import shutil
from urllib2 import Request, urlopen

from lxml import html


# 3rd party library
from premailer import transform

# Project library
from park import serialize
from park.plugins.stories import get_tweets_since
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
        content = _get_parsed_content(url)
        entry = {
            'url': url,
            'title': _get_title(content) or url,
            'description': _get_description(content),
            'user': user,
            'timestamp': datetime.datetime.now().isoformat()
        }
        entries.append(entry)

    path = join(bot.root, DB_NAME)
    bot.lock.acquire()
    _save_entries(path, entries)
    bot.lock.release()

    return


def idle_hook(bot):
    """ Check if it is time to send the newsletter, and send it. """

    data = bot.read_state()
    last_newsletter = (
        datetime.datetime.strptime(data['last_newsletter'], _TIMESTAMP_FMT)
        if 'last_newsletter' in data else None
    )

    if last_newsletter is None:
        _save_timestamp(bot)

    elif _time_since(last_newsletter).days >= 7:
        db = join(bot.root, DB_NAME)
        _send_newsletter(bot, db, last_newsletter)
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
        additional_content = {'stories': _get_stories(bot, save=False)}
        body = _get_email(bot, path, subject, additional_content)
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


def _get_description(content):
    """ Get the description of a given the parsed content. """

    # Get description like Google+ snippets does
    elements = [
        content.find("//*[@itemprop='description']"),
        content.find("//*[@property='og:description']"),
        content.find("//meta[@name='description']")
    ]

    descriptions = [
        element.text_content() or element.get('content') or ''

        for element in elements if element is not None
    ]

    if len(descriptions) == 0:
        description = ''

    elif len(descriptions) == 1:
        description = descriptions[0]

    else:
        description = max(descriptions, key=len)

    return description.strip().encode('utf8')


def _get_email_content(bot, urls):
    """" Return the content section of the email. """

    from ago import human

    # fixme: we could do a better job with repeated items, order of urls

    for entry in urls:
        email = entry['user']
        entry['name'] = bot.users.get(email) or bot.invited.get(email, email)
        entry['hash'] = hashlib.md5(email).hexdigest()
        if 'title' not in entry or len(entry['title'].strip()) == 0:
            entry['title'] = entry['url']

        entry['human_timestamp'] = human(
            datetime.datetime.strptime(entry['timestamp'], _TIMESTAMP_FMT)
        )

    return urls


def _get_email(bot, db, title, additional_content=None):
    """ Return the content to be used for the newsletter. """

    # Get urls from the db
    bot.lock.acquire()
    urls = serialize.read_state(db)
    bot.lock.release()

    entries = [
        entry for entry in _get_email_content(bot, urls[:])

        if len(entry['url']) != 0
    ]
    context = {'title': title}

    for entry in entries:
        if 'github.com/punchagan/childrens-park' in entry['url']:
            context.setdefault('code_updates', []).append(entry)

        else:
            context.setdefault('shared_links', []).append(entry)

    if additional_content is not None:
        context.update(additional_content)

    template = join(HERE, 'data', 'newsletter_template.html')
    return transform(render_template(template, context))


def _get_parsed_content(url):
    """ Return the parsed html of a given page. """

    try:
        request = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(request)

    except Exception:
        from StringIO import StringIO
        response = StringIO('<html></html>')

    return html.parse(response)


def _get_title(content):
    """ Get the title of the page given parsed content. """

    element = content.find('.//title')
    title = element.text or '' if element is not None else ''

    return title.strip().encode('utf8')


def _get_stories(bot, save=True):
    """ Get the stories posted since the last newsletter. """

    data = bot.read_state()
    last_newsletter = (
        datetime.datetime.strptime(data['last_newsletter'], _TIMESTAMP_FMT)
        if 'last_newsletter' in data else None
    )
    stories_max_id = data.get('stories_since_id', None)
    tweets = get_tweets_since(last_newsletter, stories_max_id)

    if len(tweets) > 0 and save:
        bot.save_state(extra_state={'stories_since_id': tweets[0].id})

    return tweets


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


def _send_newsletter(bot, db, last_sent):
    """ Send the newsletter and save the timestamp to the state. """

    last_sent = last_sent.strftime('%b %d')
    now = datetime.datetime.now().strftime('%b %d')
    subject = 'Parkly Newsletter for %s to %s' % (last_sent, now)
    additional_content = {'stories': _get_stories(bot)}
    body = _get_email(bot, db, subject, additional_content)
    fro = bot.username
    to = bot.users.keys() + bot.invited.keys()

    send_email(fro, to, subject, body, typ_='html', debug=bot.debug)

    return


def _time_since(timestamp):
    """ Return a timedelta of current time and the given timestamp. """

    return datetime.datetime.now() - timestamp

#### EOF ######################################################################
