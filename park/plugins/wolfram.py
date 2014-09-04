REQUIREMENTS = ['wolframalpha']

import wolframalpha
import threading


def main(bot, user, args):
    """ Fetch top most result from Wolfram Alpha. """

    try:
        from park.settings import WOLFRAM_API_KEY
    except ImportError:
        return 'Need an API Key to be able to use Wolfram API.'

    def query_wolfram(args):
        results = wolframalpha.Client(WOLFRAM_API_KEY).query(args)

        try:
            result = next(results.results).text

        except StopIteration:
            result = None

        if result is not None:
            bot.message_queue.append(
                '%s wolframmed for %s... and here you go: '
                % (bot.users[user], args)
            )
            bot.message_queue.append(result)

        else:
            return 'No results found!'

    thread = threading.Thread(target=query_wolfram, args=(args,))
    thread.start()
