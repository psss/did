from click import echo

from tmt.steps.provision.base import ProvisionBase

class ProvisionLocalhost(ProvisionBase):
    def execute(self, *args, **kwargs):
        self.run(self.join(args))
