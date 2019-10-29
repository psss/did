
======================
    tmt
======================

Test Management Tool


Description
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``tmt`` python module and command line tool implement the L1
and L2 Metadata Specification which allows to store all needed
test execution data directly within a git repository. In this way
it makes tests independent on any external test management system.

The Flexible Metadata Format ``fmf`` is used to store data in both
human and machine readable way close to the source code. Thanks to
inheritance and elasticity metadata are organized in the structure
efficiently, preventing unnecessary duplication.

Command line tool allows to easily create new tests, convert old
metadata, list and filter available tests and verify them against
the L1 specification. Plans are used to group tests and precisely
define individual test steps defined by the L2 specification, like
environment preparation. Stories are used to track implementation,
test and documentation coverage for individual features.

Last but not least, the tool provides a user-friendly way how to
run, debug and develop tests directly from your laptop across many
different test environments. This is currently a proof-of-concept
so many features are still on the way. Check stories to see which
functionality has already been implemented.


Synopsis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Command line usage is straightforward::

    tmt command [options]


Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run all or selected steps for each plan::

    tmt run
    tmt run discover
    tmt run prepare execute

List tests, show details, check against the specification::

    tmt test ls
    tmt test show
    tmt test lint

Create a new test, convert old metadata::

    tmt test create
    tmt test convert

List plans, show details, check against the specification::

    tmt plan ls
    tmt plan show
    tmt plan lint

List stories, check details, show coverage status::

    tmt story ls
    tmt story show
    tmt story coverage

Many commands support regular expression filtering and other
specific options::

    tmt story ls cli
    tmt story show create
    tmt story coverage --implemented

Check help message of individual commands for the full list of
available options.


Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here is the list of the most frequently used commands and options.

Run
---

The `run` command is used to execute test steps. By default all
test steps are run. See the L2 Metadata specification for detailed
description of individual steps. For now here is at least a brief
overview:

discover
    gather and show information about test cases to be executed

provision
    provision an environment for testing (or use localhost)

prepare
    configure environment for testing (e.g. ansible playbook)

execute
    run the tests (using the specified framework and its settings)

report
    provide an overview of test results and send notifications

finish
    additional actions to be performed after the test execution

Note: This is only preview / draft of future functionality.
Features described above are not implemented yet.


Test
----

Manage tests (L1 metadata). Check available tests, inspect their
metadata, gather old metadata from various sources and stored them
in the new fmf format.

ls
    List available tests.
show
    Show test details.
lint
    Check tests against the L1 metadata specification.
create
    Create a new test based on given template.
convert
    Convert old test metadata into the new fmf format.


Plan
----

Manage test plans (L2 metadata). Search for available plans.
Explore detailed test step configuration.

ls
    List available plans.
show
    Show plan details.
lint
    Check plans against the L2 metadata specification.


Story
-----

Manage user stories. Check available user stories. Explore
coverage (test, implementation, documentation).

ls
    List available stories.
show
    Show story details.
coverage
    Show code, test and docs coverage for given stories.
export
    Export selected stories into desired format.


Utils
-----

Various utility options.

--path PATH
    Path to the metadata tree (default: current directory)

--verbose
    Print additional information standard error output

--debug
    Turn on debugging output, do not catch exceptions

Check help message of individual commands for the full list of
available options.


Install
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The tmt package is available in Fedora and EPEL::

    dnf install tmt

Install the latest version from the Copr repository::

    dnf copr enable psss/tmt
    dnf install tmt

Use PIP (you can omit the ``--user`` flag if in a virtualenv)::

    pip install --user tmt


Develop
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to experiment, play with the latest bits and develop
improvements it is best to use a virtual environment::

    mkvirtualenv tmt
    git clone https://github.com/psss/tmt
    cd tmt
    pip install -e .

Install ``python3-virtualenvwrapper`` to easily create and enable
virtual environments using ``mkvirtualenv`` and ``workon``. You
can also easily install optional dependencies in this way::

    pip install .[docs]
    pip install .[tests]
    pip install .[all]


Links
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Git:
https://github.com/psss/tmt

Docs:
http://tmt.readthedocs.io/

Stories:
https://tmt.readthedocs.io/en/latest/stories.html

Issues:
https://github.com/psss/tmt/issues

Releases:
https://github.com/psss/tmt/releases

Copr:
http://copr.fedoraproject.org/coprs/psss/tmt

PIP:
https://pypi.org/project/tmt/

Travis:
https://travis-ci.org/psss/tmt

Coveralls:
https://coveralls.io/github/psss/tmt

Specification:
https://pagure.io/fedora-ci/metadata

Flexible Metadata Format:
http://fmf.readthedocs.io/

Packit & Testing Farm:
https://packit.dev/testing-farm/


Authors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Petr Šplíchal, Miro Hrončok, Alexander Sosedkin, Lukáš Zachar,
Petr Menšík, Leoš Pol, Miroslav Vadkerti and Pavel Valena.


Copyright
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Copyright (c) 2019 Red Hat, Inc.

This program is free software; you can redistribute it and/or
modify it under the terms of the MIT License.
