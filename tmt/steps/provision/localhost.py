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
        # Playbook paths should be relative to the metadata tree root
        playbook = os.path.join(self.step.plan.run.tree.root, what)
        # Run ansible playbook against localhost, in verbose mode
        ansible = f'ansible-playbook -v -c local -i localhost, {playbook}'
        # Force column width to 80 chars, to mitigate issues with too long
        # lines due to indent. Column width is the same as with libvirt plugin.
        columns = 'stty cols 80'
        self.run(f'sudo sh -c "{columns}; {ansible}"')

    def _prepare_shell(self, what):
        """ Run ansible on localhost """
        # Set current working directory to the test metadata root
        self.run(what, cwd=self.step.plan.run.tree.root)

    def prepare(self, how, what):
        """ Run prepare phase """
        try:
            self._prepare_map[how](what)
        except AttributeError as e:
            raise SpecificationError(
                f"Prepare method '{how}' is not supported.")
