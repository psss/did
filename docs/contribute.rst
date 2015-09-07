
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

    coverage run --source=did -m py.test tests
    coverage report

Install pytest and coverage using yum::

    yum install pytest python-coverage

or pip::

    # sudo required if not in a virtualenv
    pip install pytest coveralls


MrBob
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use also use `mrbob` to easily create templates to help
you get started contributing::

    pip install mrbob
    mrbob examples/mr.bob/plugin -O ./did/plugins

`mrbob` should have asked you a few questions before creating a
new basic Stats plugin for you in `did/plugins/`. Check `git
status` to see the new files it created as a result.
