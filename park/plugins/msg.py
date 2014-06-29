def message_processor(bot, user, text):
    """ Tweet the story, if message starts with >>>"""

    pending_messages = getattr(bot, 'pending_messages', {})
    if user in pending_messages:

        messages = [
            '%s -- %s' % (bot.users[email], text)
            for email, text in pending_messages.pop(user, [])
        ]

        msg = (
            '%s, the following messages were sent to you, '
            'while you were offline :: \n' % bot.users[user]
        )

        msg += '\n'.join(messages)

        bot.send(user, msg)


def main(bot, user, text):
    """ Save messages to send to user when they first say something. """

    if len(text) > 0:
        nick = text.split()[0]
        email = bot.get_email_from_nick(nick)
        msg = text[len(nick):].strip()

        if email is None:
            message = 'Need a valid nick to send message to.'

        elif len(msg) == 0:
            message = 'Need a message to leave for the user.'

        else:
            # fixme: have a function that plugins can add to bot's start-up?
            # may not help much because plugins are added at runtime...
            # plugin.initialize, basically.  should be called on
            # install/initialization too.
            if not hasattr(bot, 'pending_messages'):
                bot.pending_messages = bot.read_state().get(
                    'pending_messages', {}
                )

            bot.pending_messages.setdefault(email, []).append((user, msg))

            message = (
                'Your message will be delivered to %s, '
                'when they are online.\n'
                'Note: these messages are not persisted and '
                'may be lost if we restart!' % nick
            )

        return message
