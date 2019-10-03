======================
    Dreams
======================

A couple of dreams for the future...


Creation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Creating a new test, executing it and enabling in the continuous
integration should be a joy. Just a couple of concise commands::

    dnf install tmt-all
    git clone https://some.git/repo
    cd repo
    tmt init
    tmt testset create --beakerlib /testsets/basic

This would be done only once in order to prepare everything needed
for testing. The everyday workflow would be much shorter::

    tmt test create --beakerlib /tests/area/feature
    cd tests/area/feature
    vim main.fmf
    vim test.sh
    tmt run test .
    git add .
    git commit -m "New test for area/feature"
    git push


Execution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Executing a test, a set of tests, or all tests available in the
repo should be short, user friendly and straightforward::

    tmt run
    tmt run test .
    tmt run testset /testsets/smoke


Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Selecting the environment where tests will be executed should be
simple and there should be plenty of options to choose freely::

    tmt run --localhost
    tmt run --beaker=f31
    tmt run --openstack=fedora
    tmt run --container=fedora:rawhide
    tmt run --mock=fedora-31-x86_64


Debugging
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Investigating test failures and debugging test code should be
comfortable and as fast as possible::

    tmt run --keep discover provision prepare
    tmt run --keep execute
    tmt run --keep execute
    ...
    tmt run --keep report finish
