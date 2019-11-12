from click import echo

from tmt.steps.provision.base import ProvisionBase
from shlex import join

class ProvisionLocalhost(ProvisionBase):
    def execute(self, *args, **kwargs):
        self.run(self.join(args))
