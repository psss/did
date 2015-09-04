
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


Installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install directly from Fedora/Copr repository or use PIP::

    # Basic dependencies for buiding/installing pip packages
    sudo yum install gcc krb5-devel
    sudo yum install python-devel python-pip python-virtualenv

    # Upgrade to the latest pip/setup/virtualenv installer code
    sudo pip install -U pip setuptools virtualenv

    # Install into a python virtual environment (OPTIONAL)
    virtualenv --no-site-packages ~/virtenv_statusreport
    source ~/virtenv_statusreport/bin/activate

    # Install status_report (sudo required if not in a virtualenv)
    pip install status_report

To build and execute in a docker container, run::

    make run_docker


Configuration
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

    [footer]
    type = footer
    next = Plans, thoughts, ideas...
    status = Status: Green | Yellow | Orange | Red

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

See examples to get some more inspiration on how to customize your
config file. Use environment variable ``STATUS_REPORT_CONFIG`` to
override the default config file location.


Contributing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you're planning to contribute to this project consider copying
the following hooks into your git config::

    GIT=~/git/status-report # update to your actual path
    cp $GIT/examples/pre-commit.py $GIT/.git/hooks/pre-commit
    cp $GIT/examples/commit-msg.py $GIT/.git/hooks/commit-msg

To run tests using pytest::

    coverage run --source=status_report -m py.test source/tests
    coverage report

Install pytest and coverage using yum::

    yum install pytest python-coverage

or pip::

    # sudo required if not in a virtualenv
    pip install pytest coveralls


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
