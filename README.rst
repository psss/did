
======================
    did
======================

What did you do last week, month, year?


Description
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comfortably gather status report data (e.g. list of committed
changes) for given week, month, quarter, year or selected date
range. By default all available stats for this week are reported.


Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Gather all stats for current week::

    did

Gather stats for the last week::

    did last week

See ``did --help`` for complete list of available stats.


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

The config file ``~/.did`` is used to store both general
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
    apps = /home/psss/git/apps

    [tests]
    type = git
    tests = /home/psss/git/tests/*

    [trac]
    type = trac
    prefix = TT
    url = https://some.trac.com/trac/project/rpc

    [footer]
    type = footer
    next = Plans, thoughts, ideas...
    status = Status: Green | Yellow | Orange | Red

See examples to get some more inspiration on how to customize your
config file. Use environment variable ``STATUS_REPORT_CONFIG`` to
override the default config file location.


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
