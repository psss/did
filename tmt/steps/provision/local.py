import dataclasses
from typing import Any, List, Optional, Union

import tmt
import tmt.steps
import tmt.steps.provision
import tmt.utils
from tmt.utils import BaseLoggerFnType, Command, ShellScript


@dataclasses.dataclass
class ProvisionLocalData(tmt.steps.provision.GuestData, tmt.steps.provision.ProvisionStepData):
    pass


class GuestLocal(tmt.Guest):
    """ Local Host """

    localhost = True
    parent: tmt.steps.Step

    @property
    def is_ready(self) -> bool:
        """ Local is always ready """
        return True

    def ansible(self, playbook: str, extra_args: Optional[str] = None) -> None:
        """ Prepare localhost using ansible playbook """
        playbook = self._ansible_playbook_path(playbook)
        stdout, _ = self.run(
            Command(
                'sudo', '-E',
                'ansible-playbook',
                *self._ansible_verbosity(),
                *self._ansible_extra_args(extra_args),
                '-c', 'local',
                '-i', 'localhost,',
                playbook),
            env=self._prepare_environment())
        self._ansible_summary(stdout)

    def execute(self,
                command: Union[Command, ShellScript],
                cwd: Optional[str] = None,
                env: Optional[tmt.utils.EnvironmentType] = None,
                friendly_command: Optional[str] = None,
                test_session: bool = False,
                silent: bool = False,
                log: Optional[BaseLoggerFnType] = None,
                interactive: bool = False,
                **kwargs: Any) -> tmt.utils.CommandOutput:
        """ Execute command on localhost """
        # Prepare the environment (plan/cli variables override)
        environment: tmt.utils.EnvironmentType = dict()
        environment.update(env or {})
        environment.update(self.parent.plan.environment)

        if isinstance(command, Command):
            actual_command = command

        else:
            actual_command = command.to_shell_command()

        if friendly_command is None:
            friendly_command = str(actual_command)

        # Run the command under the prepared environment
        return self.run(actual_command,
                        env=environment,
                        log=log if log else self._command_verbose_logger,
                        friendly_command=friendly_command,
                        silent=silent,
                        cwd=cwd,
                        interactive=interactive,
                        **kwargs)

    def stop(self) -> None:
        """ Stop the guest """

        self.debug(f"Doing nothing to stop guest '{self.guest}'.")

    def reboot(self,
               hard: bool = False,
               command: Optional[Union[Command, ShellScript]] = None,
               timeout: Optional[int] = None) -> bool:
        """ Reboot the guest, return True if successful """

        self.debug(f"Doing nothing to reboot guest '{self.guest}'.")

        return False

    def push(
            self,
            source: Optional[str] = None,
            destination: Optional[str] = None,
            options: Optional[List[str]] = None) -> None:
        """ Nothing to be done to push workdir """

    def pull(
            self,
            source: Optional[str] = None,
            destination: Optional[str] = None,
            options: Optional[List[str]] = None,
            extend_options: Optional[List[str]] = None) -> None:
        """ Nothing to be done to pull workdir """


@tmt.steps.provides_method('local')
class ProvisionLocal(tmt.steps.provision.ProvisionPlugin):
    """
    Use local host for test execution

    In general it is not recommended to run tests on your local machine
    as there might be security risks. Run only those tests which you
    know are safe so that you don't destroy your laptop ;-)

    Example config:

        provision:
            how: local

    Note that 'tmt run' is expected to be executed under a regular user.
    If there are admin rights required (for example in the prepare step)
    you might be asked for a sudo password.
    """

    _data_class = ProvisionLocalData
    _guest_class = GuestLocal

    # Guest instance
    _guest = None

    def go(self) -> None:
        """ Provision the container """
        super().go()

        # Create a GuestLocal instance
        data = tmt.steps.provision.GuestData(
            guest='localhost',
            role=self.get('role')
            )
        self._guest = GuestLocal(logger=self._logger, data=data, name=self.name, parent=self.step)

    def guest(self) -> Optional[GuestLocal]:
        """ Return the provisioned guest """
        return self._guest
