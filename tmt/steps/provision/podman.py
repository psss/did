import os

from click import echo
from tmt.steps.provision.base import ProvisionBase
from tmt.utils import GeneralError, SpecificationError


class ProvisionPodman(ProvisionBase):
    """ Podman Provisioner """

    def __init__(self, data, step):
        super(ProvisionPodman, self).__init__(data, step)

        self._prepare_map = {
            'ansible': self._prepare_ansible,
            'shell': self._prepare_shell,
        }

        # Get image from provision options
        self.image = self.option('image')
        self.pull = self.option('container_pull')

        # Instances variables initialized later
        self.container_name = None
        self.container_id = None

    def podman(self, command, **kwargs):
        return self.run(f'podman {command}', **kwargs)[0].rstrip()

    def option(self, key):
        """ Return option specified on command line """
        # Consider command line as priority
        if self.opt(key):
            return self.opt(key)

        return self.data.get(key, None)

    def go(self):
        super(ProvisionPodman, self).go()

        # Show which image we are using
        self.info('image', '{}{}'.format(
            self.image, ' (force pull)' if self.pull else ''), 'green')

        # Check if the image is available
        self.image_id = self.podman(
            f'images -q {self.image}',
            message=f'check for image {self.image}')

        # Pull image if not available or pull forced
        if not self.image_id or self.pull:
            self.image_id = self.podman(
                f'pull -q {self.image}',
                message=f'pull image {self.image}')

        # Deduce container name from run id, as it can be a path,
        # make it podman container name friendly
        tmt_workdir = self.step.plan.workdir
        self.container_name = 'tmt' + tmt_workdir.replace('/', '-')

        # Run the container
        self.container_id = self.podman(
            f'run --name {self.container_name} '
            f'-v {tmt_workdir}:{tmt_workdir}:Z -itd {self.image}',
            message=f'running container {self.image}')

    def execute(self, *args, **kwargs):
        if not self.container_name:
            raise GeneralError(
                'Could not execute without provisioned container')

        self.info('args', self.join(args), 'red')
        self.podman(f'exec {self.container_name} {self.join(args)}')

    def _prepare_ansible(self, what):
        """ Prepare using ansible """
        # Playbook paths should be relative to the metadata tree root
        playbook = os.path.join(self.step.plan.run.tree.root, what)
        # Run ansible playbook against localhost, in verbose mode
        # Set collumns to 80 characters
        self.run(
            f'stty cols 80; podman unshare ansible-playbook '
            f'-v -c podman -i {self.container_name}, {playbook}')

    def _prepare_shell(self, what):
        """ Prepare using shell """
        # Set current working directory to the test metadata root
        self.info('preparing shell')
        self.execute(what, cwd=self.step.plan.run.tree.root)

    def prepare(self, how, what):
        """ Run prepare phase """
        try:
            self._prepare_map[how](what)
        except AttributeError as e:
            raise SpecificationError(
                f"Prepare method '{how}' is not supported.")

    def destroy(self):
        """ Remove the container """
        self.podman(f'container rm -f {self.container_name}')
