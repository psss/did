import dataclasses
import os.path
import tempfile
from typing import Any, List, Optional, Union, cast

import click
import requests

import tmt
import tmt.steps
import tmt.steps.prepare
import tmt.utils
from tmt.steps.provision import Guest
from tmt.utils import PrepareError, retry_session


class _RawAnsibleStepData(tmt.steps._RawStepData, total=False):
    playbook: Union[str, List[str]]
    playbooks: List[str]


@dataclasses.dataclass
class PrepareAnsibleData(tmt.steps.prepare.PrepareStepData):
    playbook: List[str] = dataclasses.field(default_factory=list)
    extra_args: Optional[str] = None

    # The method violates a liskov substitution principle, but it's fine
    # Thanks to how tmt initializes module, we can assume PrepareAnsibleData.pre_normalization()
    # would be called with source data matching _RawAnsibleStepData
    @classmethod
    def pre_normalization(  # type: ignore[override]
            cls,
            raw_data: _RawAnsibleStepData,
            logger: tmt.utils.Common) -> None:
        super().pre_normalization(raw_data, logger)

        # Perform `playbook` normalization here, so we could merge `playbooks` to it.
        playbook = raw_data.pop('playbook', [])
        raw_data['playbook'] = [playbook] if isinstance(playbook, str) else playbook

        assert isinstance(raw_data['playbook'], list)
        raw_data['playbook'] += raw_data.pop('playbooks', [])


@tmt.steps.provides_method('ansible')
class PrepareAnsible(tmt.steps.prepare.PreparePlugin):
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

    _data_class = PrepareAnsibleData

    # TODO: fix types once superclass gains its annotations
    @classmethod
    def options(cls, how: Optional[str] = None) -> Any:
        """ Prepare command line options """
        return cast(List[tmt.options.ClickOptionDecoratorType], [
            click.option(
                '-p', '--playbook', metavar='PLAYBOOK', multiple=True,
                help='Path or URL of an ansible playbook to run.'),
            click.option(
                '--extra-args', metavar='EXTRA-ARGS',
                help='Optional arguments for ansible-playbook.')
            ]) + super().options(how)

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
