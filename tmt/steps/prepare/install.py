import os
import re
import shutil

import click
import fmf

import tmt

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

    Use 'directory' to install all packages from given folder and
    'exclude' to skip selected packages:

        prepare:
            how: install
            directory: tmp/RPMS/noarch
            exclude: tmt-provision-virtual

    Use 'order' attribute to select in which order preparation should
    happen if there are multiple configs. Default order is '50'.
    Default order of required packages installation is '70'.
    """

    # Supported methods
    _methods = [tmt.steps.Method(name='install', doc=__doc__, order=50)]

    # Supported keys
    _keys = ["package", "directory", "copr", "exclude", "missing"]

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
                '-x', '--exclude', metavar='PACKAGE', multiple=True,
                help='Packages to be skipped during installation.'),
            click.option(
                '-m', '--missing', metavar='ACTION',
                type=click.Choice(['fail', 'skip']),
                help='Action on missing packages, fail (default) or skip.'),
            ] + super().options(how)

    def default(self, option, default=None):
        """ Return default data for given option """
        if option == 'missing':
            return 'fail'
        if option == 'exclude':
            return []
        return default

    def wake(self, keys=None):
        """ Wake up the plugin, process data, apply options """
        super().wake(keys=keys)
        # Convert to list if necessary
        tmt.utils.listify(
            self.data, split=True,
            keys=['package', 'directory', 'copr', 'exclude'])

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

    def prepare_packages(self, package_list, title):
        """ Show package info and return quoted package names """
        # Show a brief summary by default
        if not self.opt('verbose'):
            summary = fmf.utils.listed(package_list, max=3)
            self.info(title, summary, 'green')
        # Provide a full list of packages in verbose mode
        else:
            summary = fmf.utils.listed(package_list, 'package')
            self.info(title, summary + ' requested', 'green')
            for package in sorted(package_list):
                self.verbose(package, shift=1)
        # Return quoted package names
        return " ".join([tmt.utils.quote(package) for package in package_list])

    def go(self, guest):
        """ Prepare the guests """
        super().go(guest)
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

        # Enable copr repositories
        self.enable_copr(command, plugin, guest)

        # Check parameters, bail out if nothing to do
        packages = self.get('package', [])
        repo_packages = []
        local_packages = []
        debuginfo_packages = []
        directories = self.get('directory', [])
        if not packages and not directories:
            self.debug("No packages for installation found.", level=3)
            return

        # Detect local, debuginfo and repository packages
        for package in packages:
            if package.endswith('.rpm'):
                local_packages.append(package)
            elif re.search(r"-debug(info|source)(\.|$)", package):
                # Strip the '-debuginfo' string from package name
                # (installing with it doesn't work on RHEL7)
                package = re.sub(r"-debuginfo((?=\.)|$)", "", package)
                debuginfo_packages.append(package)
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

        # Prepare the install options
        options = '-y'
        for package in self.get('exclude'):
            options += " --exclude " + tmt.utils.quote(package)

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
            guest.execute(f"{command} install {options} {rpms_directory}/*")
            guest.execute(f"{command} reinstall {options} {rpms_directory}/*")
            summary = fmf.utils.listed(local_packages, 'local package')
            self.info('total', f"{summary} installed", 'green')

        # Install from repositories
        if repo_packages:
            packages = self.prepare_packages(repo_packages, title="package")
            # Extra ignore/check for yum to workaround BZ#1920176
            check = f'rpm -q --whatprovides {packages}'
            if 'yum' in command:
                yum_check = " || true" if skip else f" && {check}"
            else:
                yum_check = ""
            # Check and install
            guest.execute(
                f"{check} || {command} install {options} "
                f"{packages}{yum_check}")

        # Install debug{info,source} from repos
        if debuginfo_packages:
            packages = self.prepare_packages(
                debuginfo_packages, title="debuginfo")
            # Make sure debuginfo-install is present on the target system
            guest.execute(f"{command} install -y /usr/bin/debuginfo-install")
            guest.execute(f"debuginfo-install -y {packages}")
