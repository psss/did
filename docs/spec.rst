.. _specification:

Metadata Specification
======================

This specification defines a way how to store all metadata needed
for test execution in plain text files close to the test code or
application source code. Files are stored under version control
directly in the git repository.

`Flexible Metadata Format`_ is used to store data in a concise
human and machine readable way plus adds a couple of nice features
like virtual hierarchy, inheritance and elasticity to minimize
data duplication and maintenance.

.. _Flexible Metadata Format: https://fmf.readthedocs.io/

The following metadata levels are defined:

Level 0: Core
    :ref:`/spec/core` attributes such as :ref:`/spec/core/summary`
    for short overview, :ref:`/spec/core/description` for detailed
    texts or the :ref:`/spec/core/order` which are common and can
    be used across all metadata levels.

Level 1: Tests
    Metadata closely related to individual :ref:`/spec/tests` such
    as the :ref:`/spec/tests/test` script, directory
    :ref:`/spec/tests/path` or maximum :ref:`/spec/tests/duration`
    which are stored directly with the test code.

Level 2: Plans
    :ref:`/spec/plans` are used to group relevant tests and enable
    them in the CI. They describe how to
    :ref:`/spec/plans/discover` tests for execution, how to
    :ref:`/spec/plans/provision` the environment and
    :ref:`/spec/plans/prepare` it for testing, how to
    :ref:`/spec/plans/execute` tests and :ref:`/spec/plans/report`
    test results.

Level 3: Stories
    User :ref:`/spec/stories` can be used to describe expected
    features of the application by defining the user
    :ref:`/spec/stories/story` and to easily track which
    functionality has been already implemented, verified and
    documented.

.. toctree::
    :maxdepth: 2

    spec/core
    spec/tests
    spec/plans
    spec/stories
    spec/context
    spec/hardware
