# coding: utf-8

""" Discover Step Classes """

import tmt

from tmt.steps.discover.fmf import DiscoverFmf
from tmt.steps.discover.shell import DiscoverShell


class Discover(tmt.steps.Step):
    """ Gather and show information about test cases to be executed """

    def __init__(self, data, plan):
        """ Store supported attributes, check for sanity """
        super(Discover, self).__init__(data, plan)
        self.workers = []

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        super(Discover, self).wake()
        # Choose the plugin
        for step in self.data:
            how = step.get('how')
            if how == 'fmf':
                self.workers.append(DiscoverFmf(step, self))
            elif how == 'shell':
                self.workers.append(DiscoverShell(step, self))
            else:
                raise tmt.utils.SpecificationError(
                    "Unknown discover method '{}'.".format(how))

    def show(self):
        """ Show discover details """
        keys = ['how', 'repository', 'destination', 'revision', 'filter']
        super(Discover, self).show(keys)

    def go(self):
        """ Execute the test step """
        super(Discover, self).go()
        self.tests = []
        for worker in self.workers:
            worker.go()
            self.tests.extend(worker.tests)
        for test in self.tests:
            test.show()
