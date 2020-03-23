import os

from tmt.steps.provision.base import ProvisionBase
from tmt.utils import GeneralError, SpecificationError

DEFAULT_IMAGE = 'fedora'


class ProvisionPodman(ProvisionBase):
    """ Podman Provisioner """

    def __init__(self, data, step):
        super(ProvisionPodman, self).__init__(data, step)

        self._prepare_map = {
            'ansible': self._prepare_ansible,
            'shell': self._prepare_shell,
        }

        # Get image from provision options
        self.image = self.option('image') or DEFAULT_IMAGE
        self.pull = self.option('container_pull')

        # Instances variables initialized later
        self.container_name = None
        self.container_id = None

        # Environment variables compatible with commands used
        self.podman_env = [f'-e {env}' for env in self.opt('environment')]
        self.shell_env = ' '.join(self.opt('environment'))

    def podman(self, command, **kwargs):
        """ Run given command via podman """
        return self.run(
            ['podman'] + command, shell=False, **kwargs)[0].rstrip()

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
        image_id = self.podman(
            ['images', '-q', self.image],
            message=f'check for image {self.image}')

        # Pull image if not available or pull forced
        if not image_id or self.pull:
            self.podman(
                ['pull', '-q', self.image], message=f'pull image {self.image}')

        # Deduce container name from run id, as it can be a path,
        # make it podman container name friendly
        tmt_workdir = self.step.plan.workdir
        self.container_name = 'tmt' + tmt_workdir.replace('/', '-')

        # Run the container, add environment variables
        self.container_id = self.podman(
            ['run'] + self.podman_env + ['--name', self.container_name,
            '-v', f'{tmt_workdir}:{tmt_workdir}:Z', '-itd', self.image],
            message=f'running container {self.image}')

    def execute(self, *args, **kwargs):
        """ Execute given commands in podman via shell """
        if not self.container_name:
            raise GeneralError(
                'Could not execute without provisioned container')

        # Note that we MUST run commands via bash, so variables
        # work as expected
        self.podman(
            ['exec'] + self.podman_env + [self.container_name,
            'sh', '-c', self.join(args)], **kwargs)

    def _prepare_ansible(self, what):
        """ Prepare using ansible """
        # Playbook paths should be relative to the metadata tree root
        playbook = os.path.join(self.step.plan.run.tree.root, what)

        # Run ansible playbook against localhost, in verbose mode
        # Set columns to 80 characters so it looks the same as with vagrant
        self.run(
            f'stty cols 80; {self.shell_env} podman unshare ansible-playbook '
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
        except AttributeError:
            raise SpecificationError(
                f"Prepare method '{how}' is not supported.")

    def destroy(self):
        """ Remove the container """
        if self.container_name:
            self.podman(['container', 'rm', '-f', self.container_name])
