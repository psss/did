from typing import Any, Optional

import tmt
import tmt.steps.prepare
from tmt.steps import Method
from tmt.steps.provision import Guest


class PrepareMultihost(tmt.steps.prepare.PreparePlugin):  # type: ignore[misc]
    """
    Prepare the guest for running a multihost test.

    This step is enabled implicitly, when multiple guests are detected in
    the plan. It exports the information about guest roles and updates
    /etc/hosts accordingly. Default order is '10'.

    This method requires specifying roles and hosts. The expected format is
    the following:

    roles:
      - server:
          - server-one
          - server-two

    hosts:
      - server-one: 10.10.10.10
      - server-two: 10.10.10.11

    The exported roles are comma-separated.
    """

    # Supported methods
    _methods = [Method(name='multihost', doc=__doc__, order=50)]

    # Supported keys
    _keys = ['roles', 'hosts']

    def default(self, option: str, default: Optional[Any] = None) -> Any:
        """ Return default data for given option """
        if option in ('roles', 'hosts'):
            return {}
        return default

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
                    f'echo "{host_address} {host_name}" >> /etc/hosts')
