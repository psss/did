
======================
    did
======================

What did you do last week, month, year?


Description
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comfortably gather status report data (e.g. list of committed
changes) for given week, month, quarter, year or selected date
range. By default all available stats for this week are reported.

Based on the config, ``did`` explores user's activity for given
tools in provided time frame. For example checks all configured
git repositories for the list of commits or contacts Bugzilla to
search for bugs created, modified or closed.

Some information (like git commits) is gathered from the local
file system, but usually individual plugins are contacting remote
API of the tool to query for the latest data. For tools which
provide a public API there is no need for authentication. Some
plugins support Kerberos, other need to create an authentication
token. See individual plugin documentation for details.


Synopsis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Usage is straightforward::

    did [this|last] [week|month|quarter|year] [opts]


Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Gather all stats for current week::

    did

Show me all stats for today, yesterday, last Friday::

    did today
    did yesterday
    did last friday

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

At least one email address needs to be provided on command line
unless defined in the config file. Use the complete email address
format ``Name Surname <email@example.org>`` to display full name
in the report output. For date values ``today`` and ``yesterday``
can be used instead of the full date format.

--email=EMAILS
    User email address(es)

--since=SINCE
    Start date in the YYYY-MM-DD format

--until=UNTIL
    End date in the YYYY-MM-DD format

Format
------

The default output is plain text of maximum width 79 characters.
This can be adjusted using the ``--width`` parameter. To disable
shortening altogether use ``--width=0``. The default width value
can be saved in the config file as well. Use ``--format=wiki`` to
enable simple MoinMoin wiki syntax. For stats which support them,
``--brief`` and ``--verbose`` can be used to specify a different
level of detail to be shown.

--format=FMT
    Output style, possible values: text (default) or wiki

--width=WIDTH
    Maximum width of the report output (default: 79)

--brief
    Show brief summary only, do not list individual items

--verbose
    Include more details (like modified git directories)

Utils
-----

Multiple emails can be used to put together a team report or to
gather stats for all of your email aliases. For this use case
``--total`` and ``--merge`` can be used to append the overall
summary at the end or merge all results into a single report
respectively. Use ``--debug`` or set the environment variable
``DEBUG`` to 1 through 5 to set the desired level of debugging.

--config=FILE
    Use alternate configuration file (default: 'config')

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

Or use pip to install from Python Package Index::

    pip install did

You may want to install some or all extra requires::

    pip install did[plugin]
    pip install did[all]

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
https://did.readthedocs.io

Issues:
https://github.com/psss/did/issues

Releases:
https://github.com/psss/did/releases

Copr:
https://copr.fedoraproject.org/coprs/psss/did

PIP:
https://pypi.org/project/did


Authors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Petr Šplíchal, Karel Šrot, Lukáš Zachar, Matěj Cepl, Ondřej Pták,
Chris Ward, Tomáš Hofman, Martin Mágr, Stanislav Kozina, Paul
Belanger, Eduard Trott, Martin Frodl, Randy Barlow, Alois Mahdal,
Evgeni Golov, Stanislav Ochotnický, Maroš Kopec, Robbie Harwood,
Christopher Sams, Thomas Heute, Giulio Fidente, Han Han, Qiao
Zhao, Henrique Ferreiro, Jakub Vávra, Luigi Toscano, Lukáš
Zapletal, Maryna Nalbandian, Dominika Hoďovská, Jakub Haruda,
Han Han, Štěpán Němec, Evgeny Fedin, Mikel Olasagasti Uranga,
Miloš Malík, Jeffrey Bastian, Côme Chilliet and Konrad Kleine.


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

.. image:: https://coveralls.io/repos/github/psss/did/badge.svg
    :target: https://coveralls.io/github/psss/did

.. image:: https://img.shields.io/pypi/dm/did.svg
    :target: https://pypi.python.org/pypi/did/

.. image:: https://img.shields.io/pypi/l/did.svg
    :target: https://pypi.python.org/pypi/did/

.. image:: https://readthedocs.org/projects/did/badge/
    :target: https://readthedocs.org/projects/did/
