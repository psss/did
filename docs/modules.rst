
===============
    Modules
===============


Class Structure
---------------

Here's the overview of available classes::

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
    │   │   └── ExecuteSimple
    │   ├── FinishPlugin
    │   ├── PreparePlugin
    │   │   ├── PrepareAnsible
    │   │   ├── PrepareInstall
    │   │   └── PrepareShell
    │   ├── ProvisionPlugin
    │   │   ├── ProvisionConnect
    │   │   ├── ProvisionLocal
    │   │   ├── ProvisionPodman
    │   │   ├── ProvisionTestcloud
    │   │   └── ProvisionVagrant
    │   └── ReportPlugin
    │       └── ReportDisplay
    └── Run

Note: The list is not complete. There is a plan to clean up plugin
inheritance and naming.


Essential Classes
-----------------

.. automodule:: tmt
    :members:
    :undoc-members:
