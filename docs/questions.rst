======================
    Questions
======================

.. _fmf-and-tmt:

What is the difference between fmf and tmt?
------------------------------------------------------------------

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
------------------------------------------------------------------

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
------------------------------------------------------------------

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
------------------------------------------------------------------

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
