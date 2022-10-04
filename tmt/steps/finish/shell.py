import dataclasses
from typing import List, Optional

import click
import fmf

import tmt
import tmt.steps
import tmt.steps.finish
from tmt.steps.provision import Guest


@dataclasses.dataclass
class FinishShellData(tmt.steps.finish.FinishStepData):
    script: List[str] = dataclasses.field(default_factory=list)

    _normalize_script = tmt.utils.NormalizeKeysMixin._normalize_string_list


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

    @classmethod
    def options(cls, how: Optional[str] = None) -> List[tmt.options.ClickOptionDecoratorType]:
        """ Finish command line options """
        options = super().options(how)
        options[:0] = [
            click.option(
                '-s', '--script', metavar='SCRIPT',
                multiple=True,
                help='Shell script to be executed, can be used multiple times.')
            ]
        return options

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
