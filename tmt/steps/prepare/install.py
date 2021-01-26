import os
import re
import fmf
import tmt
import click
import shutil

COPR_URL = 'https://copr.fedorainfracloud.org/coprs'

class PrepareInstall(tmt.steps.prepare.PreparePlugin):
    """
    Install packages on the guest

    Example config:

        prepare:
            how: install
            copr: psss/tmt
            package: tmt-all
            missing: fail

    Use 'copr' for enabling desired copr repository and 'missing' to
    choose if missing packages should be silently ignored (skip) or a
    preparation error should be reported (fail), which is the default.

    In addition to package name you can also use one or more paths to
    local rpm files to be installed:

        prepare:
            how: install
            package:
                - tmp/RPMS/noarch/tmt-0.15-1.fc31.noarch.rpm
                - tmp/RPMS/noarch/python3-tmt-0.15-1.fc31.noarch.rpm

    Use 'directory' to install all packages from given folder:

        prepare:
            how: install
            directory: tmp/RPMS/noarch

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
                '-p', '--package', metavar='PACKAGE', multiple=True,
                help='Package name or path to rpm to be installed.'),
            click.option(
                '-D', '--directory', metavar='PATH', multiple=True,
                help='Path to a local directory with rpm packages.'),
            click.option(
                '-c', '--copr', metavar='REPO', multiple=True,
                help='Copr repository to be enabled.'),
            click.option(
                '-m', '--missing', metavar='ACTION',
                type=click.Choice(['fail', 'skip']),
                help='Action on missing packages, fail (default) or skip.'),
            ] + super().options(how)

    def default(self, option, default=None):
        """ Return default data for given option """
        if option == 'missing':
            return 'fail'
        return default

    def show(self):
        """ Show provided scripts """
        super().show(['package', 'directory', 'copr', 'missing'])

    def wake(self, data=None):
        """ Override options and wake up the guest """
        super().wake(['package', 'directory', 'copr', 'missing'])

        # Convert to list if necessary
        tmt.utils.listify(
            self.data, split=True, keys=['package', 'directory', 'copr'])

    def enable_copr_epel6(self, copr, guest):
        """ Manually enable copr repositories for epel6 """
        # Parse the copr repo name
        matched = re.match("^(@)?([^/]+)/([^/]+)$", copr)
        if not matched:
            raise tmt.utils.PrepareError(f"Invalid copr repository '{copr}'.")
        group, name, project = matched.groups()
        group = 'group_' if group else ''
        # Prepare the repo file url
        parts = [COPR_URL] + (['g'] if group else [])
        parts += [name, project, 'repo', 'epel-6']
        parts += [f"{group}{name}-{project}-epel-6.repo"]
        url = '/'.join(parts)
        # Download the repo file on guest
        try:
            guest.execute(f'curl -LOf {url}', cwd='/etc/yum.repos.d')
        except tmt.utils.RunError as error:
            if 'not found' in error.stderr.lower():
                raise tmt.utils.PrepareError(
                    f"Copr repository '{copr}' not found.")
            raise

    def enable_copr(self, command, plugin, guest):
        """ Enable requested copr repositories """
        coprs = self.get('copr')
        if not coprs:
            return
        # Try to install copr plugin
        self.debug('Make sure the copr plugin is available.')
        try:
            guest.execute(f'rpm -q {plugin} || {command} install -y {plugin}')
        # Enable repositories manually for epel6
        except tmt.utils.RunError:
            for copr in coprs:
                self.info('copr', copr, 'green')
                self.enable_copr_epel6(copr, guest)
        # Enable repositories using copr plugin
        else:
            for copr in coprs:
                self.info('copr', copr, 'green')
                guest.execute(f'{command} copr enable -y {copr}')

    def go(self, guest):
        """ Prepare the guests """
        super().go()
        # Nothing to do in dry mode
        if self.opt('dry'):
            return

        # Prepare the right dnf/yum command
        self.debug('Check if sudo is necessary.', level=2)
        user = guest.execute('whoami')[0].strip()
        sudo = '' if user == 'root' else 'sudo '
        self.debug('Check if dnf is available.', level=2)
        skip = ' --skip-broken' if self.get('missing') == 'skip' else ''
        try:
            guest.execute('rpm -q dnf')
            command = f"{sudo}dnf{skip}"
            plugin = 'dnf-plugins-core'
        except tmt.utils.RunError:
            command = f"{sudo}yum{skip}"
            plugin = 'yum-plugin-copr'
        self.debug(f"Using '{command}' for all package operations.")

        # Check parameters, bail out if nothing to do
        packages = self.get('package', [])
        repo_packages = []
        local_packages = []
        directories = self.get('directory', [])
        if not packages and not directories:
            self.debug("No packages for installation found.", level=3)
            return

        # Enable copr repositories
        self.enable_copr(command, plugin, guest)

        # Detect local packages and directories
        for package in packages:
            if package.endswith('.rpm'):
                local_packages.append(package)
            else:
                repo_packages.append(package)

        # Check rpm packages in local directories
        for directory in directories:
            self.info('directory', directory, 'green')
            if not os.path.isdir(directory):
                raise tmt.utils.PrepareError(
                    f"Packages directory '{directory}' not found.")
            for filename in os.listdir(directory):
                if filename.endswith('.rpm'):
                    self.debug(f"Found rpm '{filename}'.", level=3)
                    local_packages.append(os.path.join(directory, filename))

        # Install from local filesystem
        if local_packages:
            rpms_directory = os.path.join(self.step.workdir, 'rpms')
            os.makedirs(rpms_directory)

            # Copy local packages into workdir, push to guests
            for package in local_packages:
                self.verbose(os.path.basename(package), shift=1)
                self.debug(f"Copy '{package}' to '{rpms_directory}'.", level=3)
                shutil.copy(package, rpms_directory)
            for guest in self.step.plan.provision.guests():
                guest.push()

            # Use both dnf install/reinstall to get all packages refreshed
            # FIXME Simplify this once BZ#1831022 is fixed/implemeted.
            guest.execute(f"{command} install -y {rpms_directory}/*")
            guest.execute(f"{command} reinstall -y {rpms_directory}/*")
            summary = fmf.utils.listed(local_packages, 'local package')
            self.info('total', f"{summary} installed", 'green')

        # Install from repositories
        if repo_packages:
            # Show a brief summary by default
            if not self.opt('verbose'):
                summary = fmf.utils.listed(repo_packages, max=3)
                self.info('package', summary, 'green')
            # Provide a full list of packages in verbose mode
            else:
                summary = fmf.utils.listed(repo_packages, 'package')
                self.info('package', summary + ' requested', 'green')
                for package in sorted(repo_packages):
                    self.verbose(package, shift=1)
            # Quote package names and prepare the rpm check
            packages = ' '.join(
                [tmt.utils.quote(package) for package in repo_packages])
            check = f'rpm -q --whatprovides {packages}'
            # Check and install (extra check for yum to workaround BZ#1920176)
            guest.execute(
                f'{check} || {command} install -y {packages}' +
                (f' && {check}' if 'yum' in command else ''))
