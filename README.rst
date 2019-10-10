
======================
    tmt
======================

Test Metadata Tool


Description
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``tmt`` Python module and command line tool implement the test
metadata specification (L1 and L2) and allows easy test execution.


Synopsis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Command line usage is straightforward::

    tmt command [options]


Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default all steps are executed for each plan detected::

    tmt run

You can select which steps should be performed::

    tmt run discover

Multiple steps can be provided as well::

    tmt run prepare execute

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

Check available tests, inspect their metadata, gather old metadata
from various sources and stored them in the new fmf format.

test convert
    migrate test metadata from the old format to `fmf`


Utils
-----

Various utility options.

--path PATHS
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

or use PIP (you can omit the ``--user`` flag if in a virtualenv)::

    pip install --user tmt

See documentation for more details about installation options.


Links
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Git:
https://github.com/psss/tmt

Docs:
http://tmt.readthedocs.io/

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


Authors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Petr Šplíchal.


Copyright
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Copyright (c) 2019 Red Hat, Inc.

This program is free software; you can redistribute it and/or
modify it under the terms of the MIT License.
