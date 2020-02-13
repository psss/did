import os

from click import echo
from tmt.steps.provision.base import ProvisionBase
from tmt.utils import SpecificationError


class ProvisionPodman(ProvisionBase):
    """ Podman Provisioner """

    def __init__(self, data, step):
        super(ProvisionPodman, self).__init__(data, step)

        self._prepare_map = {
            'ansible': self._prepare_ansible,
            'shell': self._prepare_shell,
        }

        # get image from provision options
        self.image = self.option('image')
        self.pull = self.option('pull')

        self.image_id = self.podman(
            f'images -q {self.image}',
            message=f'check for image {self.image}'
        )

        # pull image if not available or pull forced
        if not self.image_id or self.pull:
            self.image_id = self.podman(
                f'pull -q {self.image}',
                message=f'pull image {self.image}'
            )

    def podman(self, command, **kwargs):
        return self.run(f'podman {command}', **kwargs)[0].rstrip()

    def option(self, key):
        """ Return option specified on commandline """
        # consider command line as priority
        if self.opt(key):
            return self.opt(key)

        return self.data.get(key, None)

    def go(self):
        super(ProvisionPodman, self).go()

        # show which image we are using
        self.info('image', '{}{}'.format(self.image, '(force pull)' if self.pull else ''), 'green')

        # deduce container name from run id, as it can be a path, make it podman container name friendly
        tmt_workdir = self.step.plan.workdir
        self.container_name = 'tft-' + tmt_workdir.replace('/', '-')

        # run the container
        self.container_id = self.podman(
            f'run --name {self.container_name} -v {tmt_workdir}:{tmt_workdir}:Z -itd {self.image}',
            message=f'running container {self.image}'
        )
        
    def execute(self, *args, **kwargs):
        self.info('args', self.join(args), 'red')
        self.podman(f'exec {self.container_id} {self.join(args)}')

    def _prepare_ansible(self, what):
        """ Run ansible on localhost """
        # Playbook paths should be relative to the metadata tree root
        playbook = os.path.join(self.step.plan.run.tree.root, what)
        # Run ansible playbook against localhost, in verbose mode
        # Set collumns to 80 characters
        self.run(f'stty cols 80; podman unshare ansible-playbook -vvv -c podman -i {self.container_id}, {playbook}')

    def _prepare_shell(self, what):
        """ Run ansible on localhost """
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
