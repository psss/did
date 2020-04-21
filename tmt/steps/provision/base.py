import tmt
import os
import random
import string

from click import echo

class ProvisionBase(tmt.utils.Common):
    def __init__(self, data, step, instance_name=None):
        self.instance_name = instance_name or ''.join(random.choices(string.ascii_letters, k=16))
        self.super = super(ProvisionBase, self)
        self.super.__init__(parent=step, name=self.instance_name)
        self.data = data
        self.step = step
        self.provision_dir = os.path.join(step.workdir, self.instance_name)
        os.mkdir(self.provision_dir)

    def sync_workdir_to_guest(self):
        """ sync self.plan.workdir from host to guests """
        pass

    def sync_workdir_from_guest(self):
        """ sync self.plan.workdir from guest to host """
        pass

    def go(self):
        """ do the actual provisioning """
        pass

    def load(self):
        """ load state from workdir """
        self.data = self.read(self.data)

    def save(self):
        """ save state to workdir """
        self.write(self.data)

    def destroy(self):
        """ destroy the machine """
        pass

    def join(self, *args):
        if len(args) == 0:
            return ""
        elif len(args) == 1:
            args = args[0]

        return ' '.join(args)

    def write(self, data):
        self.super.write(self.path, self.dict_to_yaml(data))

    def read(self, current):
        if os.path.exists(self.path) and os.path.isfile(self.path):
            return self.super.read(self.path)
        else:
            return current
