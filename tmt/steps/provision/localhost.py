from click import echo

from tmt.steps.provision.base import ProvisionBase


class ProvisionLocalhost(ProvisionBase):
    def provision(self):
        echo('provisioning localhost')

    def save(self):
        echo('saving localhost')
