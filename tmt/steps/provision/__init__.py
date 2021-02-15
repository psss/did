import os
import re
import click
import random
import string

import fmf
import tmt


class Provision(tmt.steps.Step):
    """ Provision an environment for testing or use localhost. """

    # Default implementation for provision is a virtual machine
    how = 'virtual'

    def __init__(self, data, plan):
        """ Initialize provision step data """
        super().__init__(data, plan)
        # List of provisioned guests and loaded guest data
        self._guests = []
        self._guest_data = {}

    def load(self):
        """ Load guest data from the workdir """
        super().load()
        try:
            self._guest_data = tmt.utils.yaml_to_dict(self.read('guests.yaml'))
        except tmt.utils.FileError:
            self.debug('Provisioned guests not found.', level=2)

    def save(self):
        """ Save guest data to the workdir """
        super().save()
        try:
            guests = dict(
                [(guest.name, guest.save()) for guest in self.guests()])
            self.write('guests.yaml', tmt.utils.dict_to_yaml(guests))
        except tmt.utils.FileError:
            self.debug('Failed to save provisioned guests.')

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        super().wake()

        # Choose the right plugin and wake it up
        for data in self.data:
            plugin = ProvisionPlugin.delegate(self, data)
            self._plugins.append(plugin)
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
            self.try_running_login()
            return

        # Provision guests
        self._guests = []
        for plugin in self.plugins():
            plugin.go()
            if isinstance(plugin, ProvisionPlugin):
                plugin.guest().details()
                self._guests.append(plugin.guest())

        # Give a summary, update status and save
        self.summary()
        self.status('done')
        self.save()

    def guests(self):
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
        for plugin in self.plugins(classes=ProvisionPlugin):
            requires.update(plugin.requires())
        return list(requires)


class ProvisionPlugin(tmt.steps.Plugin):
    """ Common parent of provision plugins """

    # Default implementation for provision is a virtual machine
    how = 'virtual'

    # List of all supported methods aggregated from all plugins
    _supported_methods = []

    @classmethod
    def base_command(cls, method_class=None, usage=None):
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

    def wake(self, options=None, data=None):
        """
        Wake up the plugin

        Override data with command line options.
        Wake up the guest based on provided guest data.
        """
        super().wake(options)

    def guest(self):
        """
        Return provisioned guest

        Each ProvisionPlugin has to implement this method.
        Should return a provisioned Guest() instance.
        """
        raise NotImplementedError

    def requires(self):
        """ List of required packages needed for workdir sync """
        return Guest.requires()


class Guest(tmt.utils.Common):
    """
    Guest provisioned for test execution

    The following keys are expected in the 'data' dictionary::

        guest ...... hostname or ip address
        user ....... user name to log in
        key ........ private key
        password ... password

    These are by default imported into instance attributes (see the
    class attribute '_keys' below).
    """

    # List of supported keys
    # (used for import/export to/from attributes during load and save)
    _keys = ['guest', 'user', 'key', 'password']

    def __init__(self, data, name=None, parent=None):
        """ Initialize guest data """
        super().__init__(parent, name)
        self.load(data)

    def _random_name(self):
        """ Generate a random name """
        return ''.join(random.choices(string.ascii_letters, k=16))

    def _ssh_guest(self):
        """ Return user@guest """
        return f'{self.user}@{self.guest}'

    def _ssh_options(self, join=False):
        """ Return common ssh options (list or joined) """
        options = [
            '-oStrictHostKeyChecking=no',
            '-oUserKnownHostsFile=/dev/null',
            ]
        if self.key:
            options.extend(['-i', self.key])
        return ' '.join(options) if join else options

    def _ssh_command(self, join=False):
        """ Prepare an ssh command line for execution (list or joined) """
        command = ['sshpass', f'-p{self.password}'] if self.password else []
        command += ['ssh'] + self._ssh_options()
        return ' '.join(command) if join else command

    def load(self, data):
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
        for key in self._keys:
            setattr(self, key, data.get(key))

    def save(self):
        """
        Save guest data for future wake up

        Export all essential guest data into a dictionary which will be
        stored in the `guests.yaml` file for possible future wake up of
        the guest. Everything needed to attach to a running instance
        should be added into the data dictionary by child classes.
        """
        data = dict()
        for key in self._keys:
            value = getattr(self, key)
            if value is not None:
                data[key] = value
        return data

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
        except tmt.utils.RunError:
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
        if distro:
            self.info('distro', distro, 'green')

        # Kernel
        kernel = self.execute('uname -r')[0].strip()
        self.verbose('kernel', kernel, 'green')

    def _ansible_verbosity(self):
        """ Prepare verbose level based on the --debug option count """
        if self.opt('debug') < 3:
            return ''
        else:
            return ' -' + (self.opt('debug') - 2) * 'v'

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
        playbook = os.path.join(self.parent.plan.run.tree.root, playbook)
        self.debug(f"Playbook full path: '{playbook}'", level=2)
        return playbook

    def _export_environment(self, execute_environment=None):
        """ Prepare shell export of environment variables """
        # Prepare environment variables so they can be correctly passed
        # to ssh's shell. Create a copy to prevent modifying source.
        environment = dict()
        environment.update(execute_environment or dict())
        # Plan environment and variables provided on the command line
        # override environment provided to execute().
        environment.update(self.parent.plan.environment)
        # Prepend with export and run as a separate command.
        if not environment:
            return ''
        return 'export {}; '.format(
            ' '.join(tmt.utils.shell_variables(environment)))

    def ansible(self, playbook):
        """ Prepare guest using ansible playbook """
        playbook = self._ansible_playbook_path(playbook)
        stdout, stderr = self.run(
            f'stty cols {tmt.utils.OUTPUT_WIDTH}; ansible-playbook '
            f'--ssh-common-args="{self._ssh_options(join=True)}" '
            f'-e ansible_python_interpreter=auto'
            f'{self._ansible_verbosity()} -i {self._ssh_guest()}, {playbook}')
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
        environment = self._export_environment(kwargs.get('env', dict()))

        # Change to given directory on guest if cwd provided
        directory = kwargs.get('cwd') or ''
        if directory:
            directory = f"cd '{directory}'; "

        # Run in interactive mode if requested
        interactive = ['-t'] if kwargs.get('interactive') else []

        # Prepare command and run it
        if isinstance(command, (list, tuple)):
            command = ' '.join(command)
        self.debug(f"Execute command '{command}' on guest '{self.guest}'.")
        command = (
            self._ssh_command() + interactive + [self._ssh_guest()] +
            [f'{environment}{directory}{command}'])
        return self.run(command, shell=False, **kwargs)

    def push(self):
        """ Push workdir to guest """
        self.debug(f"Push workdir to guest '{self.guest}'.")
        self.run(
            f'rsync -Rrz --links --safe-links --delete '
            f'-e "{self._ssh_command(join=True)}" '
            f'--safe-links {self.parent.plan.workdir} {self._ssh_guest()}:/')

    def pull(self):
        """ Pull workdir from guest """
        self.debug(f"Pull workdir from guest '{self.guest}'.")
        self.run(
            f'rsync -Rrz --links --safe-links '
            f'-e "{self._ssh_command(join=True)}" '
            f'{self._ssh_guest()}:{self.parent.plan.workdir} /')

    def stop(self):
        """
        Stop the guest

        Shut down a running guest instance so that it does not consume
        any memory or cpu resources. If needed, perform any actions
        necessary to store the instance status to disk.
        """
        self.debug(f"Doing nothing to stop guest '{self.guest}'.")

    def remove(self):
        """
        Remove the guest

        Completely remove all guest instance data so that it does not
        consume any disk resources.
        """
        self.debug(f"Doing nothing to remove guest '{self.guest}'.")

    @classmethod
    def requires(cls):
        """ Syncing workdir with the guest needs rsync installed """
        return ['rsync']
