.. childrens-park documentation master file, created by
   sphinx-quickstart on Fri Sep  7 02:54:02 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to childrens-park's documentation!
------------------------------------------

.. include:: ../README.rst

Features
=========

The bot comes in with a bunch of builtin commands.  Run ,help or look at the
:ref:`auto-doc` documentation.

But, apart from this you can add new commands using the ,addbotcmd. Look at
:ref:`howto-add-cmd`.

.. _howto-add-cmd:

How-to add new bot commands
===========================

New commands can be added to the bot using the ,addbotcmd.  The command can
take either a `raw gist url <https://gist.github.com>`_ url or a string, with
the required function definition, as an argument. For example ::

    ,addbotcmd https://gist.github.com/punchagan/7cb723285b00c4900ce5/raw/468f0c72ad0e01eb11754816bcf3d9f789b558ff/youtube_cmd.py

    ,addbotcmd<space>
    <Your function goes here>

Only the commands added through a gist-url will be persisted across restarts.

Here are a few things, you need to keep in mind, when writing your code:

    + As of now, your code (in the gist or directly typed into chat) should
      have only one function definition, and nothing else.  You can, obviously
      have other functions or classes defined within your own function.

    + Your function must have a doc-string, which will be shown in the help
      shown to the users

    + Your function can take upto 3 arguments, which is any ordered-
      combination of (self, mess, args) -- i.e, your function can only have
      any one of the following signatures ::

        f(),
        f(self), f(mess), f(args),
        f(self, mess), f(self,args), f(mess, args),
        f(self, mess, args)

      `self` is the :class:`ChatRoomJabberBot`, `mess` is the actual message
      object, from which you can extract information about the sender, etc.,
      and `args` is the text in the message, after stripping out the command
      name.

    + Anything returned by your function, will be sent only to the invoker of
      your command.

    + Anything that is printed by your function will be sent to all the users.
      Alternately, you can append your messages to the :attr:`message_queue`
      of the :class:`ChatRoomJabberBot` instance passed to your function.

    + To help debug your code, a built-in `,see` command is provided.  You can
      pass this command the names of the attributes that you'd like to *see*,
      at any point. For instance, send the message `,see users` to see the
      list of all the users currently subscribed.

    + You can also dynamically add your own instance variables, to the
      :class:`ChatRoomJabberBot` instance.  The :meth:`__getattr__` of
      :class:`ChatRoomJabberBot` has been overridden to return a `None`
      instead of raising and `AttributeError` when accessing undefined
      attributes.  This lets you add attributes in your function, just by
      checking if it's None, without having to use things like `getattr` or
      `hasattr`.

    + To prevent over-writing variables, defined by other users, it is
      recommended that you use a namespace convention `cmd_name_variable_name`
      for your variables.  For example, if your command is called `rps` and
      you'd like to add a `score`, use the name `rps_score` for your variable.
      If you don't variables to be viewable using the `,see` command, use a
      private variable like `_rps_score`.

We have tried to make it as easy as possible for developers to develop their
code, without having to test on a running instance of the bot.  Feel free to
comment upon/suggest any more ideas to make this easier on developers.

With all this in mind, let's write a simple command called `time_it` that
gives you the time between the current invocation and the previous invocation
of the command.  We start writing a simple module `time_it.py` that can run
independently.

::

    prev_time = None

    def time_it():
        """ Send time delta since the last run, to all users.
        """
        import time
        global prev_time
        cur_time = time.time()
        if prev_time is None:
            print "This is the first run."
        else:
            print cur_time - prev_time, "seconds, since last run."
        prev_time = cur_time
        return 'The current time is', cur_time

    if __name__ == '__main__':
        time_it()
        time.sleep(5)
        time_it()
        time.sleep(2)
        time_it()

All the variables, that we intend to set as attributes of the
:class:`ChatRoomJabberBot` are initialized as globals, and set to None.  All
the messages that should be sent to all users, are just printed out.  Once we
have a working function, we can modify it, to have it working with the bot.
In the above function, we change the function to take one argument `self`, and
change the global `prev_time` to be an attribute of the
:class:`ChatRoomJabberBot`.  The code finally, would look as follows ::

    def time_it(self):
        """ Send time delta since the last run, to all users.
        """
        import time
        cur_time = time.time()
        if self.prev_time is None:
            print "This is the first run."
        else:
            print cur_time - self.prev_time, "seconds, since last run."
        self.prev_time = cur_time
        return 'The current time is', cur_time

Now, we can go ahead and add this code as a new bot command!

More examples are available on github --

    + `Clear command <https://gist.github.com/37d4875e41056b58a8f5>`_
    + `Cows and Bulls game <https://gist.github.com/e5de28c7afd150d60fc0>`_


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

.. currentmodule:: chatroom

.. autoclass:: ChatRoomJabberBot
    :members:
