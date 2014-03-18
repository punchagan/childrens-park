Description
============

This is a Jabber/Gtalk bot written using the python-jabberbot library.  This
bot is written to behave like a chatroom, where all the messages are sent to
all the subscribed users.


Usage
=====

+ `python setup.py develop`  is the recommended way to use this bot. This
  creates a sample `settings.py` and `state.json` file.  Edit the
  `settings.py`with appropriate values, and change the info of the first user
  in `state.json`.


Bugs/Issues
===========

+ *Known Issue*: Google doesn't allow sending and receiving more than 50
  messages in a period of 12.5 seconds.  This basically makes the bot
  unusable, even for three or four users in the channel.  Use jabber.org for
  hosting the bot, instead.

+ Report other bugs/issues at `GitHub`_

.. _GitHub: https://github.com/punchagan/childrens-park/issues

