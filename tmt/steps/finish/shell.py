import dataclasses
from typing import List

import fmf

import tmt
import tmt.steps
import tmt.steps.finish
import tmt.utils
from tmt.steps.provision import Guest


@dataclasses.dataclass
class FinishShellData(tmt.steps.finish.FinishStepData):
    script: List[str] = tmt.utils.field(
        default_factory=list,
        option=('-s', '--script'),
        multiple=True,
        metavar='SCRIPT',
        help='Shell script to be executed. Can be used multiple times.',
        normalize=tmt.utils.normalize_string_list
        )


@tmt.steps.provides_method('shell')
class FinishShell(tmt.steps.finish.FinishPlugin):
    """
    Perform finishing tasks using shell (bash) scripts

    Example config:

    finish:
        how: shell
        script:
            - upload-logs.sh || true
            - rm -rf /tmp/temporary-files

    Use the 'order' attribute to select in which order finishing tasks
    should happen if there are multiple configs. Default order is '50'.
    """

    _data_class = FinishShellData

    def go(self, guest: Guest) -> None:
        """ Perform finishing tasks on given guest """
        super().go(guest)

        # Give a short summary
        scripts = self.get('script')
        overview = fmf.utils.listed(scripts, 'script')
        self.info('overview', f'{overview} found', 'green')

        # Execute each script on the guest
        for script in scripts:
            self.verbose('script', script, 'green')
            guest.execute(script, cwd=self.step.plan.worktree)
