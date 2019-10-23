# coding: utf-8

""" Discover Step Classes """

import tmt

from tmt.steps.discover.fmf import DiscoverFmf
from tmt.steps.discover.shell import DiscoverShell


class Discover(tmt.steps.Step):
    """ Gather and show information about test cases to be executed """
    name = 'discover'

    def __init__(self, data, plan):
        """ Store supported attributes, check for sanity """
        super(Discover, self).__init__(data, plan)
        self.workers = []
        if not self.data or not self.plan.run:
            return
        for data in self.data:
            how = data.get('how')
            if how == 'fmf':
                self.workers.append(DiscoverFmf(data, self))
            elif how == 'shell':
                self.workers.append(DiscoverShell(data, self))
            else:
                raise tmt.utils.SpecificationError(
                    "Unknown discover method '{}' in plan '{}'.".format(
                        how, self.plan))

    def show(self):
        """ Show discover details """
        keys = ['how', 'repository', 'destination', 'revision', 'filter']
        super(Discover, self).show(keys)

    def go(self):
        """ Execute the test step """
        if not self.enabled:
            return
        super(Discover, self).go()
        self.tests = []
        for worker in self.workers:
            worker.go()
            self.tests.extend(worker.tests)
        for test in self.tests:
            test.show()
