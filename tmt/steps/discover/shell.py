# coding: utf-8

""" Shell Tests Discovery """

import os
import fmf
import tmt
import copy
import shutil
import tmt.steps.discover

class DiscoverShell(tmt.steps.discover.DiscoverPlugin):
    """ Discover available tests from manually provided list """

    # Supported methods
    _methods = [
        tmt.steps.Method(
            name='shell',
            summary='Manual list of shell tests',
            order=50),
        ]

    def wake(self):
        # Check provided tests, default to an empty list
        if 'tests' not in self.data:
            self.data['tests'] = []
        self._tests = []

    def go(self):
        """ Discover available tests """
        super(DiscoverShell, self).go()
        tests = fmf.Tree(dict(summary='tests'))

        # Check and process each defined shell test
        for data in self.data['tests']:
            # Create data copy (we want to keep original data for save()
            data = copy.deepcopy(data)
            # Extract name, make sure it is present
            try:
                name = data.pop('name')
            except KeyError:
                raise tmt.utils.SpecificationError(
                    f"Missing test name in '{self.step.plan.name}'.")
            # Make sure that the test script is defined
            if 'test' not in data:
                raise tmt.utils.SpecificationError(
                    f"Missing test script in '{self.step.plan.name}'.")
            # Prepare path to the test working directory (tree root by default)
            try:
                data['path'] = f"/tests{data['path']}"
            except KeyError:
                data['path'] = f"/tests"

            # Create a simple fmf node, adjust its name
            tests.child(name, data)

        # Copy directory tree to the workdir
        directory = self.step.plan.run.tree.root
        testdir = os.path.join(self.workdir, 'tests')
        self.info('directory', directory, 'green')
        self.debug("Copy '{}' to '{}'.".format(directory, testdir))
        shutil.copytree(directory, testdir)

        # Use a tmt.Tree to apply possible command line filters
        tests = tmt.Tree(tree=tests).tests()
        self._tests = tests

    def tests(self):
        return self._tests
