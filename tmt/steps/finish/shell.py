from typing import Any, List, Optional

import click
import fmf

import tmt
import tmt.steps
import tmt.steps.finish
from tmt.steps.provision import Guest


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

    # Supported keys
    _keys = ["script"]

    @classmethod
    def options(cls, how: Optional[str] = None) -> List[tmt.options.ClickOptionDecoratorType]:
        """ Finish command line options """
        options = super().options(how)
        options[:0] = [
            click.option(
                '-s', '--script', metavar='SCRIPT',
                help='Shell script to be executed.')
            ]
        return options

    def default(self, option: str, default: Optional[Any] = None) -> Any:
        """ Return default data for given option """
        if option == 'script':
            return []
        return default

    # TODO: use better types once superclass gains its annotations
    def wake(self) -> None:
        """ Wake up the plugin, process data, apply options """
        super().wake()

        # Convert to list if single script provided
        tmt.utils.listify(self.data, keys=['script'])

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
