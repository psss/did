# coding: utf-8

""" Provision Step Classes """

import tmt

from click import echo

from .localhost import ProvisionLocalhost
from tmt.utils import SpecificationError


class Provision(tmt.steps.Step):
    """
    Provision step

    Note: provision.how contains forced how step from command-line
    """
    name = 'provision'

    def __init__(self, data, plan):
        super(Provision, self).__init__(data, plan)

        # List of provisioned guests
        self.guests = []

        if not self.data or not self.plan.run:
            return

        # choose correct plugin
        for item in self.data:
            if item.get('how') == 'local':
                self.guests.append(ProvisionLocalhost(item, self))
            else:
                raise SpecificationError("Unknown how '{}'".format(how))

    def go(self):
        """ provision all resources """
        super(Provision, self).go()

        for guest in self.guests:
            guest.provision()
            guest.save()
