.. _overview:

======================
    tmt
======================

Test Management Tool


Description
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``tmt`` tool provides a user-friendly way to work with tests.
You can comfortably create new tests, safely and easily run tests
across different environments, review test results, debug test
code and enable tests in the CI using a consistent and concise
config.

The python module and command-line tool implement the Metadata
Specification which allows storing all needed test execution data
directly within a git repository. Together with possibility to
reference remote repositories it makes it easy to share test
coverage across projects and distros.

The Flexible Metadata Format ``fmf`` is used to store data in both
human and machine readable way close to the source code. Thanks to
inheritance and elasticity metadata are organized in the structure
efficiently, preventing unnecessary duplication.


Specification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are several metadata levels defined by the specification:

**Core** attributes such as `summary` or `description` which are
common across all levels are defined by the special L0 metadata.

**Tests**, or L1 metadata, define attributes which are closely
related to individual test cases such as `test` script,
`framework`, directory `path` where the test should be executed,
maximum test `duration` or packages required to run the test.

**Plans**, also called L2 metadata, are used to group relevant
tests and enable them in the CI. They describe how to `discover`
tests for execution, how to `provision` the environment, how to
`prepare` it for testing, how to `execute` tests and `report` test
results.

**Stories**, which implement the L3 metadata, can be used to track
implementation, test and documentation coverage for individual
features or requirements. Thanks to this you can track everything
in one place, including the project implementation progress.


Synopsis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Command line usage is straightforward::

    tmt command [options]


Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's see which tests, plans and stories are available::

    tmt

Initialize the metadata tree in the current directory, optionally
with example content based on templates::

    tmt init
    tmt init --template base

Run all or selected steps for each plan::

    tmt run
    tmt run discover
    tmt run prepare execute

List tests, show details, check against the specification::

    tmt test ls
    tmt test show
    tmt test lint

Create a new test, import test metadata from other formats::

    tmt test create
    tmt test import

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
description of individual steps. Here is a brief overview:

discover
    Gather information about test cases to be executed.

provision
    Provision an environment for testing or use localhost.

prepare
    Prepare the environment for testing.

execute
    Run tests using the specified executor.

report
    Provide test results overview and send reports.

finish
    Perform the finishing tasks and clean up provisioned guests.


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
import
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

--root PATH
    Path to the metadata tree, current directory used by default.

--verbose
    Print additional information.

--debug
    Turn on debugging output.

Check help message of individual commands for the full list of
available options.


.. _install:

Install
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The main ``tmt`` package provides the core features with a minimal
set of dependencies::

    sudo dnf install tmt

In order to enable additional functionality, such as particular
provision or report plugins, install the respective subpackage::

    sudo dnf install tmt-test-convert
    sudo dnf install tmt-report-html
    sudo dnf install tmt-provision-container
    sudo dnf install tmt-provision-virtual

If you don't care about disk space and want to have all available
features right at hand install everything::

    sudo dnf install tmt-all

For RHEL 8 and CentOS 8, first make sure that you have available
the `EPEL <https://fedoraproject.org/wiki/EPEL>`_ repository. You
might also have to enable additional repositories::

    sudo dnf install https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
    sudo dnf config-manager --enable powertools  # CentOS 8
    sudo dnf config-manager --enable rhel-CRB    # RHEL 8
    sudo dnf install tmt

For plugins which cannot work outside of VPN and so live within
its walls you need to enable the internal copr repository first.
Then you can install either everything or only those you need::

    sudo dnf install tmt-redhat-all
    sudo dnf install tmt-redhat-*

Impatient to try the fresh features as soon as possible? Install
the latest greatest version from the ``copr`` repository::

    sudo dnf copr enable psss/tmt
    sudo dnf install tmt

Not sure, just want to try out how it works? Experiment safely and
easily inside a container::

    podman run -it --rm quay.io/testing-farm/tmt bash
    podman run -it --rm quay.io/testing-farm/tmt-all bash

When installing using ``pip`` you might need to install additional
packages on your system::

    sudo dnf install gcc {python3,libvirt,krb5,libpq}-devel
    pip install --user tmt

Note: You can omit the ``--user`` flag if in a virtual environment.


Shell Completion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The rpm package includes a system wide script which enables the
command line completion for ``bash`` so no additional config
should be needed. If you use a different installation method or
prefer another shell, see the instructions below.

For Bash, add this to ``~/.bashrc``::

    eval "$(_TMT_COMPLETE=source_bash tmt)"

For Zsh, add this to ``~/.zshrc``::

    eval "$(_TMT_COMPLETE=source_zsh tmt)"

For Fish, add this to ``~/.config/fish/completions/tmt.fish``::

    eval (env _TMT_COMPLETE=source_fish tmt)

Open a new shell to enable completion. Or run the ``eval`` command
directly in your current shell to enable it temporarily.


Exit Codes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following exit codes are returned from ``tmt run``. Note that
you can use the ``--quiet`` option to completely disable output
and only check for the exit code.

0
    At least one test passed, there was no fail, warn or error.
1
    There was a fail or warn identified, but no error.
2
    Errors occured during test execution.
3
    No test results found.


Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following environment variables can be used to modify
behaviour of the ``tmt`` command.

TMT_DEBUG
    Enable the desired debug level. Most of the commands support
    levels from 1 to 3. However, some of the plugins go even
    deeper when needed.

NO_COLOR
    Disable colors in the terminal output. Output only plain,
    non-colored text. See https://no-color.org/ for more
    information.

The following environment variables are provided to the test
during the execution:

TMT_TREE
    The full path of the working directory where the metadata tree
    is copied. This usually contains the whole git repository from
    which tests have been executed.

TMT_TEST_DATA
    Path to the directory where test can store logs and other
    artifacts generated during its execution. These will be pulled
    back from the guest and available for inspection after the
    test execution is finished.

TMT_PLAN_DATA
    Path to the common directory used for storing logs and other
    artifacts related to the whole plan execution. It is pulled
    back from the guest and available for inspection after the
    plan is completed.

TMT_REBOOT_COUNT
    During the test execution the ``tmt-reboot`` command can be
    used to request reboot of the guest. This variable contains
    number of reboots which already happened during the test.
    Value is set to ``0`` if no reboot occurred.

    In order to keep backward-compatibility with older tests,
    ``rhts-reboot`` and ``rstrnt-reboot`` commands are supported
    for requesting the reboot, variables ``REBOOTCOUNT`` and
    ``RSTRNT_REBOOTCOUNT`` contain number of reboots as well.


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

Metadata Specification:
https://tmt.readthedocs.io/en/latest/spec.html

Flexible Metadata Format:
http://fmf.readthedocs.io/

Packit & Testing Farm:
https://packit.dev/testing-farm/


Authors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Petr Šplíchal, Miro Hrončok, Alexander Sosedkin, Lukáš Zachar,
Petr Menšík, Leoš Pol, Miroslav Vadkerti, Pavel Valena, Jakub
Heger, Honza Horák, Rachel Sibley, František Nečas, Michal
Ruprich, Martin Kyral, Miloš Prchlík, Tomáš Navrátil, František
Lachman, Patrik Kis, Ondrej Mosnáček, Andrea Ficková, Denis
Karpelevich, Michal Srb, Jan Ščotka, Artem Zhukov, Vinzenz
Feenstra, Inessa Vasilevskaya, Štěpán Němec, Robin Hack, Yulia
Kopkova, Ondrej Moriš, Martin Zelený, Karel Šrot and František
Zatloukal.


Copyright
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Copyright Red Hat

This program is free software; you can redistribute it and/or
modify it under the terms of the MIT License.
