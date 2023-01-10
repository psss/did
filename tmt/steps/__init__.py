
""" Step Classes """

import dataclasses
import os
import re
import shutil
import sys
import textwrap
from typing import (TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple,
                    Type, TypeVar, Union, cast, overload)

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

import click
from click import echo

import tmt.log
import tmt.options
import tmt.utils
from tmt.options import show_step_method_hints

if TYPE_CHECKING:
    import tmt.base
    import tmt.cli
    from tmt.base import Plan
    from tmt.steps.provision import Guest


DEFAULT_PLUGIN_METHOD_ORDER: int = 50


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
            *,
            order: int = tmt.utils.DEFAULT_PLUGIN_ORDER,
            **kwargs: Any):
        super().__init__(**kwargs)
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

# A type alias for plugin classes
PluginClass = Type['BasePlugin']

_RawStepData = TypedDict('_RawStepData', {
    'how': str,
    'name': str
    }, total=False)

RawStepDataArgument = Union[_RawStepData, List[_RawStepData]]


T = TypeVar('T', bound='StepData')


@dataclasses.dataclass
class StepData(
        tmt.utils.SpecBasedContainer,
        tmt.utils.NormalizeKeysMixin,
        tmt.utils.SerializableContainer):
    """
    Keys necessary to describe, create, save and restore a step.

    Very basic set of keys shared across all steps.

    Provides basic functionality for transition between "raw" step data, which
    consists of fmf nodes and CLI options, and this container representation with
    keys and types more suitable for internal use.

    Implementation expects simple 1:1 relation between ``StepData`` attributes - keys -
    and their fmf/CLI sources, where keys replace options' dashes (``-``) with
    underscores (``_``). For example, to hold value of an fmf key ``foo-bar`` - or
    value of a corresponding CLI option, ``--foo-bar``, a step data class should
    declare key named ``foo_data``. All ``StepData`` methods would honor this mapping.
    """

    # TODO: we can easily add lists of keys for various verbosity levels...
    KEYS_SHOW_ORDER = ['name', 'how']

    name: str
    how: str
    order: int = tmt.utils.DEFAULT_PLUGIN_ORDER
    summary: Optional[str] = None

    # ignore[override]: expected, we do want to return more specific
    # type than the one declared in superclass.
    def to_spec(self) -> _RawStepData:  # type: ignore[override]
        """ Convert to a form suitable for saving in a specification file """

        return cast(_RawStepData, {
            tmt.utils.key_to_option(key): value
            for key, value in self.items()
            })

    @classmethod
    def pre_normalization(cls, raw_data: _RawStepData, logger: tmt.log.Logger) -> None:
        """ Called before normalization, useful for tweaking raw data """

        logger.debug(f'{cls.__name__}: original raw data', str(raw_data), level=4)

    def post_normalization(self, raw_data: _RawStepData, logger: tmt.log.Logger) -> None:
        """ Called after normalization, useful for tweaking normalized data """

        pass

    # ignore[override]: expected, we do want to accept more specific
    # type than the one declared in superclass.
    @classmethod
    def from_spec(  # type: ignore[override]
            cls: Type[T],
            raw_data: _RawStepData,
            logger: tmt.log.Logger) -> T:
        """ Convert from a specification file or from a CLI option """

        cls.pre_normalization(raw_data, logger)

        data = cls(name=raw_data['name'], how=raw_data['how'])
        data._load_keys(cast(Dict[str, Any], raw_data), cls.__name__, logger)

        data.post_normalization(raw_data, logger)

        return data


@dataclasses.dataclass
class WhereableStepData:
    """
    Keys shared by step data that may be limited to a particular guest.

    To be used as a mixin class, adds necessary keys.

    See [1] and [2] for specification.

    1. https://tmt.readthedocs.io/en/stable/spec/plans.html#where
    2. https://tmt.readthedocs.io/en/stable/spec/plans.html#spec-plans-prepare-where
    """

    where: Optional[str] = None


class Step(tmt.utils.Common):
    """ Common parent of all test steps """

    # Default implementation for all steps is "shell", but some
    # steps like provision may have better defaults for their
    # area of expertise.
    DEFAULT_HOW: str = 'shell'

    # Refers to a base class for all plugins registered with this step.
    _plugin_base_class: PluginClass

    #: Stores the normalized step data. Initialized first time step's `data`
    #: is accessed.
    #
    # The delayed initialization is necessary to support `how` changes via
    # command-line - code instantiating steps must be able to invalidate
    # and replace raw step data entries before they get normalized and become
    # the single source of information for plugins involved.
    _data: List[StepData]

    #: Stores the original raw step data. Initialized by :py:meth:`__init__`
    #: or :py:meth:`wake`, and serves as a source for normalization performed
    #: by :py:meth:`_normalize_data`.
    _raw_data: List[_RawStepData]

    # The step has pruning capability to remove all irrelevant files. All
    # important files located in workdir should be specified in the list below
    # to avoid deletion during pruning.
    _preserved_files: List[str] = ['step.yaml']

    def __init__(
            self,
            *,
            plan: 'Plan',
            data: Optional[RawStepDataArgument] = None,
            name: Optional[str] = None,
            workdir: tmt.utils.WorkdirArgumentType = None,
            logger: tmt.log.Logger) -> None:
        """ Initialize and check the step data """
        logger.apply_verbosity_options(**self.__class__._options)

        super().__init__(name=name, parent=plan, workdir=workdir, logger=logger)

        # Initialize data
        self.plan: 'Plan' = plan
        self._status: Optional[str] = None
        self._phases: List[Phase] = []

        # Normalize raw data to be a list of step configuration data, one item per
        # distinct step configuration. Make sure all items have `name`` and `how` keys.
        #
        # NOTE: this is not a normalization step as performed by NormalizeKeysMixin.
        # Here we make sure the raw data can be consumed by the delegation code, we
        # do not modify any existing content of raw data items.

        # Create an empty step by default (can be updated from cli)
        if data is None:
            self._raw_data = [{}]

        # Convert to list if only a single config provided
        elif isinstance(data, dict):
            self._raw_data = [data]

        # List is as good as it gets
        elif isinstance(data, list):
            self._raw_data = data

        # Shout about invalid configuration
        else:
            raise tmt.utils.GeneralError(
                f"Invalid '{self}' config in '{self.plan}'.")

        for i, raw_datum in enumerate(self._raw_data):
            # Add default unique names even to multiple configs so that the users
            # don't need to specify it if they don't care about the name
            if raw_datum.get('name', None) is None:
                raw_datum['name'] = f'{tmt.utils.DEFAULT_NAME}-{i}'

            # Set 'how' to the default if not specified
            if raw_datum.get('how', None) is None:
                raw_datum['how'] = self.DEFAULT_HOW

    def _normalize_data(
            self,
            raw_data: List[_RawStepData],
            logger: tmt.log.Logger) -> List[StepData]:
        """
        Normalize step data entries.

        Every entry of ``raw_data`` is converted into an instance of
        :py:class:`StepData` or one of its subclasses. Particular class
        is derived from a plugin identified by raw data's ``how`` field
        and step's plugin registry.
        """

        data: List[StepData] = []

        for raw_datum in raw_data:
            plugin = self._plugin_base_class.delegate(self, raw_data=raw_datum)

            data.append(plugin.data)

        return data

    @property
    def data(self) -> List[StepData]:
        if not hasattr(self, '_data'):
            self._data = self._normalize_data(self._raw_data, self._logger)

        return self._data

    @data.setter
    def data(self, data: List[StepData]) -> None:
        self._data = data

    @property
    def enabled(self) -> Optional[bool]:
        """ True if the step is enabled """
        if self.plan.my_run is None or self.plan.my_run._context_object is None:
            return None

        return self.name in self.plan.my_run._context_object.steps

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

        usage = textwrap.dedent(cls.__doc__)
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

    def show(self) -> None:
        """ Show step details """

        for data in self.data:
            self._plugin_base_class.delegate(self, data=data).show()

    def load(self) -> None:
        """ Load status and step data from the workdir """
        try:
            raw_step_data: Dict[Any, Any] = tmt.utils.yaml_to_dict(self.read('step.yaml'))
            self.debug('Successfully loaded step data.', level=2)

            self.data = [
                StepData.unserialize(raw_datum) for raw_datum in raw_step_data['data']
                ]
            self.status(raw_step_data['status'])
        except tmt.utils.GeneralError:
            self.debug('Step data not found.', level=2)

    def save(self) -> None:
        """ Save status and step data to the workdir """
        content: Dict[str, Any] = {
            'status': self.status(),
            'data': [datum.to_serialized() for datum in self.data]
            }
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
                self.data[0].how in ['display', 'html']):
            self.debug("Report step always force mode enabled.")
            self._workdir_cleanup()
            self.status('todo')

        # Nothing more to do when the step is already done
        if self.status() == 'done':
            self.debug('Step is done, not touching its data.')
            return

        # Override step data with command line options
        how: str = self.opt('how')
        if how is not None:
            # If 'how' has been given, when it comes to current entries in `self.data`,
            # there are two options:
            #
            # * entry's `how` is the same as the one given via command-line. Then we can
            # keep step data we already have.
            # * entry's `how` is different, and then we need to throw the entry away and
            # replace it with new `how`.
            #
            # To handle both variants, we replace `self.data` with new set of entries,
            # based on newly constructed set of raw data.
            self.debug(f'CLI-provided how={how} overrides all existing step data', level=4)

            _raw_data: List[_RawStepData] = []

            # Do NOT iterate over `self.data`: reading `self.data` would trigger materialization
            # of its content, calling plugins owning various raw step data to create corresponding
            # `StepData` instances. That is actually harmful, as plugins that might be explicitly
            # overriden by `--how` option, would run, with unexpected side-effects.
            # Instead, iterate over raw data, and replace incompatible plugins with the one given
            # on command line. There is no reason to ever let dropped plugin's `StepData` to
            # materialize when it's going to be thrown away anyway.
            for raw_datum in self._raw_data:
                # We can re-use this one - to make handling easier, just dump it to "raw"
                # form for _normalize_data().
                if raw_datum['how'] == how:
                    self.debug(f'  compatible step data:   {raw_datum}', level=4)
                    _raw_data.append(raw_datum)

                # Mismatch, throwing away, replacing with new `how` - but we can keep the name.
                else:
                    self.debug(f'  incompatible step data: {raw_datum}', level=4)
                    _raw_data.append({
                        'name': raw_datum['name'],
                        'how': how
                        })

            self.data = self._normalize_data(_raw_data, self._logger)
            self._raw_data = _raw_data

            self.debug('updated data', str(self.data), level=4)

        else:
            self.debug('CLI did not change existing step data', level=4)

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

    def prune(self) -> None:
        """ Remove all uninteresting files from the step workdir """
        if self.workdir is None:
            return
        self.debug(f"Prune workdir '{self.workdir}'.", level=3, shift=1)

        # Do not prune plugin workdirs, each plugin decides what should
        # be pruned from the workdir and what should be kept there
        plugins = self.phases(classes=BasePlugin)
        plugin_workdirs = []
        for plugin in plugins:
            if plugin.workdir is not None:
                plugin_workdirs.append(os.path.basename(plugin.workdir))
            plugin.prune()

        # Prune everything except for the preserved files
        preserved_files = self._preserved_files + plugin_workdirs
        for file in os.listdir(self.workdir):
            if file in preserved_files:
                continue
            full_path = os.path.join(self.workdir, file)
            self.debug(f"Remove '{full_path}'.", level=3, shift=1)
            try:
                if os.path.isfile(full_path) or os.path.islink(full_path):
                    os.remove(full_path)
                else:
                    shutil.rmtree(full_path)
            except OSError as error:
                self.warn(f"Unable to remove '{full_path}': {error}", shift=1)


class Method:
    """ Step implementation method """

    def __init__(
            self,
            name: str,
            class_: Optional[PluginClass] = None,
            doc: Optional[str] = None,
            order: int = DEFAULT_PLUGIN_METHOD_ORDER
            ) -> None:
        """ Store method data """

        doc = (doc or getattr(class_, '__doc__') or '').strip()

        if not doc:
            if class_:
                raise tmt.utils.GeneralError(f"Plugin class '{class_}' provides no docstring.")

            raise tmt.utils.GeneralError(f"Plugin method '{name}' provides no docstring.")

        self.name = name
        self.class_ = class_
        self.doc = doc
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


def provides_method(
        name: str,
        doc: Optional[str] = None,
        order: int = DEFAULT_PLUGIN_METHOD_ORDER) -> Callable[[PluginClass], PluginClass]:
    """
    A plugin class decorator to register plugin's method with tmt steps.

    In the following example, developer marks ``SomePlugin`` as providing two discover methods,
    ``foo`` and ``bar``, with ``bar`` being sorted to later position among methods:

    .. code-block:: python

       @tmt.steps.provides_method('foo')
       @tmt.steps.provides_method('bar', order=80)
       class SomePlugin(tmt.steps.discover.DicoverPlugin):
         ...

    :param name: name of the method.
    :param doc: method documentation. If not specified, docstring of the decorated class is used.
    :param order: order of the method among other step methods.
    """

    def _method(cls: PluginClass) -> PluginClass:
        plugin_method = Method(name, class_=cls, doc=doc, order=order)

        # FIXME: make sure cls.__bases__[0] is really BasePlugin class
        cast('BasePlugin', cls.__bases__[0])._supported_methods.append(plugin_method)

        return cls

    return _method


class BasePlugin(Phase):
    """ Common parent of all step plugins """

    # Deprecated, use @provides_method(...) instead. left for backward
    # compatibility with out-of-tree plugins.
    _methods: List[Method] = []

    # Default implementation for all steps is shell
    # except for provision (virtual) and report (display)
    how: str = 'shell'

    # List of all supported methods aggregated from all plugins of the same step.
    _supported_methods: List[Method] = []

    _data_class: Type[StepData] = StepData
    data: StepData

    # TODO: do we need this list? Can whatever code is using it use _data_class directly?
    # List of supported keys
    # (used for import/export to/from attributes during load and save)
    @property
    def _keys(self) -> List[str]:
        return list(self._data_class.keys())

    def __init__(
            self,
            *,
            step: Step,
            data: StepData,
            workdir: tmt.utils.WorkdirArgumentType = None,
            logger: tmt.log.Logger) -> None:
        """ Store plugin name, data and parent step """
        logger.apply_verbosity_options(**self.__class__._options)

        # Store name, data and parent step
        super().__init__(
            logger=logger,
            parent=step,
            name=data.name,
            workdir=workdir,
            order=data.order)

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
        return [
            metadata.option
            for metadata in (
                tmt.utils.dataclass_field_metadata(field)
                for field in dataclasses.fields(cls._data_class)
                )
            if metadata.option is not None
            ] + tmt.options.VERBOSITY_OPTIONS + tmt.options.FORCE_DRY_OPTIONS

    @classmethod
    def command(cls) -> click.Command:
        """ Prepare click command for all supported methods """
        # Create one command for each supported method
        commands: Dict[str, click.Command] = {}
        method_overview: str = f'Supported methods ({cls.how} by default):\n\n\b'
        for method in cls.methods():
            assert method.class_ is not None
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
            data: Optional[StepData] = None,
            raw_data: Optional[_RawStepData] = None) -> 'BasePlugin':
        """
        Return plugin instance implementing the data['how'] method

        Supports searching by method prefix as well (e.g. 'virtual').
        The first matching method with the lowest 'order' wins.
        """

        if data is not None:
            how = data.how
        elif raw_data is not None:
            how = raw_data['how']
        else:
            raise tmt.utils.GeneralError('Either data or raw data must be given.')

        step.debug(
            f'{cls.__name__}.delegate(step={step}, data={data}, raw_data={raw_data})',
            level=3)

        # Filter matching methods, pick the one with the lowest order
        for method in cls.methods():
            assert method.class_ is not None
            if method.name.startswith(how):
                step.debug(
                    f"Using the '{method.class_.__name__}' plugin "
                    f"for the '{how}' method.", level=2)

                plugin_class = method.class_
                plugin_data_class = plugin_class._data_class

                # If we're given raw data, construct a step data instance, applying
                # normalization in the process.
                if raw_data is not None:
                    try:
                        data = plugin_data_class.from_spec(raw_data, step._logger)

                    except Exception as exc:
                        raise tmt.utils.GeneralError(
                            f'Failed to load step data for {plugin_data_class.__name__}: {exc}') \
                            from exc

                assert data is not None
                assert data.__class__ is plugin_data_class, \
                    f'Data package is instance of {data.__class__.__name__}, ' \
                    f'plugin {plugin_class.__name__} ' \
                    f'expects {plugin_data_class.__name__}'

                plugin = plugin_class(
                    logger=step._logger.descend(logger_name=None),
                    step=step,
                    data=data
                    )
                assert isinstance(plugin, BasePlugin)
                return plugin

        show_step_method_hints(step, step.name, how)
        # Report invalid method
        if step.plan is None:
            raise tmt.utils.GeneralError(f"Plan for {step.name} is not set.")
        raise tmt.utils.SpecificationError(
            f"Unsupported {step.name} method '{how}' "
            f"in the '{step.plan.name}' plan.")

    def default(self, option: str, default: Optional[Any] = None) -> Any:
        """ Return default data for given option """

        value = self._data_class.default(tmt.utils.option_to_key(option), default=default)

        if value is None:
            return default

        return value

    def get(self, option: str, default: Optional[Any] = None) -> Any:
        """ Get option from plugin data, user/system config or defaults """

        # Check plugin data first
        #
        # Since self.data is a dataclass instance, the option would probably exist.
        # As long as there's no typo in name, it would be defined. Which complicates
        # the handling of "default" as in "return *this* when attribute is unset".
        key = tmt.utils.option_to_key(option)

        try:
            value = getattr(self.data, key)

            # If the value is no longer the default one, return the value. If it
            # still matches the default value, instead of returning the default
            # value right away, call `self.default()` so the plugin has chance to
            # catch calls for computed or virtual keys, keys that don't exist as
            # atributes of our step data.
            #
            # One way would be to subclass step's base plugin class' step data class
            # (which is a subclass of `StepData` and `SerializedContainer`), and
            # override its `default()` method to handle these keys. But, plugins often
            # are pretty happy with the base data class, many don't need their own
            # step data class, and plugin developer might be forced to create a subclass
            # just for this single method override.
            #
            # Instead, keep plugin's `default()` around - everyone can use it to get
            # default value for a given option/key, and plugins can override it as needed
            # (they will always subclass step's base plugin class anyway!). Default
            # implementation would delegate to step data `default()`, and everyone's
            # happy.

            if value != self.data.default(key):
                return value

        except AttributeError:
            pass

        return self.default(option, default)

    def show(self, keys: Optional[List[str]] = None) -> None:
        """ Show plugin details for given or all available keys """
        # Avoid circular imports
        import tmt.base

        # Show empty config with default method only in verbose mode
        if self.data.is_bare and not self.opt('verbose'):
            return
        # Step name (and optional summary)
        echo(tmt.utils.format(
            self.step.name, self.get('summary') or '',
            key_color='blue', value_color='blue'))
        # Show all or requested step attributes
        if keys is None:
            keys = list(set(self.data.keys()))

        def _emit_key(key: str) -> None:
            # Skip showing the default name
            if key == 'name' and self.name.startswith(tmt.utils.DEFAULT_NAME):
                return

            # Skip showing summary again
            if key == 'summary':
                return

            value = self.get(key)

            # No need to show the default order
            if key == 'order' and value == tmt.base.DEFAULT_ORDER:
                return

            if value is None:
                return

            # TODO: hides keys that were used to be in the output...
            # if value == self.data.default(key):
            #     return

            echo(tmt.utils.format(tmt.utils.key_to_option(key), value))

        # First, follow the order prefered by step data, but emit only the keys
        # that are allowed. Each emitted key would be removed so we wouldn't
        # emit it again when showing the unsorted rest of keys.
        for key in self.data.KEYS_SHOW_ORDER:
            if key not in keys:
                continue

            _emit_key(key)

            keys.remove(key)

        # Show the rest
        for key in keys:
            _emit_key(key)

    def enabled_on_guest(self, guest: 'Guest') -> bool:
        """ Check if the plugin is enabled on the specific guest """
        where: str = self.get('where')
        if not where:
            return True
        return where in (guest.name, guest.role)

    def _update_data_from_options(self, keys: Optional[List[str]] = None) -> None:
        """
        Update plugin data with values provided by CLI options.

        Called by the plugin wake-up mechanism to allow CLI options to take an
        effect.

        :param keys: if specified, only the listed keys would be affected.
        """

        keys = keys or list(self.data.keys())

        for keyname in keys:
            value = self.opt(tmt.utils.key_to_option(keyname))

            # TODO: this test is incorrect. It should not test for false-ish values,
            # but rather check whether the value returned by `self.opt()` is or is
            # not option default. And that's apparently not trivial with current CLI
            # handling.
            if value is None or value == [] or value == () or value is False:
                continue

            tmt.utils.dataclass_normalize_field(self.data, keyname, value, self._logger)

    def wake(self) -> None:
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

        assert self.data.__class__ is self._data_class, \
            f'Plugin {self.__class__.__name__} woken with incompatible ' \
            f'data {self.data}, ' \
            f'expects {self._data_class.__name__}'

        if self.step.status() == 'done':
            self.debug('step is done, not overwriting plugin data')
            return

        # TODO: conflicts with `upgrade` plugin which does this on purpose :/
        # if self.opt('how') is not None:
        #     assert self.opt('how') in [method.name for method in self.methods()], \
        #         f'Plugin {self.__class__.__name__} woken with unsupported ' \
        #         f'how "{self.opt("how")}", ' \
        #         f'supported methods {", ".join([method.name for method in self.methods()])}, ' \
        #         f'current data is {self.data}'

        self._update_data_from_options()

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
        if not self.name.startswith(tmt.utils.DEFAULT_NAME):
            self.info('name', self.name, 'magenta')
        # Include order in verbose mode
        self.verbose('order', str(self.order), 'magenta', level=3)

    def requires(self) -> List[str]:
        """ List of packages required by the plugin on the guest """
        return []

    def prune(self) -> None:
        """
        Prune uninteresting files from the plugin workdir

        By default we remove the whole workdir. Individual plugins can
        override this method to keep files and directories which are
        useful for inspection when the run is finished.
        """
        if self.workdir is None:
            return
        self.debug(f"Remove plugin workdir '{self.workdir}'.", level=3)
        try:
            shutil.rmtree(self.workdir)
        except OSError as error:
            self.warn(f"Unable to remove '{self.workdir}': {error}")


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
            assert step.plan.my_run is not None  # narrow type
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

    def __init__(self, *, step: Step, order: int, logger: tmt.log.Logger) -> None:
        """ Initialize relations, store the reboot order """
        super().__init__(logger=logger, parent=step, name='reboot', order=order)

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
        def reboot(context: 'tmt.cli.Context', **kwargs: Any) -> None:
            """ Reboot the guest. """
            Reboot._save_context(context)
            Reboot._enabled = True

        return reboot

    @classmethod
    def plugins(cls, step: Step) -> List['Reboot']:
        """ Return list of reboot instances for given step """
        if not Reboot._enabled:
            return []
        return [Reboot(logger=step._logger.descend(), step=step, order=phase)
                for phase in cls.phases(step)]

    def go(self) -> None:
        """ Reboot the guest(s) """
        self.info('reboot', 'Rebooting guest', color='yellow')
        assert isinstance(self.parent, Step)
        assert hasattr(self.parent, 'plan') and self.parent.plan is not None
        for guest in self.parent.plan.provision.guests():
            guest.reboot(hard=self.opt('hard'))
        self.info('reboot', 'Reboot finished', color='yellow')


class Login(Action):
    """ Log into the guest """

    # TODO: remove when Step becomes Generic (#1372)
    # Change typing of inherited attr
    parent: Step

    # True if interactive login enabled
    _enabled: bool = False

    def __init__(self, *, step: Step, order: int, logger: tmt.log.Logger) -> None:
        """ Initialize relations, store the login order """
        super().__init__(logger=logger, parent=step, name='login', order=order)

    @classmethod
    def command(
            cls,
            method_class: Optional[Method] = None,
            usage: Optional[str] = None) -> click.Command:
        """ Create the login command """
        # Avoid circular imports
        from tmt.result import ResultOutcome

        @click.command()
        @click.pass_context
        @click.option(
            '-s', '--step', metavar='STEP[:PHASE]', multiple=True,
            help='Log in during given phase of selected step(s).')
        @click.option(
            '-w', '--when', metavar='RESULT', multiple=True,
            type=click.Choice([m.value for m in ResultOutcome.__members__.values()]),
            help='Log in if a test finished with given result(s).')
        @click.option(
            '-c', '--command', metavar='COMMAND',
            multiple=True, default=['bash'],
            help="Run given command(s). Default is 'bash'.")
        @click.option(
            '-t', '--test', is_flag=True,
            help='Log into the guest after each executed test in the execute phase.')
        def login(context: 'tmt.cli.Context', **kwargs: Any) -> None:
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
        return [Login(logger=step._logger.descend(), step=step, order=phase)
                for phase in cls.phases(step)]

    def go(self) -> None:
        """ Login to the guest(s) """

        if self._enabled_by_results(self.parent.plan.execute.results()):
            self._login()

    def _enabled_by_results(self, results: List['tmt.base.Result']) -> bool:
        """ Verify possible test result condition """
        # Avoid circular imports
        from tmt.result import ResultOutcome
        expected_results: Optional[List[ResultOutcome]] = [ResultOutcome.from_spec(
            raw_expected_result) for raw_expected_result in self.opt('when', [])]

        # Return True by default -> no expected results
        if not expected_results:
            return True

        # Check for expected result
        for result in results:
            if result.result in expected_results:
                return True
        else:  # No break/return in for cycle
            self.info('Skipping interactive shell', color='yellow')
            return False

    def _login(
            self,
            cwd: Optional[str] = None,
            env: Optional[tmt.utils.EnvironmentType] = None) -> None:
        """ Run the interactive command """
        scripts = [tmt.utils.ShellScript(script) for script in self.opt('command')]
        self.info('login', 'Starting interactive shell', color='yellow')
        for guest in self.parent.plan.provision.guests():
            # Attempt to push the workdir to the guest
            try:
                guest.push()
                cwd = cwd or self.parent.plan.worktree
            except tmt.utils.GeneralError:
                self.warn("Failed to push workdir to the guest.")
                cwd = None
            # Execute all requested commands
            for script in scripts:
                self.debug(f"Run '{script}' in interactive mode.")
                guest.execute(script, interactive=True, cwd=cwd, env=env)
        self.info('login', 'Interactive shell finished', color='yellow')

    def after_test(
            self,
            result: 'tmt.base.Result',
            cwd: Optional[str] = None,
            env: Optional[tmt.utils.EnvironmentType] = None) -> None:
        """ Check and login after test execution """
        if self._enabled_by_results([result]):
            self._login(cwd, env)
