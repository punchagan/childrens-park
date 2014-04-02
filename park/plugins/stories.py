REQUIREMENTS = ['python-twitter']


def message_processor(bot, user, text):
    """ Tweet the story, if message starts with >>>"""

    if text.startswith('>>>') and not text.startswith('>>>>'):
        _tweet_story(bot, text[3:], user)

    return


# fixme: modify this to allow storytellers to be registered.
def main():
    """ Get link to the story archive! """

    message = (
        'Mr. Gu10berg archives all the shor10sweet stories here:'
        'https://twitter.com/tenwordsworth. Mr. Park10 suggests, follow!'
    )
    return message


def _post_tweet(text):
    """ Post the given text, using credentials from our settings. """

    from park.settings import (
        CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN_KEY, ACCESS_TOKEN_SECRET
    )

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
        print (
            'That story was longer than 10 words. It goes un-tweeted. '
            '(And, this is how you tell a story within 10 words.)'
        )
        return

    if user in bot.storytellers:
        tweetstory = story + ' - @' + bot.storytellers[user]

    else:
        tweetstory = story

    message = _post_tweet(tweetstory)
    if message is None:
        message = 'wOOt! You just got published %s' % bot.users[user]

    print message

#### EOF ######################################################################
