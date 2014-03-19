.. childrens-park documentation master file, created by
   sphinx-quickstart on Fri Sep  7 02:54:02 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to childrens-park's documentation!
------------------------------------------

.. include:: ../README.rst

Features
=========

The bot comes in with a bunch of builtin commands.  Run ``,help`` or look
at the :ref:`auto-doc` documentation.

New commands can be added by editing the source and adding new methods
on the :py:class:`ChatRoomJabberBot` class, decorated with the
:py:func:`botcmd` decorator.

New commands can also be added through plugins added into the source
or, more interestingly, via chat.  Look at the :ref:`plugins`
documentation, for details on how to do this.
