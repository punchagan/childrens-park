Description
============

``park`` is a Jabber/Gtalk bot written using the python-jabberbot library.
This bot is written to behave like a chatroom, where all the messages are
sent to all the subscribed users.


Installation
============

+ Clone the repository from `GitHub`_

+ Run ``python setup.py develop`` to install the dependencies and
  setup your environment for running the bot.

+ This will create a dummy ``settings.py`` and ``state.json`` in the
  ``park`` directory. Edit these files with the appropriate values.

Usage
=====

You can run the bot using the command ``park`` after installing it.
You should have the first user manually "registered" in the
``state.json``, and he/she can invite the other users.


Bugs/Issues
===========

+ *Known Issue*: Google doesn't allow sending and receiving more than 50
  messages in a period of 12.5 seconds.  This basically makes the bot
  unusable, even for three or four users in the channel.  Use jabber.org for
  hosting the bot, instead.

+ Report other bugs/issues at `GitHub`_

.. _GitHub: https://github.com/punchagan/childrens-park/
