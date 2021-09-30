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

Here's just a couple of hints how to get the virtualization
quickly working on your laptop. See the `Getting started with
virtualization`__ docs to learn more.

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
------------------------------------------------------------------

Each tmt test has a unique `fmf identifier`__ which can look like
this::

    name: /tests/core/docs
    url: https://github.com/psss/tmt.git
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


STI migration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Another possible metadata migration path can from `STI`__.
Standard test interface is described in ``tests.yml`` Ansible
playbook. It uses standard test `Ansible roles`__. Ansible
playbook in YAML has similar but not the same format as FMF.

__ https://docs.fedoraproject.org/en-US/ci/standard-test-interface/
__ https://docs.fedoraproject.org/en-US/ci/standard-test-roles/#_roles

Below you can see original STI ansible playbooks and it's equivalents
written in fmf.

Simple running binary
------------------------------------------------------------------

STI example::

    - hosts: localhost
      roles:
      - role: standard-test-basic
        tags:
        - classic
        tests:
        - simple:
            dir: .
            run: binary --help

tmt example plan (L2 metadata)::

    execute:
        script: binary --help


Test plan running script cmd-line-options
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
        - which         # which package required for cmd-line-options
        - rpm-build     # upstream-testsuite requires rpmbuild command
        - libtool       # upstream-testsuite requires libtool
        - gettext       # upstream-testsuite requires gettext

tmt example plan (L2 metadata)::

    summary: Check basics cmd options
    prepare:
        how: install
        package:
          - which         # which package required for cmd-line-options
          - rpm-build     # upstream-testsuite requires rpmbuild command
          - libtool       # upstream-testsuite requires libtool
          - gettext       # upstream-testsuite requires gettext
    execute:
        script: cmd-line-options


Test plan from remote repository
------------------------------------------------------------------

Tests in this plan are also filtered by the tag.

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


Split metadata to more files
------------------------------------------------------------------

In this migration of STI is created L2 metadata (plan) and each
original test is stored in separate L1 metadata file (test). This
approach allows setup of different environment variables and
required packages for each test.

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


Using 'dist-git-source' feature of the 'discover' plugin
------------------------------------------------------------------
This feature of 'discover' plugin allows to extract tests from the
extracted (rpm) sources.

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

See :ref:`/spec/plans/discover/fmf` for details.
