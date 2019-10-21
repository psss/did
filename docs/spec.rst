
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
    Core attributes such as ``summary`` for short overview,
    ``description`` for detailed texts or the ``order`` which are
    common and can be used across all metadata levels.

Level 1
    Metadata closely related to individual test cases such as
    the ``test`` script, directory ``path`` or maximum
    ``duration`` which are stored directly with the test code.

Level 2
    Description of how to ``provision`` the environment for
    testing and how to ``prepare`` it or which frameworks should
    be used to ``execute`` tests relevant for given ``artifact``.

Level 3
    A user ``story`` can be used to define expected features of
    the application and to easily track which functionality has
    been already ``implemented``, ``tested`` and ``documented``.

.. toctree::
    :maxdepth: 2

    spec/core
    spec/tests
    spec/plans
    spec/steps
    spec/stories
