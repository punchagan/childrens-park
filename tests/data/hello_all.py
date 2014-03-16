def main(bot, user, text):
    """ Send a hello from user to all users. """

    bot.message_queue.append('%s says namaste' % user)

    return
