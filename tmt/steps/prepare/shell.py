import dataclasses
from typing import List, Optional

import click
import fmf

import tmt
import tmt.options
import tmt.steps
import tmt.steps.prepare
import tmt.utils
from tmt.steps.provision import Guest


# TODO: remove `ignore` with follow-imports enablement
@dataclasses.dataclass
class PrepareShellData(tmt.steps.prepare.PrepareStepData):
    script: List[str] = dataclasses.field(default_factory=list)

    _normalize_script = tmt.utils.NormalizeKeysMixin._normalize_string_list


# TODO: drop ignore once type annotations between modules enabled
@tmt.steps.provides_method('shell')
class PrepareShell(tmt.steps.prepare.PreparePlugin):
    """
    Prepare guest using shell (bash) scripts

    Example config:

    prepare:
        how: shell
        script:
        - sudo dnf install -y 'dnf-command(copr)'
        - sudo dnf copr enable -y psss/tmt
        - sudo dnf install -y tmt

    Use 'order' attribute to select in which order preparation should
    happen if there are multiple configs. Default order is '50'.
    Default order of required packages installation is '70'.
    """

    _data_class = PrepareShellData

    @classmethod
    def options(cls, how: Optional[str] = None) -> List[tmt.options.ClickOptionDecoratorType]:
        """ Prepare command line options """
        return [
            click.option(
                '-s', '--script', metavar='SCRIPT',
                multiple=True,
                help='Shell script to be executed, can be used multiple times.')
            ] + super().options(how)

    def go(self, guest: Guest) -> None:
        """ Prepare the guests """
        super().go(guest)

        # Give a short summary
        scripts = self.get('script')
        overview = fmf.utils.listed(scripts, 'script')
        self.info('overview', f'{overview} found', 'green')

        # Execute each script on the guest (with default shell options)
        for script in scripts:
            self.verbose('script', script, 'green')
            script_with_options = f'{tmt.utils.SHELL_OPTIONS}; {script}'
            guest.execute(script_with_options, cwd=self.step.plan.worktree)
