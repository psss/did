from typing import Any, List, Optional, Union

import tmt
import tmt.steps
import tmt.steps.provision


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

    # Guest instance
    _guest = None

    def wake(self, data: Optional[tmt.steps.provision.GuestData] = None) -> None:
        """ Wake up the plugin, process data, apply options """
        super().wake(data=data)
        if data:
            self._guest = GuestLocal(data, name=self.name, parent=self.step)

    def go(self) -> None:
        """ Provision the container """
        super().go()

        # Create a GuestLocal instance
        data = tmt.steps.provision.GuestData(
            guest='localhost',
            role=self.get('role')
            )
        self._guest = GuestLocal(data, name=self.name, parent=self.step)

    def guest(self) -> Optional['GuestLocal']:
        """ Return the provisioned guest """
        return self._guest

    def requires(self) -> List[str]:
        """ List of required packages needed for workdir sync """
        return GuestLocal.requires()


class GuestLocal(tmt.Guest):
    """ Local Host """

    localhost = True
    parent: tmt.steps.Step

    def ansible(self, playbook: str, extra_args: Optional[str] = None) -> None:
        """ Prepare localhost using ansible playbook """
        playbook = self._ansible_playbook_path(playbook)
        stdout, stderr = self.run(
            ['sudo', '-E', 'ansible-playbook'] +
            self._ansible_verbosity() +
            self._ansible_extra_args(extra_args) +
            ['-c', 'local', '-i', 'localhost,', playbook],
            env=self._prepare_environment())
        self._ansible_summary(stdout)

    def execute(self, command: Union[List[str], str], **kwargs: Any) -> tmt.utils.CommandOutput:
        """ Execute command on localhost """
        # Prepare the environment (plan/cli variables override)
        environment = dict()
        environment.update(kwargs.pop('env', dict()))
        environment.update(self.parent.plan.environment)
        # Run the command under the prepared environment
        return self.run(command, env=environment, shell=True, **kwargs)

    def stop(self) -> None:
        """ Stop the guest """

        self.debug(f"Doing nothing to stop guest '{self.guest}'.")

    def reboot(self,
               hard: bool = False,
               command: Optional[str] = None,
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
