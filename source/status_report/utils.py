# coding: utf-8
""" Comfortably generate reports - Utils """

from __future__ import absolute_import

import ConfigParser
import logging
import os
from pprint import pformat as pretty  # NOQA - pyflakes ignore
import re
import sys
import unicodedata

log = logging.getLogger('status-report')

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Config file location
CONFIG = os.path.expanduser("~/.status-report")

# Default maximum width
MAX_WIDTH = 79

# Coloring
COLOR_ON = 1
COLOR_OFF = 0
COLOR_AUTO = 2

# Logging
LOG_ERROR = logging.ERROR
LOG_WARN = logging.WARN
LOG_INFO = logging.INFO
LOG_DEBUG = logging.DEBUG
LOG_CACHE = 7
LOG_DATA = 4
LOG_ALL = 1

# Extract name and email from string
# See: http://stackoverflow.com/questions/14010875
EMAIL_REGEXP = re.compile(r'(?:"?([^"]*)"?\s)?(?:<?(.+@[^>]+)>?)')

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Utils
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def eprint(text):
    """ Print (optionaly encoded) text """
    # When there's no terminal we need to explicitly encode strings.
    # Otherwise this would cause problems when redirecting output.
    print((text if sys.stdout.isatty() else text.encode("utf8")))


def header(text):
    """ Show text as a header. """
    eprint(u"\n{0}\n {1}\n{0}".format(79 * "~", text))


def shorted(text, width=79):
    """ Shorten text, make sure it's not cut in the middle of a word """
    if len(text) <= width:
        return text
    # We remove any word after first overlapping non-word character
    return u"{0}...".format(re.sub(r"\W+\w*$", "", text[:width - 2]))


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
    eprint(u"{0}* {1}".format(u" " * indent, shorted(unicode(text), width)))


def pluralize(singular=None, plural=None):
    """ Naively pluralize words """
    if singular is not None and plural is None:
        if singular.endswith("y") and not singular.endswith("ay"):
            plural = singular[:-1] + "ies"
        elif singular.endswith("s"):
            plural = singular + "es"
        else:
            plural = singular + "s"
    return plural


def listed(items, singular=None, plural=None, max=None, quote=""):
    """
    Convert an iterable into a nice, human readable list or description.

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
    items = range(items) if isinstance(items, int) else list(items)
    more = " more"
    # Description mode expected when singular provided but no maximum set
    if singular is not None and max is None:
        max = 0
        more = ""
    # Set the default plural form
    plural = pluralize(singular, plural)
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


def ascii(text):
    """ Transliterate special unicode characters into pure ascii """
    if not isinstance(text, unicode):
        text = unicode(text)
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore')


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
        LOG_CACHE: "cyan",
        LOG_DATA: "magenta",
    }
    # Environment variable mapping
    MAPPING = {
        0: LOG_WARN,
        1: LOG_INFO,
        2: LOG_DEBUG,
        3: LOG_CACHE,
        4: LOG_DATA,
        5: LOG_ALL,
    }
    # All levels
    LEVELS = "CRITICAL DEBUG ERROR FATAL INFO NOTSET WARN WARNING".split()

    # Default log level is WARN
    _level = LOG_WARN

    def __init__(self, name='status-report'):
        self.logger = self._create_logger()
        self.set()

    class ColoredFormatter(logging.Formatter):
        """ Custom color formatter for logging """
        def format(self, record):
            # Handle custom log level names
            if record.levelno == LOG_ALL:
                levelname = "ALL"
            elif record.levelno == LOG_DATA:
                levelname = "DATA"
            elif record.levelno == LOG_CACHE:
                levelname = "CACHE"
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
            return u"{0} {1}".format(level, record.getMessage())

    @staticmethod
    def _create_logger(name='status-report', level=None):
        """ Create status-report logger """
        # Create logger, handler and formatter
        logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        handler.setFormatter(Logging.ColoredFormatter())
        logger.addHandler(handler)
        # Save log levels in the logger itself (backward compatibility)
        for level in Logging.LEVELS:
            setattr(logger, level, getattr(logging, level))
        # Additional logging constants and methods for cache and xmlrpc
        logger.DATA = LOG_DATA
        logger.CACHE = LOG_CACHE
        logger.ALL = LOG_ALL
        logger.cache = lambda message: logger.log(LOG_CACHE, message) # NOQA
        logger.data = lambda message: logger.log(LOG_DATA, message) # NOQA
        logger.all = lambda message: logger.log(LOG_ALL, message) # NOQA
        return logger

    def set(self, level=None):
        """
        Set the default log level

        If the level is not specified environment variable DEBUG is used
        with the following meaning:

            DEBUG=0 ... LOG_WARN (default)
            DEBUG=1 ... LOG_INFO
            DEBUG=2 ... LOG_DEBUG
            DEBUG=3 ... LOG_CACHE
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
            except StandardError:
                Logging._level = logging.WARN
        self.logger.setLevel(Logging._level)

    def get(self):
        """ Get the current log level """
        return self.logger.level


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Config
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Config(object):
    """ User config file """

    def __init__(self):
        """ Read the config file. """
        self.parser = ConfigParser.SafeConfigParser()
        self.parser.read([CONFIG])

    @property
    def user(self):
        try:
            return self.parser.get("general", "user").split(", ")
        except ConfigParser.NoOptionError:
            return []

    @property
    def email(self):
        try:
            mails = self.parser.get("general", "email").split(", ")
            return [mail.decode("utf-8") for mail in mails]
        except ConfigParser.NoOptionError:
            return []

    @property
    def width(self):
        """ Maximum width of the report """
        try:
            return int(self.parser.get("general", "width"))
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            return MAX_WIDTH

    @property
    def grades(self):
        """ Include bug grades """
        try:
            value = self.parser.get("general", "grades")
            return value == '1' or value.lower() == 'true'
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            return False

    def sections(self, kind=None):
        """ Return all sections (optionally of given kind only) """
        result = []
        for section in self.parser.sections():
            # Selected kind only if provided
            if kind is not None:
                try:
                    section_type = self.parser.get(section, "type")
                    if section_type != kind:
                        continue
                except ConfigParser.NoOptionError:
                    # Implicit header/footer type for backward compatibility
                    if (section == kind == "header" or
                            section == kind == "footer"):
                        pass
                    else:
                        continue
            result.append(section)
        return result

    def section(self, section, skip=None):
        """ Return section items, skip selected (type/order by default) """
        if skip is None:
            skip = ['type', 'order']
        return [(key, val) for key, val in self.parser.items(section)
                if key not in skip]

    def item(self, section, it):
        """ Return content of given item in selected section """
        for key, value in self.section(section, skip=['type']):
            if key == it:
                return value
        raise ConfigError(
            "Item '{0}' not found in section '{1}'".format(it, section))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Color
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
        """ Set the coloring mode """
        # Detect from the environment if no mode given (only once)
        if mode is None:
            # Nothing to do if already detected
            if self._mode is not None:
                return
            # Detect from the environment variable COLOR
            try:
                mode = int(os.environ["COLOR"])
            except StandardError:
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


def set_color_mode(mode):
    """
    Set the coloring mode

    If enabled, some objects (like case run Status) are printed in color
    to easily spot failures, errors and so on. By default the feature is
    enabled when script is attached to a terminal. Possible values are:

        COLOR=0 ... COLOR_OFF .... coloring disabled
        COLOR=1 ... COLOR_ON ..... coloring enabled
        COLOR=2 ... COLOR_AUTO ... if terminal attached (default)

    Environment variable COLOR can be used to set up the coloring to the
    desired mode without modifying code.
    """
    Coloring().set(mode)


def get_color_mode():
    """ Get the current coloring mode """
    return Coloring().get()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Exceptions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class ConfigError(Exception):
    """ General problem with configuration file """
    pass


class ReportError(Exception):
    """ General problem with report generation """
    pass
