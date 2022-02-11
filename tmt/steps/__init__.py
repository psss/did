
""" Step Classes """

import os
import re

import click
from click import echo

import tmt.utils
from tmt.options import show_step_method_hints
from tmt.utils import GeneralError

# Supported steps and actions
STEPS = ['discover', 'provision', 'prepare', 'execute', 'report', 'finish']
ACTIONS = ['login', 'reboot']

# Step phase order
PHASE_START = 10
PHASE_BASE = 50
PHASE_END = 90


class Step(tmt.utils.Common):
    """ Common parent of all test steps """

    # Default implementation for all steps is shell
    # except for provision (virtual) and report (display)
    how = 'shell'

    def __init__(self, data=None, plan=None, name=None):
        """ Initialize and check the step data """
        super().__init__(name=name, parent=plan)
        # Initialize data
        self.plan = plan
        self.data = data or {}
        self._status = None
        self._plugins = []

        # Create an empty step by default (can be updated from cli)
        if self.data is None:
            self.data = [{'name': tmt.utils.DEFAULT_NAME}]
        # Convert to list if only a single config provided
        elif isinstance(self.data, dict):
            # Give it a name unless defined
            if not self.data.get('name'):
                self.data['name'] = tmt.utils.DEFAULT_NAME
            self.data = [self.data]
        # Shout about invalid configuration
        elif not isinstance(self.data, list):
            raise GeneralError(f"Invalid '{self}' config in '{self.plan}'.")

        # Add default unique names even to multiple configs so that the users
        # don't need to specify it if they don't care about the name
        for i, data in enumerate(self.data):
            if 'name' not in data:
                data['name'] = f'{tmt.utils.DEFAULT_NAME}-{i}'

        # Final sanity checks
        for data in self.data:
            # Set 'how' to the default if not specified
            if data.get('how') is None:
                data['how'] = self.how
            # Ensure that each config has a name
            if 'name' not in data and len(self.data) > 1:
                raise GeneralError(
                    f"Missing 'name' in the {self} step config "
                    f"of the '{self.plan}' plan.")

    @property
    def enabled(self):
        """ True if the step is enabled """
        try:
            return self.name in self.plan.my_run._context.obj.steps
        except AttributeError:
            return None

    @classmethod
    def usage(cls, method_overview):
        """ Prepare general usage message for the step """
        # Main description comes from the class docstring
        usage = re.sub('\n    ', '\n', cls.__doc__)
        # Append the list of supported methods
        usage += '\n\n' + method_overview
        # Give a hint about detailed help
        name = cls.__name__.lower()
        usage += (
            f"\n\nUse 'tmt run {name} --help --how <method>' to learn more "
            f"about given {name} method and all its supported options.")
        return usage

    def status(self, status=None):
        """
        Get and set current step status

        The meaning of the status is as follows:
        todo ... config, data and command line processed (we know what to do)
        done ... the final result of the step stored to workdir (we are done)
        """
        # Update status
        if status is not None:
            # Check for valid values
            if status not in ['todo', 'done']:
                raise GeneralError(f"Invalid status '{status}'.")
            # Show status only if changed
            elif self._status != status:
                self._status = status
                self.debug('status', status, color='yellow', level=2)
        # Return status
        return self._status

    def load(self, extra_keys=None):
        """ Load status and step data from the workdir """
        extra_keys = extra_keys or []
        try:
            content = tmt.utils.yaml_to_dict(self.read('step.yaml'))
            self.debug('Successfully loaded step data.', level=2)
            self.data = content['data']
            for key in extra_keys:
                if key in content:
                    setattr(self, key, content[key])
            self.status(content['status'])
        except GeneralError:
            self.debug('Step data not found.', level=2)

    def save(self, data=None):
        """ Save status and step data to the workdir """
        data = data or {}
        content = dict(status=self.status(), data=self.data)
        content.update(data)
        self.write('step.yaml', tmt.utils.dict_to_yaml(content))

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        # Cleanup possible old workdir if called with --force
        if self.opt('force'):
            self._workdir_cleanup()

        # Load stored data
        self.load()

        # Status 'todo' means the step has not finished successfully.
        # Probably interrupted in the middle. Clean up the work
        # directory to give it another chance with a fresh start.
        if self.status() == 'todo':
            self.debug("Step has not finished. Let's try once more!", level=2)
            self._workdir_cleanup()

        # Special handling for the report step to always enable force mode in
        # order to cover a very frequent use case 'tmt run --last report'
        # FIXME find a better way how to enable always-force per plugin
        if (isinstance(self, tmt.steps.report.Report) and
                self.data[0].get('how') in ['display', 'html']):
            self.debug("Report step always force mode enabled.")
            self._workdir_cleanup()
            self.status('todo')

        # Nothing more to do when the step is already done
        if self.status() == 'done':
            return

        # Override step data with command line options
        how = self.opt('how')
        if how is not None:
            for data in self.data:
                data['how'] = how

    def setup_actions(self):
        """ Insert login and reboot plugins if requested """
        for plugin in Login.plugins(step=self):
            self.debug(
                f"Insert a login plugin into the '{self}' step "
                f"with order '{plugin.order}'.", level=2)
            self._plugins.append(plugin)

        for plugin in Reboot.plugins(step=self):
            self.debug(
                f"Insert a reboot plugin into the '{self}' step "
                f"with order '{plugin.order}'.", level=2)
            self._plugins.append(plugin)

    def plugins(self, classes=None):
        """
        Iterate over plugins by their order

        By default iterates over all available plugins. Optional filter
        'classes' can be used to iterate only over instances of given
        class (single class or tuple of classes).
        """
        return sorted(
            [plugin for plugin in self._plugins
                if classes is None or isinstance(plugin, classes)],
            key=lambda plugin: plugin.order)

    def actions(self):
        """ Run all loaded Login or Reboot plugin instances of the step """
        for plugin in self.plugins():
            if isinstance(plugin, (Reboot, Login)):
                plugin.go()

    def go(self):
        """ Execute the test step """
        # Show step header and how
        self.info(self.name, color='blue')
        # Show workdir in verbose mode
        self.debug('workdir', self.workdir, 'magenta')


class Method(object):
    """ Step implementation method """

    def __init__(self, name, doc, order):
        """ Store method data """
        self.name = name
        self.doc = doc.strip()
        self.order = order

        # Parse summary and description from provided doc string
        lines = [re.sub('^    ', '', line) for line in self.doc.split('\n')]
        self.summary = lines[0].strip()
        self.description = '\n'.join(lines[1:]).lstrip()

    def describe(self):
        """ Format name and summary for a nice method overview """
        return f'{self.name} '.ljust(22, '.') + f' {self.summary}'

    def usage(self):
        """ Prepare a detailed usage from summary and description """
        if self.description:
            usage = self.summary + '\n\n' + self.description
        else:
            usage = self.summary
        # Disable wrapping for all paragraphs
        return re.sub('\n\n', '\n\n\b\n', usage)


class PluginIndex(type):
    """ Plugin metaclass used to register all available plugins """

    def __init__(cls, name, bases, attributes):
        """ Store all defined methods in the parent class """
        try:
            for method in cls._methods:
                # Store reference to the implementing class
                method.class_ = cls
                # Add to the list of supported methods in parent class
                bases[0]._supported_methods.append(method)
        except AttributeError:
            pass


class Plugin(tmt.utils.Common, metaclass=PluginIndex):
    """ Common parent of all step plugins """

    # Default implementation for all steps is shell
    # except for provision (virtual) and report (display)
    how = 'shell'

    # Common keys for all plugins of given step
    _common_keys = []

    # Keys specific for given plugin
    _keys = []

    def __init__(self, step, data):
        """ Store plugin name, data and parent step """

        # Ensure that plugin data contains name
        if 'name' not in data:
            raise GeneralError(
                f"Missing 'name' in the {step} step config "
                f"of the '{step.plan}' plan.")

        # Store name, data and parent step
        super().__init__(parent=step, name=data['name'])
        self.data = data
        self.step = step

        # Initialize plugin order
        try:
            self.order = int(self.data['order'])
        except (ValueError, KeyError):
            self.order = tmt.utils.DEFAULT_PLUGIN_ORDER

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options for given method """
        # Include common options supported across all plugins
        return tmt.options.verbose_debug_quiet + tmt.options.force_dry

    @classmethod
    def command(cls):
        """ Prepare click command for all supported methods """
        # Create one command for each supported method
        commands = {}
        method_overview = f'Supported methods ({cls.how} by default):\n\n\b'
        for method in cls.methods():
            method_overview += f'\n{method.describe()}'
            command = cls.base_command(usage=method.usage())
            # Apply plugin specific options
            for option in method.class_.options(method.name):
                command = option(command)
            commands[method.name] = command

        # Create base command with common options using method class
        method_class = tmt.options.create_method_class(commands)
        command = cls.base_command(method_class, usage=method_overview)
        # Apply common options
        for option in cls.options():
            command = option(command)
        return command

    @classmethod
    def methods(cls):
        """ Return all supported methods ordered by priority """
        return sorted(cls._supported_methods, key=lambda method: method.order)

    @classmethod
    def delegate(cls, step, data):
        """
        Return plugin instance implementing the data['how'] method

        Supports searching by method prefix as well (e.g. 'virtual').
        The first matching method with the lowest 'order' wins.
        """
        # Filter matching methods, pick the one with the lowest order
        for method in cls.methods():
            if method.name.startswith(data['how']):
                step.debug(
                    f"Using the '{method.class_.__name__}' plugin "
                    f"for the '{data['how']}' method.", level=2)
                return method.class_(step, data)

        show_step_method_hints(step, step.name, data['how'])
        # Report invalid method
        raise tmt.utils.SpecificationError(
            f"Unsupported {step.name} method '{data['how']}' "
            f"in the '{step.plan.name}' plan.")

    def default(self, option, default=None):
        """ Return default data for given option """
        return default

    def get(self, option, default=None):
        """ Get option from plugin data, user/system config or defaults """
        # Check plugin data first
        try:
            return self.data[option]
        except KeyError:
            pass

        # Check user config and system config
        # TODO

        # Finally check plugin defaults
        return self.default(option, default)

    def show(self, keys=None):
        """ Show plugin details for given or all available keys """
        # Show empty config with default method only in verbose mode
        if (set(self.data.keys()) == set(['how', 'name'])
                and not self.opt('verbose')
                and self.data['how'] == self.how):
            return
        # Step name (and optional summary)
        echo(tmt.utils.format(
            self.step, self.get('summary', ''),
            key_color='blue', value_color='blue'))
        # Show all or requested step attributes
        base_keys = ['name', 'how']
        if keys is None:
            keys = self._common_keys + self._keys
        for key in base_keys + keys:
            # Skip showing the default name
            if key == 'name' and self.name == tmt.utils.DEFAULT_NAME:
                continue
            # Skip showing summary again
            if key == 'summary':
                continue
            value = self.get(key)
            if value is not None:
                echo(tmt.utils.format(key, value))

    def enabled_on_guest(self, guest):
        """ Check if the plugin is enabled on the specific guest """
        where = self.get('where')
        if not where:
            return True
        return where in (guest.name, guest.role)

    def wake(self, keys=None):
        """
        Wake up the plugin, process data, apply options

        Check command line options corresponding to plugin keys
        and store their value into the 'self.data' dictionary if
        their value is True or non-empty.

        By default, all supported options corresponding to common
        and plugin-specific keys are processed. List of key names
        in the 'keys' parameter can be used to override only
        selected ones.
        """
        if keys is None:
            keys = self._common_keys + self._keys
        for key in keys:
            value = self.opt(key)
            if value:
                self.data[key] = value

    def go(self):
        """ Go and perform the plugin task """
        # Show the method
        self.info('how', self.get('how'), 'magenta')
        # Give summary if provided
        if self.get('summary'):
            self.info('summary', self.get('summary'), 'magenta')
        # Show name only if it's not the default one
        if self.name != tmt.utils.DEFAULT_NAME:
            self.info('name', self.name, 'magenta')
        # Include order in verbose mode
        self.verbose('order', self.order, 'magenta', level=3)

    def requires(self):
        """ List of packages required by the plugin on the guest """
        return []


class Action(tmt.utils.Common):
    """ A special action performed during a normal step. """

    # Dictionary containing list of requested phases for each enabled step
    _phases = None

    @classmethod
    def phases(cls, step):
        """ Return list of phases enabled for given step """
        # Build the phase list unless done before
        if cls._phases is None:
            cls._phases = cls._parse_phases(step)
        # Return enabled phases, empty list if step not found
        try:
            return cls._phases[step.name]
        except KeyError:
            return []

    @classmethod
    def _parse_phases(cls, step):
        """ Parse options and store phase order """
        phases = dict()
        options = cls._opt('step', default=[])

        # Use the end of the last enabled step if no --step given
        if not options:
            login_during = None
            # The last run may have failed before all enabled steps were
            # completed, select the last step done
            if step.plan.my_run.opt('last'):
                steps = [s for s in step.plan.steps() if s.status() == 'done']
                login_during = steps[-1] if steps else None
            # Default to the last enabled step if no completed step found
            if login_during is None:
                login_during = list(step.plan.steps())[-1]
            # Only login if the error occurred after provision
            if login_during != step.plan.discover:
                phases[login_during.name] = [PHASE_END]

        # Process provided options
        for option in options:
            # Parse the step:phase format
            matched = re.match(r'(\w+)(:(\w+))?', option)
            if matched:
                step_name, _, phase = matched.groups()
            if not matched or step_name not in STEPS:
                raise tmt.utils.GeneralError(f"Invalid step '{option}'.")
            # Check phase format, convert into int, use end by default
            try:
                phase = int(phase)
            except TypeError:
                phase = PHASE_END
            except ValueError:
                # Convert 'start' and 'end' aliases
                try:
                    phase = dict(start=PHASE_START, end=PHASE_END)[phase]
                except KeyError:
                    raise tmt.utils.GeneralError(f"Invalid phase '{phase}'.")
            # Store the phase for given step
            try:
                phases[step_name].append(phase)
            except KeyError:
                phases[step_name] = [phase]
        return phases


class Reboot(Action):
    """ Reboot guest """

    # True if reboot enabled
    _enabled = False

    def __init__(self, step, order):
        """ Initialize relations, store the reboot order """
        super().__init__(parent=step, name='reboot')
        self.order = order

    @classmethod
    def command(cls, method_class=None, usage=None):
        """ Create the reboot command """
        @click.command()
        @click.pass_context
        @click.option(
            '-s', '--step', metavar='STEP[:PHASE]', multiple=True,
            help='Reboot machine during given phase of selected step(s).')
        @click.option(
            '--hard', is_flag=True,
            help='Hard reboot of the machine. Unsaved data may be lost.')
        def reboot(context, **kwargs):
            """ Reboot the guest. """
            Reboot._save_context(context)
            Reboot._enabled = True

        return reboot

    @classmethod
    def plugins(cls, step):
        """ Return list of reboot instances for given step """
        if not Reboot._enabled:
            return []
        return [Reboot(step, phase) for phase in cls.phases(step)]

    def go(self, *args, **kwargs):
        """ Reboot the guest(s) """
        self.info('reboot', 'Rebooting guest', color='yellow')
        for guest in self.parent.plan.provision.guests():
            guest.reboot(self.opt('hard'))
        self.info('reboot', 'Reboot finished', color='yellow')


class Login(Action):
    """ Log into the guest """

    # True if interactive login enabled
    _enabled = False

    def __init__(self, step, order):
        """ Initialize relations, store the login order """
        super().__init__(parent=step, name='login')
        self.order = order

    @classmethod
    def command(cls, method_class=None, usage=None):
        """ Create the login command """
        @click.command()
        @click.pass_context
        @click.option(
            '-s', '--step', metavar='STEP[:PHASE]', multiple=True,
            help='Log in during given phase of selected step(s).')
        @click.option(
            '-w', '--when', metavar='RESULT', multiple=True,
            type=click.Choice(tmt.base.Result._results),
            help='Log in if a test finished with given result(s).')
        @click.option(
            '-c', '--command', metavar='COMMAND',
            multiple=True, default=['bash'],
            help="Run given command(s). Default is 'bash'.")
        def login(context, **kwargs):
            """
            Provide user with an interactive shell on the guest.

            By default the shell is provided at the end of the last
            enabled step. When used together with the --last option the
            last completed step is selected. Use one or more --step
            options to select a different step instead.

            Optional phase can be provided to specify the exact phase of
            the step when the shell should be provided. The following
            values are supported:

            \b
                start ... beginning of the step (same as '10')
                end ..... end of the step (default, same as '90')
                00-99 ... integer order defining the exact phase

            Usually the main step execution happens with order 50.
            Consult individual step documentation for more details.

            For the execute step and following steps it is also possible
            to conditionally enable the login feature only if some of
            the tests finished with given result (pass, info, fail,
            warn, error).
            """
            Login._save_context(context)
            Login._enabled = True

        return login

    @classmethod
    def plugins(cls, step):
        """ Return list of login instances for given step """
        if not Login._enabled:
            return []
        return [Login(step, phase) for phase in cls.phases(step)]

    def go(self, *args, **kwargs):
        """ Login to the guest(s) """
        # Verify possible test result condition
        count = dict()
        expected_results = self.opt('when')
        if expected_results:
            for expected_result in expected_results:
                count[expected_result] = len([
                    result for result in self.parent.plan.execute.results()
                    if result.result == expected_result])
            if not any(count.values()):
                self.info('Skipping interactive shell', color='yellow')
                return

        # Run the interactive command
        commands = self.opt('command')
        self.info('login', 'Starting interactive shell', color='yellow')
        for guest in self.parent.plan.provision.guests():
            # Attempt to push the workdir to the guest
            try:
                guest.push()
                cwd = self.parent.plan.worktree
            except tmt.utils.GeneralError:
                self.warn("Failed to push workdir to the guest.")
                cwd = None
            # Execute all requested commands
            for command in commands:
                self.debug(f"Run '{command}' in interactive mode.")
                guest.execute(command, interactive=True, cwd=cwd)
        self.info('login', 'Interactive shell finished', color='yellow')
