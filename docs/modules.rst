.. _modules:

===============
    Modules
===============


Class Structure
---------------

Here's the overview of core classes::

    Common
    ├── Tree
    ├── Node
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
    │   │   ├── ProvisionTestcloud
    │   │   └── ProvisionVagrant
    │   └── ReportPlugin
    │       ├── ReportDisplay
    │       └── ReportHtml
    ├── Guest
    │   ├── GuestContainer
    │   ├── GuestLocal
    │   ├── GuestMinute
    │   └── GuestTestcloud
    └── Run


Essential Classes
-----------------

.. automodule:: tmt
    :members:
    :undoc-members:
