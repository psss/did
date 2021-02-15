import tmt
import click

class ProvisionPodman(tmt.steps.provision.ProvisionPlugin):
    """
    Create a new container using podman

    Example config:

        provision:
            how: container
            image: fedora:latest

    In order to always pull the fresh container image use 'pull: yes'.
    """

    # Guest instance
    _guest = None

    # Supported keys
    _keys = ['image', 'container', 'pull']

    # Supported methods
    _methods = [tmt.steps.Method(name='container', doc=__doc__, order=50)]

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options for connect """
        return [
            click.option(
                '-i', '--image', metavar='IMAGE',
                help='Select image to use. Short name or complete url.'),
            click.option(
                '-c', '--container', metavar='NAME',
                help='Name or id of an existing container to be used.'),
            click.option(
                '-p', '--pull', is_flag=True,
                help='Force pulling a fresh container image.'),
            ] + super().options(how)

    def default(self, option, default=None):
        """ Return default data for given option """
        # User 'fedora' as a default image
        if option == 'image':
            return 'fedora'
        # No other defaults available
        return default

    def show(self):
        """ Show provision details """
        super().show(self._keys)

    def wake(self, data=None):
        """ Override options and wake up the guest """
        super().wake(self._keys)
        # Wake up podman instance
        if data:
            guest = GuestContainer(data, name=self.name, parent=self.step)
            guest.wake()
            self._guest = guest

    def go(self):
        """ Provision the container """
        super().go()

        # Show which image we are using
        pull = ' (force pull)' if self.get('pull') else ''
        self.info('image', f"{self.get('image')}{pull}", 'green')

        # Prepare data for the guest instance
        data = dict()
        for key in self._keys:
            data[key] = self.get(key)

        # Create a new GuestTestcloud instance and start it
        self._guest = GuestContainer(data, name=self.name, parent=self.step)
        self._guest.start()

    def guest(self):
        """ Return the provisioned guest """
        return self._guest

    def requires(self):
        """ List of required packages needed for workdir sync """
        return GuestContainer.requires()


class GuestContainer(tmt.Guest):
    """ Container Instance """

    def load(self, data):
        """ Load guest data and initialize attributes """
        super().load(data)

        # Load basic data
        self.image = data.get('image')
        self.force_pull = data.get('pull')
        self.container = data.get('container')

        # Instances variables initialized later
        self.container_id = None

    def save(self):
        """ Save guest data for future wake up """
        data = {
            'container': self.container,
            'image': self.image,
            }
        return data

    def wake(self):
        """ Wake up the guest """
        self.debug(
            f"Waking up container '{self.container}'.", level=2, shift=0)

    def start(self):
        """ Start provisioned guest """
        if self.opt('dry'):
            return
        # Check if the image is available
        image_id = self.podman(
            ['images', '-q', self.image],
            message=f"Check for container image '{self.image}'.")[0].strip()

        # Pull image if not available or pull forced
        if not image_id or self.force_pull:
            self.podman(
                ['pull', '-q', self.image],
                message=f"Pull image '{self.image}'.")

        # Deduce container name from run id, as it can be a path,
        # make it podman container name friendly
        tmt_workdir = self.parent.plan.workdir
        self.container = 'tmt' + tmt_workdir.replace('/', '-')
        self.verbose('name', self.container, 'green')

        # Run the container
        self.container_id = self.podman(
            ['run'] + ['--name', self.container,
            '-v', f'{tmt_workdir}:{tmt_workdir}:Z', '-itd', self.image],
            message=f"Start container '{self.image}'.")[0].strip()

    def ansible(self, playbook):
        """ Prepare container using ansible playbook """
        playbook = self._ansible_playbook_path(playbook)
        stdout, stderr = self.run(
            f'stty cols {tmt.utils.OUTPUT_WIDTH}; '
            f'{self._export_environment()}'
            f'podman unshare ansible-playbook'
            f'{self._ansible_verbosity()} -c podman -i {self.container}, '
            f'{playbook}')
        self._ansible_summary(stdout)

    def podman(self, command, **kwargs):
        """ Run given command via podman """
        return self.run(['podman'] + command, shell=False, **kwargs)

    def execute(self, command, **kwargs):
        """ Execute given commands in podman via shell """
        if not self.container and not self.opt('dry'):
            raise tmt.utils.ProvisionError(
                'Could not execute without provisioned container.')

        # Change to given directory on guest if cwd provided
        directory = kwargs.get('cwd', '')
        if directory:
            directory = f"cd '{directory}'; "

        # Prepare the environment variables export
        environment = self._export_environment(kwargs.get('env', dict()))

        # Run in interactive mode if requested
        interactive = ['-it'] if kwargs.get('interactive') else []

        # Note that we MUST run commands via bash, so variables
        # work as expected
        if isinstance(command, list):
            command = ' '.join(command)
        command = directory + environment + command
        return self.podman(
            ['exec'] + interactive +
            [self.container or 'dry', 'sh', '-c', command], **kwargs)

    def push(self):
        """ Nothing to be done to push workdir """

    def pull(self):
        """ Nothing to be done to pull workdir """

    def stop(self):
        """ Stop provisioned guest """
        if self.container:
            self.podman(['container', 'stop', self.container])
            self.info('container', 'stopped', 'green')

    def remove(self):
        """ Remove the container """
        if self.container:
            self.podman(['container', 'rm', '-f', self.container])
            self.info('container', 'removed', 'green')

    @classmethod
    def requires(cls):
        """ No packages needed to sync workdir to the container """
        return []
