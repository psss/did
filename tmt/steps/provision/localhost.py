from click import echo

from tmt.steps.provision.base import ProvisionBase


class ProvisionLocalhost(ProvisionBase):
    def go(self):
        echo('provisioning localhost')

    def save(self):
        echo('saving localhost')
