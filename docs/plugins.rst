.. _plugins:

===============
    Plugins
===============

Let's have a look at plugins. Each of the six steps defined by
:ref:`/spec/plans` supports multiple methods. These methods are
implemented by plugins which are dynamically loaded from the
standard location under ``tmt/steps`` , from all directories
provided in the ``TMT_PLUGINS`` environment variable and from
``tmt.plugin`` entry point.


Inheritance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The plugin is implemented by a class which inherits from the
corresponding step class, for example ``ProvisionPodman`` inherits
from the ``ProvisionPlugin`` class. See the :ref:`classes` page
for more details about the class structure. The plugin class
defines a couple of essential methods:

options()
    command line options specific for given plugin

wake()
    additional plugin data processing after the wake-up

show()
    give a concise overview of the step configuration

go()
    the main implementation of the plugin functionality

There may be additional required methods which need to be
implemented. See individual plugin examples for details.


Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Example plugin skeletons are located in the `examples/plugins`__
directory. Get some inspiration for writing plugins there. There
is a lot of comments and you can use the examples as a skeleton
for your new plugin.

The ``discover`` plugin example demonstrates a simple plugin
functionality defining an additional ``tests()`` method which
returns a list of discovered tests.

The ``provision`` step example is more complex and consists of two
classes. In addition to the provisioning part itself it also
implements the ``GuestExample`` class which inherits from
``Guest`` and overloads its methods to handle special guest
features which cannot be covered by generic ssh implementation of
the ``Guest`` class.

__ https://github.com/teemtee/tmt/tree/main/examples/plugins
