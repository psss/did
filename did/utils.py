# coding: utf-8

""" Logging, config, constants & utilities """

import importlib
import logging
import os
import pkgutil
import re
import sys
import unicodedata
from pprint import pformat as pretty  # noqa: F401 (used by other modules)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Coloring
COLOR_ON = 1
COLOR_OFF = 0
COLOR_AUTO = 2

# Logging
LOG_ERROR = logging.ERROR
LOG_WARN = logging.WARN
LOG_INFO = logging.INFO
LOG_DEBUG = logging.DEBUG
LOG_DETAILS = 7
LOG_DATA = 4
LOG_ALL = 1

# Extract name and email from string
# See: http://stackoverflow.com/questions/14010875
EMAIL_REGEXP = re.compile(r'(?:"?([^"]*)"?\s)?(?:<?(.+@[^>]+)>?)')


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Utils
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def _find_base(path):
    """
    Given a path to a python file or package, find the top level
    directory that isn't a valid package.
    """
    if not os.path.isdir(path):
        path = os.path.dirname(path)

    if not os.path.exists(os.path.join(path, "__init__.py")):
        return None

    while os.path.exists(os.path.join(path, "__init__.py")):
        path = os.path.dirname(path)

    return path


def _import(path, continue_on_error):
    """
    Eats or raises import exceptions based on ``continue_on_error``.
    """
    log.debug("Importing %s" % path)
    try:
        # importlib is available in stdlib from 2.7+
        return importlib.import_module(path)
    except Exception as ex:
        log.info(ex)
        if not continue_on_error:
            raise


def _load_components(
        path, include=".*", exclude="test", continue_on_error=True):
    """ Import modules, handle include/exclude filtering """
    num_loaded = 0
    if path.endswith(".py"):
        path, _ = os.path.splitext(path)

    path = path.rstrip("/").replace("/", ".")

    package = _import(path, continue_on_error)
    if not package:
        return 0

    num_loaded += 1

    do_include = re.compile(include).search if include else lambda x: True
    do_exclude = re.compile(exclude).search if exclude else lambda x: False

    if not hasattr(package, "__path__"):
        return num_loaded

    prefix = package.__name__ + "."
    for _, name, is_pkg in pkgutil.iter_modules(
            path=package.__path__, prefix=prefix):
        if not name.startswith(prefix):
            name = prefix + name
        if is_pkg:
            num_loaded += _load_components(
                name, include, exclude, continue_on_error)
        else:
            if do_include(name) and not do_exclude(name):
                _import(name, continue_on_error)
                num_loaded += 1

    return num_loaded


def load_components(*paths, **kwargs):
    """
    Load all components on the paths

    Each path should be a package or module. All components beneath a
    path are loaded. This method works whether the package or module is
    on the filesystem or in an .egg. If it's in an egg, the egg must
    already be on the ``PYTHONPATH``.

    Args:
        paths (str): A package or module to load

    Keyword Args:
        include (str): A regular expression of packages and modules to
            include. Defaults to '.*'
        exclude (str): A regular expression of packges and modules to
            exclude. Defaults to 'test'
        continue_on_error (bool): If True, continue importing even if
            something raises an ImportError. If False, raise the first
            ImportError.

    Returns:
        int: The total number of modules loaded.

    Raises:
        ImportError
    """
    continue_on_error = kwargs.get("continue_on_error", True)
    num_loaded = 0
    for path in paths:
        tmp = os.path.expandvars(os.path.expanduser(path))
        fs_path = os.path.realpath(tmp)
        if os.path.exists(fs_path):
            base = _find_base(fs_path)
            if not base:
                msg = "%s is not a valid python module or package." % path
                if continue_on_error:
                    log.info(msg)
                    continue
                else:
                    raise ImportError(path)
            if base not in sys.path:
                sys.path.insert(0, base)

            target = os.path.relpath(fs_path, base)
            num_loaded += _load_components(target, **kwargs)
        else:
            num_loaded += _load_components(path, **kwargs)
    return num_loaded


def header(text, separator_width=79, separator="~"):
    """ Show text as a header. """
    print("\n{0}\n {1}\n{0}".format(separator_width * separator, text))


def shorted(text, width=79):
    """ Shorten text, make sure it's not cut in the middle of a word """
    if len(text) <= width:
        return text
    # We remove any word after first overlapping non-word character
    return "{0}...".format(re.sub(r"\W+\w*$", "", text[:width - 2]))


def item(text, level=0, options=None):
    """ Print indented item. """
    # Extra line before in each section (unless brief)
    if level == 0 and not options.brief:
        print('')
    # Only top-level items displayed in brief mode
    if level == 1 and options.brief:
        return
    # Four space for each level, additional space for wiki format
    indent = level * 4
    if options.format == "wiki" and level == 0:
        indent = 1
    # Shorten the text if necessary to match the desired maximum width
    width = options.width - indent - 2 if options.width else 333
    print("{0}* {1}".format(" " * indent, shorted(str(text), width)))


def pluralize(singular=None):
    """ Naively pluralize words """
    if singular.endswith("y") and not singular.endswith("ay"):
        plural = singular[:-1] + "ies"
    elif singular.endswith("s"):
        plural = singular + "es"
    else:
        plural = singular + "s"
    return plural


def listed(items, singular=None, plural=None, max=None, quote=""):
    """
    Convert an iterable into a nice, human readable list or
    description::

        listed(range(1)) .................... 0
        listed(range(2)) .................... 0 and 1
        listed(range(3), quote='"') ......... "0", "1" and "2"
        listed(range(4), max=3) ............. 0, 1, 2 and 1 more
        listed(range(5), 'number', max=3) ... 0, 1, 2 and 2 more numbers
        listed(range(6), 'category') ........ 6 categories
        listed(7, "leaf", "leaves") ......... 7 leaves

    If singular form is provided but max not set the description-only
    mode is activated as shown in the last two examples. Also, an int
    can be used in this case to get a simple inflection functionality.
    """

    # Convert items to list if necessary
    items = list(range(items)) if isinstance(items, int) else list(items)
    more = " more"
    # Description mode expected when singular provided
    # but no maximum set
    if singular is not None and max is None:
        max = 0
        more = ""
    # Set the default plural form
    if singular is not None and plural is None:
        plural = pluralize(singular)
    # Convert to strings and optionally quote each item
    items = ["{0}{1}{0}".format(quote, item) for item in items]

    # Select the maximum of items and describe the rest if max provided
    if max is not None:
        # Special case when the list is empty (0 items)
        if max == 0 and len(items) == 0:
            return "0 {0}".format(plural)
        # Cut the list if maximum exceeded
        if len(items) > max:
            rest = len(items[max:])
            items = items[:max]
            if singular is not None:
                more += " {0}".format(singular if rest == 1 else plural)
            items.append("{0}{1}".format(rest, more))

    # For two and more items use 'and' instead of the last comma
    if len(items) < 2:
        return "".join(items)
    else:
        return ", ".join(items[0:-2] + [" and ".join(items[-2:])])


def split(values, separator=re.compile("[ ,]+")):
    """
    Convert space-or-comma-separated values into a single list

    Common use case for this is merging content of options with multiple
    values allowed into a single list of strings thus allowing any of
    the formats below and converts them into ['a', 'b', 'c']::

        --option a --option b --option c ... ['a', 'b', 'c']
        --option a,b --option c ............ ['a,b', 'c']
        --option 'a b c' ................... ['a b c']

    Accepts both string and list. By default space and comma are used as
    value separators. Use any regular expression for custom separator.
    """
    if not isinstance(values, list):
        values = [values]
    return sum([separator.split(value) for value in values], [])


def ascii(text):
    """ Transliterate special unicode characters into pure ascii """
    if not isinstance(text, str):
        text = str(text)
    return unicodedata.normalize(
        'NFKD', text).encode('ascii', 'ignore').decode('utf-8')


def info(message, newline=True):
    """ Log provided info message to the standard error output """
    sys.stderr.write(message + ("\n" if newline else ""))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Logging
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Logging(object):
    """ Logging Configuration """

    # Color mapping
    COLORS = {
        LOG_ERROR: "red",
        LOG_WARN: "yellow",
        LOG_INFO: "blue",
        LOG_DEBUG: "green",
        LOG_DETAILS: "cyan",
        LOG_DATA: "magenta",
        }
    # Environment variable mapping
    MAPPING = {
        0: LOG_WARN,
        1: LOG_INFO,
        2: LOG_DEBUG,
        3: LOG_DETAILS,
        4: LOG_DATA,
        5: LOG_ALL,
        }
    # All levels
    LEVELS = "CRITICAL DEBUG ERROR FATAL INFO NOTSET WARN WARNING".split()

    # Default log level is WARN
    _level = LOG_WARN

    # Already initialized loggers by their name
    _loggers = dict()

    def __init__(self, name='did'):
        # Use existing logger if already initialized
        try:
            self.logger = Logging._loggers[name]
        # Otherwise create a new one, save it and set it
        except KeyError:
            self.logger = self._create_logger(name=name)
            Logging._loggers[name] = self.logger
            self.set()

    class ColoredFormatter(logging.Formatter):
        """ Custom color formatter for logging """

        def format(self, record):
            # Handle custom log level names
            if record.levelno == LOG_ALL:
                levelname = "ALL"
            elif record.levelno == LOG_DATA:
                levelname = "DATA"
            elif record.levelno == LOG_DETAILS:
                levelname = "DETAILS"
            else:
                levelname = record.levelname
            # Map log level to appropriate color
            try:
                colour = Logging.COLORS[record.levelno]
            except KeyError:
                colour = "black"
            # Color the log level, use brackets when coloring off
            if Coloring().enabled():
                level = color(" " + levelname + " ", "lightwhite", colour)
            else:
                level = "[{0}]".format(levelname)
            return "{0} {1}".format(level, record.getMessage())

    @staticmethod
    def _create_logger(name='did', level=None):
        """ Create did logger """
        # Create logger, handler and formatter
        logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        handler.setFormatter(Logging.ColoredFormatter())
        logger.addHandler(handler)
        # Save log levels in the logger itself (backward compatibility)
        for level in Logging.LEVELS:
            setattr(logger, level, getattr(logging, level))
        # Additional logging constants and methods for details and data
        logger.DATA = LOG_DATA
        logger.DETAILS = LOG_DETAILS
        logger.ALL = LOG_ALL
        logger.details = lambda message: logger.log(
            LOG_DETAILS, message)  # NOQA
        logger.data = lambda message: logger.log(
            LOG_DATA, message)  # NOQA
        logger.all = lambda message: logger.log(
            LOG_ALL, message)  # NOQA
        return logger

    def set(self, level=None):
        """
        Set the default log level

        If the level is not specified environment variable DEBUG is used
        with the following meaning::

            DEBUG=0 ... LOG_WARN (default)
            DEBUG=1 ... LOG_INFO
            DEBUG=2 ... LOG_DEBUG
            DEBUG=3 ... LOG_DETAILS
            DEBUG=4 ... LOG_DATA
            DEBUG=5 ... LOG_ALL (log all messages)
        """
        # If level specified, use given
        if level is not None:
            Logging._level = level
        # Otherwise attempt to detect from the environment
        else:
            try:
                Logging._level = Logging.MAPPING[int(os.environ["DEBUG"])]
            except KeyError:
                Logging._level = logging.WARN
        self.logger.setLevel(Logging._level)

    def get(self):
        """ Get the current log level """
        return self.logger.level


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Coloring
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def color(text, color=None, background=None, light=False, enabled=True):
    """
    Return text in desired color if coloring enabled

    Available colors: black red green yellow blue magenta cyan white.
    Alternatively color can be prefixed with "light", e.g. lightgreen.
    """
    colors = {"black": 30, "red": 31, "green": 32, "yellow": 33,
              "blue": 34, "magenta": 35, "cyan": 36, "white": 37}
    # Nothing do do if coloring disabled
    if not enabled:
        return text
    # Prepare colors (strip 'light' if present in color)
    if color and color.startswith("light"):
        light = True
        color = color[5:]
    color = color and ";{0}".format(colors[color]) or ""
    background = background and ";{0}".format(colors[background] + 10) or ""
    light = light and 1 or 0
    # Starting and finishing sequence
    start = "\033[{0}{1}{2}m".format(light, color, background)
    finish = "\033[1;m"
    return "".join([start, text, finish])


class Coloring(object):
    """ Coloring configuration """

    # Default color mode is auto-detected from the terminal presence
    _mode = None
    MODES = ["COLOR_OFF", "COLOR_ON", "COLOR_AUTO"]
    # We need only a single config instance
    _instance = None

    def __new__(cls, *args, **kwargs):
        """ Make sure we create a single instance only """
        if not cls._instance:
            cls._instance = super(Coloring, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, mode=None):
        """ Initialize the coloring mode """
        # Nothing to do if already initialized
        if self._mode is not None:
            return
        # Set the mode
        self.set(mode)

    def set(self, mode=None):
        """
        Set the coloring mode

        If enabled, some objects (like case run Status) are printed in
        color to easily spot failures, errors and so on. By default the
        feature is enabled when script is attached to a terminal.
        Possible values are::

            COLOR=0 ... COLOR_OFF .... coloring disabled
            COLOR=1 ... COLOR_ON ..... coloring enabled
            COLOR=2 ... COLOR_AUTO ... if terminal attached (default)

        Environment variable COLOR can be used to set up the coloring to
        the desired mode without modifying code.
        """
        # Detect from the environment if no mode given (only once)
        if mode is None:
            # Nothing to do if already detected
            if self._mode is not None:
                return
            # Detect from the environment variable COLOR
            try:
                mode = int(os.environ["COLOR"])
            except KeyError:
                mode = COLOR_AUTO
        elif mode < 0 or mode > 2:
            raise RuntimeError("Invalid color mode '{0}'".format(mode))
        self._mode = mode
        log.debug(
            "Coloring {0} ({1})".format(
                "enabled" if self.enabled() else "disabled",
                self.MODES[self._mode]))

    def get(self):
        """ Get the current color mode """
        return self._mode

    def enabled(self):
        """ True if coloring is currently enabled """
        # In auto-detection mode color enabled when terminal attached
        if self._mode == COLOR_AUTO:
            return sys.stdout.isatty()
        return self._mode == COLOR_ON


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Default Logger
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Create the default output logger
log = Logging('did').logger
