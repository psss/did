======================
    Dreams
======================

A couple of dreams for the future...


Test Creation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Creating a new test, executing it and enabling in the continuous
integration should be a joy. Just a couple of concise commands::

    dnf install tmt-all
    git clone https://some.git/repo
    cd repo
    tmt init
    tmt plan create --beakerlib /plan/basic

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


Test Execution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Executing a test, a set of tests, or all tests available in the
repo should be short, user friendly and straightforward::

    tmt run
    tmt run test .
    tmt run plan /plan/smoke


Environment Selection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Selecting the environment where tests will be executed should be
simple and there should be plenty of options to choose freely::

    tmt run --localhost
    tmt run --beaker=f31
    tmt run --openstack=fedora
    tmt run --container=fedora:rawhide
    tmt run --mock=fedora-31-x86_64


Interactive Investigation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Obtaining a test environment to interactively investigate test
failures and easily develop tests should be as comfortable and as
fast as possible::

    tmt run discover provision prepare
    tmt run execute
    tmt run execute
    ...
    tmt run report finish


Hands-Free Debugging
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A very common loop of modifying the source code and re-executing
the test should be accessible without subsequent user interaction
with the tool::

    tmt run debug

* run the tool once, keep it running
* observe the execution results
* open an editor in a separate window
* modify the file, save the changes
* observe the updated execution results
* ...

Prioritize latency and reuse as much as possible from the previous
execution. Ideally, start the re-execution from the modified line.
