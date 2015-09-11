
======================
    did
======================

What did you do last week, month, year?


Description
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comfortably gather status report data (e.g. list of committed
changes) for given week, month, quarter, year or selected date
range. By default all available stats for this week are reported.


Synopsis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Usage is straightforward::

    did [last] [week|month|quarter|year] [opts]


Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Gather all stats for current week::

    did

Show me all stats for today::

    did today

Gather stats for the last month::

    did last month

See ``did --help`` for complete list of available stats.


Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The list of available options depends on which plugins are
configured. Here's the list of general options which are not
related to any plugin:

Select
------

--email=EMAILS
    User email address(es)

--since=SINCE
    Start date in the YYYY-MM-DD format

--until=UNTIL
    End date in the YYYY-MM-DD format

Format
------

--format=FMT
    Output style, possible values: text (default) or wiki

--width=WIDTH
    Maximum width of the report output (default: 79)

--brief
    Show brief summary only, do not list individual items

--verbose
    Include more details (like modified git directories)

Other
-----

--total
    Append total stats after listing individual users

--merge
    Merge stats of all users into a single report

--debug
    Turn on debugging output, do not catch exceptions

See ``did --help`` for complete list of available options.



Install
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install directly from Fedora/Copr repository::

    yum install did

or use PIP (sudo required if not in a virtualenv)::

    pip install did

To build and execute in a docker container, run::

    make run_docker

See documentation for more details about installation options.


Config
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The config file ``~/.did/config`` is used to store both general
settings and configuration of individual reports::

    [general]
    email = "Petr Šplíchal" <psplicha@redhat.com>
    width = 79

    [header]
    type = header
    highlights = Highlights
    joy = Joy of the week ;-)

    [tools]
    type = git
    did = /home/psss/git/did

    [tests]
    type = git
    tests = /home/psss/git/tests/*

    [trac]
    type = trac
    prefix = TT
    url = https://some.trac.com/trac/project/rpc

    [bz]
    type = bugzilla
    prefix = BZ
    url = https://bugzilla.redhat.com/xmlrpc.cgi

    [footer]
    type = footer
    next = Plans, thoughts, ideas...
    status = Status: Green | Yellow | Orange | Red

See plugin documentation for more detailed description of options
available for particular plugin. You can also check python module
documentation directly, e.g. ``pydoc did.plugins.git`` or use the
example config provided in the package and web documentation.


Links
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Git:
https://github.com/psss/did

Docs:
http://did.readthedocs.org

Issues:
https://github.com/psss/did/issues

Releases:
https://github.com/psss/did/releases

Copr:
http://copr.fedoraproject.org/coprs/psss/did

PIP:
https://pypi.python.org/pypi/did


Authors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Petr Šplíchal, Karel Šrot, Lukáš Zachar,
Matěj Cepl, Ondřej Pták and Chris Ward.


Copyright
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Copyright (c) 2015 Red Hat, Inc. All rights reserved.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation; either version 2 of
the License, or (at your option) any later version.


Status
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. image:: https://badge.fury.io/py/did.svg
    :target: http://badge.fury.io/py/did

.. image:: https://travis-ci.org/psss/did.svg?branch=master
    :target: https://travis-ci.org/psss/did

.. image:: https://coveralls.io/repos/psss/did/badge.svg
    :target: https://coveralls.io/r/psss/did

.. image:: https://img.shields.io/pypi/dm/did.svg
    :target: https://pypi.python.org/pypi/did/

.. image:: https://img.shields.io/pypi/l/did.svg
    :target: https://pypi.python.org/pypi/did/

.. image:: https://readthedocs.org/projects/did/badge/
    :target: https://readthedocs.org/projects/did/
