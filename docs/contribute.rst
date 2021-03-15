.. _contribute:

==================
    Contribute
==================


Introduction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Feel free and welcome to contribute to this project. You can start
with filing issues and ideas for improvement in GitHub tracker__.
My favorite thoughts from The Zen of Python:

* Beautiful is better than ugly.
* Simple is better than complex.
* Readability counts.

A couple of recommendations from `PEP8`__ and myself:

* Comments should be complete sentences.
* The first word should be capitalized (unless identifier).
* When using hanging indent, the first line should be empty.

__ https://github.com/psss/tmt
__ https://www.python.org/dev/peps/pep-0008/


Makefile
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are several Makefile targets defined to make the common
daily tasks easy & efficient:

make test
    Execute the test suite.

make smoke
    Perform quick basic functionality test.

make coverage
    Run the test suite under coverage and report results.

make docs
    Build documentation.

make packages
    Build rpm and srpm packages.

make images
    Build container images.

make tags
    Create or update the Vim ``tags`` file for quick searching.
    You might want to use ``set tags=./tags;`` in your ``.vimrc``
    to enable parent directory search for the tags file as well.

make clean
    Cleanup all temporary files.


Commits
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is challenging to be both concise and descriptive, but that is
what a well-written summary should do. Consider the commit message
as something that could/will be pasted into release notes:

* The first line should have up to 50 characters.
* Complete sentence with the first word capitalized.
* Should concisely describe the purpose of the patch.
* Other details should be separated by a blank line.

Why should I care?

* It helps others (and yourself) find relevant commits quickly.
* The summary line can be re-used later (e.g. for rpm changelog).
* Some tools do not handle wrapping, so it is then hard to read.
* You will make the maintainer happy to read beautiful commits :)

You can get some more context in the `stackoverflow`__ article.

__ http://stackoverflow.com/questions/2290016/


Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the default set of tests directly on your localhost::

    tmt run

Execute the whole test coverage, including tests which need the
full virtualization support::

    tmt -c how=full run

To run unit tests using pytest::

    coverage run --source=tmt -m py.test tests
    coverage report

Install pytest and coverage using dnf::

    dnf install pytest python-coverage

or pip::

    # sudo required if not in a virtualenv
    pip install pytest coveralls

See Travis CI and Coveralls for the latest test/coverage results:

* https://travis-ci.org/psss/tmt/builds
* https://coveralls.io/github/psss/tmt


Docs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For building documentation locally install necessary modules::

    pip install sphinx sphinx_rtd_theme

Make sure docutils are installed in order to build man pages::

    dnf install python-docutils

Building documentation is then quite straightforward::

    make docs

Find the resulting html pages under the ``docs/_build/html``
folder.


Class Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here's the overview of core classes::

    Common
    ├── Tree
    ├── Node
    │   ├── Plan
    │   ├── Story
    │   └── Test
    ├── Step
    │   ├── Discover
    │   ├── Execute
    │   ├── Finish
    │   ├── Prepare
    │   ├── Provision
    │   └── Report
    ├── Plugin
    │   ├── DiscoverPlugin
    │   │   ├── DiscoverFmf
    │   │   └── DiscoverShell
    │   ├── ExecutePlugin
    │   │   ├── ExecuteDetach
    │   │   └── ExecuteInternal
    │   ├── FinishPlugin
    │   │   └── FinishShell
    │   ├── PreparePlugin
    │   │   ├── PrepareAnsible
    │   │   ├── PrepareInstall
    │   │   └── PrepareShell
    │   ├── ProvisionPlugin
    │   │   ├── ProvisionConnect
    │   │   ├── ProvisionLocal
    │   │   ├── ProvisionMinute
    │   │   ├── ProvisionPodman
    │   │   ├── ProvisionTestcloud
    │   │   └── ProvisionVagrant
    │   └── ReportPlugin
    │       ├── ReportDisplay
    │       └── ReportHtml
    ├── Guest
    │   ├── GuestContainer
    │   ├── GuestLocal
    │   ├── GuestMinute
    │   └── GuestTestcloud
    └── Run


Essential Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tmt
    :members:
    :undoc-members:
