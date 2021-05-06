.. _Plugins:

======================
    Plugins
======================

Let's have a look at a plugins.

Skeletons for example plugin are located in:
examples/plugins/

Plugin can contain more steps so plugin is not only one file but it can
be more files which covers different steps.

Example plugin covers two steps: discover and provision.

How to create a plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's use our example plugin and describe discover step.

There is example.py file in tmt/steps/discover/ directory
and it contains latest changes. There is a lot of comments
and you can use it as skeleton for your new plugin.

Most important part is, that you need to overload 4 methods:

- show()
- wake()
- go()
- tests()

Another step covered here is provision step. You can find example.py file in
tmt/steps/provision/ directory. This step is more complex and is divided to 2 classes.
One part is provisioning itself and second part is Guest class.

Your Class needs to inherit from tmt.steps.provision.ProvisionPlugin.
Then file should contains class which inherits from tmt.Guest.
