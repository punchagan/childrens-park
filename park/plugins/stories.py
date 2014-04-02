REQUIREMENTS = ['python-twitter']

from park.settings import (
    CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN_KEY, ACCESS_TOKEN_SECRET
)


def message_processor(bot, user, text):
    """ Tweet the story, if message starts with >>>"""

    if text.startswith('>>>') and not text.startswith('>>>>'):
        _tweet_story(bot, text[3:].strip(), user)

    return


def main(bot, user, text):
    """ Get link to the story archive or register!

    To register, first call command with "register" argument, and follow the
    authorization link.  Next call the command with the PIN as argument.

    """

    if len(text.strip()) == 0:
        message = (
            'Mr. Gu10berg archives all the shor10sweet stories here:'
            'https://twitter.com/tenwordsworth. Mr. Park10 suggests, follow!'
        )

        return message

    if len(text.strip().split()) > 1:
        message = 'Only accepts "register" or PIN'

    elif text == 'register':
        url, token, secret = _get_authorization_url()

        if hasattr(bot, 'stories_tokens'):
            bot.stories_tokens[user] = token, secret

        else:
            bot.stories_tokens = {user: (token, secret)}

        message = 'Please authorize here: %s' % url

    else:
        stories_tokens = getattr(bot, 'stories_tokens', {})
        if user not in stories_tokens:
            message = 'Register with the ,stories register first!'

        else:
            pin = text.strip()
            token, secret = stories_tokens.get(user)
            handle = _get_twitter_handle(token, secret, pin)
            bot.storytellers[user] = handle
            message = 'Registered as story teller - %s.' % handle

    return message


def _get_authorization_url():
    """ Return a twitter authorization URL (and the oauth_token and secret?) """

    from requests_oauthlib import OAuth1Session

    REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
    AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'

    oauth = OAuth1Session(CONSUMER_KEY, CONSUMER_SECRET)
    response = oauth.fetch_request_token(REQUEST_TOKEN_URL)
    oauth_token = response.get('oauth_token')
    oauth_token_secret = response.get('oauth_token_secret')
    authorization_url = oauth.authorization_url(AUTHORIZATION_URL)

    return authorization_url, oauth_token, oauth_token_secret


def _get_twitter_handle(token, secret, pin):
    from requests_oauthlib import OAuth1Session

    ACCESS_TOKEN_URL = 'https://api.twitter.com/oauth/access_token'

    client = OAuth1Session(
        CONSUMER_KEY,
        CONSUMER_SECRET,
        token,
        secret,
        verifier=pin
    )
    data = client.fetch_access_token(ACCESS_TOKEN_URL)

    return data['screen_name']


def _post_tweet(text):
    """ Post the given text, using credentials from our settings. """

    import twitter

    api = twitter.Api(
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        access_token_key=ACCESS_TOKEN_KEY,
        access_token_secret=ACCESS_TOKEN_SECRET
    )

    try:
        api.PostUpdate(text)
        message = None

    except twitter.TwitterError as e:
        message = e.message[0]['message']

    return message


def _tweet_story(bot, story, user):
    """ Tweets the story if it is within 10 words and 140 chars."""

    if len(story.split()) > 10:
        message = (
            'That story was longer than 10 words. It goes un-tweeted. '
            '(And, this is how you tell a story within 10 words.)'
        )
        # fixme: prints inside hooks are not captured, only commands!
        bot.message_queue.append(message)
        return

    elif story.split()[-1].startswith('@'):
        bot.message_queue.append('You cannot tweet stories by others!')
        return

    if user in bot.storytellers:
        story += ' - @' + bot.storytellers[user]

    message = _post_tweet(story)
    if message is None:
        message = 'wOOt! You just got published %s' % bot.users[user]

    bot.message_queue.append(message)

#### EOF ######################################################################
