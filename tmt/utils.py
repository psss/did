
""" Test Metadata Utilities """

import contextlib
import dataclasses
import datetime
import functools
import glob
import io
import os
import pprint
import re
import shlex
import shutil
import subprocess
import sys
import unicodedata
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from threading import Thread
from typing import (IO, TYPE_CHECKING, Any, Dict, Generator, Iterable, List,
                    NamedTuple, Optional, Pattern, Tuple, Type, TypeVar, Union,
                    cast, overload)

import click
import fmf
import pkg_resources
import requests
import requests.adapters
import requests.packages.urllib3.util.retry
import urllib3.exceptions
from click import echo, style, wrap_text
from ruamel.yaml import YAML, scalarstring
from ruamel.yaml.comments import CommentedMap

if sys.version_info >= (3, 8):
    from typing import Literal, Protocol
else:
    from typing_extensions import Literal, Protocol


if TYPE_CHECKING:
    import tmt.base


log = fmf.utils.Logging('tmt').logger

# Default workdir root and max
WORKDIR_ROOT = '/var/tmp/tmt'
WORKDIR_MAX = 1000

# Log in workdir
LOG_FILENAME = 'log.txt'

# Maximum number of lines of stdout/stderr to show upon errors
OUTPUT_LINES = 100
# Default output width
OUTPUT_WIDTH = 79

# Hierarchy indent
INDENT = 4

# Default name and order for step plugins
DEFAULT_NAME = 'default'
DEFAULT_PLUGIN_ORDER = 50
DEFAULT_PLUGIN_ORDER_MULTIHOST = 10
DEFAULT_PLUGIN_ORDER_REQUIRES = 70
DEFAULT_PLUGIN_ORDER_RECOMMENDS = 75

# Config directory
CONFIG_PATH = '~/.config/tmt'

# Special process return code
PROCESS_TIMEOUT = 124

# Default select.select(timeout) in seconds
DEFAULT_SELECT_TIMEOUT = 5

# Shell options to be set for all run shell scripts
SHELL_OPTIONS = 'set -eo pipefail'

# Defaults for HTTP/HTTPS retries and timeouts (see `retry_session()`).
DEFAULT_RETRY_SESSION_RETRIES: int = 3
DEFAULT_RETRY_SESSION_BACKOFF_FACTOR: float = 0.1

# Defaults for HTTP/HTTPS retries for getting environment file
# Retry with exponential backoff, maximum duration ~511 seconds
ENVFILE_RETRY_SESSION_RETRIES: int = 10
ENVFILE_RETRY_SESSION_BACKOFF_FACTOR: float = 1

# A stand-in variable for generic use.
T = TypeVar('T')

# A FMF context type, representing name/values context.
FmfContextType = Dict[str, List[str]]

# A "environment" type, representing name/value environment variables.
EnvironmentType = Dict[str, str]

# Workdir argument type, can be True, a string, a path or None
WorkdirArgumentType = Union[Literal[True], str, None]

# Workdir type, can be None or a string
WorkdirType = Optional[str]

# Option to skip to initialize work tree in plan
PLAN_SKIP_WORKTREE_INIT = 'plan_skip_worktree_init'


class BaseLoggerFnType(Protocol):
    def __call__(
            self,
            key: str,
            value: Optional[str] = None,
            color: Optional[str] = None,
            shift: int = 0,
            level: int = 1,
            err: bool = False) -> None:
        pass


class LevelessLoggerFnType(Protocol):
    def __call__(
            self,
            key: str,
            value: Optional[str] = None,
            color: Optional[str] = None,
            shift: int = 0,
            err: bool = False) -> None:
        pass


class SemanticLoggerFnType(Protocol):
    def __call__(self, message: str, shift: int = 0) -> None:
        pass


LoggerFnType = Union[
    BaseLoggerFnType,
    LevelessLoggerFnType,
    SemanticLoggerFnType]


def indent(
        key: str,
        value: Optional[str] = None,
        color: Optional[str] = None,
        level: int = 0) -> str:
    """
    Indent a key/value message.

    If both ``key`` and ``value`` are specified, ``{key}: {value}``
    message is rendered. Otherwise, just ``key`` is used alone. If
    ``value`` contains multiple lines, each but the very first line is
    indented by one extra level.

    :param value: optional value to print at right side of ``key``.
    :param color: optional color to apply on ``key``.
    :param level: number of indentation levels. Each level is indented
                  by :py:data:`INDENT` spaces.
    """

    indent = ' ' * INDENT * level
    deeper = ' ' * INDENT * (level + 1)

    # Colorize
    if color is not None:
        key = style(key, fg=color)

    # Handle key only
    if value is None:
        message = key

    # Handle key + value
    else:
        # Multiline content indented deeper
        if isinstance(value, str):
            lines = value.splitlines()
            if len(lines) > 1:
                value = ''.join([f"\n{deeper}{line}" for line in lines])

        message = f'{key}: {value}'

    return indent + message


class Config(object):
    """ User configuration """

    def __init__(self) -> None:
        """ Initialize config directory path """
        self.path = os.path.expanduser(CONFIG_PATH)
        if not os.path.exists(self.path):
            try:
                os.makedirs(self.path)
            except OSError as error:
                raise GeneralError(
                    f"Failed to create config '{self.path}'.\n{error}")

    def last_run(self, run_id: Optional[str] = None) -> Optional[str]:
        """ Get and set last run id """
        symlink = os.path.join(self.path, 'last-run')
        if run_id:
            try:
                os.remove(symlink)
            except OSError:
                pass
            try:
                os.symlink(run_id, symlink)
            except OSError as error:
                raise GeneralError(
                    f"Unable to save last run '{self.path}'.\n{error}")
            return run_id
        if os.path.islink(symlink):
            return os.path.realpath(symlink)
        return None


class StreamLogger(Thread):
    """
    Reading pipes of running process in threads.

    Code based on:
    https://github.com/packit/packit/blob/main/packit/utils/logging.py#L10
    """

    def __init__(self,
                 stream: Optional[IO[bytes]],
                 log_header: str,
                 logger: BaseLoggerFnType) -> None:
        super().__init__(daemon=True)
        self.stream = stream
        self.output: List[str] = []
        self.log_header = log_header
        self.logger = logger

    def run(self) -> None:
        if self.stream is None:
            return

        for _line in self.stream:
            line = _line.decode('utf-8', errors='replace')
            if line != '':
                self.logger(
                    self.log_header,
                    line.rstrip('\n'),
                    'yellow',
                    level=3)
            self.output.append(line)

    def get_output(self) -> str:
        return "".join(self.output)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Common
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CommonDerivedType = TypeVar('CommonDerivedType', bound='Common')


class CommandOutput(NamedTuple):
    stdout: Optional[str]
    stderr: Optional[str]


class Common(object):
    """
    Common shared stuff

    Takes care of command line context, options and workdir handling.
    Provides logging functions info(), verbose() and debug().
    Implements read() and write() for comfortable file access.
    Provides the run() method for easy command execution.
    """

    # Command line context, options and workdir
    _context: Optional[click.Context] = None
    # When set to true, _opt will be ignored (default will be returned)
    ignore_class_options: bool = False
    _options: Dict[str, Any] = dict()
    _workdir: WorkdirType = None

    def __init__(
            self,
            parent: Optional[CommonDerivedType] = None,
            name: Optional[str] = None,
            workdir: WorkdirArgumentType = None,
            context: Optional[click.Context] = None,
            relative_indent: int = 1):
        """
        Initialize name and relation with the parent object

        Prepare the workdir for provided id / directory path
        or generate a new workdir name if workdir=True given.
        Store command line context and options for future use
        if context is provided.
        """
        # Use lowercase class name as the default name
        self.name = name or self.__class__.__name__.lower()
        self.parent = parent

        # Relative log indent level shift against the parent
        self._relative_indent = relative_indent

        # Store command line context
        if context:
            self._save_context(context)

        # Initialize the workdir if requested
        self._workdir_load(workdir)

    def __str__(self) -> str:
        """ Name is the default string representation """
        return self.name

    @classmethod
    def _save_context(cls, context: click.Context) -> None:
        """ Save provided command line context and options for future use """
        cls._context = context
        cls._options = context.params

    @overload
    @classmethod
    def _opt(cls, option: str) -> Any:
        pass

    @overload
    @classmethod
    def _opt(cls, option: str, default: T) -> T:
        pass

    @classmethod
    def _opt(cls, option: str, default: Any = None) -> Any:
        """ Get an option from the command line context (class version) """
        if cls.ignore_class_options:
            return default
        return cls._options.get(option, default)

    def _fmf_context(self) -> FmfContextType:
        """ Return the current fmf context """
        if self._context is None:
            return dict()

        try:
            return cast(FmfContextType, self._context.obj.fmf_context)
        except AttributeError:
            return dict()

    def opt(self, option: str, default: Optional[Any] = None) -> Any:
        """
        Get an option from the command line options

        Checks also parent options. For flags (boolean values) parent's
        True wins over child's False (e.g. run --quiet enables quiet
        mode for all included plans and steps).

        For options that can be used multiple times, the child overrides
        the parent if it was defined (e.g. run -av provision -vvv runs
        all steps except for provision in mildly verbose mode, provision
        is run with the most verbosity).

        Environment variables override command line options.
        """
        # Translate dashes to underscores to match click's conversion
        option = option.replace('-', '_')
        # Check the environment first
        if option == 'debug':
            try:
                debug = os.environ['TMT_DEBUG']
                return int(debug)
            except ValueError:
                raise GeneralError(
                    f"Invalid debug level '{debug}', use an integer.")
            except KeyError:
                pass

        # Get local option
        local = self._options.get(option, default)
        # Check parent option
        parent = None
        if self.parent:
            parent = self.parent.opt(option)
        # Special handling for special flags (parent's yes always wins)
        if option in ['quiet', 'force', 'dry']:
            return parent if parent else local
        # Special handling for counting options (child overrides the
        # parent if it was defined)
        elif option in ['debug', 'verbose']:
            winner = local if local else parent
            if winner is None:
                winner = 0
            return winner
        else:
            return parent if parent is not None else local

    def _level(self) -> int:
        """ Hierarchy level """
        if self.parent is None:
            return -1
        else:
            return self.parent._level() + self._relative_indent

    def _indent(
            self,
            key: str,
            value: Optional[str] = None,
            color: Optional[str] = None,
            shift: int = 0) -> str:
        """ Indent message according to the object hierarchy """

        return indent(
            key,
            value=value,
            color=color,
            level=self._level() + shift)

    def _log(self, message: str) -> None:
        """ Append provided message to the current log """
        # Nothing to do if there is no workdir
        if self.workdir is None:
            return

        # Store log only in the top parent
        if self.parent:
            self.parent._log(message)
        else:
            with open(os.path.join(self.workdir, LOG_FILENAME), 'a') as log:
                log.write(datetime.datetime.utcnow().strftime('%H:%M:%S') + ' '
                          + remove_color(message) + '\n')

    def print(
            self,
            key: str,
            value: Optional[str] = None,
            color: Optional[str] = None,
            shift: int = 0,
            err: bool = False) -> None:
        """ Print a message regardless the quiet mode """
        self._log(self._indent(key, value, color=None, shift=shift))
        echo(self._indent(key, value, color, shift), err=err)

    def info(
            self,
            key: str,
            value: Optional[str] = None,
            color: Optional[str] = None,
            shift: int = 0,
            err: bool = False) -> None:
        """ Show a message unless in quiet mode """
        self._log(self._indent(key, value, color=None, shift=shift))
        if not self.opt('quiet'):
            echo(self._indent(key, value, color, shift), err=err)

    def verbose(
            self,
            key: str,
            value: Optional[str] = None,
            color: Optional[str] = None,
            shift: int = 0,
            level: int = 1,
            err: bool = False) -> None:
        """
        Show message if in requested verbose mode level

        In quiet mode verbose messages are not displayed.
        """
        self._log(self._indent(key, value, color=None, shift=shift))
        if not self.opt('quiet') and self.opt('verbose') >= level:
            echo(self._indent(key, value, color, shift), err=err)

    def debug(
            self,
            key: str,
            value: Optional[str] = None,
            color: Optional[str] = None,
            shift: int = 0,
            level: int = 1,
            err: bool = False) -> None:
        """
        Show message if in requested debug mode level

        In quiet mode debug messages are not displayed.
        """
        self._log(self._indent(key, value, color=None, shift=shift))
        if not self.opt('quiet') and self.opt('debug') >= level:
            echo(self._indent(key, value, color, shift), err=err)

    def warn(self, message: str, shift: int = 0) -> None:
        """ Show a yellow warning message on info level, send to stderr """
        self.info('warn', message, color='yellow', shift=shift, err=True)

    def fail(self, message: str, shift: int = 0) -> None:
        """ Show a red failure message on info level, send to stderr """
        self.info('fail', message, color='red', shift=shift, err=True)

    def _run(self,
             command: Union[str, List[str]],
             cwd: Optional[str],
             shell: bool,
             env: Optional[EnvironmentType],
             log: Optional[BaseLoggerFnType],
             join: bool = False,
             interactive: bool = False,
             timeout: Optional[int] = None) -> CommandOutput:
        """
        Run command, capture the output

        By default stdout and stderr are captured separately.
        Use join=True to merge stderr into stdout.
        Use timeout=<seconds> to finish process after given time
        """
        # By default command ouput is logged using debug
        if not log:
            log = self.debug
        # Prepare the environment
        if env:
            if not isinstance(env, dict):
                raise GeneralError(f"Invalid environment '{env}'.")
            # Do not modify current process environment
            environment = os.environ.copy()
            environment.update(env)
        else:
            environment = None
        self.debug('environment', pprint.pformat(environment), level=4)

        # Run the command in interactive mode if requested
        if interactive:
            try:
                subprocess.run(
                    command, cwd=cwd, shell=shell, env=environment, check=True)
            except subprocess.CalledProcessError:
                # Interactive mode can return non-zero if the last command
                # failed, ignore errors here
                pass
            finally:
                return CommandOutput(None, None)

        # Create the process
        try:
            process = subprocess.Popen(
                command, cwd=cwd, shell=shell, env=environment,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT if join else subprocess.PIPE)
        except FileNotFoundError as error:
            raise RunError(
                f"File '{error.filename}' not found.", command, 127)

        stdout_thread = StreamLogger(
            process.stdout, log_header='out', logger=log)
        stderr_thread = stdout_thread
        if not join:
            stderr_thread = StreamLogger(
                process.stderr, log_header='err', logger=log)
        stdout_thread.start()
        if not join:
            stderr_thread.start()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.returncode = PROCESS_TIMEOUT
        stdout_thread.join()
        if not join:
            stderr_thread.join()

        # Handle the exit code, return output
        if process.returncode != 0:
            raise RunError(
                message=f"Command returned '{process.returncode}'.",
                command=command,
                returncode=process.returncode,
                stdout=stdout_thread.get_output(),
                stderr=stderr_thread.get_output())
        if join:
            return CommandOutput(
                stdout_thread.get_output(), None)
        else:
            return CommandOutput(
                stdout_thread.get_output(), stderr_thread.get_output())

    def run(self,
            command: Union[str, List[str]],
            message: Optional[str] = None,
            cwd: Optional[str] = None,
            dry: bool = False,
            shell: bool = False,
            env: Optional[EnvironmentType] = None,
            interactive: bool = False,
            join: bool = False,
            log: Optional[BaseLoggerFnType] = None,
            timeout: Optional[int] = None) -> CommandOutput:
        """
        Run command, give message, handle errors

        Command is run in the workdir be default.
        In dry mode commands are not executed unless dry=True.
        Environment is updated with variables from the 'env' dictionary.
        Output is logged using self.debug() or custom 'log' function.
        Returns stdout if join=True, (stdout, stderr) tuple otherwise.
        """

        # Use a generic message if none given, prepare error message
        if not message:
            if isinstance(command, (list, tuple)):
                line = ' '.join(command)
            else:
                line = command
            message = f"Run command '{line}'."
        self.debug(message, level=2)
        message = "Failed to " + message[0].lower() + message[1:]

        # Nothing more to do in dry mode (unless requested)
        if self.opt('dry') and not dry:
            return CommandOutput(None, None)

        # Run the command, handle the exit code
        cwd = cwd or self.workdir

        # Fail nicely if the working directory does not exist
        if cwd and not os.path.exists(cwd):
            raise GeneralError(
                f"The working directory '{cwd}' does not exist.")

        try:
            return self._run(
                command, cwd, shell, env, log, join, interactive, timeout)
        except RunError as error:
            self.debug(error.message, level=3)
            message += f" Reason: {error.message}"
            raise RunError(
                message, error.command, error.returncode,
                error.stdout, error.stderr)

    def read(self, path: str, level: int = 2) -> str:
        """ Read a file from the workdir """
        if self.workdir:
            path = os.path.join(self.workdir, path)
        self.debug(f"Read file '{path}'.", level=level)
        try:
            with open(path, encoding='utf-8', errors='replace') as data:
                return data.read()
        except OSError as error:
            raise FileError(f"Failed to read '{path}'.\n{error}")

    def write(
            self,
            path: str,
            data: Any,
            mode: str = 'w',
            level: int = 2) -> None:
        """ Write a file to the workdir """
        if self.workdir:
            path = os.path.join(self.workdir, path)
        action = 'Append to' if mode == 'a' else 'Write'
        self.debug(f"{action} file '{path}'.", level=level)
        # Dry mode
        if self.opt('dry'):
            return
        try:
            with open(path, mode, encoding='utf-8', errors='replace') as file:
                file.write(data)
        except OSError as error:
            raise FileError(f"Failed to write '{path}'.\n{error}")

    def _workdir_init(self, id_: WorkdirArgumentType = None) -> None:
        """
        Initialize the work directory

        Workdir under WORKDIR_ROOT is used/created if 'id' is provided.
        If 'id' is a path, that directory is used instead. Otherwise a
        new workdir is created under the WORKDIR_ROOT directory.
        """
        # Prepare the workdir name from given id or path
        if isinstance(id_, str):
            # Use provided directory if full path given
            if '/' in id_:
                workdir = id_
            # Construct directory name under workdir root
            else:
                workdir = os.path.join(WORKDIR_ROOT, id_)
        # Generate a unique workdir name
        elif id_ is None:
            for id_bit in range(1, WORKDIR_MAX + 1):
                directory = 'run-{}'.format(str(id_bit).rjust(3, '0'))
                workdir = os.path.join(WORKDIR_ROOT, directory)
                if not os.path.exists(workdir):
                    break
            else:
                raise GeneralError(
                    f"Workdir full. Cleanup the '{WORKDIR_ROOT}' directory.")
        # Weird workdir id
        else:
            raise GeneralError(
                f"Invalid workdir '{id_}', expected a string or None.")

        # Cleanup possible old workdir if called with --scratch
        if self.opt('scratch'):
            self._workdir_cleanup(workdir)

        # Create the workdir
        # Make sure WORKDIR_ROOT has 1777 permission if recreated
        if workdir.startswith(WORKDIR_ROOT) and not os.path.isdir(WORKDIR_ROOT):
            try:
                os.makedirs(WORKDIR_ROOT, exist_ok=True)
                os.chmod(WORKDIR_ROOT, 0o1777)
            except OSError as error:
                raise FileError(f"Failed to prepare workdir '{WORKDIR_ROOT}': {error}")
        create_directory(workdir, 'workdir', quiet=True)
        self._workdir = workdir

    def _workdir_name(self) -> Optional[str]:
        """ Construct work directory name from parent workdir """
        # Need the parent workdir
        if self.parent is None or self.parent.workdir is None:
            return None
        # Join parent name with self
        return os.path.join(self.parent.workdir, self.name.lstrip('/'))

    def _workdir_load(self, workdir: WorkdirArgumentType) -> None:
        """
        Create the given workdir if it is not None

        If workdir=True, the directory name is automatically generated.
        """
        if workdir is True:
            self._workdir_init()
        elif workdir is not None:
            self._workdir_init(workdir)

    def _workdir_cleanup(self, path: Optional[str] = None) -> None:
        """ Clean up the work directory """
        directory = path or self._workdir_name()
        if directory is not None:
            if os.path.isdir(directory):
                self.debug(f"Clean up workdir '{directory}'.", level=2)
                shutil.rmtree(directory)
        self._workdir = None

    @property
    def workdir(self) -> Optional[str]:
        """ Get the workdir, create if does not exist """
        if self._workdir is None:
            self._workdir = self._workdir_name()
            # Workdir not enabled, even parent does not have one
            if self._workdir is None:
                return None
            # Create a child workdir under the parent workdir
            create_directory(self._workdir, 'workdir', quiet=True)
        return self._workdir

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Exceptions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class GeneralError(Exception):
    """ General error """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Store the original exception for future use
        self.original = kwargs.get('original')


class GitUrlError(GeneralError):
    """ Remote git url is not reachable """


class FileError(GeneralError):
    """ File operation error """


class RunError(GeneralError):
    """ Command execution error """

    def __init__(
            self,
            message: str,
            command: Union[str, List[str]],
            returncode: int,
            stdout: Optional[str] = None,
            stderr: Optional[str] = None,
            *args: Any,
            **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.message = message
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class MetadataError(GeneralError):
    """ General metadata error """


class SpecificationError(MetadataError):
    """ Metadata specification error """


class ConvertError(MetadataError):
    """ Metadata conversion error """


class StructuredFieldError(GeneralError):
    """ StructuredField parsing error """


# Step exceptions


class DiscoverError(GeneralError):
    """ Discover step error """


class ProvisionError(GeneralError):
    """ Provision step error """


class PrepareError(GeneralError):
    """ Prepare step error """


class ExecuteError(GeneralError):
    """ Execute step error """


class ReportError(GeneralError):
    """ Report step error """


class FinishError(GeneralError):
    """ Finish step error """


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Utilities
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def quote(string: str) -> str:
    """ Surround a string with double quotes """
    return f'"{string}"'


def ascii(text: Any) -> bytes:
    """ Transliterate special unicode characters into pure ascii """
    if not isinstance(text, str):
        text = str(text)
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore')


def listify(
        data: Union[Tuple[Any, ...], List[Any], str, Dict[Any, Any]],
        split: bool = False,
        keys: Optional[List[str]] = None) -> Union[List[Any], Dict[Any, Any]]:
    """
    Ensure that variable is a list, convert if necessary

    For dictionaries check all items or only those with provided keys.
    Also split strings on white-space/comma if split=True.
    """
    separator = re.compile(r'[\s,]+')
    if isinstance(data, tuple):
        data = list(data)
    if isinstance(data, list):
        return fmf.utils.split(data, separator) if split else data
    if isinstance(data, str):
        return fmf.utils.split(data, separator) if split else [data]
    if isinstance(data, dict):
        for key in keys or data:
            if key in data:
                data[key] = listify(data[key], split=split)
        return data
    return [data]


def copytree(
        src: str,
        dst: str,
        symlinks: bool = False,
        dirs_exist_ok: bool = False,
        ) -> Any:
    """ Similar to shutil.copytree but with dirs_exist_ok for Python < 3.8 """
    # No need to reimplement for newer python or if argument is not requested
    if not dirs_exist_ok or sys.version_info >= (3, 8):
        return shutil.copytree(
            src=src, dst=dst, symlinks=symlinks, dirs_exist_ok=dirs_exist_ok)
    # Choice was to either copy python implementation and change ONE line
    # or use rsync (or cp with shell)
    # We need to copy CONTENT of src into dst
    # so src has to end with / and dst cannot
    if src[-1] != '/':
        src += '/'
    if dst[-1] == '/':
        dst = dst[:-1]

    command = ["rsync", "-r"]
    if symlinks:
        command.append('-l')
    command.extend([src, dst])

    log.debug(f"Calling command '{command}'.")
    outcome = subprocess.run(
        command,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, universal_newlines=True)

    if outcome.returncode != 0:
        raise shutil.Error(
            [f"Unable to copy '{src}' into '{dst}' using rsync.",
             outcome.returncode, outcome.stdout])
    return dst


# These two are helpers for shell_to_dict and environment_to_dict -
# there is some overlap of their functionality.
def _add_simple_var(result: EnvironmentType, var: str) -> None:
    """
    Add a single NAME=VALUE pair into result dictionary

    Parse given string VAR to its constituents, NAME and VALUE, and add
    them to the provided dict.
    """

    matched = re.match("([^=]+)=(.*)", var)
    if not matched:
        raise GeneralError(f"Invalid variable specification '{var}'.")
    name, value = matched.groups()
    result[name] = value


def _add_file_vars(result: EnvironmentType, filepath: str) -> None:
    """
    Add variables loaded from file into the result dictionary

    Load mapping from a YAML file 'filepath', and add its content -
    "name: value" entries - to the provided dict.
    """

    if not filepath[1:]:
        raise GeneralError(
            f"Invalid variable file specification '{filepath}'.")

    try:
        with open(filepath[1:], 'r') as file:
            # Handle empty file as an empty environment
            content = file.read()
            if not content:
                log.warn(f"Empty environment file '{filepath}'.")
                return
            file_vars = yaml_to_dict(content)
    except Exception as exception:
        raise GeneralError(
            f"Failed to load variables from '{filepath}': {exception}")

    for name, value in file_vars.items():
        result[name] = str(value)


def shell_to_dict(variables: Union[str, List[str]]) -> EnvironmentType:
    """
    Convert shell-like variables into a dictionary

    Accepts single string or list of strings. Allowed forms are:
    'X=1'
    'X=1 Y=2 Z=3'
    ['X=1', 'Y=2', 'Z=3']
    ['X=1 Y=2 Z=3', 'A=1 B=2 C=3']
    'TXT="Some text with spaces in it"'
    """
    if not isinstance(variables, (list, tuple)):
        variables = [variables]
    result: EnvironmentType = dict()
    for variable in variables:
        if variable is None:
            continue
        for var in shlex.split(variable):
            _add_simple_var(result, var)

    return result


def environment_to_dict(variables: Union[str, List[str]]) -> EnvironmentType:
    """
    Convert environment variables into a dictionary

    Variables may be specified in the following two ways:

    * NAME=VALUE pairs
    * @foo.yaml

    If "variable" starts with "@" character, it is treated as a path to
    a YAML file that contains "key: value" pairs which are then
    transparently loaded and added to the final dictionary.

    In general, allowed inputs are the same as in "shell_to_dict"
    function, with the addition of "@foo.yaml" form:
    'X=1'
    'X=1 Y=2 Z=3'
    ['X=1', 'Y=2', 'Z=3']
    ['X=1 Y=2 Z=3', 'A=1 B=2 C=3']
    'TXT="Some text with spaces in it"'
    @foo.yaml
    @../../bar.yaml
    """

    if not isinstance(variables, (list, tuple)):
        variables = [variables]
    result: EnvironmentType = dict()

    for variable in variables:
        if variable is None:
            continue
        for var in shlex.split(variable):
            if var.startswith('@'):
                _add_file_vars(result, var)
            else:
                _add_simple_var(result, var)

    return result


@lru_cache(maxsize=None)
def environment_file_to_dict(env_file: str, root: str = ".") -> EnvironmentType:
    """
    Read environment variables from the given file.

    File should be in YAML format (``.yaml`` or ``.yml`` suffixes), or in dotenv format.

    .. code-block:: bash
       :caption: dotenv file example

       A=B
       C=D

    .. code-block:: yaml
       :caption: YAML file example

       A: B
       C: D

    Path to each file should be relative to the metadata tree root.

    .. note::

       For loading environment variables from multiple files, see
       :py:func:`environment_files_to_dict`.
    """

    env_file = env_file.strip()

    # Fetch a remote file
    if env_file.startswith("http"):
        # Create retry session for longer retries, see #1229
        session = retry_session.create(
            retries=ENVFILE_RETRY_SESSION_RETRIES,
            backoff_factor=ENVFILE_RETRY_SESSION_BACKOFF_FACTOR,
            allowed_methods=('GET',),
            status_forcelist=(
                429,  # Too Many Requests
                500,  # Internal Server Error
                502,  # Bad Gateway
                503,  # Service Unavailable
                504   # Gateway Timeout
                ),
            )
        try:
            response = session.get(env_file)
            response.raise_for_status()
            content = response.text
        except requests.RequestException as error:
            raise GeneralError(
                f"Failed to fetch the environment file from '{env_file}'. "
                f"The problem was: '{error}'")

    # Read a local file
    else:
        # Ensure we don't escape from the metadata tree root
        try:
            root_path = Path(root).resolve()
            full_path = (Path(root_path) / Path(env_file)).resolve()
            full_path.relative_to(root_path)
        except ValueError:
            raise GeneralError(
                f"The 'environment-file' path '{full_path}' is outside "
                f"of the metadata tree root '{root}'.")
        if not Path(full_path).is_file():
            raise GeneralError(f"File '{full_path}' doesn't exist.")

        content = Path(full_path).read_text()

    # Parse yaml file
    if os.path.splitext(env_file)[1].lower() in ('.yaml', '.yml'):
        environment = parse_yaml(content)

    else:
        try:
            environment = parse_dotenv(content)

        except ValueError:
            raise GeneralError(
                f"Failed to extract variables from environment file "
                f"'{full_path}'. Ensure it has the proper format "
                f"(i.e. A=B).")

    if not environment:
        log.warn(f"Empty environment file '{env_file}'.")

        return {}

    return environment


def environment_files_to_dict(env_files: Iterable[str], root: str = ".") -> EnvironmentType:
    """
    Read environment variables from the given list of files.

    Files should be in YAML format (``.yaml`` or ``.yml`` suffixes), or in dotenv format.

    .. code-block:: bash
       :caption: dotenv file example

       A=B
       C=D

    .. code-block:: yaml
       :caption: YAML file example

       A: B
       C: D

    Path to each file should be relative to the metadata tree root.

    .. note::

       For loading environment variables from a single file, see
       :py:func:`environment_file_to_dict`, which is a function
       ``environment_files_to_dict()`` calls for each file,
       accumulating data from all input files.
    """

    result: EnvironmentType = {}

    for env_file in env_files:
        result.update(environment_file_to_dict(env_file, root=root))

    return result


@contextlib.contextmanager
def modify_environ(
        new_elements: EnvironmentType) -> Generator[None, None, None]:
    """ A context manager for os.environ that restores the initial state """
    environ_backup = os.environ.copy()
    os.environ.clear()
    os.environ.update(new_elements)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(environ_backup)


def context_to_dict(context: List[str]) -> FmfContextType:
    """
    Convert command line context definition into a dictionary

    Does the same as environment_to_dict() plus separates possible
    comma-separated values into lists. Here's a couple of examples:

    distro=fedora-33 ---> {'distro': ['fedora']}
    arch=x86_64,ppc64 ---> {'arch': ['x86_64', 'ppc64']}
    """
    return {
        key: value.split(',')
        for key, value in environment_to_dict(context).items()}


def dict_to_yaml(
        data: Union[Dict[str, Any], List[Any]],
        width: Optional[int] = None,
        sort: bool = False,
        start: bool = False) -> str:
    """ Convert dictionary into yaml """
    output = io.StringIO()
    yaml = YAML()
    yaml.indent(mapping=4, sequence=4, offset=2)
    yaml.default_flow_style = False
    yaml.allow_unicode = True
    yaml.encoding = 'utf-8'
    yaml.width = width
    yaml.explicit_start = start
    # Convert multiline strings
    scalarstring.walk_tree(data)
    if sort:
        # Sort the data https://stackoverflow.com/a/40227545
        sorted_data = CommentedMap()
        for key in sorted(data):
            sorted_data[key] = data[key]
        data = sorted_data
    yaml.dump(data, output)
    return output.getvalue()


YamlTypType = Literal['rt', 'safe', 'unsafe', 'base']


def yaml_to_dict(data: Any,
                 yaml_type: Optional[YamlTypType] = None) -> Dict[Any, Any]:
    """ Convert yaml into dictionary """
    yaml = YAML(typ=yaml_type)
    loaded_data = yaml.load(data)
    if loaded_data is None:
        return dict()
    if not isinstance(loaded_data, dict):
        raise GeneralError(
            f"Expected dictionary in yaml data, "
            f"got '{type(loaded_data).__name__}'.")
    return loaded_data


SerializableContainerDerivedType = TypeVar(
    'SerializableContainerDerivedType',
    bound='SerializableContainer')


@dataclasses.dataclass
class SerializableContainer:
    """
    A mixin class for objects that may be saved in files and restored later
    """

    def to_dict(self) -> Dict[str, Any]:
        """ Return keys and values in the form of a dictionary """

        return dataclasses.asdict(self)

    # This method should remain a class-method: 1. list of keys is known
    # already, therefore it's not necessary to create an instance, and
    # 2. some functionality makes use of this knowledge.
    @classmethod
    def keys(cls) -> Generator[str, None, None]:
        """ Iterate over key names """

        for field in dataclasses.fields(cls):
            yield field.name

    def values(self) -> Generator[Any, None, None]:
        """ Iterate over key values """

        yield from self.to_dict().values()

    def items(self) -> Generator[Tuple[str, Any], None, None]:
        """ Iterate over key/value pairs """

        yield from self.to_dict().items()

    #
    # Moving data between containers and objects owning them
    #

    def inject_to(self, obj: Any) -> None:
        """
        Inject keys from this container into attributes of a given object
        """

        for name, value in self.items():
            setattr(obj, name, value)

    @classmethod
    def extract_from(cls: Type[SerializableContainerDerivedType],
                     obj: Any) -> SerializableContainerDerivedType:
        """ Extract keys from given object, and save them in a container """

        data = cls()

        for key in cls.keys():
            value = getattr(obj, key)
            if value is not None:
                setattr(data, key, value)

        return data

    #
    # Serialization - writing containers into YAML files, and restoring
    # them later.
    #

    def to_serialized(self) -> Dict[str, Any]:
        """
        Return keys and values in the form allowing later reconstruction.

        Used to transform container into a structure one can save in a
        YAML file, and restore it later.

        See :py:meth:`from_serialized` for its counterpart.
        """

        fields = self.to_dict()

        # Add a special field tracking what class we just shattered to pieces.
        fields.update({
            '__class__': {
                'module': self.__class__.__module__,
                'name': self.__class__.__name__
                }
            })

        return fields

    @classmethod
    def from_serialized(
            cls: Type[SerializableContainerDerivedType],
            serialized: Dict[str, Any]) -> SerializableContainerDerivedType:
        """
        Recreate container from its serialized form.

        Used to transform data read from a YAML file into the original
        container.

        See :py:meth:`to_serialized` for its counterpart.
        """

        # Our special key may or may not be present, depending on who
        # calls this method.  In any case, it is not needed, because we
        # already know what class to restore: this one.
        serialized.pop('__class__', None)

        return cls(**serialized)

    @staticmethod
    def unserialize(serialized: Dict[str, Any]
                    ) -> SerializableContainerDerivedType:
        """
        Recreate container from its serialized form.

        Similar to :py:meth:`from_serialized`, but this method knows
        nothing about container's class, and will locate the correct
        module and class by inspecting serialized data. Discovered
        class' :py:meth:`from_serialized` is then used to create the
        container.

        Used to transform data read from a YAML file into original
        containers when their classes are not know to the code.
        Restoring such containers requires inspection of serialized data
        and dynamic imports of modules as needed.
        """

        from tmt.plugins import import_

        # Unpack class info, to get nicer variable names
        klass_info = serialized.pop('__class__')
        klass_module_name = klass_info['module']
        klass_name = klass_info['name']

        # Make sure the module is imported. It probably is, but really,
        # make sure of it.
        import_(klass_module_name)

        # Now the module should be available in `sys.modules` like any
        # other, and we can go and grab the class we need from it.
        klass_module = sys.modules[klass_module_name]
        klass = getattr(klass_module, klass_name)

        if klass is None:
            raise SystemExit(
                f"Failed to import '{klass_name}' "
                f"from '{klass_module_name}' module.")

        # Stay away from classes that are not derived from this one, to
        # honor promise given by return value annotation.
        assert issubclass(klass, SerializableContainer)

        # Apparently, the issubclass() check above is not good enough for mypy.
        return cast(
            SerializableContainerDerivedType,
            klass.from_serialized(serialized))


def markdown_to_html(filename: str) -> str:
    """
    Convert markdown to html

    Expects: Markdown document as a file.
    Returns: An HTML document as a string.
    """
    try:
        import markdown
    except ImportError:
        raise ConvertError("Install tmt-test-convert to export tests.")

    try:
        with open(filename, 'r') as file:
            try:
                text = file.read()
            except UnicodeError:
                raise MetadataError(f"Unable to read '{filename}'.")
            return markdown.markdown(text)
    except IOError:
        raise ConvertError(f"Unable to open '{filename}'.")


def shell_variables(
        data: Union[List[str], Tuple[str, ...], Dict[str, Any]]) -> List[str]:
    """
    Prepare variables to be consumed by shell

    Convert dictionary or list/tuple of key=value pairs to list of
    key=value pairs where value is quoted with shlex.quote().
    """

    # Convert from list/tuple
    if isinstance(data, list) or isinstance(data, tuple):
        converted_data = []
        for item in data:
            splitted_item = item.split('=')
            key = splitted_item[0]
            value = shlex.quote('='.join(splitted_item[1:]))
            converted_data.append(f'{key}={value}')
        return converted_data

    # Convert from dictionary
    return [f"{key}={shlex.quote(str(value))}" for key, value in data.items()]


def duration_to_seconds(duration: str) -> int:
    """ Convert sleep time format into seconds """
    units = {
        's': 1,
        'm': 60,
        'h': 60 * 60,
        'd': 60 * 60 * 24,
        }
    try:
        match = re.match(r'^(\d+)([smhd]?)$', str(duration))
        if match is None:
            raise SpecificationError(f"Invalid duration '{duration}'.")
        number, suffix = match.groups()
        return int(number) * units.get(suffix, 1)
    except (ValueError, AttributeError):
        raise SpecificationError(f"Invalid duration '{duration}'.")


def verdict(
        decision: Optional[bool],
        comment: Optional[str] = None,
        good: str = 'pass',
        bad: str = 'fail',
        problem: str = 'warn',
        **kwargs: Any) -> Optional[bool]:
    """
    Print verdict in green, red or yellow based on the decision

    The supported decision values are:

        True .... good (green)
        False ... bad (red)
        None .... problem (yellow)

    Anything else raises an exception. Additional arguments
    are passed to the `echo` function. Returns back the decision.
    """

    if decision is False:
        text = style(bad, fg='red')
    elif decision is True:
        text = style(good, fg='green')
    elif decision is None:
        text = style(problem, fg='yellow')
    else:
        raise GeneralError(
            "Invalid decision value, must be 'True', 'False' or 'None'.")
    if comment:
        text = text + ' ' + comment
    echo(text, **kwargs)
    return decision


def format(
        key: str,
        value: Union[None, str, List[Any], Dict[Any, Any]] = None,
        indent: int = 12,
        width: int = 72,
        wrap: Literal[True, False, 'auto'] = 'auto',
        key_color: str = 'green',
        value_color: str = 'black') -> str:
    """
    Nicely format and indent a key-value pair

    The following values for 'wrap' are supported:

        True .... always reformat text and wrap long lines
        False ... preserve text, no new line changes
        auto .... wrap only if text contains a long line
    """
    indent_string = (indent + 1) * ' '
    # Key
    output = '{} '.format(str(key).rjust(indent, ' '))
    if key_color is not None:
        output = style(output, fg=key_color)
    # Bool
    if isinstance(value, bool):
        output += ('true' if value else 'false')
    # List
    elif isinstance(value, list):
        # Make sure everything is string, prepare list, check for spaces
        value = [str(item) for item in value]
        listed_text = fmf.utils.listed(value)
        has_spaces = any([item.find(' ') > -1 for item in value])
        # Use listed output only for short lists without spaces
        if len(listed_text) < width - indent and not has_spaces:
            output += listed_text
        # Otherwise just place each item on a new line
        else:
            output += ('\n' + indent_string).join(value)
    # Dictionary
    elif isinstance(value, dict):
        # Place each key value pair on a separate line
        output += ('\n' + indent_string).join(
            f'{item[0]}: {item[1]}' for item in value.items())
    # Text
    elif isinstance(value, str):
        # In 'auto' mode enable wrapping when long lines present
        if wrap == 'auto':
            wrap = any(
                [len(line) + indent - 7 > width
                 for line in value.split('\n')])
        if wrap:
            output += (wrap_text(
                value, width=width,
                preserve_paragraphs=True,
                initial_indent=indent_string,
                subsequent_indent=indent_string).lstrip())
        else:
            output += (('\n' + indent_string).join(
                value.rstrip().split('\n')))
    else:
        output += str(value)
    return output


def create_directory(
        path: str,
        name: str,
        dry: bool = False,
        quiet: bool = False) -> None:
    """ Create a new directory, handle errors """
    say = log.debug if quiet else echo
    if os.path.isdir(path):
        say("Directory '{}' already exists.".format(path))
        return
    if dry:
        say("Directory '{}' would be created.".format(path))
        return
    try:
        os.makedirs(path, exist_ok=True)
        say("Directory '{}' created.".format(path))
    except OSError as error:
        raise FileError("Failed to create {} '{}' ({})".format(
            name, path, error))


def create_file(
        path: str,
        content: str,
        name: str,
        dry: bool = False,
        force: bool = False,
        mode: int = 0o664,
        quiet: bool = False) -> None:
    """ Create a new file, handle errors """
    say = log.debug if quiet else echo
    action = 'would be created' if dry else 'created'
    if os.path.exists(path):
        if force:
            action = 'would be overwritten' if dry else 'overwritten'
        else:
            raise FileError("File '{}' already exists.".format(path))

    if dry:
        say("{} '{}' {}.".format(name.capitalize(), path, action))
        return

    try:
        with open(path, 'w') as file_:
            file_.write(content)
        say("{} '{}' {}.".format(name.capitalize(), path, action))
        os.chmod(path, mode)
    except OSError as error:
        raise FileError("Failed to create {} '{}' ({})".format(
            name, path, error))


# Avoid multiple subprocess calls for the same url
@lru_cache(maxsize=None)
def check_git_url(url: str) -> str:
    """ Check that a remote git url is accessible """
    try:
        log.debug(f"Check git url '{url}'.")
        subprocess.check_call(
            ["git", "ls-remote", "--heads", url],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env={"GIT_ASKPASS": "echo", "GIT_TERMINAL_PROMPT": "0"})
        return url
    except subprocess.CalledProcessError:
        raise GitUrlError(f"Unable to contact remote git via '{url}'.")


def public_git_url(url: str) -> str:
    """
    Convert a git url into a public format

    Return url in the format which can be accessed without
    authentication. For now just cover the most common services.
    """

    # GitHub, GitLab
    # old: git@github.com:teemtee/tmt.git
    # new: https://github.com/teemtee/tmt.git
    matched = re.match('git@(.*):(.*)', url)
    if matched:
        host, project = matched.groups()
        return f'https://{host}/{project}'

    # RHEL packages
    # old: git+ssh://psplicha@pkgs.devel.redhat.com/tests/bash
    # old: ssh://psplicha@pkgs.devel.redhat.com/tests/bash
    # old: ssh://pkgs.devel.redhat.com/tests/bash
    # new: git://pkgs.devel.redhat.com/tests/bash
    matched = re.match(
        r'(git\+)?ssh://(\w+@)?(pkgs\.devel\.redhat\.com)/(.*)', url)
    if matched:
        _, _, host, project = matched.groups()
        return f'git://{host}/{project}'

    # Fedora packages, Pagure
    # old: git+ssh://psss@pkgs.fedoraproject.org/tests/shell
    # old: ssh://psss@pkgs.fedoraproject.org/tests/shell
    # new: https://pkgs.fedoraproject.org/tests/shell
    matched = re.match(r'(git\+)?ssh://(\w+@)?([^/]*)/(.*)', url)
    if matched:
        _, _, host, project = matched.groups()
        return f'https://{host}/{project}'

    # Otherwise return unmodified
    return url


class TimeoutHTTPAdapter(requests.adapters.HTTPAdapter):
    """
    Spice up request's session with custom timeout.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.timeout = kwargs.pop('timeout', None)

        super().__init__(*args, **kwargs)

    def send(  # type: ignore # does not match superclass type on purpose
            self,
            request: requests.PreparedRequest,
            **kwargs: Any) -> requests.Response:
        kwargs.setdefault('timeout', self.timeout)

        return super().send(request, **kwargs)


class RetryStrategy(requests.packages.urllib3.util.retry.Retry):  # type: ignore[misc]
    def increment(
            self,
            *args: Any,
            **kwargs: Any
            ) -> requests.packages.urllib3.util.retry.Retry:
        error = cast(Optional[Exception], kwargs.get('error', None))

        # Detect a subset of exception we do not want to follow with a retry.
        if error is not None:
            # Failed certificate verification - this issue will probably not get any better
            # should we try again.
            if isinstance(error, urllib3.exceptions.SSLError) \
                    and 'certificate verify failed' in str(error):

                # [mpr] I'm not sure how stable this *iternal* API is, but pool seems to be the
                # only place aware of the remote hostname. Try our best to get the hostname for
                # a better error message, but don't crash because of a missing attribute or
                # something as dumb.

                connection_pool = kwargs.get('_pool', None)

                if connection_pool is not None and hasattr(connection_pool, 'host'):
                    message = f"Certificate verify failed for '{connection_pool.host}'."
                else:
                    message = 'Certificate verify failed.'

                raise GeneralError(message, original=error) from error

        return super().increment(*args, **kwargs)


class retry_session(contextlib.AbstractContextManager):  # type: ignore
    """
    Context manager for requests.Session() with retries and timeout
    """
    @staticmethod
    def create(
            retries: int = DEFAULT_RETRY_SESSION_RETRIES,
            backoff_factor: float = DEFAULT_RETRY_SESSION_BACKOFF_FACTOR,
            allowed_methods: Optional[Tuple[str, ...]] = None,
            status_forcelist: Optional[Tuple[int, ...]] = None,
            timeout: Optional[int] = None
            ) -> requests.Session:
        retry_strategy = RetryStrategy(
            total=retries,
            status_forcelist=status_forcelist,
            # `method_whitelist`` has been renamed to `allowed_methods` since
            # urllib3 1.26, and it will be removed in urllib3 2.0.
            # `allowed_methods` is therefore the future-proof name, but for the
            # sake of backward compatibility, internally we need to use the
            # deprecated parameter for now. Or request newer urllib3, but that
            # might a problem because of RPM availability.
            method_whitelist=allowed_methods,
            backoff_factor=backoff_factor)

        if timeout is not None:
            http_adapter: requests.adapters.HTTPAdapter = TimeoutHTTPAdapter(
                timeout=timeout, max_retries=retry_strategy)
        else:
            http_adapter = requests.adapters.HTTPAdapter(
                max_retries=retry_strategy)

        session = requests.Session()
        session.mount('http://', http_adapter)
        session.mount('https://', http_adapter)

        return session

    def __init__(
            self,
            retries: int = DEFAULT_RETRY_SESSION_RETRIES,
            backoff_factor: float = DEFAULT_RETRY_SESSION_BACKOFF_FACTOR,
            allowed_methods: Optional[Tuple[str, ...]] = None,
            status_forcelist: Optional[Tuple[int, ...]] = None,
            timeout: Optional[int] = None
            ) -> None:
        self.retries = retries
        self.backoff_factor = backoff_factor
        self.allowed_methods = allowed_methods
        self.status_forcelist = status_forcelist
        self.timeout = timeout

    def __enter__(self) -> requests.Session:
        return self.create(
            retries=self.retries,
            backoff_factor=self.backoff_factor,
            allowed_methods=self.allowed_methods,
            status_forcelist=self.status_forcelist,
            timeout=self.timeout)

    def __exit__(self, *args: Any) -> None:
        pass


def remove_color(text: str) -> str:
    """ Remove ansi color sequences from the string """
    return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)


def default_branch(repository: str, remote: str = 'origin') -> str:
    """ Detect default branch from given local git repository """
    head = os.path.join(repository, f'.git/refs/remotes/{remote}/HEAD')
    # Make sure the HEAD reference is available
    if not os.path.exists(head):
        subprocess.run(
            f'git remote set-head {remote} --auto'.split(), cwd=repository)
    # The ref format is 'ref: refs/remotes/origin/main'
    with open(head) as ref:
        return ref.read().strip().split('/')[-1]


def parse_dotenv(content: str) -> EnvironmentType:
    """ Parse dotenv (shell) format of variables """
    return dict([line.split("=", maxsplit=1)
                for line in shlex.split(content, comments=True)])


def parse_yaml(content: str) -> EnvironmentType:
    """ Parse variables from yaml, ensure flat dictionary format """
    yaml_as_dict = YAML(typ="safe").load(content)
    # Handle empty file as an empty environment
    if yaml_as_dict is None:
        return dict()
    if any(isinstance(val, dict) for val in yaml_as_dict.values()):
        raise GeneralError(
            "Can't set the environment from the nested yaml config. The "
            "config should be just key, value pairs.")
    return {key: str(value) for key, value in yaml_as_dict.items()}


def validate_git_status(test: 'tmt.base.Test') -> Tuple[bool, str]:
    """
    Validate that test has current metadata on fmf_id

    Return a tuple (boolean, message) as the result of validation.

    Checks that sources:
    - all local changes are committed
    - up to date on remote repository
    - .fmf/version marking fmf root is committed as well

    When all checks pass returns (True, '').
    """
    sources = test.node.sources + \
        [os.path.join(test.node.root, '.fmf', 'version')]

    # Use tmt's run instead of subprocess.run
    run = Common().run

    # Check for not committed metadata changes
    cmd = ['git', 'status', '--porcelain', '--'] + sources
    try:
        result = run(cmd, cwd=test.node.root, join=True)
    except RunError as error:
        return (
            False,
            f"Failed to run git status: {error.stdout}"
            )

    not_committed = []
    assert result.stdout is not None
    for line in result.stdout.split('\n'):
        if line:
            # XY PATH or XY ORIG -> PATH. XY and PATH are separated by space
            not_committed.append(line[3:])

    if not_committed:
        return (False, "Uncommitted changes in " + " ".join(not_committed))

    # Check for not pushed changes
    cmd = ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]
    try:
        result = run(cmd, cwd=test.node.root)
    except RunError as error:
        return (
            False,
            f'Failed to get remote branch, error raised: "{error.stderr}"'
            )

    assert result.stdout is not None
    remote_ref = result.stdout.strip()

    cmd = [
        'git',
        'diff',
        f'HEAD..{remote_ref}',
        '--name-status',
        '--'] + sources
    try:
        result = run(cmd, cwd=test.node.root)
    except RunError as error:
        return (
            False,
            f'Failed to diff against remote branch, error raised: "{error.stderr}"')

    not_pushed = []
    assert result.stdout is not None
    for line in result.stdout.split('\n'):
        if line:
            _, path = line.strip().split('\t', maxsplit=2)
            not_pushed.append(path)
    if not_pushed:
        return (False, "Not pushed changes in " + " ".join(not_pushed))

    return (True, '')


def generate_runs(
        path: str, id_: Optional[str] = None) -> Generator[str, None, None]:
    """ Generate absolute paths to runs from path """
    # Prepare absolute workdir path if --id was used
    if id_:
        if '/' not in id_:
            id_ = os.path.join(path, id_)
        if os.path.isabs(id_):
            if os.path.exists(id_):
                yield id_
            return
    if not os.path.exists(path):
        return
    for filename in os.listdir(path):
        abs_path = os.path.join(path, filename)
        # If id_ is None, the abs_path is considered valid (no filtering
        # is being applied). If it is defined, it has been transformed
        # to absolute path and must be equal to abs_path for the run
        # in abs_path to be generated.
        invalid_id = id_ and abs_path != id_
        invalid_run = not os.path.exists(
            os.path.join(abs_path, 'run.yaml'))
        if not os.path.isdir(abs_path) or invalid_id or invalid_run:
            continue
        yield abs_path


def load_run(run: 'tmt.base.Run') -> Tuple[bool, Optional[Exception]]:
    """ Load a run and its steps from the workdir """
    try:
        run.load_from_workdir()
    except GeneralError as error:
        return False, error
    for plan in run.plans:
        for step in plan.steps(disabled=True):
            step.load()
    return True, None


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  StructuredField
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SFSectionValueType = Union[str, List[str]]


class StructuredField(object):
    """
    Handling multiple text data in a single text field

    The StructuredField allows you to easily store and extract several
    sections of text data to/from a single text field. The sections are
    separated by section names in square brackets and can be hosted in
    other text as well.

    The section names have to be provided on a separate line and there
    must be no leading/trailing white space before/after the brackets.
    The StructuredField supports two versions of the format:

    Version 0: Simple, concise, useful when neither the surrounding text
    or the section data can contain lines which could resemble section
    names. Here's an example of a simple StructuredField::

        Note written by human.

        [section-one]
        Section one content.

        [section-two]
        Section two content.

        [section-three]
        Section three content.

        [end]

        Another note written by human.

    Version 1: Includes unique header to prevent collisions with the
    surrounding text and escapes any section-like lines in the content::

        Note written by human.

        [structured-field-start]
        This is StructuredField version 1. Please, edit with care.

        [section-one]
        Section one content.

        [section-two]
        Section two content.
        [structured-field-escape][something-resembling-section-name]

        [section-three]
        Section three content.

        [structured-field-end]

        Another note written by human.

    Note that an additional empty line is added at the end of each
    section to improve the readability. This line is not considered
    to be part of the section content.

    Besides handling the whole section content it's also possible to
    store several key-value pairs in a single section, similarly as in
    the ini config format::

        [section]
        key1 = value1
        key2 = value2
        key3 = value3

    Provide the key name as the optional argument 'item' when accessing
    these single-line items. Note that the section cannot contain both
    plain text data and key-value pairs.

    Example::

        field = qe.StructuredField()
        field.set("project", "Project Name")
        field.set("details", "somebody", "owner")
        field.set("details", "2013-05-27", "started")
        field.set("description", "This is a description.\\n"
                "It spans across multiple lines.\\n")
        print field.save()

            [structured-field-start]
            This is StructuredField version 1. Please, edit with care.

            [project]
            Project Name

            [details]
            owner = somebody
            started = 2013-05-27

            [description]
            This is a description.
            It spans across multiple lines.

            [structured-field-end]

        field.version(0)
        print field.save()

            [project]
            Project Name

            [details]
            owner = somebody
            started = 2013-05-27

            [description]
            This is a description.
            It spans across multiple lines.

            [end]

    Multiple values for the same key are supported as well. Enable this
    feature with 'multi=True' when initializing the structured field.
    If multiple values are present their list will be returned instead
    of a single string. Similarly use list for setting multiple values::

        field = qe.StructuredField(multi=True)
        requirements = ['hypervisor=', 'labcontroller=lab.example.com']
        field.set("hardware", requirements, "hostrequire")
        print field.save()

            [structured-field-start]
            This is StructuredField version 1. Please, edit with care.

            [hardware]
            hostrequire = hypervisor=
            hostrequire = labcontroller=lab.example.com

            [structured-field-end]

        print field.get("hardware", "hostrequire")

            ['hypervisor=', 'labcontroller=lab.example.com']
    """

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #  StructuredField Special
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __init__(
            self,
            text: Optional[str] = None,
            version: int = 1,
            multi: bool = False) -> None:
        """ Initialize the structured field """
        self.version(version)
        self._header: str = ""
        self._footer: str = ""
        # Sections are internally stored in their serialized form, i.e. as
        # strings.
        self._sections: Dict[str, str] = {}
        self._order: List[str] = []
        self._multi = multi
        if text is not None:
            self.load(text)

    def __iter__(self) -> Generator[str, None, None]:
        """ By default iterate through all available section names """
        for section in self._order:
            yield section

    def __nonzero__(self) -> bool:
        """ True when any section is defined """
        return len(self._order) > 0

    __bool__ = __nonzero__

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #  StructuredField Private
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _load_version_zero(self, text: str) -> None:
        """ Load version 0 format """
        # Attempt to split the text according to the section tag
        section = re.compile(r"\n?^\[([^\]]+)\]\n", re.MULTILINE)
        parts = section.split(text)
        # If just one part ---> no sections present, just plain text
        if len(parts) == 1:
            self._header = parts[0]
            return
        # Pick header & footer, make sure [end] tag is present
        self._header = parts[0]
        self._footer = re.sub("^\n", "", parts[-1])
        if parts[-2] != "end":
            raise StructuredFieldError("No [end] section tag found")
        # Convert to dictionary and save the order
        keys = parts[1:-2:2]
        values = parts[2:-2:2]
        for key, value in zip(keys, values):
            self.set(key, value)

    def _load(self, text: str) -> None:
        """ Load version 1+ format """
        # The text must exactly match the format
        format = re.compile(
            r"(.*)^\[structured-field-start\][ \t]*\n"
            r"(.*)\n\[structured-field-end\][ \t]*\n(.*)",
            re.DOTALL + re.MULTILINE)
        # No match ---> plain text or broken structured field
        matched = format.search(text)
        if not matched:
            if "[structured-field" in text:
                raise StructuredFieldError("StructuredField parse error")
            self._header = text
            log.debug("StructuredField not found, treating as a plain text")
            return
        # Save header & footer (remove trailing new lines)
        self._header = re.sub("\n\n$", "\n", matched.groups()[0])
        if self._header:
            log.debug(u"Parsed header:\n{0}".format(self._header))
        self._footer = re.sub("^\n", "", matched.groups()[2])
        if self._footer:
            log.debug(u"Parsed footer:\n{0}".format(self._footer))
        # Split the content on the section names
        section = re.compile(r"\n\[([^\]]+)\][ \t]*\n", re.MULTILINE)
        parts = section.split(matched.groups()[1])
        # Detect the version
        version_match = re.search(r"version (\d+)", parts[0])
        if not version_match:
            log.error(parts[0])
            raise StructuredFieldError(
                "Unable to detect StructuredField version")
        self.version(int(version_match.groups()[0]))
        log.debug(
            "Detected StructuredField version {0}".format(
                self.version()))
        # Convert to dictionary, remove escapes and save the order
        keys = parts[1::2]
        escape = re.compile(r"^\[structured-field-escape\]", re.MULTILINE)
        values = [escape.sub("", value) for value in parts[2::2]]
        for key, value in zip(keys, values):
            self.set(key, value)
        log.debug(u"Parsed sections:\n{0}".format(
            pprint.pformat(self._sections)))

    def _save_version_zero(self) -> str:
        """ Save version 0 format """
        result = []
        if self._header:
            result.append(self._header)
        for section, content in self.iterate():
            result.append(u"[{0}]\n{1}".format(section, content))
        if self:
            result.append(u"[end]\n")
        if self._footer:
            result.append(self._footer)
        return "\n".join(result)

    def _save(self) -> str:
        """ Save version 1+ format """
        result = []
        # Regular expression for escaping section-like lines
        escape = re.compile(r"^(\[.+\])$", re.MULTILINE)
        # Header
        if self._header:
            result.append(self._header)
        # Sections
        if self:
            result.append(
                u"[structured-field-start]\n"
                u"This is StructuredField version {0}. "
                u"Please, edit with care.\n".format(self._version))
            for section, content in self.iterate():
                result.append(u"[{0}]\n{1}".format(section, escape.sub(
                    "[structured-field-escape]\\1", content)))
            result.append(u"[structured-field-end]\n")
        # Footer
        if self._footer:
            result.append(self._footer)
        return "\n".join(result)

    def _read_section(self, content: str) -> Dict[str, SFSectionValueType]:
        """ Parse config section and return ordered dictionary """
        dictionary: Dict[str, SFSectionValueType] = OrderedDict()
        for line in content.split("\n"):
            # Remove comments and skip empty lines
            line = re.sub("#.*", "", line)
            if re.match(r"^\s*$", line):
                continue
            # Parse key and value
            matched = re.search("([^=]+)=(.*)", line)
            if not matched:
                raise StructuredFieldError(
                    "Invalid key/value line: {0}".format(line))
            key = matched.groups()[0].strip()
            value = matched.groups()[1].strip()
            # Handle multiple values if enabled
            if key in dictionary and self._multi:
                stored_value = dictionary[key]
                if isinstance(stored_value, list):
                    stored_value.append(value)
                else:
                    dictionary[key] = [stored_value, value]
            else:
                dictionary[key] = value
        return dictionary

    def _write_section(self, dictionary: Dict[str, SFSectionValueType]) -> str:
        """ Convert dictionary into a config section format """
        section = ""
        for key in dictionary:
            if isinstance(dictionary[key], list):
                for value in dictionary[key]:
                    section += "{0} = {1}\n".format(key, value)
            else:
                section += "{0} = {1}\n".format(key, dictionary[key])
        return section

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #  StructuredField Methods
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def iterate(self) -> Generator[Tuple[str, str], None, None]:
        """ Return (section, content) tuples for all sections """
        for section in self:
            yield section, self._sections[section]

    def version(self, version: Optional[int] = None) -> int:
        """ Get or set the StructuredField version """
        if version is not None:
            if version in [0, 1]:
                self._version = version
            else:
                raise StructuredFieldError(
                    "Bad StructuredField version: {0}".format(version))
        return self._version

    def load(self, text: str, version: Optional[int] = None) -> None:
        """ Load the StructuredField from a string """
        if version is not None:
            self.version(version)
        # Make sure we got a text, convert from bytes if necessary
        if isinstance(text, bytes):
            text = text.decode("utf8")
        if not isinstance(text, str):
            raise StructuredFieldError(
                "Invalid StructuredField, expecting string")
        # Remove possible carriage returns
        text = re.sub("\r\n", "\n", text)
        # Make sure the text has a new line at the end
        if text and text[-1] != "\n":
            text += "\n"
        log.debug(u"Parsing StructuredField\n{0}".format(text))
        # Parse respective format version
        if self._version == 0:
            self._load_version_zero(text)
        else:
            self._load(text)

    def save(self) -> str:
        """ Convert the StructuredField into a string """
        if self.version() == 0:
            return self._save_version_zero()
        else:
            return self._save()

    def header(self, content: Optional[str] = None) -> str:
        """ Get or set the header content """
        if content is not None:
            self._header = content
        return self._header

    def footer(self, content: Optional[str] = None) -> str:
        """ Get or set the footer content """
        if content is not None:
            self._footer = content
        return self._footer

    def sections(self) -> List[str]:
        """ Get the list of available sections """
        return self._order

    def get(
            self,
            section: str,
            item: Optional[str] = None) -> SFSectionValueType:
        """ Return content of given section or section item """
        try:
            content = self._sections[section]
        except KeyError:
            raise StructuredFieldError(
                "Section [{0!r}] not found".format(ascii(section)))
        # Return the whole section content
        if item is None:
            return content
        # Return only selected item from the section
        try:
            return self._read_section(content)[item]
        except KeyError:
            raise StructuredFieldError(
                "Unable to read '{0!r}' from section '{1!r}'".format(
                    ascii(item), ascii(section)))

    def set(self, section: str, content: Any,
            item: Optional[str] = None) -> None:
        """ Update content of given section or section item """
        # Convert to string if necessary, keep lists untouched
        if isinstance(content, list):
            pass
        elif isinstance(content, bytes):
            content = content.decode("utf8")
        elif not isinstance(content, str):
            content = str(content)
        # Set the whole section content
        if item is None:
            # Add new line if missing
            if content and content[-1] != "\n":
                content += "\n"
            self._sections[section] = content
        # Set only selected item from the section
        else:
            try:
                current = self._sections[section]
            except KeyError:
                current = ""
            dictionary = self._read_section(current)
            dictionary[item] = content
            self._sections[section] = self._write_section(dictionary)
        # Remember the order when adding a new section
        if section not in self._order:
            self._order.append(section)

    def remove(self, section: str, item: Optional[str] = None) -> None:
        """ Remove given section or section item """
        # Remove the whole section
        if item is None:
            try:
                del self._sections[section]
                del self._order[self._order.index(section)]
            except KeyError:
                raise StructuredFieldError(
                    "Section [{0!r}] not found".format(ascii(section)))
        # Remove only selected item from the section
        else:
            try:
                dictionary = self._read_section(self._sections[section])
                del(dictionary[item])
            except KeyError:
                raise StructuredFieldError(
                    "Unable to remove '{0!r}' from section '{1!r}'".format(
                        ascii(item), ascii(section)))
            self._sections[section] = self._write_section(dictionary)


class DistGitHandler(object):
    """ Common functionality for DistGit handlers """
    sources_file_name = 'sources'
    uri = "/rpms/{name}/{filename}/{hashtype}/{hash}/{filename}"

    usage_name: str  # Name to use for dist-git-type
    re_source: Pattern[str]
    re_ignore_extensions: Pattern[str] = re.compile(r'\.(sign|asc|key)$')
    lookaside_server: str
    remote_substring: Pattern[str]

    def url_and_name(self, cwd: str = '.') -> List[Tuple[str, str]]:
        """
        Return list of urls and basenames of the used source

        The 'cwd' parameter has to be a DistGit directory.
        """
        # Assumes <package>.spec
        globbed = glob.glob(os.path.join(cwd, '*.spec'))
        if len(globbed) != 1:
            raise GeneralError(f"No .spec file is present in '{cwd}'.")
        package = os.path.basename(globbed[0])[:-len('.spec')]
        ret_values = []
        try:
            with open(os.path.join(cwd, self.sources_file_name)) as f:
                for line in f.readlines():
                    match = self.re_source.match(line)
                    if match is None:
                        raise GeneralError(
                            f"Couldn't match '{self.sources_file_name}' "
                            f"content with '{self.re_source.pattern}'.")
                    used_hash, source_name, hash_value = match.groups()
                    ret_values.append((self.lookaside_server + self.uri.format(
                        name=package,
                        filename=source_name,
                        hash=hash_value,
                        hashtype=used_hash.lower()
                        ), source_name))
        except Exception as error:
            raise GeneralError(
                f"Couldn't read '{self.sources_file_name}' file.",
                original=error)
        if not ret_values:
            raise GeneralError(
                "No sources found in '{self.sources_file_name}' file.")
        return ret_values

    def its_me(self, remotes: List[str]) -> bool:
        """ True if self can work with remotes """
        return any([self.remote_substring.search(item) for item in remotes])


class FedoraDistGit(DistGitHandler):
    """ Fedora Handler """
    usage_name = "fedora"
    re_source = re.compile(r"^(\w+) \(([^)]+)\) = ([0-9a-fA-F]+)$")
    lookaside_server = "https://src.fedoraproject.org/repo/pkgs"
    remote_substring = re.compile(r'fedoraproject\.org')


class CentOSDistGit(DistGitHandler):
    """ CentOS Handler """
    usage_name = "centos"
    re_source = re.compile(r"^(\w+) \(([^)]+)\) = ([0-9a-fA-F]+)$")
    lookaside_server = "https://sources.stream.centos.org/sources"
    remote_substring = re.compile(r'redhat/centos')


def get_distgit_handler(
        remotes: Optional[List[str]] = None,
        usage_name: Optional[str] = None) -> DistGitHandler:
    """
    Return the right DistGitHandler

    Pick the DistGitHandler class which understands specified
    remotes or by usage_name.
    """
    for candidate_class in DistGitHandler.__subclasses__():
        if usage_name is not None and usage_name == candidate_class.usage_name:
            return candidate_class()
        if remotes is not None:
            ret_val = candidate_class()
            if ret_val.its_me(remotes):
                return ret_val
    raise GeneralError(f"No known remote in '{remotes}'.")


def get_distgit_handler_names() -> List[str]:
    """ All known distgit handlers """
    return [i.usage_name for i in DistGitHandler.__subclasses__()]


def git_clone(
        url: str,
        destination: str,
        common: Common,
        env: Optional[EnvironmentType] = None,
        shallow: bool = False
        ) -> CommandOutput:
    """
    Git clone url to destination, retry without shallow if necessary

    For shallow=True attempt to clone repository using --depth=1 option first.
    If not successful attempt to clone whole repo.

    Common instance is used to run the command for appropriate logging.
    Environment is updated by 'env' dictionary.
    """
    depth = ['--depth=1'] if shallow else []
    command = ['git', 'clone'] + depth + [url, destination]
    try:
        return common.run(command, env=env)
    except RunError:
        if not shallow:
            # Do not retry if shallow was not used
            raise
        # Git server might not support shallow cloning, try again
        return git_clone(url, destination, common, env, shallow=False)


class updatable_message(contextlib.AbstractContextManager):  # type: ignore
    """ Updatable message suitable for progress-bar-like reporting """

    def __init__(
            self,
            key: str,
            enabled: bool = True,
            indent_level: int = 0,
            key_color: Optional[str] = None,
            default_value_color: Optional[str] = None
            ) -> None:
        """
        Updatable message suitable for progress-bar-like reporting.

        .. code:block:: python3

           with updatable_message('foo') as message:
               while ...:
                   ...

                   # check state of remote request, and update message
                   state = remote_api.check()
                   message.update(state)

        :param key: a string to use as the left-hand part of logged message.
        :param enabled: if unset, no output would be performed.
        :param indent_level: desired indentation level.
        :param key_color: optional color to apply to ``key``.
        :param default_color: optional color to apply to value when
            :py:meth:`update` is called with ``color`` left out.
        """

        self.key = key
        self.enabled = enabled
        self.indent_level = indent_level
        self.key_color = key_color
        self.default_value_color = default_value_color

        # No progress if terminal not attached
        if not sys.stdout.isatty():
            self.enabled = False

        self._previous_line: Optional[str] = None

    def __enter__(self) -> 'updatable_message':
        return self

    def __exit__(self, *args: Any) -> None:
        sys.stdout.write('\n')
        sys.stdout.flush()

    def update(self, value: str, color: Optional[str] = None) -> None:
        if not self.enabled:
            return

        if self._previous_line is not None:
            message = value.ljust(len(self._previous_line))

        else:
            message = value

        self._previous_line = value

        message = indent(
            self.key,
            value=style(
                message,
                fg=color or self.default_value_color),
            color=self.key_color,
            level=self.indent_level)

        sys.stdout.write(f"\r{message}")
        sys.stdout.flush()


def find_fmf_root(path: str) -> List[str]:
    """
    Search trough path and return all fmf roots that exist there

    Returned list is ordered by path length, shortest one first.

    Raise `MetadataError` if no fmf root is found.
    """
    fmf_roots = []
    for root, _, files in os.walk(path):
        if not os.path.basename(root) == '.fmf':
            continue
        if 'version' in files:
            fmf_roots.append(os.path.dirname(root))
    if not fmf_roots:
        raise MetadataError(f"No fmf root present inside '{path}'.")
    fmf_roots.sort(key=lambda path: len(path))
    return fmf_roots


#
# JSON schema-based validation helpers
#
# Aims at FMF data consumed by tmt, but can be used for any structure.
#

# `Schema` represents a loaded JSON schema structure. It may be fairly complex,
# but it's not needed to provide the exhaustive and fully detailed type since
# tmt code is not actually "reading" it. Loaded schema is passed down to
# jsonschema library, and while `Any` would be perfectly valid, let's use an
# alias to make schema easier to track in our code.
Schema = Dict[str, Any]
SchemaStore = Dict[str, Schema]


@functools.lru_cache(maxsize=None)
def load_schema(schema_filepath: str) -> Schema:
    """ Load a JSON schema from a given filepath """

    if not os.path.isabs(schema_filepath):
        schema_filepath = os.path.join(
            pkg_resources.resource_filename(
                'tmt', 'schemas'), schema_filepath)

    try:
        with open(schema_filepath, 'r', encoding='utf-8') as f:
            return cast(Schema, yaml_to_dict(f.read()))

    except Exception as exc:
        raise FileError(f"Failed to load schema file {schema_filepath}\n{exc}")


@functools.lru_cache(maxsize=None)
def load_schema_store() -> SchemaStore:
    """
    Load all available JSON schemas, and put them into a "store".

    Schema store is a simple mapping between schema IDs and schemas.
    """

    store: SchemaStore = {}

    schema_dirpath = pkg_resources.resource_filename('tmt', 'schemas')

    try:
        for dirpath, dirnames, filenames in os.walk(
                schema_dirpath, followlinks=True):
            for filename in filenames:
                # Ignore all files but YAML files.
                if os.path.splitext(filename)[1].lower() not in ('.yaml', '.yml'):
                    continue

                schema = load_schema(os.path.join(dirpath, filename))

                store[schema['$id']] = schema

    except Exception as exc:
        raise FileError(f"Failed to discover schema files\n{exc}")

    return store
