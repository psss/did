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
        # Check provided tests
        if 'tests' not in self.data:
            raise tmt.utils.SpecificationError(
                f"Missing 'tests' in '{self.step.plan.name}'.")
        self._tests = []

    def go(self):
        """ Discover available tests """
        super(DiscoverShell, self).go()
        tests = []
        path = False
        for data in self.data['tests']:
            # Extract name, make sure it is present
            try:
                name = data.pop('name')
            except KeyError:
                raise tmt.utils.SpecificationError(
                    f"Missing test name in '{self.step.plan.name}'.")
            # Adjust path if necessary (defaults to '.')
            try:
                data['path'] = f"/{self.name}/tests{data['path']}"
                path = True
            except KeyError:
                data['path'] = '.'
            # Create a simple fmf node, adjust its name
            node = fmf.Tree(data)
            node.name = name
            # Create a tmt test
            test = tmt.Test(node)
            tests.append(test)
        # Copy current directory to workdir only if any path specified
        if path:
            directory = self.step.plan.run.tree.root
            testdir = os.path.join(self.workdir, 'tests')
            self.info('directory', directory, 'green')
            self.debug("Copy '{}' to '{}'.".format(directory, testdir))
            shutil.copytree(directory, testdir)
        # Summary of selected tests, test list in verbose mode
        summary = fmf.utils.listed(len(tests), 'test') + ' selected'
        self.info('tests', summary, 'green')
        for test in tests:
            self.verbose(test.name, color='red', shift=1)
        self._tests = tests

    def tests(self):
        return self._tests
