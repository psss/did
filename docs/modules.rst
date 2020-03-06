
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
    │   ├── FinishPlugin
    │   ├── PreparePlugin
    │   ├── ProvisionPlugin
    │   └── ReportPlugin
    └── Run

Note: The list is not complete. There is a plan to clean up plugin
inheritance and naming.


base
----

.. automodule:: tmt.base
    :members:
    :undoc-members:

steps
-----

.. automodule:: tmt.steps
    :members:
    :undoc-members:

utils
-----

.. automodule:: tmt.utils
    :members:
    :undoc-members:

cli
---

.. automodule:: tmt.cli
    :members:
    :undoc-members:

convert
-------

.. automodule:: tmt.convert
    :members:
    :undoc-members:
