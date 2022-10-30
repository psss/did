"""
tmt's logging subsystem.

Adds a layer on top of Python's own :py:mod:`logging` subsystem. This layer implements the desired
verbosity and debug levels, colorization, formatting, verbosity inheritance and other features used
by tmt commands and code.

The main workhorses are :py:class:`Logger` instances. Each instance wraps a particular
:py:class:`logging.Logger` instance - usually there's a chain of such instances, with the root one
having console and logfile handlers attached. tmt's log verbosity/debug/quiet features are handled
on our side, with the use of :py:class:`logging.Filter` classes.

``Logger`` instances can be cloned and modified, to match various levels of tmt's runtime class
tree - ``tmt`` spawns a "root logger" from which a new one is cloned - and indented by one extra
level - for ``Run`` instance, and so on. This way, every object in tmt's hierarchy uses a given
logger, which may have its own specific settings, and, in the future, possibly also handlers for
special output channels.

While tmt recognizes several levels of verbosity (``-v``) and debugging (``-d``), all messages
emitted by :py:meth:`Logger.verbose` and :py:meth:`Logger.debug` use a single logging level,
``INFO`` or ``DEBUG``, respectively. The level of verbosity and debugging is then handled by a
special :py:class:`logging.Filter`` classes. This allows different levels when logging to console
but all-capturing log files while keeping implementation simple - the other option would be
managing handlers themselves, which would be very messy given the propagation of messages.
"""

import itertools
import logging
import logging.handlers
import os
import os.path
import sys
from typing import Any, Optional, cast

import click

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

# Log in workdir
LOG_FILENAME = 'log.txt'

# Hierarchy indent
INDENT = 4

DEFAULT_VERBOSITY_LEVEL = 0
DEFAULT_DEBUG_LEVEL = 0


def _debug_level_from_global_envvar() -> int:
    import tmt.utils

    raw_value = os.getenv('TMT_DEBUG', None)

    if raw_value is None:
        return 0

    try:
        return int(raw_value)

    except ValueError:
        raise tmt.utils.GeneralError(f"Invalid debug level '{raw_value}', use an integer.")


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
        key = click.style(key, fg=color)

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


class LogRecordDetails(TypedDict, total=False):
    """ tmt's log message components attached to log records """

    key: str
    value: Optional[str]

    color: Optional[str]
    shift: int

    logger_verbosity_level: int
    message_verbosity_level: Optional[int]

    logger_debug_level: int
    message_debug_level: Optional[int]

    logger_quiet: bool
    ignore_quietness: bool


class LogfileHandler(logging.FileHandler):
    def __init__(self, filepath: str) -> None:
        super().__init__(filepath, mode='a')


# ignore[type-arg]: StreamHandler is a generic type, but such expression would be incompatible
# with older Python versions. Since it's not critical to mark the handler as "str only", we can
# ignore the issue for now.
class ConsoleHandler(logging.StreamHandler):  # type: ignore[type-arg]
    pass


class _Formatter(logging.Formatter):
    def __init__(self, fmt: str, apply_colors: bool = False) -> None:
        super().__init__(fmt, datefmt='%H:%M:%S')

        self.apply_colors = apply_colors

        # TODO: this is an ugly hack, removing colors after they have been added...
        # Wouldn't it be better to not add them at first place?
        #
        # This is needed to deal with the code that colorizes just part of the message, like
        # tmt.result.Result outcomes: these are colorized, then merged with the number
        # of such outcomes, for example, and the string is handed over to logging method.
        # When colors are *not* to be applied, it's too late because colors have been
        # applied already. Something to fix...
        self._decolorize = self._dont_decolorize if apply_colors else self._do_decolorize

    def _do_decolorize(self, s: str) -> str:
        import tmt.utils

        return tmt.utils.remove_color(s)

    def _dont_decolorize(self, s: str) -> str:
        return s

    def format(self, record: logging.LogRecord) -> str:
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        # When message already exists, do nothing - it either some other logging subsystem,
        # or tmt's own, already rendered message.
        if hasattr(record, 'message'):
            pass

        # Otherwise render the message.
        else:
            if record.msg and record.args:
                record.message = record.msg % record.args

            else:
                record.message = record.msg

        # Original code from Formatter.format() - hard to inherit when overriding
        # Formatter.format()...
        s = self._decolorize(self.formatMessage(record))
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + record.exc_text
        if record.stack_info:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + self.formatStack(record.stack_info)
        return s


class LogfileFormatter(_Formatter):
    def __init__(self) -> None:
        super().__init__('%(asctime)s %(message)s', apply_colors=False)


class ConsoleFormatter(_Formatter):
    def __init__(self, apply_colors: bool = True) -> None:
        super().__init__('%(message)s', apply_colors=apply_colors)


class VerbosityLevelFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno != logging.INFO:
            return True

        details: Optional[LogRecordDetails] = getattr(record, 'details', None)

        if details is None:
            return True

        message_verbosity_level = details.get('message_verbosity_level', None)

        if message_verbosity_level is None:
            return True

        return True if details['logger_verbosity_level'] >= message_verbosity_level else False


class DebugLevelFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno != logging.DEBUG:
            return True

        details: Optional[LogRecordDetails] = getattr(record, 'details', None)

        if details is None:
            return True

        message_debug_level = details.get('message_debug_level', None)

        if message_debug_level is None:
            return True

        return True if details['logger_debug_level'] >= message_debug_level else False


class QuietnessFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno not in (logging.DEBUG, logging.INFO):
            return True

        details: Optional[LogRecordDetails] = getattr(record, 'details', None)

        if details is None:
            return False

        if not details.get('logger_quiet', False):
            return True

        if details.get('ignore_quietness', False):
            return True

        return False


class Logger:
    """
    A logging entry point, representing a certain level of verbosity and handlers.

    Provides actual logging methods plus methods for managing verbosity levels
    and handlers.
    """

    def __init__(
            self,
            actual_logger: logging.Logger,
            base_shift: int = 0,
            verbosity_level: int = DEFAULT_VERBOSITY_LEVEL,
            debug_level: int = DEFAULT_DEBUG_LEVEL,
            quiet: bool = False
            ) -> None:
        """
        Create a ``Logger`` instance with given verbosity levels.

        :param actual_logger: a :py:class:`logging.Logger` instance, the _raw logger_
            to use for logging.
        :param base_shift: shift applied to all messages processed by this logger.
        :param verbosity_level: desired verbosity level, usually derived from ``-v``
            command-line option.
        :param debug_level: desired debugging level, usually derived from ``-d``
            command-line option.
        :param quiet: if set, all messages would be supressed, with the exception of
            warnings (:py:meth:`warn`), errors (:py:meth:`fail`) and messages emitted
            with :py:meth:`print`.
        """

        self._logger = actual_logger

        self._base_shift = base_shift

        self._child_id_counter = itertools.count()

        self.verbosity_level = verbosity_level
        self.debug_level = debug_level
        self.quiet = quiet

    def __repr__(self) -> str:
        return '<Logger:' \
            f' name={self._logger.name}' \
            f' verbosity={self.verbosity_level}' \
            f' debug={self.debug_level}' \
            f' quiet={self.quiet}>'

    @staticmethod
    def _normalize_logger(logger: logging.Logger) -> logging.Logger:
        """ Reset properties of a given :py:class:`logging.Logger` instance """

        logger.propagate = True
        logger.level = logging.DEBUG

        logger.handlers = []

        return logger

    def clone(self) -> 'Logger':
        """
        Create a copy of this logger instance.

        All its settings are propagated to new instance. Settings are **not** shared,
        and may be freely modified after cloning without affecting the other logger.
        """

        return Logger(
            self._logger,
            base_shift=self._base_shift,
            verbosity_level=self.verbosity_level,
            debug_level=self.debug_level,
            quiet=self.quiet
            )

    def descend(
            self,
            logger_name: Optional[str] = None,
            extra_shift: int = 1
            ) -> 'Logger':
        """
        Create a copy of this logger instance, but with a new raw logger.

        New :py:class:`logging.Logger` instance is created from our raw logger, forming a
        parent/child relationship betwen them, and it's then wrapped with ``Logger`` instance.
        Settings of this logger are copied to new one, with the exception of ``base_shift``
        which is increased by one, effectively indenting all messages passing through new logger.

        :param logger_name: optional name for the underlying :py:class:`logging.Logger` instance.
            Useful for debugging. If not set, a generic one is created.
        :param extra_shift: by how many extra levels should messages be indented by new logger.
        """

        logger_name = logger_name or f'logger{next(self._child_id_counter)}'
        actual_logger = self._normalize_logger(self._logger.getChild(logger_name))

        return Logger(
            actual_logger,
            base_shift=self._base_shift + extra_shift,
            verbosity_level=self.verbosity_level,
            debug_level=self.debug_level,
            quiet=self.quiet
            )

    def add_logfile_handler(self, filepath: str) -> None:
        """ Attach a log file handler to this logger """

        handler = LogfileHandler(filepath)

        handler.setFormatter(LogfileFormatter())

        self._logger.addHandler(handler)

    def add_console_handler(self, apply_colors: bool = False) -> None:
        """ Attach console handler to this logger """

        handler = ConsoleHandler(stream=sys.stderr)

        handler.setFormatter(ConsoleFormatter(apply_colors=apply_colors))

        handler.addFilter(VerbosityLevelFilter())
        handler.addFilter(DebugLevelFilter())
        handler.addFilter(QuietnessFilter())

        self._logger.addHandler(handler)

    def apply_verbosity_options(self, **kwargs: Any) -> 'Logger':
        """
        Update logger's settings to match given CLI options.

        Use this method to update logger's settings after :py:meth:`Logger.descend` call,
        to reflect options given to a tmt subcommand.
        """

        verbosity_level = cast(Optional[int], kwargs.get('verbose', None))
        if verbosity_level is None:
            pass

        elif verbosity_level == 0:
            pass

        else:
            self.verbosity_level = verbosity_level

        debug_level_from_global_envvar = _debug_level_from_global_envvar()

        if debug_level_from_global_envvar not in (None, 0):
            self.debug_level = debug_level_from_global_envvar

        else:
            debug_level_from_option = cast(Optional[int], kwargs.get('debug', None))

            if debug_level_from_option is None:
                pass

            elif debug_level_from_option == 0:
                pass

            else:
                self.debug_level = debug_level_from_option

        quietness_level = kwargs.get('quiet', False)

        if quietness_level is True:
            self.quiet = quietness_level

        return self

    @classmethod
    def create(
            cls,
            actual_logger: Optional[logging.Logger] = None,
            **verbosity_options: Any) -> 'Logger':
        """
        Create a (root) tmt logger.

        This method has a very limited set of use cases:

        * CLI bootstrapping right after tmt started.
        * Unit tests of code that requires logger as one of its inputs.
        * 3rd party apps treating tmt as a library, i.e. when they wish tmt to
          use their logger instead of tmt's default one.

        :param actual_logger: a :py:class:`logging.Logger` instance to wrap.
            If not set, a default logger named ``tmt`` is created.
        """

        actual_logger = actual_logger or cls._normalize_logger(logging.getLogger('tmt'))

        return Logger(actual_logger) \
            .apply_verbosity_options(**verbosity_options)

    def _log(
            self,
            level: int,
            details: LogRecordDetails,
            message: str = ''
            ) -> None:
        """
        Emit a log record describing the message and related properties.

        This method converts tmt's specific logging approach, with keys, values, colors
        and shifts, to :py:class:`logging.LogRecord` instances compatible with :py:mod:`logging`
        workflow and carrying extra information for our custom filters and handlers.
        """

        details['logger_verbosity_level'] = self.verbosity_level
        details['logger_debug_level'] = self.debug_level
        details['logger_quiet'] = self.quiet

        details['shift'] = details.get('shift', 0) + self._base_shift

        if not message:
            message = indent(
                details['key'],
                value=details['value'],
                # Always apply colors - message can be decolorized later.
                color=details.get('color', None),
                level=details.get('shift', 0))

        self._logger._log(level, message, tuple(), extra={'details': details})

    def print(
            self,
            key: str,
            value: Optional[str] = None,
            color: Optional[str] = None,
            shift: int = 0,
            ) -> None:
        self._log(
            logging.INFO,
            {
                'key': key,
                'value': value,
                'color': color,
                'shift': shift,
                'ignore_quietness': True
                }
            )

    def info(
            self,
            key: str,
            value: Optional[str] = None,
            color: Optional[str] = None,
            shift: int = 0
            ) -> None:
        self._log(logging.INFO, {'key': key, 'value': value, 'color': color, 'shift': shift})

    def verbose(
            self,
            key: str,
            value: Optional[str] = None,
            color: Optional[str] = None,
            shift: int = 0,
            level: int = 1,
            ) -> None:
        self._log(
            logging.INFO,
            {
                'key': key,
                'value': value,
                'color': color,
                'shift': shift,
                'message_verbosity_level': level
                }
            )

    def debug(
            self,
            key: str,
            value: Optional[str] = None,
            color: Optional[str] = None,
            shift: int = 0,
            level: int = 1
            ) -> None:
        self._log(
            logging.DEBUG,
            {
                'key': key,
                'value': value,
                'color': color,
                'shift': shift,
                'message_debug_level': level
                }
            )

    def warn(
            self,
            message: str,
            shift: int = 0
            ) -> None:
        self._log(
            logging.WARN,
            {
                'key': 'warn',
                'value': message,
                'color': 'yellow',
                'shift': shift
                }
            )

    def fail(
            self,
            message: str,
            shift: int = 0
            ) -> None:
        self._log(
            logging.ERROR,
            {
                'key': 'fail',
                'value': message,
                'color': 'red',
                'shift': shift
                }
            )
