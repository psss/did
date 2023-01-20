
==================
    Contribute
==================


Introduction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Feel free and welcome to contribute to this project. You can start
with filing issues and ideas for improvement in GitHub tracker__.
Our favorite thoughts from The Zen of Python:

* Beautiful is better than ugly.
* Simple is better than complex.
* Readability counts.

We respect the `PEP8`__ Style Guide for Python Code. Here's a
couple of recommendations to keep on mind when writing code:

* Comments should be complete sentences.
* The first word should be capitalized (unless identifier).
* When using hanging indent, the first line should be empty.
* The closing brace/bracket/parenthesis on multiline constructs
  is under the first non-whitespace character of the last line

__ https://github.com/psss/did/issues
__ https://www.python.org/dev/peps/pep-0008/


Commits
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is challenging to be both concise and descriptive, but that is
what a well-written summary should do. Consider the commit message
as something that will be pasted into release notes:

* Maximum line length is 88 for code and 72 for docs.
* The first line should have up to 50 characters.
* Complete sentence with the first word capitalized.
* Should concisely describe the purpose of the patch.
* Do not prefix the message with file or module names.
* Other details should be separated by a blank line.

Why should I care?

* It helps others (and yourself) find relevant commits quickly.
* The summary line will be re-used later (e.g. for rpm changelog).
* Some tools do not handle wrapping, so it is then hard to read.
* You will make the maintainers happy to read beautiful commits :)

You can get some more context in the `stackoverflow`__ article.

__ http://stackoverflow.com/questions/2290016/


Develop
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to experiment, play with the latest bits and develop
improvements it is best to use a virtual environment. First make
sure that you have python3 installed on your box::

    sudo dnf install python3

Install ``python3-virtualenvwrapper`` to easily create and enable
virtual environments using ``mkvirtualenv`` and ``workon``. Note
that if you have freshly installed the package you need to open a
new shell session to enable the wrapper functions::

    sudo dnf install python3-virtualenvwrapper

Now let's create a new virtual environment and install ``did`` in
editable mode there::

    mkvirtualenv did
    git clone https://github.com/psss/did
    cd did
    pip install -e .

The main ``did`` package contains only the core dependencies. For
building documentation, testing changes or using individual
plugins install the extra deps::

    pip install '.[docs]'
    pip install '.[tests]'
    pip install '.[bugzilla]'
    pip install '.[jira]'
    ...

Or simply install all extra dependencies to make sure you have
everything needed for the did development ready on your system::

    pip install '.[all]'

Install the ``pre-commit`` hooks to run all available checks
for your commits to the project::

    pre-commit install


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

make hooks
    Link git commit hooks.

make tags
    Create or update the Vim ``tags`` file for quick searching.
    You might want to use ``set tags=./tags;`` in your ``.vimrc``
    to enable parent directory search for the tags file as well.

make clean
    Cleanup all temporary files.


Hooks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can find git commit hooks in the ``examples`` directory.
Consider linking or copying them into your git config::

    GIT=~/git/did # Update to your actual path
    ln -snf $GIT/hooks/pre-commit $GIT/.git/hooks
    ln -snf $GIT/hooks/commit-msg $GIT/.git/hooks

Or simply run ``make hooks`` which will do the linking for you.
Note that this will overwrite existing hooks.


Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To run tests using pytest::

    coverage run --source=did -m py.test tests
    coverage report

Install pytest and coverage using yum::

    yum install pytest python-coverage

or pip::

    pip install .[tests]


Docs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For building documentation locally install necessary modules::

    pip install .[docs]

Building documentation is then quite straightforward::

    make docs

Find the resulting html pages under the ``docs/_build/html``
folder.


MrBob
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use also use `mrbob` to easily create templates to help
you get started contributing::

    pip install mr.bob
    mrbob examples/mr.bob/plugin -O ./did/plugins

`mrbob` should have asked you a few questions before creating a
new basic Stats plugin for you in `did/plugins/`. Check `git
status` to see the new files it created as a result.
