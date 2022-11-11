
==============
    Config
==============

The config file ``~/.did/config`` is used to store both general
settings and configuration of individual reports. Command line
option ``--config`` allows to select a different config file from
the config directory. This can serve as a kind of a profile and is
especially useful for gathering team reports.

Use the ``DID_DIR`` environment variable to override the default
config directory ``~/.did`` and use your custom location instead.
For example if you prefer to keep you home directory clean you
might want to add the following line into ``.bashrc``::

    export DID_DIR=~/.config/did/


.. _general:

General
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Minimum config file should contain at least a ``general`` section
with an email address which will be used for searching. Option
``width`` specifies the maximum width of the report, ``quarter``
can be used to choose a different start month of the quarter.
The ``separator`` and ``separator_width`` options control the
character used, and width of the separator between users::

    [general]
    email = Petr Šplíchal <psplicha@redhat.com>
    width = 79
    quarter = 1
    separator = #
    separator_width = 20

In order to load additional plugins from your custom locations
provide paths to be searched in the ``plugins`` option::

    [general]
    email = Petr Šplíchal <psplicha@redhat.com>
    plugins = ~/.did/plugins

Each path should be a package or module. This method works whether
the package or module is on the filesystem or in an ``.egg``.


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


Aliases
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Custom email or login alias can be provided in stats sections.
This allows to override the default value for individual stats::

    [github]
    type = github
    url = https://api.github.com/
    login = psss

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
