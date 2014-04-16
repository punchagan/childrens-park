REQUIREMENTS = ['python-twitter']

# 3rd-party library
from requests_oauthlib import OAuth1Session
import twitter

# Project library
# fixme: should we have a way to add stuff into settings.py?
try:
    from park.settings import (
        CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN_KEY, ACCESS_TOKEN_SECRET
    )
except ImportError:
    CONSUMER_KEY = CONSUMER_SECRET = ''
    ACCESS_TOKEN_KEY = ACCESS_TOKEN_SECRET = ''

ACCESS_TOKEN_URL = 'https://api.twitter.com/oauth/access_token'
APP_URL = 'https://twitter.com/settings/applications'
AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'
REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'


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
            'All stories are archived at https://twitter.com/tenwordsworth\n'
        )

        message += 'Currently registered story tellers:\n'

        message += '\n'.join(
            [
                '%s - @%s' % (bot.users[key], value)
                for key, value in bot.storytellers.iteritems()
            ]
        )

        return message

    if len(text.strip().split()) > 1:
        message = 'Only accepts "register", "unregister" or PIN'

    elif text == 'register':
        url, token, secret = _get_authorization_url()

        if hasattr(bot, 'stories_tokens'):
            bot.stories_tokens[user] = token, secret

        else:
            bot.stories_tokens = {user: (token, secret)}

        message = 'Please authorize here: %s\n' % url

        message += (
            'Note: Though our application has write access, we are currently '
            'not going to make any tweets from your account. We ask you to '
            'register only to ascertain your twitter handle. You can revoke '
            'access once you register (this is recommended!) from: %s'
        ) % APP_URL

    elif text == 'unregister':
        story_teller = bot.storytellers.pop(user, None)
        story_token = bot.stories_tokens.pop(user, None)
        if story_teller is not None or story_token is not None:
            message = 'You have successfully unregistered'

        else:
            message = 'You were not registered!'

    else:
        stories_tokens = getattr(bot, 'stories_tokens', {})
        if user not in stories_tokens:
            message = 'Register with the ,stories register first!'

        else:
            pin = text.strip()
            token, secret = stories_tokens.pop(user)
            handle = _get_twitter_handle(token, secret, pin)
            bot.storytellers[user] = handle
            message = 'Registered as story teller - %s. ' % handle
            message += (
                'You are encouraged to revoke access from: %s' % APP_URL
            )

    return message


def get_tweets_since(last_checked=None, since_id=None):
    """ Return the list of tweets after a specified time or id.

    If an id is not specified, either all tweets newer than the specified
    timestamp or a maximum of 200 tweets are returned.

    """

    api = twitter.Api(
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        access_token_key=ACCESS_TOKEN_KEY,
        access_token_secret=ACCESS_TOKEN_SECRET
    )

    # 200 limit is set by twitter? python-twitter doesn't let count > 200.
    try:
        tweets = api.GetUserTimeline(
            count=200, since_id=since_id, include_rts=False
        )

    except Exception:
        tweets = []

    if last_checked is not None:
        tweets = [
            tweet for tweet in tweets
            if tweet.created_at_in_seconds > _to_seconds(last_checked)
        ]

    return tweets


def _get_authorization_url():
    """ Return a twitter authorization URL, the oauth token and secret. """

    oauth = OAuth1Session(CONSUMER_KEY, CONSUMER_SECRET)
    response = oauth.fetch_request_token(REQUEST_TOKEN_URL)
    oauth_token = response.get('oauth_token')
    oauth_token_secret = response.get('oauth_token_secret')
    authorization_url = oauth.authorization_url(AUTHORIZATION_URL)

    return authorization_url, oauth_token, oauth_token_secret


def _get_twitter_handle(token, secret, pin):

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


def _to_seconds(timestamp):
    """ Convert a datetime timestamp into seconds since epoch. """

    return (timestamp - timestamp.utcfromtimestamp(0)).total_seconds()


def _tweet_story(bot, story, user):
    """ Tweets the story if it is within 10 words and 140 chars."""

    if len(story.split()) > 10:
        message = (
            'That story was longer than 10 words. It goes un-tweeted. '
            '(And, this is how you tell a story within 10 words.)'
        )
        print message
        return

    elif story.split()[-1].startswith('@'):
        print 'You cannot tweet stories by others!'
        return

    if user in bot.storytellers:
        story += ' - @' + bot.storytellers[user]

    message = _post_tweet(story)
    if message is None:
        message = 'wOOt! You just got published %s' % bot.users[user]

    print message

#### EOF ######################################################################
