from typing import Any, List, Optional

import click
import fmf

import tmt
import tmt.steps.finish
from tmt.steps.provision import Guest


class FinishShell(tmt.steps.finish.FinishPlugin):  # type: ignore[misc]
    """
    Perform finishing tasks using shell scripts

    Example config:

    finish:
        how: shell
        script:
            - upload-logs.sh || true
            - rm -rf /tmp/temporary-files

    Use the 'order' attribute to select in which order finishing tasks
    should happen if there are multiple configs. Default order is '50'.
    """

    # Supported methods
    _methods = [tmt.steps.Method(name='shell', doc=__doc__, order=50)]

    # Supported keys
    _keys = ["script"]

    @classmethod
    def options(cls, how: Optional[str] = None) -> Any:
        """ Finish command line options """
        return [
            click.option(
                '-s', '--script', metavar='SCRIPT',
                help='Shell script to be executed.')
            ] + super().options(how)

    def default(self, option: str, default: Optional[Any] = None) -> Any:
        """ Return default data for given option """
        if option == 'script':
            return []
        return default

    # TODO: use better types once superclass gains its annotations
    def wake(self, keys: Optional[List[str]] = None) -> None:
        """ Wake up the plugin, process data, apply options """
        super().wake(keys=keys)

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
