# coding: utf-8

""" Provision Step Classes """

import tmt
import os

from click import echo

from tmt.utils import SpecificationError


class Provision(tmt.steps.Step):
    """ Provision step """

    # Default implementation for provision is a virtual machine
    how = 'virtual'

    def __init__(self, data, plan):
        super(Provision, self).__init__(data, plan)
        # List of provisioned guests
        self.guests = []
        self.super = super(Provision, self)
        self.path = os.path.join(self.workdir, 'guests.yaml')

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        super(Provision, self).wake()
        image = self.opt('image')
        # Choose the plugin
        for data in self.data:
            how = data.get('how')
            # Update the image if provided
            if image is not None:
                data['image'] = image
            if how == 'local':
                from .localhost import ProvisionLocalhost
                self.guests.append(ProvisionLocalhost(data, self))
            else:
                from .vagrant import ProvisionVagrant
                self.guests.append(ProvisionVagrant(data, self))

    def go(self):
        """ Provision all resources """
        self.super.go()

        for guest in self.guests:
            guest.go()
            # this has to be fixed first
            #guest.save()

    def execute(self, *args, **kwargs):
        for guest in self.guests:
            guest.execute(*args, **kwargs)

    def load(self):
        self.guests = self.read(self.guests)

        for guest in self.guests:
            guest.load()

    def save(self):
        self.write(self.guests)

        for guest in self.guests:
            guest.save()

    def show(self):
        """ Show provision details """
        keys = ['how', 'image']
        super(Provision, self).show(keys)

    def sync_workdir_to_guest(self):
        for guest in self.guests:
            guest.sync_workdir_to_guest()

    def sync_workdir_from_guest(self):
        for guest in self.guests:
            guest.sync_workdir_from_guest()

    def copy_from_guest(self, target):
        for guest in self.guests:
            guest.copy_from_guest(target)

    def destroy(self):
        for guest in self.guests:
            guest.destroy()

    def prepare(self, how, what):
        for guest in self.guests:
            guest.prepare(how, what)

    def clean(self):
        for guest in self.guests:
            guest.clean()

    def write(self, data):
        self.super.write(self.path, self.dictionary_to_yaml(data))

    def read(self, current):
        if os.path.exists(self.path) and os.path.isfile(self.path):
            return self.super.read(self.path)
        else:
            return current
