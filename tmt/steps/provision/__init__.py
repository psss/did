# coding: utf-8

""" Provision Step Classes """

import tmt

from click import echo

from .localhost import ProvisionLocalhost
from tmt.utils import SpecificationError


class Provision(tmt.steps.Step):
    """ Provision step """

    # Default implementation for provision is a virtual machine
    how = 'virtual'

    def __init__(self, data, plan):
        super(Provision, self).__init__(data, plan)
        # List of provisioned guests
        self.guests = []

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        super(Provision, self).wake()
        # Choose the plugin
        for step in self.data:
            how = step.get('how')
            if how == 'local':
                self.guests.append(ProvisionLocalhost(step, self))
            elif how == 'virtual':
                pass
            else:
                raise SpecificationError(
                    "Unknown provision method '{}'.".format(how))

    def go(self):
        """ Provision all resources """
        super(Provision, self).go()

        for guest in self.guests:
            guest.provision()
            guest.save()
