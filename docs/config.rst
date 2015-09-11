
==============
    Config
==============

The config file ``~/.did/config`` is used to store both general
settings and configuration of individual reports. You can use the 
``DID_CONFIG`` environment variable to override the default config
directory ``~/.did`` and use your custom location instead.


Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here's an example config file with all available plugins enabled.
See :doc:`plugins` documentation for more detailed description of
options available for particular plugin. You can also check python
module documentation, e.g. ``pydoc did.plugins.git``.

.. literalinclude:: ../examples/config
    :language: ini
