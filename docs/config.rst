
==============
    Config
==============

The config file ``~/.did/config`` is used to store both general
settings and configuration of individual reports. You can use the 
``DID_CONFIG`` environment variable to override the default config
directory ``~/.did`` and use your custom location instead.


Email
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the full email format ``Name Surname <login@example.org>`` if
you want to have your full name displayed in the output or choose
the short one ``login@example.org`` if you don't care. Multiple
email addresses can be provided, separated with a comma, in both
config file and on the command line, for example::

    did --email first@email.org,second@email.org
    did --email first@email.org --email second@email.org

This can be useful if you have several email aliases or if you
want to generate report for the whole team. Note that the full
email address format can be used on the command line as well.
See :class:`did.base.User` for detailed information about the
advanced email/login alias support.


Order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Order of individual sections is based on the default order set for
each plugin separately. You can adjust stats order by providing
your desired value in respective config section, for example::

    [tools]
    type = git
    order = 100
    apps = /home/psss/git/apps

This  would place the git stats at the top of your report, just
after the header section. Check :doc:`plugins` documentation for
the default order information.


Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here's an example config file with all available plugins enabled.
See :doc:`plugins` documentation for more detailed description of
options available for particular plugin. You can also check python
module documentation, e.g. ``pydoc did.plugins.git``.

.. literalinclude:: ../examples/config
    :language: ini
