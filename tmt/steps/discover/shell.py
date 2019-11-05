# coding: utf-8

""" Shell Tests Discovery """

import os
import fmf
import tmt
import shutil
import tmt.steps.discover

class DiscoverShell(tmt.steps.discover.DiscoverPlugin):
    """ Discover available tests from manually provided list """

    def __init__(self, data, step):
        """ Check supported attributes """
        super(DiscoverShell, self).__init__(
            data=data, step=step, name=data['name'])
        # Check provided tests, default to an empty list
        if 'tests' not in self.data:
            self.data['tests'] = []
        self._tests = []

    def go(self):
        """ Discover available tests """
        super(DiscoverShell, self).go()
        tests = fmf.Tree(dict(summary='tests'))
        path = False
        for data in self.data['tests']:
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
            # Adjust path if necessary (defaults to '.')
            try:
                data['path'] = f"/{self.name}/tests{data['path']}"
                path = True
            except KeyError:
                data['path'] = '.'
            # Create a simple fmf node, adjust its name
            tests.child(name, data)
        # Copy current directory to workdir only if any path specified
        if path:
            directory = self.step.plan.run.tree.root
            testdir = os.path.join(self.workdir, 'tests')
            self.info('directory', directory, 'green')
            self.debug("Copy '{}' to '{}'.".format(directory, testdir))
            shutil.copytree(directory, testdir)
        # Use a tmt.Tree to apply possible command line filters
        tests = tmt.Tree(tree=tests).tests()
        # Summary of selected tests, test list in verbose mode
        summary = fmf.utils.listed(len(tests), 'test') + ' selected'
        self.info('tests', summary, 'green')
        for test in tests:
            self.verbose(test.name, color='red', shift=1)
        self._tests = tests

    def tests(self):
        return self._tests
