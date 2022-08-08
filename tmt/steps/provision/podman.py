import dataclasses
import os
from shlex import quote
from typing import Any, List, Optional, Tuple, Union

import click

import tmt
import tmt.steps
import tmt.steps.provision

# Timeout in seconds of waiting for a connection
CONNECTION_TIMEOUT = 60

# Defaults
DEFAULT_IMAGE = "fedora"
DEFAULT_USER = "root"


@dataclasses.dataclass
class PodmanGuestData(tmt.steps.provision.GuestData):
    image: str = DEFAULT_IMAGE
    user: str = DEFAULT_USER
    force_pull: bool = False

    container: Optional[str] = None


@tmt.steps.provides_method('container')
class ProvisionPodman(tmt.steps.provision.ProvisionPlugin):
    """
    Create a new container using podman

    Example config:

        provision:
            how: container
            image: fedora:latest

    In order to always pull the fresh container image use 'pull: true'.

    In order to run the container with different user as the default 'root',
    use 'user: USER'.
    """

    # Guest instance
    _guest = None

    # Supported keys
    _keys = ["image", "container", "pull", "user"]

    @classmethod
    def options(cls, how: Optional[str] = None) -> List[tmt.options.ClickOptionDecoratorType]:
        """ Prepare command line options for connect """
        options = super().options(how)
        options[:0] = [
            click.option(
                '-i', '--image', metavar='IMAGE',
                help='Select image to use. Short name or complete url.'),
            click.option(
                '-c', '--container', metavar='NAME',
                help='Name or id of an existing container to be used.'),
            click.option(
                '-p', '--pull', is_flag=True,
                help='Force pulling a fresh container image.'),
            click.option(
                '-u', '--user', metavar='USER',
                help='User to use for all container operations.')
            ]
        return options

    def default(self, option: str, default: Any = None) -> Any:
        """ Return default data for given option """
        if option == 'pull':
            return PodmanGuestData().force_pull

        return getattr(PodmanGuestData(), option.replace('-', '_'), default)

    def wake(self, data: Optional[tmt.steps.provision.GuestData] = None) -> None:
        """ Wake up the plugin, process data, apply options """
        super().wake(data=data)
        # Wake up podman instance
        if data:
            guest = GuestContainer(data, name=self.name, parent=self.step)
            guest.wake()
            self._guest = guest

    def go(self) -> None:
        """ Provision the container """
        super().go()

        # Show which image we are using
        pull = ' (force pull)' if self.get('pull') else ''
        self.info('image', f"{self.get('image')}{pull}", 'green')

        # Prepare data for the guest instance
        data_from_options = {
            key: self.get(key)
            for key in PodmanGuestData.keys()
            if key != 'force_pull'
            }

        data_from_options['force_pull'] = self.get('pull')

        data = PodmanGuestData(**data_from_options)

        # Create a new GuestTestcloud instance and start it
        self._guest = GuestContainer(data, name=self.name, parent=self.step)
        self._guest.start()

    def guest(self) -> Optional['GuestContainer']:
        """ Return the provisioned guest """
        return self._guest

    def requires(self) -> List[str]:
        """ List of required packages needed for workdir sync """
        return GuestContainer.requires()


class GuestContainer(tmt.Guest):
    """ Container Instance """

    _data_class = PodmanGuestData

    image: Optional[str]
    container: Optional[str]
    user: str
    force_pull: bool
    parent: tmt.steps.Step

    def wake(self) -> None:
        """ Wake up the guest """
        self.debug(
            f"Waking up container '{self.container}'.", level=2, shift=0)

    def start(self) -> None:
        """ Start provisioned guest """
        if self.opt('dry'):
            return
        # Check if the image is available
        assert self.image is not None
        command = ['images', '-q', self.image]
        podman_output = self.podman(command, message=f"Check for container image '{self.image}'.")

        if podman_output.stdout is None:
            raise tmt.utils.RunError(
                'command produced no usable output',
                command,
                0,
                podman_output.stdout,
                podman_output.stderr)

        image_id = podman_output.stdout.strip()

        # Pull image if not available or pull forced
        if not image_id or self.force_pull:
            self.podman(
                ['pull', '-q', self.image],
                message=f"Pull image '{self.image}'.")

        # Mount the whole plan directory in the container
        workdir = self.parent.plan.workdir

        self.container = self.guest = self._tmt_name()
        self.verbose('name', self.container, 'green')

        # FIXME: Workaround for BZ#1900021 (f34 container on centos-8)
        workaround = ['--security-opt', 'seccomp=unconfined']

        # Run the container
        self.debug(f"Start container '{self.image}'.")
        assert self.container is not None
        self.podman(
            ['run'] + workaround +
            ['--name', self.container, '-v', f'{workdir}:{workdir}:z',
             '-itd', '--user', self.user, self.image])

    def reboot(self, hard: bool = False,
               command: Optional[Union[str, List[str], Tuple[str, ...]]] = None,
               timeout: Optional[int] = None) -> bool:
        """ Restart the container, return True if successful  """
        if command:
            raise tmt.utils.ProvisionError(
                "Custom reboot command not supported in podman provision.")
        if not hard:
            raise tmt.utils.ProvisionError(
                "Containers do not support soft reboot, they can only be "
                "stopped and started again (hard reboot).")
        assert self.container is not None
        self.podman(['container', 'restart', self.container])
        return self.reconnect(timeout=timeout or CONNECTION_TIMEOUT)

    def ansible(self, playbook: str, extra_args: Optional[str] = None) -> None:
        """ Prepare container using ansible playbook """
        playbook = self._ansible_playbook_path(playbook)
        # As non-root we must run with podman unshare
        podman_unshare = ['podman', 'unshare'] if os.geteuid() != 0 else []
        stdout, stderr = self.run(
            podman_unshare + ['ansible-playbook'] +
            self._ansible_verbosity() +
            self._ansible_extra_args(extra_args) +
            ['-c', 'podman', '-i', f'{self.container},', playbook],
            cwd=self.parent.plan.worktree,
            env=self._prepare_environment())
        self._ansible_summary(stdout)

    def podman(self, command: List[str], **kwargs: Any) -> tmt.utils.CommandOutput:
        """ Run given command via podman """
        return self.run(['podman'] + command, **kwargs)

    def execute(self, command: Union[List[str], str], **kwargs: Any) -> tmt.utils.CommandOutput:
        """ Execute given commands in podman via shell """
        if not self.container and not self.opt('dry'):
            raise tmt.utils.ProvisionError(
                'Could not execute without provisioned container.')

        # Change to given directory on guest if cwd provided
        directory = kwargs.get('cwd', '')
        if directory:
            directory = f"cd {quote(directory)}; "

        # Prepare the environment variables export
        environment = self._export_environment(
            self._prepare_environment(kwargs.get('env', dict())))

        # Run in interactive mode if requested
        interactive = ['-it'] if kwargs.get('interactive') else []

        # Note that we MUST run commands via bash, so variables
        # work as expected
        if isinstance(command, list):
            command = ' '.join(command)
        command = directory + environment + command
        assert isinstance(command, str)
        return self.podman(
            ['exec'] + interactive +
            [self.container or 'dry', 'bash', '-c', command], **kwargs)

    def push(
            self,
            source: Optional[str] = None,
            destination: Optional[str] = None,
            options: Optional[List[str]] = None) -> None:
        """ Make sure that the workdir has a correct selinux context """
        self.debug("Update selinux context of the run workdir.", level=3)
        self.run(
            ["chcon", "--recursive", "--type=container_file_t",
             self.parent.plan.workdir], shell=False)
        # In case explicit destination is given, use `podman cp` to copy data
        # to the container
        if source and destination:
            self.podman(["cp", source, f"{self.container}:{destination}"])

    def pull(
            self,
            source: Optional[str] = None,
            destination: Optional[str] = None,
            options: Optional[List[str]] = None,
            extend_options: Optional[List[str]] = None) -> None:
        """ Nothing to be done to pull workdir """

    def stop(self) -> None:
        """ Stop provisioned guest """
        if self.container:
            self.podman(['container', 'stop', self.container])
            self.info('container', 'stopped', 'green')

    def remove(self) -> None:
        """ Remove the container """
        if self.container:
            self.podman(['container', 'rm', '-f', self.container])
            self.info('container', 'removed', 'green')
