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

Level 0
    :ref:`/spec/core` attributes such as :ref:`/spec/core/summary`
    for short overview, :ref:`/spec/core/description` for detailed
    texts or the :ref:`/spec/core/order` which are common and can
    be used across all metadata levels.

Level 1
    Metadata closely related to individual :ref:`/spec/tests` such
    as the :ref:`/spec/tests/test` script, directory
    :ref:`/spec/tests/path` or maximum :ref:`/spec/tests/duration`
    which are stored directly with the test code.

Level 2
    This level represents :ref:`/spec/plans` made up of individual
    :ref:`/spec/steps` describing how to
    :ref:`/spec/steps/provision` the environment for testing and
    how to :ref:`/spec/steps/prepare` it or which frameworks
    should be used to :ref:`/spec/steps/execute` tests relevant
    for given :ref:`/spec/plans/context`.

Level 3
    User :ref:`/spec/stories` can be used to define expected
    features of the application and to easily track which
    functionality has been already
    :ref:`/spec/stories/implemented`, :ref:`/spec/stories/tested`
    and :ref:`/spec/stories/documented`.

.. toctree::
    :maxdepth: 2

    spec/core
    spec/tests
    spec/plans
    spec/steps
    spec/stories
    spec/context
