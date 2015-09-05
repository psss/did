
==================
    Contribute
==================

Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

File issues and ideas for improvement in GitHub:

* https://github.com/psss/did/issues


Hooks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you're planning to contribute to this project consider copying
the following hooks into your git config::

    GIT=~/git/did # update to your actual path
    cp $GIT/examples/pre-commit.py $GIT/.git/hooks/pre-commit
    cp $GIT/examples/commit-msg.py $GIT/.git/hooks/commit-msg


Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To run tests using pytest::

    coverage run --source=did -m py.test source/tests
    coverage report

Install pytest and coverage using yum::

    yum install pytest python-coverage

or pip::

    # sudo required if not in a virtualenv
    pip install pytest coveralls
