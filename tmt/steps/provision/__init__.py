# coding: utf-8

""" Provision Step Classes """

import tmt
import random
import string
import os

from click import echo

from .localhost import ProvisionLocalhost


class Provision(tmt.steps.Step):
    """
        Provision step

        Note: provision.how contains forced how step from command-line
    """
    name = 'provision'

    def __init__(self, data, plan):
        super(Provision, self).__init__(data, plan)

        # If this is not an initialization for 'run' command, just ignore
        if not self.plan.run:
            return

        # List of provisioned guests
        self.guests = []

        # if there are no data but user forces it, use local provisioner
        if not data:
            if self.how:
                self.data = [{'how': 'local'}]
            return

        # choose correct plugin
        for item in self.data:
            how = self.how
            if how == 'local':
                self.guests.append(GuestLocalost(item, self))
            else:
                raise SpecificationError("Unknown how '{}'".format(how))

    def go(self):
        """ provision all resources """
        super(Provision, self).go()

        for guest in self.guests:
            guest.provision()
            guest.save()
