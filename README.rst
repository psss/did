
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

By default all steps are executed for each testset detected::

    tmt

You can select which steps should be performed::

    tmt discover

Multiple steps can be provided as well::

    tmt prepare execute

Check help message of individual commands for the full list of
available options.


Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here is the list of the most frequently used options.

Steps
------

Select steps to be executed.

discover
    gather info about test cases to be run
provision
    what environment is needed for testing, how it should provisioned
prepare
    additional configuration needed for testing (e.g. ansible playbook)
execute
    test execution itself (e.g. framework and its settings)
report
    adjusting notifications about the test progress and results
finish
    actions to be performed after the test execution has been completed


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

The tmt package will be available in Fedora and EPEL::

    dnf install tmt

Install the latest version from the Copr repository::

    dnf copr enable psss/tmt
    dnf install tmt

or use PIP (sudo required if not in a virtualenv)::

    pip install tmt

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
