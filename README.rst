Description
============

This is a Jabber/Gtalk bot written using the python-jabberbot library.  This
bot is written to behave like a chatroom, where all the messages are sent to
all the subscribed users.

Dependencies
============

  + python-jabberbot
  + xmpppy
  + BeautifulSoup
  + gdata

Usage
=====

  + You are required to have a file settings.py with the variables, JID,
    PASSWORD, CHANNEL, RES. Copy the `sample-settings.py` and edit it.

  + To add new users, the admin can either add them manually to state.json
    file.

Bugs/Issues
===========

  + *Known Issue*: Google doesn't allow sending and receiving more than 50
    messages in a period of 12.5 seconds.  This is a big problem if you have
    even three or four members in the channel.  Use jabber.org for hosting the
    bot, instead.

  + Report other bugs/issues at `GitHub`_

.. _GitHub: https://github.com/punchagan/childrens-park/issues

