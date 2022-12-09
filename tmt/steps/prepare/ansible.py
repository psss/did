import dataclasses
import os.path
import tempfile
from typing import List, Optional, Union

import requests

import tmt
import tmt.log
import tmt.options
import tmt.steps
import tmt.steps.prepare
import tmt.utils
from tmt.steps.provision import Guest
from tmt.utils import PrepareError, field, retry_session


class _RawAnsibleStepData(tmt.steps._RawStepData, total=False):
    playbook: Union[str, List[str]]
    playbooks: List[str]


@dataclasses.dataclass
class PrepareAnsibleData(tmt.steps.prepare.PrepareStepData):
    playbook: List[str] = field(
        default_factory=list,
        option=('-p', '--playbook'),
        multiple=True,
        metavar='PLAYBOOK',
        help='Path or URL of an ansible playbook to run.',
        normalize=tmt.utils.normalize_string_list
        )

    extra_args: Optional[str] = field(
        default=None,
        option='--extra-args',
        metavar='EXTRA-ARGS',
        help='Optional arguments for ansible-playbook.'
        )

    # ignore[override]: method violates a liskov substitution principle,
    # but only apparently.  Thanks to how tmt initializes module, we can
    # safely assume PrepareAnsibleData.pre_normalization() would be
    # called with source data matching _RawAnsibleStepData.
    @classmethod
    def pre_normalization(  # type: ignore[override]
            cls,
            raw_data: _RawAnsibleStepData,
            logger: tmt.log.Logger) -> None:
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
                assert self.step.plan.my_run is not None  # narrow type
                assert self.step.plan.my_run.tree is not None  # narrow type
                root_path = self.step.plan.my_run.tree.root

                try:
                    with retry_session() as session:
                        response = session.get(playbook)

                    if not response.ok:
                        raise PrepareError(
                            f"Failed to fetch remote playbook '{playbook}'.")

                except requests.RequestException as exc:
                    raise PrepareError(
                        f"Failed to fetch remote playbook '{playbook}'.") from exc

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
