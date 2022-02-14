import os.path
import sys
import tempfile
from typing import Any, List, Optional

import click
import requests

import tmt
import tmt.steps
import tmt.steps.prepare
import tmt.utils
from tmt.steps import Step
from tmt.steps.provision import Guest
from tmt.utils import PrepareError, retry_session

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

StepDataType = TypedDict(
    'StepDataType',
    {
        'playbook': List[str],
        'playbooks': List[str]
        }
    )


@tmt.steps.provides_method('ansible')
class PrepareAnsible(tmt.steps.prepare.PreparePlugin):  # type: ignore[misc]
    """
    Prepare guest using ansible

    Single playbook config:

        prepare:
            how: ansible
            playbook: ansible/packages.yml

    Multiple playbooks config:

        prepare:
            how: ansible
            playbook:
              - playbook/one.yml
              - playbook/two.yml
              - playbook/three.yml
            extra-args: '-vvv'

    Remote playbooks can be referenced as well as local ones, and both
    kinds can be intermixed:

        prepare:
            how: ansible
            playbook:
              - playbook/one.yml
              - https://foo.bar/two.yml
              - playbook/three.yml

    The playbook path should be relative to the metadata tree root.
    Use 'order' attribute to select in which order preparation should
    happen if there are multiple configs. Default order is '50'.
    Default order of required packages installation is '70'.
    """

    # Supported keys
    _keys = ["playbook", "extra-args"]

    def __init__(self, step: Step, data: StepDataType) -> None:
        """ Store plugin name, data and parent step """
        super().__init__(step, data)
        # Rename plural playbooks to singular
        if 'playbooks' in self.data:
            self.data['playbook'] = self.data.pop('playbooks')

    # TODO: fix types once superclass gains its annotations
    @classmethod
    def options(cls, how: Optional[str] = None) -> Any:
        """ Prepare command line options """
        return [
            click.option(
                '-p', '--playbook', metavar='PLAYBOOK', multiple=True,
                help='Path or URL of an ansible playbook to run.'),
            click.option(
                '--extra-args', metavar='EXTRA-ARGS',
                help='Optional arguments for ansible-playbook.')
            ] + super().options(how)

    def default(self, option: str, default: Optional[Any] = None) -> Any:
        """ Return default data for given option """
        if option == 'playbook':
            return []
        return default

    # TODO: use better types once superclass gains its annotations
    def wake(self) -> None:
        """ Wake up the plugin, process data, apply options """
        super().wake()

        # Convert to list if necessary
        tmt.utils.listify(self.data, keys=['playbook'])

    def go(self, guest: Guest) -> None:
        """ Prepare the guests """
        super().go(guest)

        # Apply each playbook on the guest
        for playbook in self.get('playbook'):
            self.info('playbook', playbook, 'green')

            lowercased_playbook = playbook.lower()
            playbook_path = playbook

            if lowercased_playbook.startswith(
                    'http://') or lowercased_playbook.startswith('https://'):
                root_path = self.step.plan.my_run.tree.root

                try:
                    with retry_session() as session:
                        response = session.get(playbook)

                    if not response.ok:
                        raise PrepareError(
                            f"Failed to fetch remote playbook '{playbook}'.")

                except requests.RequestException as exc:
                    raise PrepareError(
                        f"Failed to fetch remote playbook '{playbook}'.", original=exc)

                with tempfile.NamedTemporaryFile(
                        mode='w+b',
                        prefix='playbook-',
                        suffix='.yml',
                        dir=root_path,
                        delete=False) as file:
                    file.write(response.content)
                    file.flush()

                    playbook_path = os.path.relpath(file.name, root_path)

                self.info('playbook-path', playbook_path, 'green')

            guest.ansible(playbook_path, self.get('extra-args'))
