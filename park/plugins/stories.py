# 3rd party library
import twitter


def message_processor(bot, user, text):
    """ Tweet the story, if message starts with >>>"""

	if text.startswith('>>>') and not text.startswith('>>>>')
		_tweet_story(bot, text[3:], user);

    return



def main(bot, user, args):
    """Post link to twitter handle where stories are updated/archived.(Use this
	to register a storyteller?)"""

    message = 'Mr. Gu10berg archives all the shor10sweet stories here:
	https://twitter.com/tenwordsworth. Mr. Park10 suggets, follow!'

    return message




def _tweet_story(bot, story, user):
    """ Tweets the story if it is within 10 words and 140 chars."""

	if len(story.split()) > 10:
		print 'That story was longer than 10 words. It goes untweeted. (And, this
		is how you tell a story within 10 words.)'
		return
	
	if user in bot.storytellers:
		tweetstory = story + ' - @' + bot.storytellers[user]
	else:
		tweetstory = story
	
	if len(tweetstory) > 140:
		print 'Oops! Could not tweet that. (140 chars limit, you know :/)'
		return
	else:
		from park.settings import CONSUMER_KEY, CONSUMER_SECRET,
		ACCESS_TOKEN_KEY, ACCESS_TOKEN_SECRET
		twitterapi = twitter.Api(consumer_key=CONSUMER_KEY,
		   consumer_secret=CONSUMER_SECRET,
		     access_token_key=ACCESS_TOKEN_KEY,
			   access_token_secret=ACCESS_TOKEN_SECRET)
		api.PostUpdate(tweetstory)
		print 'wOOt! You just got published %s' % bot.users[user]

    return

#### EOF ######################################################################
