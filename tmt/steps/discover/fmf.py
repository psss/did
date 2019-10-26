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

from click import echo

class DiscoverFmf(tmt.steps.discover.DiscoverPlugin):
    """ Discover available tests from FMF metadata """

    def __init__(self, data, step):
        """ Check supported attributes """
        super(DiscoverFmf, self).__init__(step=step, name=data['name'])
        self.tree = None
        # Convert data into attributes for easy handling
        self.repository = data.get('repository')
        self.revision = data.get('revision')
        filtr = data.get('filter')
        self.filters = filtr if isinstance(filtr, list) else [filtr]

    def go(self):
        """ Discover available tests """
        testdir = os.path.join(self.workdir, 'tests')
        # Copy current repository to workdir
        if self.repository is None:
            directory = self.step.plan.run.tree.root
            echo("Copying '{}' to '{}'.".format(directory, testdir))
            shutil.copytree(directory, testdir)
        # Clone git repository
        else:
            self.run(
                f"git clone {self.repository} {testdir}",
                f"Clone '{self.repository}' to '{testdir}'.")
        # Checkout revision if requested
        if self.revision:
            self.run(
                f"git checkout -f {self.revision}",
                f"Checkout revision '{self.revision}'.")
        self.tests_tree = fmf.Tree(testdir)

    def tests(self):
        """ Return all discovered tests """
        # Prepare test name filter if provided
        names = tmt.base.Test._opt('names', [])
        if names:
            names = [names]
        return [
            tmt.Test(test) for test in self.tests_tree.prune(
            keys=['test'], filters=self.filters or [], names=names)]

    def dump(self):
        """ Dump current step data """
        self.data['filter'] = self.filters
        return self.data
