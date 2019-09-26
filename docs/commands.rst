======================
    Commands
======================

Detailed documentation for individual ``tmt`` commands.


test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Test command is used to investigate and handle test metadata. Use
``tmt test convert`` to gather old metadata stored in different
sources and convert them into the new ``fmf`` format.

By default ``Makefile`` and ``PURPOSE`` files in the current
directory are inspected and the ``Nitrate`` test case management
system is contacted to gather all related metadata::

    makefile ..... summary, component, duration
    purpose ...... description
    nitrate ...... environment, relevancy

In order to fetch data from Nitrate you need to have ``nitrate``
module installed. You can also use ``--no-nitrate`` to disable
Nitrate integration.
