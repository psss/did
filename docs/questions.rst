.. _questions:

======================
    Questions
======================

.. _fmf-and-tmt:


What is the difference between fmf and tmt?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `Flexible Metadata Format`__ or ``fmf`` is a plain text format
based on ``yaml`` used to store data in both human and machine
readable way close to the source code. Thanks to inheritance and
elasticity, metadata are organized in the structure efficiently,
preventing unnecessary duplication.

__ https://fmf.readthedocs.io/en/latest/

The `Test Management Tool`__ or ``tmt`` is a project which
consists of the :ref:`specification` which defines how tests,
plans and stories are organized, python modules implementing the
specification and the command-line tool which provides a
user-friendly way to create, debug and easily run tests.

__ https://tmt.readthedocs.io/en/latest/


.. _libvirt:


Virtualization Tips
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to safely run tests under a virtual machine started on
your laptop you only need to install the ``tmt-provision-virtual``
package. By default the ``session`` connection is used so no other
steps should be needed, just execute tests using the ``tmt run``
command.

If you want to use the ``system`` connection you might need to do
a few steps to set up your box. Here's just a couple of hints how
to get the virtualization quickly working on your laptop. See the
`Getting started with virtualization`__ docs to learn more.

Make sure the ``libvirtd`` is running on your box::

    sudo systemctl start libvirtd

Add your user account to the libvirt group::

    sudo usermod -a -G libvirt $USER

Note that you might need to restart your desktop session to get it
fully working. Or at least start a new login shell::

    su - $USER

In some cases you might also need to activate the default network
device::

    sudo virsh net-start default

Here you can find vm `images for download`__.

__ https://docs.fedoraproject.org/en-US/quick-docs/getting-started-with-virtualization/
__ https://kojipkgs.fedoraproject.org/compose/


Container Package Cache
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using containers can speed up your testing. However, fetching
package cache can slow things down substantially. Use this set of
commands to prepare a container image with a fresh dnf cache::

    podman run -itd --name fresh fedora
    podman exec fresh dnf makecache
    podman image rm fedora:fresh
    podman commit fresh fedora:fresh
    podman container rm -f fresh

Then specify the newly created image in the provision step::

    tmt run --all provision --how container --image fedora:fresh

In this way you can save up to several minutes for each plan.


Nitrate Migration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After a nitrate test case is migrated to ``fmf`` git becomes the
canonical source of the test case metadata. All further changes
should be done in git and updates synchronized back to nitrate
using ``tmt test export . --nitrate`` command. Otherwise direct
changes in Nitrate might be lost.

A unique identifier of the new test metadata location is stored in
the ``[fmf]`` section of test case notes. Below is the list of
attributes which are synchronized to corresponding nitrate fields:

* component — components tab
* contact — default tester
* description — purpose-file in the structured field
* duration — estimated time
* enabled — status
* environment — arguments
* summary — description in the structured field
* tag — tags tab
* tier — tags (e.g. ``1`` synced to the ``Tier1`` tag)

The following attributes, if present, are exported as well:

* extra-hardware — hardware in the structured field
* extra-pepa — pepa in the structured field
* extra-summary — Nitrate test case summary
* extra-task — Nitrate test case script

They have the ``extra`` prefix as they are not part of the L1
Metadata Specification and are supposed to be synced temporarily
to keep backward compatibility.


How can I integrate tmt tests with other tools?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each tmt test has a unique `fmf identifier`__ which can look like
this::

    name: /tests/core/docs
    url: https://github.com/teemtee/tmt.git
    ref: main

These identifiers can be used for integration with other tools,
for example to execute tmt tests using custom workflows. For this
use case ``tmt tests export`` command can be used to produce a
list of fmf identifiers of selected tests::

    tmt tests export --fmf-id | custom-workflow --fmf-id -
    tmt tests export core/docs --fmf-id | custom-workflow --fmf-id -

Custom workflow can then consume generated ids and perform desired
actions such as fetch the tests and execute them.

__ https://fmf.readthedocs.io/en/latest/concept.html#identifiers


How do I migrate STI tests to tmt?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`Standard Test Interface`__ tests are enabled using ``tests.yml``
Ansible playbooks together with the `Standard Test Roles`__ which
make it easier to execute tests, check their results and perform
additional actions such as installing required packages. The
configuration, however, can sometimes be confusing and quite hard
to understand.

With ``tmt`` it is possible to achieve the same result with much
more concise and clean syntax. For majority of existing tests the
conversion is relatively straightforward. Let's demonstrate it on
a couple of real-life examples. Below you can see the original STI
ansible playbooks and their ``tmt`` equivalents for inspiration.

As the first step, initialize the metadata tree using the ``tmt
init`` command in the root of the git repository. Then store the
new config files with the ``.fmf`` extension. Naming and location
of the files is up to you. See the :ref:`guide` for more details.

__ https://docs.fedoraproject.org/en-US/ci/standard-test-interface/
__ https://docs.fedoraproject.org/en-US/ci/standard-test-roles/


Simple Script
------------------------------------------------------------------

Running a simple binary using STI::

    - hosts: localhost
      roles:
      - role: standard-test-basic
        tags:
        - classic
        tests:
        - simple:
            dir: .
            run: binary --help

The equivalent ``tmt`` plan has only two lines::

    execute:
        script: binary --help

Store them for example as ``/plans/smoke.fmf`` and you're done.


Required Packages
------------------------------------------------------------------

This example prepares testing environment by installing
required packages.

STI example::

    - hosts: localhost
      tags:
      - atomic
      - classic
      - container
      roles:
      - role: standard-test-beakerlib
        tests:
        - cmd-line-options
        required_packages:
        - which
        - rpm-build
        - libtool
        - gettext

tmt example plan (L2 metadata)::

    summary: Check basic command line options
    prepare:
        how: install
        package:
          - which
          - rpm-build
          - libtool
          - gettext
    execute:
        script: cmd-line-options


Remote Repository
------------------------------------------------------------------

Tests in the following example are fetched from a remote
repository and filtered by the provided condition.

STI example::

    - hosts: localhost
      roles:
      - role: standard-test-beakerlib
        tags:
        - classic
        repositories:
        - repo: "https://src.fedoraproject.org/tests/shell.git"
          dest: "shell"
          fmf_filter: "tier: 1"

tmt example plan (L2 metadata)::

    summary: Tier 1 shell test plan
    discover:
        how: fmf
        url: https://src.fedoraproject.org/tests/shell.git
        filter: "tier: 1"
    execute:
        how: tmt


Multiple Tests
------------------------------------------------------------------

In this migration of STI a single plan (L2 metadata) is created
and each original test is stored in a separate L1 metadata file
(test). This approach allows the setup of different environment
variables and required packages for each test.

STI example::

    - hosts: localhost
      roles:
      - role: standard-test-basic
        tags:
        - classic
        tests:
        - smoke27:
            dir: tests
            run: VERSION=2.7 METHOD=virtualenv ./venv.sh
        - smoke37:
            dir: tests
            run: VERSION=3.7 ./venv.sh
        required_packages:
        - python27
        - python37
        - python2-virtualenv
        - python3-virtualenv
        - python2-devel
        - python3-devel


tmt example: plan (L2 metadata) and tests (L1 metadata)

plans/example.fmf::

    discover:
        how: fmf
    execute:
        how: tmt

tests/smoke27.fmf::

    test: ./venv.sh
    environment:
        VERSION: 2.7
        METHOD: virtualenv
    require:
      - python27
      - python2-virtualenv
      - python2-devel

tests/smoke37.fmf::

    test: ./venv.sh
    environment:
        VERSION: 3.7
    require:
      - python37
      - python3-virtualenv
      - python3-devel

This arrangement can be especially useful when a large number of
tests is stored in the repository.


Dist Git Source
------------------------------------------------------------------

Use the ``dist-git-source`` feature of the ``discover`` step to
extract tests from the (rpm) sources.

STI example::

    - hosts: localhost
      tags:
      - classic
      roles:
      - role: standard-test-source

tmt example plan (L2 metadata)::

    discover:
        how: fmf
        dist-git-source: true

See the :ref:`/spec/plans/discover/fmf` plugin documentation for
more details.
