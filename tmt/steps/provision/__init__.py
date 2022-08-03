import collections
import dataclasses
import datetime
import os
import random
import re
import shlex
import string
import subprocess
import tempfile
import time
from shlex import quote
from typing import Dict, List, Optional, Type

import click
import fmf

import tmt
import tmt.steps
import tmt.utils
from tmt.steps import Action

# Timeout in seconds of waiting for a connection after reboot
CONNECTION_TIMEOUT = 5 * 60

# Default rsync options
DEFAULT_RSYNC_OPTIONS = [
    "-R", "-r", "-z", "--links", "--safe-links", "--delete"]


class Provision(tmt.steps.Step):
    """ Provision an environment for testing or use localhost. """

    # Default implementation for provision is a virtual machine
    how = 'virtual'

    def __init__(self, plan, data):
        """ Initialize provision step data """
        super().__init__(plan=plan, data=data)
        # Check that the names are unique
        names = [data.get('name') for data in self.data]
        names_count = collections.defaultdict(int)
        for name in names:
            names_count[name] += 1
        if len(self.data) > 1 and len(self.data) != len(names_count):
            duplicate = [k for k, v in names_count.items() if v > 1]
            duplicate_string = ', '.join(duplicate)
            raise tmt.utils.GeneralError(
                f"Provision step names must be unique for multihost testing. "
                f"Duplicate names: {duplicate_string} in plan '{plan.name}'.")
        # List of provisioned guests and loaded guest data
        self._guests: List['Guest'] = []
        self._guest_data: Dict[str, 'GuestData'] = {}
        self.is_multihost = False

    def load(self, extra_keys=None):
        """ Load guest data from the workdir """
        extra_keys = extra_keys or []
        super().load(extra_keys)
        try:
            raw_guest_data = tmt.utils.yaml_to_dict(self.read('guests.yaml'))

            self._guest_data = {
                name: tmt.utils.SerializableContainer.unserialize(guest_data)
                for name, guest_data in raw_guest_data.items()
                }

        except tmt.utils.FileError:
            self.debug('Provisioned guests not found.', level=2)

    def save(self, data=None):
        """ Save guest data to the workdir """
        data = data or {}
        super().save(data)
        try:
            raw_guest_data = {guest.name: guest.save().to_serialized()
                              for guest in self.guests()}

            self.write('guests.yaml', tmt.utils.dict_to_yaml(raw_guest_data))
        except tmt.utils.FileError:
            self.debug('Failed to save provisioned guests.')

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        super().wake()

        # Choose the right plugin and wake it up
        for data in self.data:
            plugin = ProvisionPlugin.delegate(self, data)
            self._phases.append(plugin)
            # If guest data loaded, perform a complete wake up
            plugin.wake(data=self._guest_data.get(plugin.name))
            if plugin.guest():
                self._guests.append(plugin.guest())

        # Nothing more to do if already done
        if self.status() == 'done':
            self.debug(
                'Provision wake up complete (already done before).', level=2)
        # Save status and step data (now we know what to do)
        else:
            self.status('todo')
            self.save()

    def show(self):
        """ Show discover details """
        for data in self.data:
            ProvisionPlugin.delegate(self, data).show()

    def summary(self):
        """ Give a concise summary of the provisioning """
        # Summary of provisioned guests
        guests = fmf.utils.listed(self.guests(), 'guest')
        self.info('summary', f'{guests} provisioned', 'green', shift=1)
        # Guest list in verbose mode
        for guest in self.guests():
            if guest.name != tmt.utils.DEFAULT_NAME:
                self.verbose(guest.name, color='red', shift=2)

    def go(self):
        """ Provision all guests"""
        super().go()

        # Nothing more to do if already done
        if self.status() == 'done':
            self.info('status', 'done', 'green', shift=1)
            self.summary()
            self.actions()
            return

        # Provision guests
        self._guests = []
        save = True
        self.is_multihost = sum([isinstance(phase, ProvisionPlugin)
                                for phase in self.phases()]) > 1
        try:
            for phase in self.phases(classes=(Action, ProvisionPlugin)):
                try:
                    phase.go()
                    if isinstance(phase, ProvisionPlugin):
                        phase.guest().details()
                    if self.is_multihost:
                        self.info('')
                finally:
                    if isinstance(phase, ProvisionPlugin):
                        if phase.guest():
                            self._guests.append(phase.guest())

            # Give a summary, update status and save
            self.summary()
            self.status('done')
        except (SystemExit, tmt.utils.SpecificationError) as error:
            # A plugin will only raise SystemExit if the exit is really desired
            # and no other actions should be done. An example of this is
            # listing available images. In such case, the workdir is deleted
            # as it's redundant and save() would throw an error.
            save = False
            raise error
        finally:
            if save:
                self.save()

    def guests(self) -> List['Guest']:
        """ Return the list of all provisioned guests """
        return self._guests

    def requires(self):
        """
        Packages required by all enabled provision plugins

        Return a list of packages which need to be installed on the
        provisioned guest so that the workdir can be synced to it.
        Used by the prepare step.
        """
        requires = set()
        for plugin in self.phases(classes=ProvisionPlugin):
            requires.update(plugin.requires())
        return list(requires)


class ProvisionPlugin(tmt.steps.GuestlessPlugin):
    """ Common parent of provision plugins """

    # Default implementation for provision is a virtual machine
    how = 'virtual'

    # List of all supported methods aggregated from all plugins
    _supported_methods = []

    # Common keys for all provision step implementations
    _common_keys = ['role']

    @classmethod
    def base_command(
            cls,
            usage: str,
            method_class: Optional[Type[click.Command]] = None) -> click.Command:
        """ Create base click command (common for all provision plugins) """

        # Prepare general usage message for the step
        if method_class:
            usage = Provision.usage(method_overview=usage)

        # Create the command
        @click.command(cls=method_class, help=usage)
        @click.pass_context
        @click.option(
            '-h', '--how', metavar='METHOD',
            help='Use specified method for provisioning.')
        def provision(context, **kwargs):
            context.obj.steps.add('provision')
            Provision._save_context(context)

        return provision

    def wake(self, keys=None, data=None):
        """
        Wake up the plugin

        Override data with command line options.
        Wake up the guest based on provided guest data.
        """
        super().wake(keys=keys)

    def guest(self):
        """
        Return provisioned guest

        Each ProvisionPlugin has to implement this method.
        Should return a provisioned Guest() instance.
        """
        raise NotImplementedError()

    def requires(self):
        """ List of required packages needed for workdir sync """
        return Guest.requires()

    @classmethod
    def clean_images(cls, clean, dry):
        """ Remove the images of one particular plugin """


@dataclasses.dataclass
class GuestData(tmt.utils.SerializableContainer):
    """
    Keys necessary to describe, create, save and restore a guest.

    Very basic set of keys shared across all known guest classes.
    """

    # guest role in the multihost scenario
    role: Optional[str] = None
    # hostname or ip address
    guest: Optional[str] = None


class Guest(tmt.utils.Common):
    """
    Guest provisioned for test execution

    A base class for guest-like classes. Provides some of the basic methods
    and functionality, but note some of the methods are left intentionally
    empty. These do not have valid implementation on this level, and it's up
    to Guest subclasses to provide one working in their respective
    infrastructure.

    The following keys are expected in the 'data' container::

        role ....... guest role in the multihost scenario
        guest ...... name, hostname or ip address

    These are by default imported into instance attributes.
    """

    # Used by save() to construct the correct container for keys.
    _data_class = GuestData

    role: Optional[str]
    guest: Optional[str]

    # Flag to indicate localhost guest, requires special handling
    localhost = False

    # TODO: do we need this list? Can whatever code is using it use _data_class directly?
    # List of supported keys
    # (used for import/export to/from attributes during load and save)
    @property
    def _keys(self) -> List[str]:
        return list(self._data_class.keys())

    def __init__(self, data: GuestData, name=None, parent=None):
        """ Initialize guest data """
        super().__init__(parent, name)

        self.load(data)

    def _random_name(self, prefix='', length=16):
        """ Generate a random name """
        # Append at least 5 random characters
        min_random_part = max(5, length - len(prefix))
        name = prefix + ''.join(
            random.choices(string.ascii_letters, k=min_random_part))
        # Return tail (containing random characters) of name
        return name[-length:]

    def _tmt_name(self):
        """ Generate a name prefixed with tmt run id """
        _, run_id = os.path.split(self.parent.plan.my_run.workdir)
        return self._random_name(prefix="tmt-{0}-".format(run_id[-3:]))

    def load(self, data: GuestData) -> None:
        """
        Load guest data into object attributes for easy access

        Called during guest object initialization. Takes care of storing
        all supported keys (see class attribute _keys for the list) from
        provided data to the guest object attributes. Child classes can
        extend it to make additional guest attributes easily available.

        Data dictionary can contain guest information from both command
        line options / L2 metadata / user configuration and wake up data
        stored by the save() method below.
        """
        data.inject_to(self)

    def save(self) -> GuestData:
        """
        Save guest data for future wake up

        Export all essential guest data into a dictionary which will be
        stored in the `guests.yaml` file for possible future wake up of
        the guest. Everything needed to attach to a running instance
        should be added into the data dictionary by child classes.
        """
        return self._data_class.extract_from(self)

    def wake(self):
        """
        Wake up the guest

        Perform any actions necessary after step wake up to be able to
        attach to a running guest instance and execute commands. Called
        after load() is completed so all guest data should be prepared.
        """
        self.debug(f"Doing nothing to wake up guest '{self.guest}'.")

    def start(self):
        """
        Start the guest

        Get a new guest instance running. This should include preparing
        any configuration necessary to get it started. Called after
        load() is completed so all guest data should be available.
        """
        self.debug(f"Doing nothing to start guest '{self.guest}'.")

    def details(self):
        """ Show guest details such as distro and kernel """
        # Skip distro & kernel check in dry mode
        if self.opt('dry'):
            return

        # Distro (check os-release first)
        try:
            distro = self.execute('cat /etc/os-release')[0].strip()
            distro = re.search('PRETTY_NAME="(.*)"', distro).group(1)
        except (tmt.utils.RunError, AttributeError):
            # Check for lsb-release
            try:
                distro = self.execute('cat /etc/lsb-release')[0].strip()
                distro = re.search(
                    'DISTRIB_DESCRIPTION="(.*)"', distro).group(1)
            except (tmt.utils.RunError, AttributeError):
                # Check for redhat-release
                try:
                    distro = self.execute('cat /etc/redhat-release')[0].strip()
                except (tmt.utils.RunError, AttributeError):
                    distro = None

        # Handle standard cloud images message when connecting
        if distro is not None and 'Please login as the user' in distro:
            raise tmt.utils.GeneralError(
                f'Login to the guest failed.\n{distro}')

        if distro:
            self.info('distro', distro, 'green')

        # Kernel
        kernel = self.execute('uname -r')[0].strip()
        self.verbose('kernel', kernel, 'green')

    def _ansible_verbosity(self):
        """ Prepare verbose level based on the --debug option count """
        if self.opt('debug') < 3:
            return []
        else:
            return ['-' + (self.opt('debug') - 2) * 'v']

    @staticmethod
    def _ansible_extra_args(extra_args):
        """ Prepare extra arguments for ansible-playbook"""
        if extra_args is None:
            return []
        else:
            return shlex.split(str(extra_args))

    def _ansible_summary(self, output):
        """ Check the output for ansible result summary numbers """
        if not output:
            return
        keys = 'ok changed unreachable failed skipped rescued ignored'.split()
        for key in keys:
            matched = re.search(rf'^.*\s:\s.*{key}=(\d+).*$', output, re.M)
            if matched and int(matched.group(1)) > 0:
                tasks = fmf.utils.listed(matched.group(1), 'task')
                self.verbose(key, tasks, 'green')

    def _ansible_playbook_path(self, playbook):
        """ Prepare full ansible playbook path """
        # Playbook paths should be relative to the metadata tree root
        self.debug(f"Applying playbook '{playbook}' on guest '{self.guest}'.")
        playbook = os.path.join(self.parent.plan.my_run.tree.root, playbook)
        self.debug(f"Playbook full path: '{playbook}'", level=2)
        return playbook

    def _prepare_environment(self, execute_environment=None):
        """ Prepare dict of environment variables """
        # Prepare environment variables so they can be correctly passed
        # to shell. Create a copy to prevent modifying source.
        environment = dict()
        environment.update(execute_environment or dict())
        # Plan environment and variables provided on the command line
        # override environment provided to execute().
        environment.update(self.parent.plan.environment)
        return environment

    @staticmethod
    def _export_environment(environment):
        """ Prepare shell export of environment variables """
        if not environment:
            return ""
        return f'export {" ".join(tmt.utils.shell_variables(environment))}; '

    def ansible(self, playbook, extra_args=None):
        """ Prepare guest using ansible playbook """

        raise NotImplementedError()

    def execute(self, command, **kwargs):
        """
        Execute command on the guest

        command ... string or list of command arguments (required)
        env ....... dictionary with environment variables
        cwd ....... working directory to be entered before execution

        If the command is provided as a list, it will be space-joined.
        If necessary, quote escaping has to be handled by the caller.
        """

        raise NotImplementedError()

    def push(self, source=None, destination=None, options=None):
        """
        Push files to the guest
        """

        raise NotImplementedError()

    def pull(
            self,
            source=None,
            destination=None,
            options=None,
            extend_options=None):
        """
        Pull files from the guest
        """

        raise NotImplementedError()

    def stop(self):
        """
        Stop the guest

        Shut down a running guest instance so that it does not consume
        any memory or cpu resources. If needed, perform any actions
        necessary to store the instance status to disk.
        """

        raise NotImplementedError()

    def reboot(self, hard=False, command=None, timeout=None):
        """
        Reboot the guest, return True if successful

        Parameter 'hard' set to True means that guest should be
        rebooted by way which is not clean in sense that data can be
        lost. When set to False reboot should be done gracefully.

        Use the 'command' parameter to specify a custom reboot command
        instead of the default 'reboot'.

        Parameter 'timeout' can be used to specify time (in seconds) to
        wait for the guest to come back up after rebooting.
        """

        raise NotImplementedError()

    def reconnect(self, timeout=None):
        """
        Ensure the connection to the guest is working

        The default timeout is 5 minutes. Custom number of seconds can be
        provided in the `timeout` parameter. This may be useful when long
        operations (such as system upgrade) are performed.
        """
        # The default is handled here rather than in the argument so that
        # the caller can pass in None as an argument (i.e. don't care value)
        timeout = timeout or CONNECTION_TIMEOUT
        self.debug("Wait for a connection to the guest.")

        # A small shortcut... `now` or `utcnow`, should not matter, becase we
        # need a difference between two values. As long as we use the same
        # function for both sides of the equation, we should be fine.
        now = datetime.datetime.utcnow
        deadline = now() + datetime.timedelta(seconds=timeout)
        while now() < deadline:
            try:
                self.execute('whoami')
                break
            except tmt.utils.RunError:
                self.debug('Failed to connect to the guest, retrying.')
                time.sleep(1)
        else:
            self.debug("Connection to guest failed.")
            return False
        return True

    def remove(self):
        """
        Remove the guest

        Completely remove all guest instance data so that it does not
        consume any disk resources.
        """
        self.debug(f"Doing nothing to remove guest '{self.guest}'.")

    def _check_rsync(self):
        """
        Make sure that rsync is installed on the guest

        On read-only distros install it under the '/root/pkg' directory.
        Returns 'already installed' when rsync is already present.
        """

        # Check for rsync (nothing to do if already installed)
        self.debug("Ensure that rsync is installed on the guest.")
        try:
            self.execute("rsync --version")
            return "already installed"
        except tmt.utils.RunError:
            pass

        # Check the package manager
        self.debug("Check the package manager.")
        try:
            self.execute("dnf --version")
            package_manager = "dnf"
        except tmt.utils.RunError:
            package_manager = "yum"

        # Install under '/root/pkg' for read-only distros
        # (for now the check is based on 'rpm-ostree' presence)
        # FIXME: Find a better way how to detect read-only distros
        self.debug("Check for a read-only distro.")
        try:
            self.execute("rpm-ostree --version")
            readonly = (
                " --installroot=/root/pkg --releasever / "
                "&& ln -sf /root/pkg/bin/rsync /usr/local/bin/rsync")
        except tmt.utils.RunError:
            readonly = ""

        # Install the rsync
        self.execute(f"{package_manager} install -y rsync" + readonly)

    @classmethod
    def requires(cls):
        """ No extra requires needed """
        return []


@dataclasses.dataclass
class GuestSshData(GuestData):
    """
    Keys necessary to describe, create, save and restore a guest with SSH
    capability.

    Derived from GuestData, this class adds keys relevant for guests that can be
    reached over SSH.
    """

    # port to connect to
    port: Optional[int] = None
    # user name to log in
    user: Optional[str] = None
    # path to the private key
    key: List[str] = dataclasses.field(default_factory=list)
    # password
    password: Optional[str] = None


class GuestSsh(Guest):
    """
    Guest provisioned for test execution, capable of accepting SSH connections

    The following keys are expected in the 'data' dictionary::

        role ....... guest role in the multihost scenario (inherited)
        guest ...... hostname or ip address (inherited)
        port ....... port to connect to
        user ....... user name to log in
        key ........ path to the private key (str or list)
        password ... password

    These are by default imported into instance attributes.
    """

    _data_class = GuestSshData

    port: Optional[int]
    user: Optional[str]
    key: List[str]
    password: Optional[str]

    # Master ssh connection process and socket path
    _ssh_master_process = None
    _ssh_socket_path = None

    def _ssh_guest(self):
        """ Return user@guest """
        return f'{self.user}@{self.guest}'

    def _ssh_socket(self):
        """ Prepare path to the master connection socket """
        if not self._ssh_socket_path:
            # Use '/run/user/uid' if it exists, '/tmp' otherwise
            run_dir = f"/run/user/{os.getuid()}"
            if os.path.isdir(run_dir):
                socket_dir = os.path.join(run_dir, "tmt")
            else:
                socket_dir = "/tmp"
            os.makedirs(socket_dir, exist_ok=True)
            self._ssh_socket_path = tempfile.mktemp(dir=socket_dir)
        return self._ssh_socket_path

    def _ssh_options(self, join=False):
        """ Return common ssh options (list or joined) """
        options = [
            '-oForwardX11=no',
            '-oStrictHostKeyChecking=no',
            '-oUserKnownHostsFile=/dev/null',
            ]
        if self.key or self.password:
            # Skip ssh-agent (it adds additional identities)
            options.append('-oIdentitiesOnly=yes')
        if self.port:
            options.append(f'-p{self.port}')
        if self.key:
            keys = self.key if isinstance(self.key, list) else [self.key]
            for key in keys:
                options.append(f'-i{shlex.quote(key) if join else key}')
        if self.password:
            options.extend(['-oPasswordAuthentication=yes'])

        # Use the shared master connection
        options.append(f'-S{self._ssh_socket()}')

        return ' '.join(options) if join else options

    def _ssh_master_connection(self, command):
        """ Check/create the master ssh connection """
        if self._ssh_master_process:
            return
        command = command + self._ssh_options() + ["-MNnT", self._ssh_guest()]
        self.debug(f"Create the master ssh connection: {' '.join(command)}")
        self._ssh_master_process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)

    def _ssh_command(self, join=False):
        """ Prepare an ssh command line for execution (list or joined) """
        command = []
        if self.password:
            password = shlex.quote(self.password) if join else self.password
            command.extend(["sshpass", "-p", password])
        command.append("ssh")

        # Check the master connection
        self._ssh_master_connection(command)

        if join:
            return " ".join(command) + " " + self._ssh_options(join=True)
        else:
            return command + self._ssh_options()

    def ansible(self, playbook, extra_args=None):
        """ Prepare guest using ansible playbook """
        playbook = self._ansible_playbook_path(playbook)
        stdout, stderr = self.run(
            ['ansible-playbook'] +
            self._ansible_verbosity() +
            self._ansible_extra_args(extra_args) +
            [f'--ssh-common-args={self._ssh_options(join=True)}'] +
            ['-i', f'{self._ssh_guest()},', playbook],
            cwd=self.parent.plan.worktree,
            env=self._prepare_environment())
        self._ansible_summary(stdout)

    def execute(self, command, **kwargs):
        """
        Execute command on the guest

        command ... string or list of command arguments (required)
        env ....... dictionary with environment variables
        cwd ....... working directory to be entered before execution

        If the command is provided as a list, it will be space-joined.
        If necessary, quote escaping has to be handled by the caller.
        """

        # Prepare the export of environment variables
        environment = self._export_environment(
            self._prepare_environment(kwargs.get('env', dict())))

        # Change to given directory on guest if cwd provided
        directory = kwargs.get('cwd') or ''
        if directory:
            directory = f"cd {quote(directory)}; "

        # Run in interactive mode if requested
        interactive = ['-t'] if kwargs.get('interactive') else []

        # Prepare command and run it
        if isinstance(command, (list, tuple)):
            command = ' '.join(command)
        self.debug(f"Execute command '{command}' on guest '{self.guest}'.")
        command = (
            self._ssh_command() + interactive + [self._ssh_guest()] +
            [f'{environment}{directory}{command}'])
        return self.run(command, **kwargs)

    def push(self, source=None, destination=None, options=None):
        """
        Push files to the guest

        By default the whole plan workdir is synced to the same location
        on the guest. Use the 'source' and 'destination' to sync custom
        location and the 'options' parametr to modify default options
        which are '-Rrz --links --safe-links --delete'.
        """
        # Prepare options and the push command
        if options is None:
            options = DEFAULT_RSYNC_OPTIONS
        if destination is None:
            destination = "/"
        if source is None:
            source = self.parent.plan.workdir
            self.debug(f"Push workdir to guest '{self.guest}'.")
        else:
            self.debug(f"Copy '{source}' to '{destination}' on the guest.")

        def rsync():
            """ Run the rsync command """
            self.run(
                ["rsync"] + options
                + ["-e", self._ssh_command(join=True)]
                + [source, f"{self._ssh_guest()}:{destination}"])

        # Try to push twice, check for rsync after the first failure
        try:
            rsync()
        except tmt.utils.RunError:
            try:
                if self._check_rsync() == "already installed":
                    raise
                rsync()
            except tmt.utils.RunError:
                # Provide a reasonable error to the user
                self.fail(
                    f"Failed to push workdir to the guest. This usually means "
                    f"that login as '{self.user}' to the guest does not work.")
                raise

    def pull(
            self,
            source=None,
            destination=None,
            options=None,
            extend_options=None):
        """
        Pull files from the guest

        By default the whole plan workdir is synced from the same
        location on the guest. Use the 'source' and 'destination' to
        sync custom location, the 'options' parameter to modify
        default options '-Rrz --links --safe-links --protect-args'
        and 'extend_options' to extend them (e.g. by exclude).
        """
        # Prepare options and the pull command
        if options is None:
            options = "-Rrz --links --safe-links --protect-args".split()
        if extend_options is not None:
            options.extend(extend_options)
        if destination is None:
            destination = "/"
        if source is None:
            source = self.parent.plan.workdir
            self.debug(f"Pull workdir from guest '{self.guest}'.")
        else:
            self.debug(f"Copy '{source}' from the guest to '{destination}'.")

        def rsync():
            """ Run the rsync command """
            self.run(
                ["rsync"] + options
                + ["-e", self._ssh_command(join=True)]
                + [f"{self._ssh_guest()}:{source}", destination])

        # Try to pull twice, check for rsync after the first failure
        try:
            rsync()
        except tmt.utils.RunError:
            try:
                if self._check_rsync() == "already installed":
                    raise
                rsync()
            except tmt.utils.RunError:
                # Provide a reasonable error to the user
                self.fail(
                    f"Failed to pull workdir from the guest. "
                    f"This usually means that login as '{self.user}' "
                    f"to the guest does not work.")
                raise

    def stop(self):
        """
        Stop the guest

        Shut down a running guest instance so that it does not consume
        any memory or cpu resources. If needed, perform any actions
        necessary to store the instance status to disk.
        """

        # Close the master ssh connection
        if self._ssh_master_process:
            self.debug("Close the master ssh connection.", level=3)
            try:
                self._ssh_master_process.terminate()
                self._ssh_master_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass

        # Remove the ssh socket
        if self._ssh_socket_path and os.path.exists(self._ssh_socket_path):
            self.debug(
                f"Remove ssh socket '{self._ssh_socket_path}'.", level=3)
            try:
                os.unlink(self._ssh_socket_path)
            except OSError as error:
                self.debug(f"Failed to remove the socket: {error}", level=3)

    def reboot(self, hard=False, command=None, timeout=None):
        """
        Reboot the guest, return True if reconnect was successful

        Parameter 'hard' set to True means that guest should be
        rebooted by way which is not clean in sense that data can be
        lost. When set to False reboot should be done gracefully.

        Use the 'command' parameter to specify a custom reboot command
        instead of the default 'reboot'.
        """

        if hard:
            raise tmt.utils.ProvisionError(
                "Method does not support hard reboot.")

        timeout = timeout or tmt.steps.provision.CONNECTION_TIMEOUT

        now = datetime.datetime.utcnow
        deadline = now() + datetime.timedelta(seconds=timeout)

        re_boot_time = re.compile(r'btime\s+(\d+)')

        def get_boot_time():
            """ Reads btime from /proc/stat """
            stdout = self.execute(["cat", "/proc/stat"]).stdout
            assert stdout
            return int(re_boot_time.search(stdout).group(1))

        current_boot_time = get_boot_time()

        try:
            command = command or "reboot"
            self.debug(f"Reboot using the command '{command}'.")
            self.execute(command)
        except tmt.utils.RunError as error:
            # Connection can be closed by the remote host even before the
            # reboot command is completed. Let's ignore such errors.
            if error.returncode == 255:
                self.debug(
                    "Seems the connection was closed too fast, ignoring.")
            else:
                raise
        # Wait until we get new boot time, connection will drop and will be
        # unreachable for some time
        while now() < deadline:
            try:
                new_boot_time = get_boot_time()
                if new_boot_time != current_boot_time:
                    # Different boot time and we are reconnected
                    return True
                self.debug("Same boot time, reboot didn't happen yet, retrying")
            except tmt.utils.RunError:
                self.debug('Failed to connect to the guest, retrying.')
            # Either couldn't connect or boot time didn't change
            time.sleep(1)
        self.debug("Connection to guest failed - timeout exceeded.")
        return False

    def remove(self):
        """
        Remove the guest

        Completely remove all guest instance data so that it does not
        consume any disk resources.
        """
        self.debug(f"Doing nothing to remove guest '{self.guest}'.")

    def _check_rsync(self):
        """
        Make sure that rsync is installed on the guest

        On read-only distros install it under the '/root/pkg' directory.
        Returns 'already installed' when rsync is already present.
        """

        # Check for rsync (nothing to do if already installed)
        self.debug("Ensure that rsync is installed on the guest.")
        try:
            self.execute("rsync --version")
            return "already installed"
        except tmt.utils.RunError:
            pass

        # Check the package manager
        self.debug("Check the package manager.")
        try:
            self.execute("dnf --version")
            package_manager = "dnf"
        except tmt.utils.RunError:
            package_manager = "yum"

        # Install under '/root/pkg' for read-only distros
        # (for now the check is based on 'rpm-ostree' presence)
        # FIXME: Find a better way how to detect read-only distros
        self.debug("Check for a read-only distro.")
        try:
            self.execute("rpm-ostree --version")
            readonly = (
                " --installroot=/root/pkg --releasever / "
                "&& ln -sf /root/pkg/bin/rsync /usr/local/bin/rsync")
        except tmt.utils.RunError:
            readonly = ""

        # Install the rsync
        self.execute(f"{package_manager} install -y rsync" + readonly)

    @classmethod
    def requires(cls):
        """ No extra requires needed """
        return []
