# Standard library
from os.path import join

# Project library
from park import serialize


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
