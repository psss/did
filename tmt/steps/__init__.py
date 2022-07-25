
""" Step Classes """

import re
import sys
from typing import (TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type,
                    TypeVar, Union, cast, overload)

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

import click
from click import echo

import tmt.options
import tmt.utils
from tmt.options import show_step_method_hints

if TYPE_CHECKING:
    import tmt.base
    from tmt.base import Plan
    from tmt.steps.provision import Guest

# Supported steps and actions
STEPS = ['discover', 'provision', 'prepare', 'execute', 'report', 'finish']
ACTIONS = ['login', 'reboot']

# Step phase order
PHASE_START = 10
PHASE_BASE = 50
PHASE_END = 90


class Phase(tmt.utils.Common):
    """ A phase of a step """

    def __init__(
            self,
            order: int = tmt.utils.DEFAULT_PLUGIN_ORDER,
            *args: Any,
            **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.order: int = order

    def enabled_on_guest(self, guest: 'Guest') -> bool:
        """ Phases are enabled across all guests by default """
        return True

    @property
    def is_in_standalone_mode(self) -> bool:
        """
        True if the phase is in stand-alone mode.

        Stand-alone mode means that only this phase should be run as a part
        of the run (and not any other even if requested using --all).
        This is useful as some plugin options may completely change its
        behaviour from the regular behaviour based on options
        (e.g. listing images inside a provision plugin).
        """
        return False


# A variable used to describe a generic type for all classes derived from Phase
PhaseT = TypeVar('PhaseT', bound=Phase)


class StepData(TypedDict, total=False):
    """
    Step data structure
    """
    name: str
    how: str
    order: Optional[int]
    tests: Optional[List['tmt.base.Test']]


class Step(tmt.utils.Common):
    """ Common parent of all test steps """

    # Default implementation for all steps is shell
    # except for provision (virtual) and report (display)
    how: str = 'shell'

    def __init__(
            self,
            plan: 'Plan',
            data: Optional[StepData] = None,
            name: Optional[str] = None,
            workdir: tmt.utils.WorkdirArgumentType = None) -> None:
        """ Initialize and check the step data """
        super().__init__(name=name, parent=plan, workdir=workdir)
        # Initialize data
        self.plan: 'Plan' = plan
        self.data: Union[StepData, List[StepData]] = data or {}
        self._status: Optional[str] = None
        self._phases: List[Phase] = []

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
            raise tmt.utils.GeneralError(
                f"Invalid '{self}' config in '{self.plan}'.")

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
                raise tmt.utils.GeneralError(
                    f"Missing 'name' in the {self} step config "
                    f"of the '{self.plan}' plan.")

    @property
    def enabled(self) -> Optional[bool]:
        """ True if the step is enabled """
        try:
            return self.name in self.plan.my_run._context.obj.steps
        except AttributeError:
            return None

    @property
    def plugins_in_standalone_mode(self) -> int:
        """
        The number of plugins in standalone mode.

        Stand-alone mode means that only this step should be run as a part
        of the run (and not any other even if requested using --all).
        This is useful as some step options may completely change its
        behaviour from the regular behaviour based on options
        (e.g. listing images inside provision).
        """
        return sum(phase.is_in_standalone_mode for phase in self.phases())

    @classmethod
    def usage(cls, method_overview: str) -> str:
        """ Prepare general usage message for the step """
        # Main description comes from the class docstring
        if cls.__name__ is None:
            raise tmt.utils.GeneralError("Missing name of the step.")

        if cls.__doc__ is None:
            raise tmt.utils.GeneralError(
                f"Missing docstring of the step {cls.__name__.lower()}.")

        usage = re.sub('\n    ', '\n', cls.__doc__)
        # Append the list of supported methods
        usage += '\n\n' + method_overview
        # Give a hint about detailed help
        name = cls.__name__.lower()
        usage += (
            f"\n\nUse 'tmt run {name} --help --how <method>' to learn more "
            f"about given {name} method and all its supported options.")
        return usage

    def status(self, status: Optional[str] = None) -> Optional[str]:
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
                raise tmt.utils.GeneralError(f"Invalid status '{status}'.")
            # Show status only if changed
            elif self._status != status:
                self._status = status
                self.debug('status', status, color='yellow', level=2)
        # Return status
        return self._status

    def load(self, extra_keys: Optional[List[str]] = None) -> None:
        """ Load status and step data from the workdir """
        extra_keys = extra_keys or []
        try:
            content: Dict[Any, Any] = tmt.utils.yaml_to_dict(
                self.read('step.yaml'))
            self.debug('Successfully loaded step data.', level=2)
            self.data = content['data']
            for key in extra_keys:
                if key in content:
                    setattr(self, key, content[key])
            self.status(content['status'])
        except tmt.utils.GeneralError:
            self.debug('Step data not found.', level=2)

    def save(self, data: Optional[StepData] = None) -> None:
        """ Save status and step data to the workdir """
        data = data or {}
        content: Dict[Any, Any] = dict(
            status=self.status(), data=self.data)
        content.update(data)
        self.write('step.yaml', tmt.utils.dict_to_yaml(content))

    def wake(self) -> None:
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

        # Importing here to avoid circular imports
        import tmt.steps.report

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
        how: str = self.opt('how')
        if how is not None:
            for data in self.data:
                assert isinstance(data, dict)
                data['how'] = how

    def setup_actions(self) -> None:
        """ Insert login and reboot plugins if requested """
        for login_plugin in Login.plugins(step=self):
            self.debug(
                f"Insert a login plugin into the '{self}' step "
                f"with order '{login_plugin.order}'.", level=2)
            self._phases.append(login_plugin)

        for reboot_plugin in Reboot.plugins(step=self):
            self.debug(
                f"Insert a reboot plugin into the '{self}' step "
                f"with order '{reboot_plugin.order}'.", level=2)
            self._phases.append(reboot_plugin)

    @overload
    def phases(self, classes: None = None) -> List[Phase]:
        pass

    @overload
    def phases(self, classes: Type[PhaseT]) -> List[PhaseT]:
        pass

    @overload
    def phases(self, classes: Tuple[Type[PhaseT], ...]) -> List[PhaseT]:
        pass

    def phases(self, classes: Optional[Union[Type[PhaseT],
               Tuple[Type[PhaseT], ...]]] = None) -> List[PhaseT]:
        """
        Iterate over phases by their order

        By default iterates over all available phases. Optional filter
        'classes' can be used to iterate only over instances of given
        class (single class or tuple of classes).
        """

        if classes is None:
            _classes: Tuple[Union[Type[Phase], Type[PhaseT]], ...] = (Phase,)

        elif not isinstance(classes, tuple):
            _classes = (classes,)

        else:
            _classes = classes

        return sorted(
            [cast(PhaseT, phase) for phase in self._phases if isinstance(phase, _classes)],
            key=lambda phase: phase.order)

    def actions(self) -> None:
        """ Run all loaded Login or Reboot action instances of the step """
        for phase in self.phases(classes=Action):
            phase.go()

    def go(self) -> None:
        """ Execute the test step """
        # Show step header and how
        self.info(self.name, color='blue')
        # Show workdir in verbose mode
        self.debug('workdir', self.workdir, 'magenta')


class Method(object):
    """ Step implementation method """

    class_: Type['BasePlugin']

    def __init__(self, name: str, doc: str, order: int):
        """ Store method data """
        self.name: str = name
        self.doc: str = doc.strip()
        self.order = order

        # Parse summary and description from provided doc string
        lines: List[str] = [re.sub('^    ', '', line)
                            for line in self.doc.split('\n')]
        self.summary: str = lines[0].strip()
        self.description: str = '\n'.join(lines[1:]).lstrip()

    def describe(self) -> str:
        """ Format name and summary for a nice method overview """
        return f'{self.name} '.ljust(22, '.') + f' {self.summary}'

    def usage(self) -> str:
        """ Prepare a detailed usage from summary and description """
        if self.description:
            usage: str = self.summary + '\n\n' + self.description
        else:
            usage = self.summary
        # Disable wrapping for all paragraphs
        return re.sub('\n\n', '\n\n\b\n', usage)


class PluginIndex(type):
    """ Plugin metaclass used to register all available plugins """

    def __init__(
            cls,
            name: str,
            bases: List['BasePlugin'],
            attributes: Any) -> None:
        """ Store all defined methods in the parent class """
        try:
            # Ignore typing here, because mypy mixes cls with self and thinks
            # it is Type[PluginIndex] and cannot be told otherwise
            for method in cls._methods:  # type: ignore
                # Store reference to the implementing class
                method.class_ = cls
                # Add to the list of supported methods in parent class
                bases[0]._supported_methods.append(method)
        except AttributeError:
            pass


class PluginData(TypedDict, total=False):
    """ Step data structure """
    name: Optional[str]
    how: Optional[str]
    order: Optional[int]


class BasePlugin(Phase, metaclass=PluginIndex):
    """ Common parent of all step plugins """

    # Default implementation for all steps is shell
    # except for provision (virtual) and report (display)
    how: str = 'shell'

    # Common keys for all plugins of given step
    _common_keys: List[str] = []

    # Keys specific for given plugin
    _keys: List[str] = []

    # Supported methods
    _methods: List[Method]

    # List of all supported methods aggregated from all plugins
    _supported_methods: List[Method]

    def __init__(
            self,
            step: Step,
            data: StepData,
            workdir: tmt.utils.WorkdirArgumentType = None) -> None:
        """ Store plugin name, data and parent step """

        # Ensure that plugin data contains name
        if 'name' not in data:
            raise tmt.utils.GeneralError(
                f"Missing 'name' in the {step} step config "
                f"of the '{step.plan}' plan.")

        # Initialize plugin order
        if 'order' not in data or data['order'] is None:
            order = tmt.utils.DEFAULT_PLUGIN_ORDER
        else:
            try:
                order = int(data['order'])
            except ValueError:
                raise tmt.utils.SpecificationError(
                    f"Invalid order '{data['order']}' in {step} config "
                    f"'{data['name']}'. Should be an integer.")

        # Store name, data and parent step
        super().__init__(
            parent=step,
            name=data['name'],
            workdir=workdir,
            order=order)
        # It is not possible to use TypedDict here because
        # all keys are not known at the time of the class definition
        self.data = data
        self.step = step

    @classmethod
    def base_command(
            cls,
            usage: str,
            method_class: Optional[Type[click.Command]] = None) -> click.Command:
        """ Create base click command (common for all step plugins) """
        raise NotImplementedError

    @classmethod
    def options(cls, how: Optional[str] = None) -> List[tmt.options.ClickOptionDecoratorType]:
        """ Prepare command line options for given method """
        # Include common options supported across all plugins
        return tmt.options.verbose_debug_quiet + tmt.options.force_dry

    @classmethod
    def command(cls) -> click.Command:
        """ Prepare click command for all supported methods """
        # Create one command for each supported method
        commands: Dict[str, click.Command] = {}
        method_overview: str = f'Supported methods ({cls.how} by default):\n\n\b'
        for method in cls.methods():
            method_overview += f'\n{method.describe()}'
            command: click.Command = cls.base_command(usage=method.usage())
            # Apply plugin specific options
            for option in method.class_.options(method.name):
                command = option(command)
            commands[method.name] = command

        # Create base command with common options using method class
        method_class = tmt.options.create_method_class(commands)
        command = cls.base_command(usage=method_overview, method_class=method_class)
        # Apply common options
        for option in cls.options():
            command = option(command)
        return command

    @classmethod
    def methods(cls) -> List[Method]:
        """ Return all supported methods ordered by priority """
        return sorted(cls._supported_methods, key=lambda method: method.order)

    @classmethod
    def delegate(
            cls,
            step: Step,
            data: StepData) -> 'BasePlugin':
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
                plugin = method.class_(step, data)
                assert isinstance(plugin, BasePlugin)
                return plugin

        show_step_method_hints(step, step.name, data['how'])
        # Report invalid method
        if step.plan is None:
            raise tmt.utils.GeneralError(f"Plan for {step.name} is not set.")
        raise tmt.utils.SpecificationError(
            f"Unsupported {step.name} method '{data['how']}' "
            f"in the '{step.plan.name}' plan.")

    def default(self, option: str, default: Optional[Any] = None) -> Any:
        """ Return default data for given option """
        return default

    def get(self, option: str, default: Optional[Any] = None) -> Any:
        """ Get option from plugin data, user/system config or defaults """
        # Check plugin data first
        try:
            # FIXME Enable type check once StepData defined more precisely
            return self.data[option]  # type: ignore
        except KeyError:
            pass

        # Check user config and system config
        # TODO

        # Finally check plugin defaults
        return self.default(option, default)

    def show(self, keys: Optional[List[str]] = None) -> None:
        """ Show plugin details for given or all available keys """
        # Show empty config with default method only in verbose mode
        if (set(self.data.keys()) == set(['how', 'name'])
                and not self.opt('verbose')
                and self.data['how'] == self.how):
            return
        # Step name (and optional summary)
        echo(tmt.utils.format(
            self.step.name, self.get('summary', ''),
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

    def enabled_on_guest(self, guest: 'Guest') -> bool:
        """ Check if the plugin is enabled on the specific guest """
        where: str = self.get('where')
        if not where:
            return True
        return where in (guest.name, guest.role)

    def wake(self, keys: Optional[List[str]] = None) -> None:
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
                # FIXME Enable type check once StepData defined more precisely
                self.data[key] = value  # type: ignore

    # NOTE: it's tempting to rename this method to `go()` and use more natural
    # `super().go()` in child classes' `go()` methods. But, `go()` does not have
    # the same signature across all plugin types, therefore we cannot have shared
    # `go()` method in superclass - overriding it in (some) child classes would
    # raise a typing linter error reporting superclass signature differs from the
    # one in a subclass.
    #
    # Therefore we need a different name, and a way how not to forget to call this
    # method from child classes.
    def go_prolog(self) -> None:
        """ Perform actions shared among plugins when beginning their tasks """
        # Show the method
        self.info('how', self.get('how'), 'magenta')
        # Give summary if provided
        if self.get('summary'):
            self.info('summary', self.get('summary'), 'magenta')
        # Show name only if it's not the default one
        if self.name != tmt.utils.DEFAULT_NAME:
            self.info('name', self.name, 'magenta')
        # Include order in verbose mode
        self.verbose('order', str(self.order), 'magenta', level=3)

    def requires(self) -> List[str]:
        """ List of packages required by the plugin on the guest """
        return []


class GuestlessPlugin(BasePlugin):
    """ Common parent of all step plugins that do not work against a particular guest """

    def go(self) -> None:
        """ Perform actions shared among plugins when beginning their tasks """

        self.go_prolog()


class Plugin(BasePlugin):
    """ Common parent of all step plugins that do work against a particular guest """

    def go(self, guest: 'Guest') -> None:
        """ Perform actions shared among plugins when beginning their tasks """

        self.go_prolog()


class Action(Phase):
    """ A special action performed during a normal step. """

    # Dictionary containing list of requested phases for each enabled step
    _phases: Optional[Dict[str, List[int]]] = None

    @classmethod
    def phases(cls, step: Step) -> List[int]:
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
    def _parse_phases(cls, step: Step) -> Dict[str, List[int]]:
        """ Parse options and store phase order """
        phases = dict()
        options: List[str] = cls._opt('step', default=[])

        # Use the end of the last enabled step if no --step given
        if not options:
            login_during: Optional[Step] = None
            # The last run may have failed before all enabled steps were
            # completed, select the last step done
            if step.plan is None:
                raise tmt.utils.GeneralError(
                    f"Plan for {step.name} is not set.")
            if step.plan.my_run.opt('last'):
                steps: List[Step] = [
                    s for s in step.plan.steps() if s.status() == 'done']
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
                    phase = cast(Dict[str, int],
                                 dict(start=PHASE_START, end=PHASE_END))[phase]
                except KeyError:
                    raise tmt.utils.GeneralError(f"Invalid phase '{phase}'.")
            # Store the phase for given step
            try:
                phases[step_name].append(phase)
            except KeyError:
                phases[step_name] = [phase]
        return phases

    def go(self) -> None:
        raise NotImplementedError()


class Reboot(Action):
    """ Reboot guest """

    # True if reboot enabled
    _enabled: bool = False

    def __init__(self, step: Step, order: int) -> None:
        """ Initialize relations, store the reboot order """
        super().__init__(parent=step, name='reboot', order=order)

    @classmethod
    def command(
            cls,
            method_class: Optional[Method] = None,
            usage: Optional[str] = None) -> click.Command:
        """ Create the reboot command """
        @click.command()
        @click.pass_context
        @click.option(
            '-s', '--step', metavar='STEP[:PHASE]', multiple=True,
            help='Reboot machine during given phase of selected step(s).')
        @click.option(
            '--hard', is_flag=True,
            help='Hard reboot of the machine. Unsaved data may be lost.')
        def reboot(context: Any, **kwargs: Any) -> None:
            """ Reboot the guest. """
            Reboot._save_context(context)
            Reboot._enabled = True

        return reboot

    @classmethod
    def plugins(cls, step: Step) -> List['Reboot']:
        """ Return list of reboot instances for given step """
        if not Reboot._enabled:
            return []
        return [Reboot(step, phase) for phase in cls.phases(step)]

    def go(self) -> None:
        """ Reboot the guest(s) """
        self.info('reboot', 'Rebooting guest', color='yellow')
        assert isinstance(self.parent, Step)
        assert hasattr(self.parent, 'plan') and self.parent.plan is not None
        for guest in self.parent.plan.provision.guests():
            guest.reboot(self.opt('hard'))
        self.info('reboot', 'Reboot finished', color='yellow')


class Login(Action):
    """ Log into the guest """

    # True if interactive login enabled
    _enabled: bool = False

    def __init__(self, step: Step, order: int):
        """ Initialize relations, store the login order """
        super().__init__(parent=step, name='login', order=order)

    @classmethod
    def command(
            cls,
            method_class: Optional[Method] = None,
            usage: Optional[str] = None) -> click.Command:
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
        def login(context: Any, **kwargs: Any) -> None:
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
    def plugins(cls, step: Step) -> List['Login']:
        """ Return list of login instances for given step """
        if not Login._enabled:
            return []
        return [Login(step, phase) for phase in cls.phases(step)]

    def go(self) -> None:
        """ Login to the guest(s) """
        # Verify possible test result condition
        count: Dict[str, int] = dict()
        expected_results: Optional[List[str]] = self.opt('when')

        assert isinstance(self.parent, Step)
        assert hasattr(self.parent, 'plan') and self.parent.plan is not None

        if expected_results:
            for expected_result in expected_results:
                count[expected_result] = len([
                    result for result in self.parent.plan.execute.results()
                    if result.result == expected_result])
            if not any(count.values()):
                self.info('Skipping interactive shell', color='yellow')
                return

        # Run the interactive command
        commands: List[str] = self.opt('command')
        self.info('login', 'Starting interactive shell', color='yellow')
        for guest in self.parent.plan.provision.guests():
            # Attempt to push the workdir to the guest
            try:
                guest.push()
                cwd: Optional[str] = self.parent.plan.worktree
            except tmt.utils.GeneralError:
                self.warn("Failed to push workdir to the guest.")
                cwd = None
            # Execute all requested commands
            for command in commands:
                self.debug(f"Run '{command}' in interactive mode.")
                guest.execute(command, interactive=True, cwd=cwd)
        self.info('login', 'Interactive shell finished', color='yellow')
