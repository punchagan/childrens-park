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

        for i, pod in enumerate(results.pods):
            if pod.id == 'Result':
                break
        else:
            pod = None
            pods = list(results.pods)

        if pod is not None or pods is not None:
            bot.message_queue.append(
                '%s wolframmed for %s... and here you go: '
                % (bot.users[user], args)
            )

            if pod is not None:
                bot.message_queue.extend([pod.title, pod.text])

            else:
                for pod in pods:
                    bot.message_queue.extend([pod.title, pod.text])

        else:
            bot.send(user, 'No results found!')

    thread = threading.Thread(target=query_wolfram, args=(args,))
    thread.start()
