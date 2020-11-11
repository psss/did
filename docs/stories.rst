
Stories
=======

This section contains user stories describing functionality
proposed to be implemented by ``tmt``. In addition to the story
you will usually find a detailed description of the purpose and a
couple of examples demonstrating expected usage.


.. toctree::
    :maxdepth: 2

    stories/install
    stories/docs
    stories/cli
    stories/api
    stories/coverage


It is also possible to list and search stories directly from the
command line using the ``story`` command::

    tmt story ls
    tmt story show
    tmt story show test/create

Current status of story coverage from implementation, testing and
documentation point of view can be viewed using the ``coverage``
subcommand with optional regular expression for filtering::

    tmt story coverage
    tmt story coverage cli
    tmt story coverage --implemented
