import copy
import os
import shutil

import click
import fmf

import tmt
import tmt.steps.discover

# For more informations please take a look at docs/example.rst file
# or online documentation.


class DiscoverExample(tmt.steps.discover.DiscoverPlugin):
    """
    You must provide docs here otherwise traceback happens. Also it's good
    to let know what this should do.
    """

    # Supported methods
    _methods = [tmt.steps.Method(name='example', doc=__doc__, order=999)]

    def show(self):
        """ Show plugin details for given or all available keys """
        super().show([])
        print("show() called")

    def wake(self):
        """
        Wake up the plugin (override data with command line)

        If a list of option names is provided, their value will be
        checked and stored in self.data unless empty or undefined.
        """
        print("wake() called")

        # Check provided tests, default to an empty list
        if 'tests' not in self.data:
            self.data['tests'] = []
        self._tests = []

    def go(self):
        """
        Go and perform the plugin task.
        Discover available tests in this case.
        """
        super(DiscoverExample, self).go()

        print("go() called")

        # Prepare test environment
        print("Code should prepare environment for tests.")

        # Use a tmt.Tree to apply possible command line filters
        tests = tmt.Tree(tree=tests).tests()
        self._tests = tests

    def tests(self):
        """
        Return discovered tests.

        Each DiscoverPlugin has to implement this method.
        Should return a list of Test() objects.
        """
        return self._tests
