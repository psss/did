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
