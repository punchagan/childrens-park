REQUIREMENTS = ['python-twitter']


def message_processor(bot, user, text):
    """ Tweet the story, if message starts with >>>"""

    if text.startswith('>>>') and not text.startswith('>>>>'):
        _tweet_story(bot, text[3:], user)

    return


def main(bot, user, text):
    """ Get link to the story archive! """

    if len(text.strip()) == 0:
        message = (
            'Mr. Gu10berg archives all the shor10sweet stories here:'
            'https://twitter.com/tenwordsworth. Mr. Park10 suggests, follow!'
        )

        return message

    # fixme: Use OAuth or something more secure to register!
    text = text.strip().split()
    if len(text) > 2:
        message = 'Only accepts twitter-handle or "email twitter-handle"'

    elif len(text) == 2:
        email, handle = text

        if email in bot.users:
            bot.storytellers[email] = handle
            message = '%s registered %s as %s' % (user, email, handle)

        else:
            message = 'Unknown or unsubscribed user'

    else:
        handle = text[0]
        bot.storytellers[user] = handle
        message = '%s registered as %s' % (user, handle)

    print message


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
        message = (
            'That story was longer than 10 words. It goes un-tweeted. '
            '(And, this is how you tell a story within 10 words.)'
        )
        # fixme: prints inside hooks are not captured, only commands!
        bot.message_queue.append(message)
        return

    if user in bot.storytellers:
        tweetstory = story + ' - @' + bot.storytellers[user]

    else:
        tweetstory = story

    message = _post_tweet(tweetstory)
    if message is None:
        message = 'wOOt! You just got published %s' % bot.users[user]

    bot.message_queue.append(message)

#### EOF ######################################################################
