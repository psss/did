import dataclasses
import os
from shlex import quote
from typing import Any, List, Optional, Union

import click

import tmt
import tmt.steps
import tmt.steps.provision
import tmt.utils
from tmt.utils import BaseLoggerFnType, Command, ShellScript

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


@dataclasses.dataclass
class ProvisionPodmanData(PodmanGuestData, tmt.steps.provision.ProvisionStepData):
    pass


class GuestContainer(tmt.Guest):
    """ Container Instance """

    _data_class = PodmanGuestData

    image: Optional[str]
    container: Optional[str]
    user: str
    force_pull: bool
    parent: tmt.steps.Step

    @property
    def is_ready(self) -> bool:
        """ Detect the guest is ready or not """
        # Check the container is running or not
        if self.container is None:
            return False
        cmd_output = self.podman(Command(
            'container', 'inspect',
            '--format', '{{json .State.Running}}',
            self.container
            ))
        cmd_stdout, cmd_stderr = cmd_output
        return str(cmd_stdout).strip() == 'true'

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

        try:
            self.podman(
                Command('image', 'exists', self.image),
                message=f"Check for container image '{self.image}'."
                )
            needs_pull = False
        except tmt.utils.RunError:
            needs_pull = True

        # Pull image if not available or pull forced
        if needs_pull or self.force_pull:
            self.podman(
                Command('pull', '-q', self.image),
                message=f"Pull image '{self.image}'."
                )

        # Mount the whole plan directory in the container
        workdir = self.parent.plan.workdir

        self.container = self.guest = self._tmt_name()
        self.verbose('name', self.container, 'green')

        # FIXME: Workaround for BZ#1900021 (f34 container on centos-8)
        workaround = ['--security-opt', 'seccomp=unconfined']

        # Run the container
        self.debug(f"Start container '{self.image}'.")
        assert self.container is not None
        self.podman(Command(
            'run',
            *workaround,
            '--name', self.container,
            '-v', f'{workdir}:{workdir}:z',
            '-itd',
            '--user', self.user,
            self.image
            ))

    def reboot(self, hard: bool = False,
               command: Optional[Union[Command, ShellScript]] = None,
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
        self.podman(Command('container', 'restart', self.container))
        return self.reconnect(timeout=timeout or CONNECTION_TIMEOUT)

    def ansible(self, playbook: str, extra_args: Optional[str] = None) -> None:
        """ Prepare container using ansible playbook """
        playbook = self._ansible_playbook_path(playbook)

        # As non-root we must run with podman unshare
        podman_command = Command()

        if os.geteuid() != 0:
            podman_command += ['podman', 'unshare']

        podman_command += [
            'ansible-playbook',
            *self._ansible_verbosity(),
            *self._ansible_extra_args(extra_args),
            '-c', 'podman', '-i', f'{self.container},', playbook
            ]

        stdout, _ = self.run(
            podman_command,
            cwd=self.parent.plan.worktree,
            env=self._prepare_environment())
        self._ansible_summary(stdout)

    def podman(self, command: Command, **kwargs: Any) -> tmt.utils.CommandOutput:
        """ Run given command via podman """
        return self.run(Command('podman') + command, **kwargs)

    def execute(self,
                command: Union[tmt.utils.Command, tmt.utils.ShellScript],
                cwd: Optional[str] = None,
                env: Optional[tmt.utils.EnvironmentType] = None,
                friendly_command: Optional[str] = None,
                test_session: bool = False,
                silent: bool = False,
                log: Optional[BaseLoggerFnType] = None,
                interactive: bool = False,
                **kwargs: Any) -> tmt.utils.CommandOutput:
        """ Execute given commands in podman via shell """
        if not self.container and not self.opt('dry'):
            raise tmt.utils.ProvisionError(
                'Could not execute without provisioned container.')

        podman_command = Command('exec')

        # Accumulate all necessary commands - they will form a "shell" script, a single
        # string passed to a shell executed inside the container.
        script = ShellScript.from_scripts(self._export_environment(self._prepare_environment(env)))

        # Change to given directory on guest if cwd provided
        if cwd is not None:
            script += ShellScript(f'cd {quote(cwd)}')

        if isinstance(command, Command):
            script += command.to_script()

        else:
            script += command

        # Run in interactive mode if requested
        if interactive:
            podman_command += ['-it']

        podman_command += [
            self.container or 'dry',
            ]

        podman_command += script.to_shell_command()

        # Note that we MUST run commands via bash, so variables
        # work as expected
        return self.podman(
            podman_command,
            log=log if log else self._command_verbose_logger,
            friendly_command=friendly_command or command,
            silent=silent,
            interactive=interactive,
            **kwargs)

    def push(
            self,
            source: Optional[str] = None,
            destination: Optional[str] = None,
            options: Optional[List[str]] = None) -> None:
        """ Make sure that the workdir has a correct selinux context """
        if not self.is_ready:
            return

        self.debug("Update selinux context of the run workdir.", level=3)
        assert self.parent.plan.workdir is not None  # narrow type
        self.run(Command(
            "chcon", "--recursive", "--type=container_file_t", self.parent.plan.workdir
            ), shell=False)
        # In case explicit destination is given, use `podman cp` to copy data
        # to the container
        if source and destination:
            self.podman(Command("cp", source, f"{self.container}:{destination}"))

    def pull(
            self,
            source: Optional[str] = None,
            destination: Optional[str] = None,
            options: Optional[List[str]] = None,
            extend_options: Optional[List[str]] = None) -> None:
        """ Nothing to be done to pull workdir """
        if not self.is_ready:
            return

    def stop(self) -> None:
        """ Stop provisioned guest """
        if self.container:
            self.podman(Command('container', 'stop', self.container))
            self.info('container', 'stopped', 'green')

    def remove(self) -> None:
        """ Remove the container """
        if self.container:
            self.podman(Command('container', 'rm', '-f', self.container))
            self.info('container', 'removed', 'green')


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

    _data_class = ProvisionPodmanData
    _guest_class = GuestContainer

    # Guest instance
    _guest = None

    @classmethod
    def options(cls, how: Optional[str] = None) -> List[tmt.options.ClickOptionDecoratorType]:
        """ Prepare command line options for connect """
        return [
            click.option(
                '-i', '--image', metavar='IMAGE',
                help='Select image to use. Short name or complete url.'),
            click.option(
                '-c', '--container', metavar='NAME',
                help='Name or id of an existing container to be used.'),
            click.option(
                '-p', '--pull', 'force_pull', is_flag=True,
                help='Force pulling a fresh container image.'),
            click.option(
                '-u', '--user', metavar='USER',
                help='User to use for all container operations.')
            ] + super().options(how)

    def default(self, option: str, default: Any = None) -> Any:
        """ Return default data for given option """
        if option == 'pull':
            return self.get('force-pull', default=default)

        return super().default(option, default=default)

    def go(self) -> None:
        """ Provision the container """
        super().go()

        # Show which image we are using
        pull = ' (force pull)' if self.get('force_pull') else ''
        self.info('image', f"{self.get('image')}{pull}", 'green')

        # Prepare data for the guest instance
        data_from_options = {
            key: self.get(key)
            for key in PodmanGuestData.keys()
            }

        data = PodmanGuestData(**data_from_options)

        # Create a new GuestTestcloud instance and start it
        self._guest = GuestContainer(
            logger=self._logger,
            data=data,
            name=self.name,
            parent=self.step)
        self._guest.start()

    def guest(self) -> Optional[GuestContainer]:
        """ Return the provisioned guest """
        return self._guest
