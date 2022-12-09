import dataclasses
from typing import Dict, List

import tmt
import tmt.steps
import tmt.steps.prepare
from tmt.steps.provision import Guest
from tmt.utils import ShellScript, field


# Derived from StepData, not PrepareStepData, on purpose: this is not a plugin
# per se, but rather a metadata structure. Other plugins may refer to data
# defined by this "step" by using `where` key in their own data.
@dataclasses.dataclass
class PrepareMultihostData(tmt.steps.prepare.PrepareStepData):
    roles: Dict[str, List[str]] = field(default_factory=dict)
    hosts: Dict[str, str] = field(default_factory=dict)


@tmt.steps.provides_method('multihost')
class PrepareMultihost(tmt.steps.prepare.PreparePlugin):
    """
    Prepare the guest for running a multihost test.

    This step is enabled implicitly, when multiple guests are detected in
    the plan. It exports the information about guest roles and updates
    /etc/hosts accordingly. Default order is '10'.

    This method requires specifying roles and hosts. The expected format is
    the following:

    roles:
      server:
          - server-one
          - server-two

    hosts:
      server-one: 10.10.10.10
      server-two: 10.10.10.11

    The exported roles are comma-separated.
    """

    _data_class = PrepareMultihostData

    def go(self, guest: 'Guest') -> None:
        """ Prepare the guests """
        super().go(guest)

        self.debug('Export roles.', level=2)
        for role, corresponding_guests in self.get('roles').items():
            formatted_guests = ','.join(corresponding_guests)
            self.step.plan._environment[f"TMT_ROLE_{role}"] = formatted_guests
        self.debug("Add hosts to '/etc/hosts'.", level=2)
        for host_name, host_address in self.get('hosts').items():
            if host_address:
                guest.execute(
                    ShellScript(f'echo "{host_address} {host_name}" >> /etc/hosts'),
                    silent=True)
