.. _classes:

===============
    Classes
===============


Class Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here's the overview of the essential classes used in the `tmt`
project. It should help you to get quickly started and better
understand the relation between the individual classes.


Basic
------------------------------------------------------------------

The ``Common`` class is the parent of most of the available
classes, it provides common methods for logging, running commands
and workdir handling. The ``Core`` class together with its child
classes ``Test``, ``Plan`` and ``Story`` cover the
:ref:`specification`::

    Common
    ├── Core
    │   ├── Plan
    │   ├── Story
    │   └── Test
    ├── Clean
    ├── Guest
    ├── Phase
    ├── Run
    ├── Status
    ├── Step
    └── Tree


Phases
------------------------------------------------------------------

Actions performed during a normal step and plugins for individual
step::

    Phase
    ├── Action
    │   ├── Login
    │   └── Reboot
    └── BasePlugin
        ├── GuestlessPlugin
        │   ├── DiscoverPlugin
        │   │   ├── DiscoverFmf
        │   │   └── DiscoverShell
        │   ├── ProvisionPlugin
        │   │   ├── ProvisionArtemis
        │   │   ├── ProvisionConnect
        │   │   ├── ProvisionLocal
        │   │   ├── ProvisionPodman
        │   │   └── ProvisionTestcloud
        │   └── ReportPlugin
        │       ├── ReportDisplay
        │       ├── ReportHtml
        │       ├── ReportJUnit
        │       ├── ReportPolarion
        │       └── ReportReportPortal
        └── Plugin
            ├── ExecutePlugin
            │   └── ExecuteInternal
            │       └── ExecuteUpgrade
            ├── FinishPlugin
            │   ├── FinishAnsible
            │   └── FinishShell
            └── PreparePlugin
                ├── PrepareAnsible
                │   └── FinishAnsible
                ├── PrepareInstall
                ├── PrepareMultihost
                └── PrepareShell


Steps
------------------------------------------------------------------

A brief overview of all test steps::

    Step
    ├── Discover
    ├── Provision
    ├── Prepare
    ├── Execute
    ├── Finish
    └── Report

Containers used for storing configuration data for individual step
plugins::

    DataContainer
    └── SpecBasedContainer, SerializableContainer
        ├── FmfId
        │   └── RequireFmfId
        ├── Link
        ├── Links
        └── StepData
            ├── DiscoverStepData
            │   ├── DiscoverFmfStepData
            │   └── DiscoverShellData
            ├── ExecuteStepData
            │   ├── ExecuteInternalData
            │   └── ExecuteUpgradeData
            ├── FinishStepData
            │   └── FinishShellData
            ├── PrepareStepData
            │   ├── PrepareAnsibleData
            │   ├── PrepareInstallData
            │   ├── PrepareMultihostData
            │   └── PrepareShellData
            ├── ProvisionStepData
            │   ├── ProvisionArtemisData
            │   ├── ProvisionConnectData
            │   ├── ProvisionLocalData
            │   ├── ProvisionPodmanData
            │   └── ProvisionTestcloudData
            └── ReportStepData
                ├── ReportHtmlData
                ├── ReportJUnitData
                ├── ReportPolarionData
                └── ReportReportPortalData


Guests
------------------------------------------------------------------

Guests provisioned for test execution::

    Guest
    ├── GuestContainer
    ├── GuestLocal
    └── GuestSsh
        ├── GuestArtemis
        └── GuestTestcloud

Data related to provisioned guests::

    GuestData
    ├── GuestSshData
    │   ├── ArtemisGuestData
    │   ├── ConnectGuestData
    │   └── TestcloudGuestData
    └── PodmanGuestData


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


Class Conversions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Various internal objects and classes often need to be converted
from their Python nature to data that can be saved, loaded or
exported in different form. To facilitate these conversions, three
families of helper methods are provided, each with its own set of
use cases.

``to_spec``/``to_minimal_spec``/``from_spec``
------------------------------------------------------------------

This family of methods works with tmt *specification*, i.e. raw
user-provided data coming from fmf files describing plans, tests,
stories, or from command-line options. ``from_spec()`` shall be
called to spawn objects representing the user input, while
``to_spec()`` should produce output one could find in fmf files.

The default implementation comes from ``tmt.utils.SpecBasedContainer``
class, all classes based on user input data should include this
class among their bases.

``to_minimal_spec`` performs the identical operation as ``to_spec``,
but its result should not include keys that are optional and not set,
while ``to_spec`` should always include all keys, even when set to
default values or not set at all.

.. code-block:: python

   # Create an fmf id object from raw data
   fmf_id = tmt.base.FmfId.from_spec({'url': ..., 'ref': ...})


``to_serialized``/``from_serialized``/``unserialize``
------------------------------------------------------------------

This family of methods is aiming at runtime objects that may be
saved into and loaded from tmt working files, i.e. files tmt uses
to store a state in its workdir, like `step.yaml` or `guests.yaml`.

Third member of this family, ``unserialize``, is similar to
``from_serialized`` - both create an object from its serialized form,
only ``unserialize`` is capable of detecting the class to instantiate
while for using ``from_serialized``, one must already know which
class to work with. ``unserialize`` then uses ``from_serialized``
under the hood to do the heavy lifting when correct class is
identified.

The default implementation comes from ``tmt.utils.SerializableContainer``
class, all classes that are being saved and loaded during tmt run
should include this class among their bases.

See https://en.wikipedia.org/wiki/Serialization for more details
on the concept of serialization.

.. code-block:: python

    # tmt.steps.discover.shell.DiscoverShellData wishes to unserialize its
    # `tests` a list of `TestDescription` objects rather than a list of
    # dictionaries (the default implementation).
    @classmethod
    def from_serialized(cls, serialized: Dict[str, Any]) -> 'DiscoverShellData':
        obj = super().from_serialized(serialized)

        obj.tests = [TestDescription.from_serialized(
            serialized_test) for serialized_test in serialized['tests']]

        return obj

   # A step saving its state...
   content: Dict[str, Any] = {
       'status': self.status(),
       'data': [datum.to_serialized() for datum in self.data]
   }
   self.write('step.yaml', tmt.utils.dict_to_yaml(content))

   # ... and loading it back.
   # Note the use of unserialize(): step data may have been serialized from
   # various different classes (derived from tmt.steps.provision.Guest),
   # and unserialize() will detect the correct class.
   raw_step_data: Dict[Any, Any] = tmt.utils.yaml_to_dict(self.read('step.yaml'))
   self.data = [
       StepData.unserialize(raw_datum) for raw_datum in raw_step_data['data']
   ]


``to_dict``/``to_minimal_dict``
------------------------------------------------------------------

Very special helper methods: its use cases are not related to any
input or output data, and most of the time, when in need of
iterating over object's keys and/or values, one can use ``keys()``,
``values()`` or ``items()`` methods. They are used as sources of data
for serialization and validation, but they usually have no use outside
of default implementations.

.. warning::

   If you think of using ``to_dict()``, please, think again and be sure
   you know what are you doing. Despite its output being sometimes
   perfectly compatible with output of ``to_serialized()`` or ``to_spec()``,
   it is not generaly true, and using it instead of proper methods may lead
   to unexpected exceptions.

   The same applies to ``to_minimal_dict()``.

.. code-block:: python

   # tmt.base.FmfId's specification is basically just a mapping,
   # therefore `to_dict()` is good enough to produce a specification.
   def to_spec(self) -> Dict[str, Any]:
        return self.to_dict()


Essential Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tmt
    :members:
    :undoc-members:
