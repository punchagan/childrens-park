""" A plugin to allow users to replace text in messages, sed style!

s/foo/bar replaces "foo" with "bar" in the last HISTORY_LENGTH messages.

The replace lets users replace text in other users messages, as well,
but preference is given to messages of the user.

"""

# Standard library
import re

HISTORY_LENGTH = 5  # keep only the last 5 messages in history.


def message_processor(bot, user, text):
    """ Dump a message to the db in the bot's root, if it has a url. """

    history = getattr(bot, 'history', [])

    expression = re.match('s/([^/]+)/([^/]*)/?', text)
    if expression is not None:
        replacements = []

        for sender, message in history:
            try:
                replaced, n = re.subn(
                    expression.group(1), expression.group(2), message
                )

                if n > 0:
                    replacements.append((sender, replaced))

            except Exception:
                # We simply print, because the attempt to replace isn't private
                print '_%s, invalid regex._' % bot.users[sender]
                break

        if len(replacements) == 0:
            print (
                '_%s, No replacements found. May be your message is too old_'
                % bot.users[user]
            )

        elif len(replacements) == 1:
            sender, replaced = replacements[0]
            print '_%s meant %s_' % (bot.users[sender], replaced)

        else:
            users_messages = [(s, r) for s, r in replacements if s == user]
            if len(users_messages) > 0:
                sender, replaced = users_messages[0]
                print '_%s meant %s_' % (bot.users[sender], replaced)

            else:
                sender, replaced = users_messages[0]
                print '_%s meant %s_' % (bot.users[sender], replaced)

    else:
        history.insert(0, (user, text))
        bot.history = history[:HISTORY_LENGTH]
