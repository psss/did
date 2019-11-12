# coding: utf-8

""" Finish Step Classes """

import tmt

from tmt.utils import SpecificationError


class Finish(tmt.steps.Step):
    """ Additional actions to be performed after the test execution """

    name = 'finish'

    def __init__(self, data, plan):
        """ Initialize the Prepare step """
        self.super = super(Finish, self)
        self.super.__init__(data, plan)

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        self.super.wake()

    def show(self):
        """ Show details """
        self.super.show()

    def go(self):
        """ Prepare the test step """
        self.super.go()

        self.plan.provision.destroy()
