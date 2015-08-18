
======================
    status-report
======================

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Generate status report stats for selected date range
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Manual section: 1
:Manual group: User Commands
:Date: April 2015


DESCRIPTION
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Comfortably generate status report stats (e.g. list of committed
changes) for given week, month, quarter, year or selected date
range. By default all available stats for this week are reported.


EXAMPLES
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Generate all stats for current week::

    status-report

Generate stats for the last week::

    status-report last week

See status-report --help for complete list of available stats.


INSTALLATION
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Install directly from Fedora/Copr repository or use PIP::

    # Basic dependencies for buiding/installing pip packages
    sudo yum install python-devel python-pip python-virtualenv
    sudo yum install gcc krb5-devel

    # Upgrade to the latest pip/setup/virtualenv installer code
    sudo pip install -U pip setuptools virtualenv

    # Install into a python virtual environment (OPTIONAL)
    virtualenv --no-site-packages ~/virtenv_statusreport
    source ~/virtenv_statusreport/bin/activate

    # Install status_report (sudo required if not in a virtualenv)
    pip install status_report


CONFIGURATION
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The config file ~/.status-report is used to store both general
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

See also examples link for some more inspiration.


DOCKER INSTALL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
To build and execute in a docker container, run::

    make run_docker

See LINKS section below for more docker resources.


TESTS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
To run tests using pytest::

    # sudo required if not in a virtualenv
    pip install pytest coveralls
    coverage run --source=status_report -m py.test source/tests
    coverage report


LINKS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Project page:
http://psss.fedorapeople.org/status-report/

Release notes:
http://psss.fedorapeople.org/status-report/notes.html

Examples:
http://psss.fedorapeople.org/status-report/examples/

Download:
http://psss.fedorapeople.org/status-report/download/

Copr repo:
http://copr.fedoraproject.org/coprs/psss/status-report/

Git repo:
https://github.com/psss/status-report

PIP repo:
https://pypi.python.org/pypi/status_report/

Docker Guides:
https://fedoraproject.org/wiki/Getting_started_with_docker
https://fedoraproject.org/wiki/Docker


AUTHORS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Petr Šplíchal, Karel Šrot, Lukáš Zachar, Matěj Cepl, Ondřej Pták,
Chris Ward.


COPYRIGHT
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Copyright (c) 2015 Red Hat, Inc. All rights reserved.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation; either version 2 of
the License, or (at your option) any later version.
