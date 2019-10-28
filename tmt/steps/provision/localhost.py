from click import echo

from tmt.steps.provision.base import ProvisionBase


class ProvisionLocalhost(ProvisionBase):
    def go(self):
        self.info('provisioning localhost')

    def save(self):
        self.info('saving localhost')
