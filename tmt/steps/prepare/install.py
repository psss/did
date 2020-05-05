import fmf
import tmt
import click

class PrepareInstall(tmt.steps.prepare.PreparePlugin):
    """
    Install packages on the guest

    Example config:

    prepare:
        how: install
        copr: psss/tmt
        package: tmt-all

    Use 'order' attribute to select in which order preparation should
    happen if there are multiple configs. Default order is '50'.
    Default order of required packages installation is '70'.
    """

    # Supported methods
    _methods = [tmt.steps.Method(name='install', doc=__doc__, order=50)]

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options """
        return [
            click.option(
                '-p', '--package', metavar='NAME', multiple=True,
                help='Package name to be installed.'),
            click.option(
                '-c', '--copr', metavar='REPO', multiple=True,
                help='Copr repository to be enabled.')
            ] + super().options(how)

    def show(self):
        """ Show provided scripts """
        super().show(['package', 'copr'])

    def wake(self, data=None):
        """ Override options and wake up the guest """
        super().wake(['package', 'copr'])

        # Convert to list if necessary
        tmt.utils.listify(self.data, split=True, keys=['package', 'copr'])

    def go(self, guest):
        """ Prepare the guests """
        super().go()

        # Enable copr repositories
        coprs = self.get('copr')
        if coprs:
            self.debug('Make sure dnf copr plugin is available.')
            guest.execute(
                'rpm -q dnf-plugins-core || '
                'sudo dnf install -y dnf-plugins-core')
            for copr in coprs:
                self.info('copr', copr, 'green')
                guest.execute(f'sudo dnf copr enable -y {copr}')

        # Install packages
        packages = self.get('package')
        if packages:
            self.info('package', fmf.utils.listed(packages, max=3), 'green')
            packages = ' '.join(
                [tmt.utils.quote(package) for package in packages])
            guest.execute(
                f'rpm -q {packages} || sudo dnf install -y {packages}')
