.. _classes:

===============
    Classes
===============


Class Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here's the overview of core classes::

    Common
    ├── Tree
    ├── Core
    │   ├── Plan
    │   ├── Story
    │   └── Test
    ├── Step
    │   ├── Discover
    │   ├── Execute
    │   ├── Finish
    │   ├── Prepare
    │   ├── Provision
    │   └── Report
    ├── Plugin
    │   ├── DiscoverPlugin
    │   │   ├── DiscoverFmf
    │   │   └── DiscoverShell
    │   ├── ExecutePlugin
    │   │   ├── ExecuteDetach
    │   │   └── ExecuteInternal
    │   ├── FinishPlugin
    │   │   └── FinishShell
    │   ├── PreparePlugin
    │   │   ├── PrepareAnsible
    │   │   ├── PrepareInstall
    │   │   └── PrepareShell
    │   ├── ProvisionPlugin
    │   │   ├── ProvisionConnect
    │   │   ├── ProvisionLocal
    │   │   ├── ProvisionMinute
    │   │   ├── ProvisionPodman
    │   │   └── ProvisionTestcloud
    │   └── ReportPlugin
    │       ├── ReportDisplay
    │       └── ReportHtml
    ├── Guest
    │   ├── GuestContainer
    │   ├── GuestLocal
    │   ├── GuestMinute
    │   └── GuestTestcloud
    ├── Run
    ├── Status
    └── Clean


Attributes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Object hierarchy is following: ``Run`` -> ``Plans`` -> ``Steps``
-> ``Plugins``, where the ``Run`` is on the top of this hierarchy.
The objects have the ``parent`` attribute, that is pointing to
the parent in which the current instance is contained.

The ``node`` attribute of ``Test``, ``Plan`` and ``Story``
instances references the original leaf node of the fmf metadata
tree from which the respective test, plan or story have been
created.

In a similar way, the ``tree`` property of the ``Tree`` instance
points to the original ``fmf.Tree`` from which it was initialized.


Essential Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tmt
    :members:
    :undoc-members:
