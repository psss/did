import os
import re
import shutil

import click
import fmf

import tmt
import tmt.steps.prepare

COPR_URL = 'https://copr.fedorainfracloud.org/coprs'


class InstallBase(tmt.utils.Common):
    """ Base class for installation implementations """

    # Each installer knows its package manager and copr plugin
    package_manager = None
    copr_plugin = None

    def __init__(self, parent, guest):
        """ Initialize installation data """
        super().__init__(parent=parent, relative_indent=0)
        self.guest = guest

        # Get package related data from the plugin
        self.packages = self.parent.get("package", [])
        self.directories = self.parent.get("directory", [])
        self.exclude = self.parent.get("exclude", [])
        if not self.packages and not self.directories:
            self.debug("No packages for installation found.", level=3)

        # Prepare package lists and installation command
        self.prepare_packages()
        self.prepare_sudo()
        self.prepare_command()

    def prepare_packages(self):
        """ Process package names and directories """
        self.local_packages = []
        self.debuginfo_packages = []
        self.repository_packages = []

        # Detect local, debuginfo and repository packages
        for package in self.packages:
            if package.endswith('.rpm'):
                self.local_packages.append(package)
            elif re.search(r"-debug(info|source)(\.|$)", package):
                # Strip the '-debuginfo' string from package name
                # (installing with it doesn't work on RHEL7)
                package = re.sub(r"-debuginfo((?=\.)|$)", "", package)
                self.debuginfo_packages.append(package)
            else:
                self.repository_packages.append(package)

        # Check rpm packages in local directories
        for directory in self.directories:
            self.info('directory', directory, 'green')
            if not os.path.isdir(directory):
                raise tmt.utils.PrepareError(f"Packages directory '{directory}' not found.")
            for filename in os.listdir(directory):
                if filename.endswith('.rpm'):
                    self.debug(f"Found rpm '{filename}'.", level=3)
                    self.local_packages.append(os.path.join(directory, filename))

    def prepare_sudo(self):
        """ Check if sudo is needed for installation """
        self.debug('Check if sudo is necessary.', level=2)
        user = self.guest.execute('whoami')[0].strip()
        self.sudo = '' if user == 'root' else 'sudo '

    def prepare_command(self):
        """ Prepare installation command"""
        raise NotImplementedError

    def prepare_repository(self, **kwargs):
        """ Configure additional repository """
        raise NotImplementedError

    def list_packages(self, package_list, title):
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

    def enable_copr_epel6(self, copr):
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
            self.guest.execute(f'curl -LOf {url}', cwd='/etc/yum.repos.d')
        except tmt.utils.RunError as error:
            if 'not found' in error.stderr.lower():
                raise tmt.utils.PrepareError(
                    f"Copr repository '{copr}' not found.")
            raise

    def enable_copr(self):
        """ Enable requested copr repositories """
        coprs = self.parent.get('copr')
        if not coprs:
            return
        # Try to install copr plugin
        self.debug('Make sure the copr plugin is available.')
        try:
            self.guest.execute(
                f'rpm -q {self.copr_plugin} || {self.command} install -y {self.copr_plugin}')
        # Enable repositories manually for epel6
        except tmt.utils.RunError:
            for copr in coprs:
                self.info('copr', copr, 'green')
                self.enable_copr_epel6(copr)
        # Enable repositories using copr plugin
        else:
            for copr in coprs:
                self.info('copr', copr, 'green')
                self.guest.execute(f'{self.command} copr enable -y {copr}')

    def prepare_install_local(self):
        """ Copy packages to the test system """
        self.rpms_directory = os.path.join(self.parent.step.workdir, 'rpms')
        os.makedirs(self.rpms_directory)

        # Copy local packages into workdir, push to guests
        for package in self.local_packages:
            self.verbose(os.path.basename(package), shift=1)
            self.debug(f"Copy '{package}' to '{self.rpms_directory}'.", level=3)
            shutil.copy(package, self.rpms_directory)
        self.guest.push()

    def install_from_repository(self):
        """ Default base install method for packages from repositories """
        pass

    def install_local(self):
        """ Default base install method for local packages """
        pass

    def install_debuginfo(self):
        """ Default base install method for debuginfo packages """
        pass

    def install(self):
        """ Perform the actual installation """
        if self.local_packages:
            self.prepare_install_local()
            self.install_local()
        if self.repository_packages:
            self.install_from_repository()
        if self.debuginfo_packages:
            self.install_debuginfo()


class InstallDnf(InstallBase):
    """ Install packages using dnf """

    package_manager = "dnf"
    copr_plugin = "dnf-plugins-core"

    def prepare_command(self):
        """ Prepare installation command """
        self.options = '-y'
        self.skip = ' --skip-broken' if self.parent.get('missing') == 'skip' else ''
        for package in self.exclude:
            self.options += " --exclude " + tmt.utils.quote(package)

        self.command = f"{self.sudo}{self.package_manager}{self.skip}"
        self.debug(f"Using '{self.command}' for all package operations.")
        self.debug(f"Options for package operations are '{self.options}'")

    def install_local(self):
        """ Install copied local packages """
        # Use both dnf install/reinstall to get all packages refreshed
        # FIXME Simplify this once BZ#1831022 is fixed/implemeted.
        self.guest.execute(f"{self.command} install {self.options} {self.rpms_directory}/*")
        self.guest.execute(f"{self.command} reinstall {self.options} {self.rpms_directory}/*")
        summary = fmf.utils.listed(self.local_packages, 'local package')
        self.info('total', f"{summary} installed", 'green')

    def install_from_repository(self):
        """ Install packages from the repository """
        packages = self.list_packages(self.repository_packages, title="package")
        check = f'rpm -q --whatprovides {packages}'
        # Check and install
        self.guest.execute(f"{check} || {self.command} install {self.options} {packages}")

    def install_debuginfo(self):
        """ Install debuginfo packages """
        packages = self.list_packages(self.debuginfo_packages, title="debuginfo")
        # Make sure debuginfo-install is present on the target system
        self.guest.execute(f"{self.command} install -y /usr/bin/debuginfo-install")
        self.guest.execute(f"debuginfo-install -y {packages}")


class InstallYum(InstallDnf):
    """ Install packages using yum """

    package_manager = "yum"
    copr_plugin = "yum-plugin-copr"

    def install_from_repository(self):
        """ Install packages from the repository """
        packages = self.list_packages(self.repository_packages, title="package")
        # Extra ignore/check for yum to workaround BZ#1920176
        check = f'rpm -q --whatprovides {packages}'
        final_check = " || true" if self.skip else f" && {check}"
        # Check and install
        self.guest.execute(
            f"{check} || {self.command} install {self.options} {packages}{final_check}")


class InstallRpmOstree(InstallBase):
    """ Install packages using rpm-ostree """

    package_manager = "rpm-ostree"
    copr_plugin = "dnf-plugins-core"

    def sort_packages(self):
        """ Identify required and recommended packages """
        self.recommended_packages = []
        self.required_packages = []
        for package in self.repository_packages:
            try:
                output = self.guest.execute(f"rpm -q --whatprovides '{package}'")
                self.debug(f"Package '{output.stdout.strip()}' already installed.")
            except tmt.utils.RunError:
                if self.skip:
                    self.recommended_packages.append(package)
                else:
                    self.required_packages.append(package)

    def prepare_command(self):
        """ Prepare installation command for rpm-ostree"""
        self.skip = True if self.parent.get('missing') == 'skip' else False
        self.command = f"{self.sudo}rpm-ostree"
        self.options = '--apply-live --idempotent --allow-inactive'
        for package in self.exclude:
            # exclude not supported in rpm-ostree
            self.warn(f"there is no support for rpm-ostree exclude. "
                      f"Package '{package}' may still be installed.")
        self.debug(f"Using '{self.command}' for all package operations.")
        self.debug(f"Options for package operations are '{self.options}'.")

    def install_debuginfo(self):
        """ Install debuginfo packages """
        self.warn("Installation of debuginfo packages not supported yet.")

    def install_local(self):
        """ Install copied local packages """
        local_packages_installed = []
        for package in self.local_packages:
            try:
                self.guest.execute(
                    f"{self.command} install {self.options} "
                    f"{self.rpms_directory}/{os.path.basename(package)}")
                local_packages_installed.append(package)
            except tmt.utils.RunError as error:
                self.warn(f"Local package '{package}' not installed: {error.stderr}")
        summary = fmf.utils.listed(local_packages_installed, 'local package')
        self.info('total', f"{summary} installed", 'green')

    def install_from_repository(self):
        """ Install packages from the repository """
        self.sort_packages()

        # Install recommended packages
        if self.recommended_packages:
            self.list_packages(self.recommended_packages, title="package")
            for package in self.recommended_packages:
                try:
                    self.guest.execute(f"{self.command} install {self.options} '{package}'")
                except tmt.utils.RunError as error:
                    if "error: Packages not found" in error.stderr and self.skip:
                        self.warn(f"No match for recommended package '{package}'.")
                        continue
                    raise

        # Install required packages
        if self.required_packages:
            packages = self.list_packages(self.required_packages, title="package")
            self.guest.execute(f"{self.command} install {self.options} {packages}")


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

    Note: When testing ostree booted deployments tmt will use
    `rpm-ostree` as the package manager to perform the installation of
    requested packages. The current limitations of the rpm-ostree
    implementation are:

        Cannot install new version of already installed local rpm.
        No support for installing debuginfo packages at this time.
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

    def go(self, guest):
        """ Perform preparation for the guests"""
        super().go(guest)

        # Nothing to do in dry mode
        if self.opt('dry'):
            return

        # Pick the right implementation
        try:
            guest.execute('stat /run/ostree-booted')
            installer = InstallRpmOstree(parent=self, guest=guest)
        except tmt.utils.RunError:
            try:
                guest.execute('rpm -q dnf')
                installer = InstallDnf(parent=self, guest=guest)
            except tmt.utils.RunError:
                installer = InstallYum(parent=self, guest=guest)

        # Enable copr repositories and install packages
        installer.enable_copr()
        installer.install()
