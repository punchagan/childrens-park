.. _plugins:

=========
 Plugins
=========

``park``'s bot comes with a plugin mechanism that aims to make it
relatively easy to extend the bot, specially in terms of adding new
bot commands, for new developers.  The hope is to let people with very
little programming knowledge to be able to add simple commands
relatively easily.  At the same time, advanced users should be able to
do any shenanigans they wish to do.

There are currently 3 extension points, to which users can contribute
their extensions.

1. Adding a bot command.
#. Adding a function as an ``idle_hook`` that runs every 5 minutes, to
   do background jobs.
#. Adding a function as a ``message_processor`` that is called on
   every message (in a separate thread). This can be used for data
   collection and analysis kind of jobs.

The `urls plugin`_ is a good example illustrating the use of these
three extension points.

The plugins can either be added by creating a new python module in the
plugins directory of ``park``'s code, or adding the url to a page with
the new source, using the ``,add`` command via chat!

NOTE: Currently, only bot commands present in the code added via chat
are used for extending the bot.  Other code is ignored!  This should
soon be fixed, though.

.. _howto-add-cmd:

Adding new commands
===================

+ The ``main`` function defined inside your plugin is added as a bot
  command.

+ Your function can have one of the following 4 signatures ::

    main(),
    main(text)
    main(user, text)
    main(bot, user, args)

  ``bot`` is and instance of the :class:`ChatRoomJabberBot` that we are
  extending, ``user`` is the email of the user who ran the command, and
  ``text`` is the text of the actual message sent by the user, after
  stripping out the command name.

+ By default, when wrapping these commands, they are decorated with
  :py:func:`requires_subscription`.  If you want to write a command
  which doesn't require subscription, you'll have to manually decorate
  your function with the :py:func:`botcmd`.

+ The doc-string of your function becomes the help string.

+ Anything returned by your function, will be sent as a message to
  **only** the user who invoked the command.

+ Anything that is printed by your function will be sent to all the
  users.  Alternately, you can append your messages to the
  :attr:`message_queue` of the :class:`ChatRoomJabberBot` instance
  passed to your function.

+ To help debug your code, a built-in `,see` command is provided.  You
  can pass this command the names of the attributes that you'd like to
  *see*, at any point. For instance, send the message `,see users` to
  see the list of all the users currently subscribed.

+ You can also dynamically add your own instance variables, to the
  :class:`ChatRoomJabberBot` instance.  The :meth:`__getattr__` of
  :class:`ChatRoomJabberBot` has been overridden to return a ``None``
  instead of raising and `AttributeError` when accessing undefined
  attributes.  This lets you add attributes in your function, just by
  checking if it's None, without having to use things like ``getattr`` or
  ``hasattr``.

+ To prevent over-writing variables, defined by other users, it is
  recommended that you use a namespace convention
  `cmd_name_variable_name` for your variables.  For example, if your
  command is called `rps` and you'd like to add a `score`, use the
  name `rps_score` for your variable.  If you don't variables to be
  viewable using the `,see` command, use a private variable like
  `_rps_score`.

I have tried to make it as easy as possible for developers to develop
their code, without having to test on a running instance of the bot.
Feel free to comment upon/suggest any more ideas to make this easier
on developers.

More examples are available on github --

    + `Clear command <https://gist.github.com/37d4875e41056b58a8f5>`_
    + `Cows and Bulls game <https://gist.github.com/e5de28c7afd150d60fc0>`_

Adding ``idle_hook``
====================

Idle hooks are functions that are run every 5 minutes, but you can
choose to return early and not do anything on a particular run.  Each
such function is run in a thread of its own.  So, your code will need
to be "thread safe".

To define a new ``idle_hook``, you just have to add a method with that
name to a plugin.  See the `urls plugin`_ for an example.

Adding ``message_processor``
============================

A message processor is a function that gets called on every message
that is sent to the chatroom.  Each message processor is run in its
own thread, and therefore cannot currently modify the messages before
they are processed further and sent to the users. They can only
process and analyze the messages and do background tasks. Again, your
code will need to be "thread safe".

To define a message processor, add a  ``message_processor`` function
to your plugin. See the `urls plugin`_ for an example.

.. _urls plugin: https://github.com/punchagan/childrens-park/blob/master/park/plugins/urls.py>

.. _auto-doc:

:py:class:`ChatRoomJabberBot`
=============================

Useful Attributes
^^^^^^^^^^^^^^^^^
.. attribute:: users

    List of all users subscribed to the bot

.. attribute:: invited

    List of all users invited to the bot

.. attribute:: topic

    Topic for the bot

.. attribute:: gist_urls

    List of all gist urls added as bot commands


Methods docs
^^^^^^^^^^^^

.. currentmodule:: park.chatroom

.. autoclass:: ChatRoomJabberBot
    :members:
