# coding: utf-8

"""
FMF Tests Discovery

Minimal config example (all available tests from the current
repository used by default)::

    discover:
        how: fmf

Full config example::

    discover:
        how: fmf
        repository: https://github.com/psss/tmt
        revision: master
        destination: tmt
        filter: 'tier: 1'
"""

import os
import re
import fmf
import tmt
import shutil
import tmt.steps.discover

class DiscoverFmf(tmt.steps.discover.DiscoverPlugin):
    """ Discover available tests from FMF metadata """

    def __init__(self, data, step):
        """ Check supported attributes """
        super(DiscoverFmf, self).__init__(
            data=data, step=step, name=data['name'])
        # Convert data into attributes for easy handling
        self.repository = data.get('repository')
        self.revision = data.get('revision')
        filtr = data.get('filter', [])
        self.filters = filtr if isinstance(filtr, list) else [filtr]
        self._tests = []

    def go(self):
        """ Discover available tests """
        super(DiscoverFmf, self).go()
        testdir = os.path.join(self.workdir, 'tests')
        # Clone provided git repository
        if self.repository:
            self.info('repository', self.repository, 'green')
            self.debug(f"Clone '{self.repository}' to '{testdir}'.")
            self.run(f'git clone {self.repository} {testdir}')
        # Copy current directory to workdir
        else:
            directory = self.step.plan.run.tree.root
            self.info('directory', directory, 'green')
            self.debug("Copy '{}' to '{}'.".format(directory, testdir))
            shutil.copytree(directory, testdir)
        # Checkout revision if requested
        if self.revision:
            self.info('revision', self.revision, 'green')
            self.debug(f"Checkout revision '{self.revision}'.")
            self.run(f"git checkout -f {self.revision}", cwd=testdir)
        # Show filters if provided
        if self.filters:
            for filter_ in self.filters:
                self.info('filter', filter_, 'green')
        # Initialize the metadata tree, search for available tests
        self.debug(f"Check metadata tree in '{testdir}'.")
        if self.opt('dry'):
            return
        self._tests = tmt.Tree(testdir).tests(filters=self.filters)
        # Prefix test path with the 'tests' subdirectory
        for test in self._tests:
            test.path = f'/tests{test.path}'

    def tests(self):
        """ Return all discovered tests """
        return self._tests
