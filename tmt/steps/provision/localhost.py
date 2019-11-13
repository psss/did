import os

from click import echo
from tmt.steps.provision.base import ProvisionBase
from tmt.utils import SpecificationError


class ProvisionLocalhost(ProvisionBase):
    """ Localhost provisioner """

    def __init__(self, data, step):
        super(ProvisionLocalhost, self).__init__(data, step)
        self._prepare_map = {
            'ansible': self._prepare_ansible,
            'shell': self._prepare_shell,
        }

    def execute(self, *args, **kwargs):
        self.run(self.join(args))

    def _prepare_ansible(self, what):
        """ Run ansible on localhost """
        # note: we expect playbooks are placed relatively to the current directory
        self.run(f'ansible-playbook -c local -i localhost, {what}', cwd=os.getcwd())

    def _prepare_shell(self, what):
        """ Run ansible on localhost """
        # note: we expect playbooks are placed relatively to the current directory
        self.run(what, cwd=os.getcwd())

    def prepare(self, how, what):
        """ Run prepare phase """
        try:
            self._prepare_map[how](what)
        except AttributeError as e:
            raise SpecificationError(f"How '{how}' is not supported.")