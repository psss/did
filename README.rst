
======================
    status-report
======================

Gather status report data for given date range.


Description
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comfortably gather status report data (e.g. list of committed
changes) for given week, month, quarter, year or selected date
range. By default all available stats for this week are reported.


Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Gather all stats for current week::

    status-report

Gather stats for the last week::

    status-report last week

See status-report --help for complete list of available stats.


Install
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install directly from Fedora/Copr repository::

    yum install status-report

or use PIP (sudo required if not in a virtualenv)::

    pip install status_report

To build and execute in a docker container, run::

    make run_docker

See documentation for more details about installation options.


Config
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The config file ``~/.status-report`` is used to store both general
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
https://github.com/psss/status-report

Docs:
http://status-report.readthedocs.org

Issues:
https://github.com/psss/status-report/issues

Releases:
https://github.com/psss/status-report/releases

Copr:
http://copr.fedoraproject.org/coprs/psss/status-report

PIP:
https://pypi.python.org/pypi/status_report


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

.. image:: https://badge.fury.io/py/status-report.svg
    :target: http://badge.fury.io/py/status-report

.. image:: https://travis-ci.org/psss/status-report.svg?branch=master
    :target: https://travis-ci.org/psss/status-report

.. image:: https://coveralls.io/repos/psss/status-report/badge.svg
    :target: https://coveralls.io/r/psss/status-report

.. image:: https://img.shields.io/pypi/dm/status-report.svg
    :target: https://pypi.python.org/pypi/status_report/

.. image:: https://img.shields.io/pypi/l/status-report.svg
    :target: https://pypi.python.org/pypi/status_report/

.. image:: https://readthedocs.org/projects/status-report/badge/
    :target: https://readthedocs.org/projects/status-report/
