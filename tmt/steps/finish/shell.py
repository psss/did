import fmf
import tmt
import click


class FinishShell(tmt.steps.finish.FinishPlugin):
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

    @classmethod
    def options(cls, how=None):
        """ Finish command line options """
        return [
            click.option(
                '-s', '--script', metavar='SCRIPT',
                help='Shell script to be executed.')
            ] + super().options(how)

    def default(self, option, default=None):
        """ Return default data for given option """
        if option == 'script':
            return []
        return default

    def show(self):
        """ Show provided scripts """
        super().show(['script'])

    def wake(self, data=None):
        """ Override options and wake up the guest """
        super().wake(['script'])

        # Convert to list if single script provided
        tmt.utils.listify(self.data, keys=['script'])

    def go(self, guest):
        """ Perform finishing tasks on given guest """
        super().go()

        # Give a short summary
        scripts = self.get('script')
        overview = fmf.utils.listed(scripts, 'script')
        self.info('overview', f'{overview} found', 'green')

        # Execute each script on the guest
        for script in scripts:
            self.verbose('script', script, 'green')
            guest.execute(script, cwd=self.step.workdir)
