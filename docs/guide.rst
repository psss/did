.. _guide:

======================
    Guide
======================

This guide will show you the way through the dense forest of
available ``tmt`` features, commands and options. But don't be
afraid, we will start slowly, with the simple examples first. And
then, when your eyes get accustomed to the shadow of omni-present
metadata `trees`__, we will slowly dive deeper and deeper so that
you don't miss any essential functionality which could make your
life smarter, brighter and more joyful. Let's go, follow me...

__ https://fmf.readthedocs.io/en/stable/concept.html#trees


The First Steps
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Installing the main package with the core functionality is quite
straightforward. No worry, there are just a few dependencies::

    sudo dnf install -y tmt

Enabling a simple smoke test in the continuous integration should
be a joy. Just a couple of concise commands, assuming you are in
your project git repository::

    tmt init --template mini
    vim plans/example.fmf

Open the example plan in your favorite editor and adjust the smoke
test script as needed. Your very first plan can look like this::

    summary: Basic smoke test
    execute:
        script: foo --version

Now you're ready to create a new pull request to check out how
it's working. During push, remote usually shows a direct link to
the page with a *Create* button, so now it's only two clicks
away::

    git add .
    git checkout -b smoke-test
    git commit -m "Enable a simple smoke test"
    git push origin -u smoke-test

But perhaps, you are a little bit impatient and would like to see
the results faster. Sure, let's try the smoke test here and now,
directly on your localhost::

    tmt run --all provision --how local

If you're a bit afraid that the test could break your machine or
just want to keep your environment clean, run it in a container
instead::

    sudo dnf install -y tmt-provision-container
    tmt run -a provision -h container

Or even in a full virtual machine if the container environment is
not enough. We'll use the :ref:`libvirt<libvirt>` to start a new
virtual machine on your localhost. Be ready for a bit more
dependencies here::

    sudo dnf install -y tmt-provision-virtual
    tmt run -a provision -h virtual

Don't care about the disk space? Simply install ``tmt-all`` and
you'll get all available functionality at hand. Check the help to
list all supported provision methods::

    sudo dnf install tmt-all
    tmt run provision --help

Now when you've met your ``--help`` friend you know everything you
need to get around without getting lost in the forest of available
options::

    tmt --help
    tmt run --help
    tmt run provision --help
    tmt run provision --how container --help

Go on and explore. Don't be shy and ask, ``--help`` is eager to
answer all your questions ;-)


Under The Hood
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now let's have a brief look under the hood. For storing all config
data we're using the `Flexible Metadata Format`__. In short, it is
a ``yaml`` format extended with a couple of nice features like
`inheritance`__ or virtual `hierarchy`__ which help to maintain
even large data efficiently without unnecessary duplication.

.. _tree:

The data are organized into `trees`__. Similarly as with ``git``,
there is a special ``.fmf`` directory which marks the root of the
fmf metadata tree. Use the ``init`` command to initialize it::

    tmt init

Do not forget to include this special ``.fmf`` directory in your
commits, it is essential for building the fmf tree structure which
is created from all ``*.fmf`` files discovered under the fmf root.

__ https://fmf.readthedocs.io
__ https://fmf.readthedocs.io/en/stable/features.html#inheritance
__ https://fmf.readthedocs.io/en/stable/features.html#hierarchy
__ https://fmf.readthedocs.io/en/stable/concept.html#trees


Plans
------------------------------------------------------------------

As we've seen above, in order to enable testing the following plan
is just enough::

    execute:
        script: foo --version

Store these two lines in a ``*.fmf`` file and that's it. Name and
location of the file is completely up to you, plans are recognized
by the ``execute`` key which is required. Once the newly created
plan is submitted to the CI system test script will be executed.

By the way, there are several basic templates available which can
be applied already during the ``init`` by using the ``--template``
option or the short version ``-t``. The minimal template, which
includes just a simple plan skeleton, is the fastest way to get
started::

    tmt init -t mini

:ref:`/spec/plans` are used to enable testing and group relevant
tests together. They describe how to :ref:`/spec/plans/discover`
tests for execution, how to :ref:`/spec/plans/provision` the
environment, how to :ref:`/spec/plans/prepare` it for testing, how
to :ref:`/spec/plans/execute` tests, :ref:`/spec/plans/report`
results and finally how to :ref:`/spec/plans/finish` the test job.

Here's an example of a slightly more complex plan which changes
the default provision method to container to speed up the testing
process and ensures that an additional package is installed before
the testing starts::

    provision:
        how: container
        image: fedora:33
    prepare:
        how: install
        package: wget
    execute:
        how: tmt
        script: wget http://example.org/

Note that each of the steps above uses the ``how`` keyword to
choose the desired method which should be applied. Steps can
provide multiple implementations which enables you to choose the
best one for your use case. For example to prepare the guest it's
possible to use the :ref:`/spec/plans/prepare/install` method for
simple package installations, :ref:`/spec/plans/prepare/ansible`
for more complex system setup or :ref:`/spec/plans/prepare/shell`
for arbitrary shell commands.


Tests
------------------------------------------------------------------

Very often testing is much more complex than running just a
single shell script. There might be many scenarios covered by
individual scripts. For these cases the ``discover`` step can
be instructed to explore available tests from fmf metadata as
well. The plan will look like this::

    discover:
        how: fmf
    execute:
        how: tmt

:ref:`/spec/tests`, identified by the required key ``test``,
define attributes which are closely related to individual test
cases such as the :ref:`/spec/tests/test` script,
:ref:`/spec/tests/framework`, directory :ref:`/spec/tests/path`
where the test should be executed, maximum test
:ref:`/spec/tests/duration` or packages
:ref:`required</spec/tests/require>` to run the test. Here's an
example of test metadata::

    summary: Fetch an example web page
    test: wget http://example.org/
    require: wget
    duration: 1m

Instead of writing the plan and test metadata manualy, you might
want to simply apply the ``base`` template which contains the plan
mentioned above together with a test example including both test
metadata and test script skeleton for inspiration::

    tmt init --template base

Similar to plans, it is possible to choose an arbitrary name for
the test. Just make sure the ``test`` key is defined. However, to
organize the metadata efficiently it is recommended to keep tests
and plans under separate folders, e.g. ``tests`` and ``plans``.
This will also allow you to use `inheritance`__ to prevent
unnecessary data duplication.

__ https://fmf.readthedocs.io/en/latest/features.html#inheritance


Stories
------------------------------------------------------------------

It's always good to start with a "why". Or, even better, with a
story which can describe more context behind the motivation.
:ref:`/spec/stories` can be used to track implementation, test and
documentation coverage for individual features or requirements.
Thanks to this you can track everything in one place, including
the project implementation progress. Stories are identified by the
``story`` attribute which every story has to define or inherit.

An example story can look like this::

    story:
        As a user I want to see more detailed information for
        particular command.
    example:
      - tmt test show -v
      - tmt test show -vvv
      - tmt test show --verbose

In order to start experimenting with the complete set of examples
covering all metadata levels, use the ``full`` template which
creates a test, a plan and a story::

    tmt init -t full


Core
------------------------------------------------------------------

Finally, there are certain metadata keys which can be used across
all levels. :ref:`/spec/core` attributes cover general metadata
such as :ref:`/spec/core/summary` or :ref:`/spec/core/description`
for describing the content, the :ref:`/spec/core/enabled`
attribute for disabling and enabling tests, plans and stories and
the :ref:`/spec/core/link` key which can be used for tracking
relations between objects.

Here's how the story above could be extended with the core
attributes ``description`` and ``link``::

    description:
        Different verbose levels can be enabled by using the
        option several times.
    link:
      - implemented-by: /tmt/cli.py
      - documented-by: /tmt/cli.py
      - verified-by: /tests/core/dry

Last but not least, the core attribute :ref:`/spec/core/adjust`
provides a flexible way to adjust metadata based on the
:ref:`/spec/context`.  But this is rather a large topic, so let's
keep it for another time. In the next chapter we'll learn how to
comfortably create new tests and plans.
