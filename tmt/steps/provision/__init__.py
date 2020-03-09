# coding: utf-8

""" Provision Step Classes """

import tmt
import os

from click import echo

from tmt.utils import SpecificationError
from tmt.steps.provision import vagrant, localhost, podman, testcloud


class Provision(tmt.steps.Step):
    """ Provision step """
    name = 'provision'

    # supported provisioners are not loaded automatically, import them and map them in how_map
    how_map = {
        'vagrant': vagrant.ProvisionVagrant,
        'libvirt': vagrant.ProvisionVagrant,
        'virtual': vagrant.ProvisionVagrant,
        'local': localhost.ProvisionLocalhost,
        'localhost': localhost.ProvisionLocalhost,
        'container': podman.ProvisionPodman,
        'podman': podman.ProvisionPodman,
        'libvirt.testcloud': testcloud.ProvisionTestcloud,
        'virtual.testcloud': testcloud.ProvisionTestcloud
    }

    # Default implementation for provision is a virtual machine
    how = 'virtual'

    def __init__(self, data, plan):
        # List of provisioned guests
        self.guests = []
        # Save parent and initialize it
        self.super = super(Provision, self)
        self.super.__init__(data, plan)

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        super(Provision, self).wake()

        # Add plugins for all guests
        for data in self.data:
            try:
                self.guests.append(self.how_map[data['how']](data, self))
            except KeyError:
                # We default to vagrant provisioner (as there might be custom
                # vagrant providers but we cannot detect them)
                self.guests.append(vagrant.ProvisionVagrant(data, self))

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
        path = os.path.join(self.workdir, 'guests.yaml')
        self.super.write(path, self.dict_to_yaml(data))

    def read(self, current):
        path = os.path.join(self.workdir, 'guests.yaml')
        if os.path.exists(path) and os.path.isfile(path):
            return self.super.read(path)
        else:
            return current
