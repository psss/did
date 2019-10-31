# coding: utf-8

""" Discover Step Classes """

import tmt

class Discover(tmt.steps.Step):
    """ Gather and show information about test cases to be executed """

    # Default implementation for discover is fmf
    how = 'fmf'

    def __init__(self, data, plan):
        """ Store supported attributes, check for sanity """
        super(Discover, self).__init__(data, plan)
        self.steps = []

    def load(self):
        """ Load step data from the workdir """
        pass

    def save(self):
        """ Save step data to the workdir """
        super(Discover, self).save()
        # Create 'tests.yaml' with the list of tests for the executor
        tests = dict([test.export(format_='execute') for test in self.tests()])
        self.write('tests.yaml', tmt.utils.dictionary_to_yaml(tests))

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        super(Discover, self).wake()
        # Choose the plugin
        for data in self.data:
            if data['how'] == 'fmf':
                from tmt.steps.discover.fmf import DiscoverFmf
                self.steps.append(DiscoverFmf(data, step=self))
            elif data['how'] == 'shell':
                from tmt.steps.discover.shell import DiscoverShell
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
        # Nothing to do if already done
        if self.status() == 'done':
            return
        # Go!
        self.status('going')
        super(Discover, self).go()
        for step in self.steps:
            step.go()
        self.save()
        self.status('done')

    def tests(self):
        """ Return a list of all tests """
        for step in self.steps:
            for test in step.tests():
                yield test


class DiscoverPlugin(tmt.steps.Plugin):
    """ Common parent of discover plugins """

    def __init__(self, data, step=None, name=None):
        """ Basic plugin initialization """
        super(DiscoverPlugin, self).__init__(data=data, step=step, name=name)

    def tests(self):
        """ Return discovered tests """
        raise NotImplementedError
