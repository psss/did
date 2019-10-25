# coding: utf-8

""" Discover Step Classes """

import tmt

class Discover(tmt.steps.Step):
    """ Gather and show information about test cases to be executed """

    def __init__(self, data, plan):
        """ Store supported attributes, check for sanity """
        super(Discover, self).__init__(data, plan)
        self.steps = []

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        super(Discover, self).wake()
        # Choose the plugin
        from tmt.steps.discover.fmf import DiscoverFmf
        from tmt.steps.discover.shell import DiscoverShell
        for data in self.data:
            if data['how'] == 'fmf':
                self.steps.append(DiscoverFmf(data, step=self))
            elif data['how'] == 'shell':
                self.steps.append(DiscoverShell(data, step=self))
            else:
                raise tmt.utils.SpecificationError(
                    f"Unknown discover method '{how}'.")

    def show(self):
        """ Show discover details """
        keys = ['how', 'repository', 'destination', 'revision', 'filter']
        super(Discover, self).show(keys)

    def go(self):
        """ Execute all steps """
        super(Discover, self).go()
        for step in self.steps:
            step.go()

    def tests(self):
        """ Return a list of all tests """
        tests = []
        for step in self.steps:
            self.tests.extend(step.tests())
        return tests


class DiscoverPlugin(tmt.steps.Plugin):
    """ Common parent of discover plugins """

    def __init__(self, data={}, step=None, name=None):
        """ Basic plugin initialization """
        super(DiscoverPlugin, self).__init__(step=step, name=name)

    def tests(self):
        """ Return discovered tests """
        raise NotImplementedError
