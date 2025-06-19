""" Config, Date, User and Exceptions """

import codecs
import configparser
import contextlib
import datetime
import io
import locale
import os
import re
import sys
from configparser import NoOptionError, NoSectionError
from datetime import timedelta
from typing import Optional

from dateutil.relativedelta import FR as FRIDAY
from dateutil.relativedelta import MO as MONDAY
from dateutil.relativedelta import SA as SATURDAY
from dateutil.relativedelta import SU as SUNDAY
from dateutil.relativedelta import TH as THURSDAY
from dateutil.relativedelta import TU as TUESDAY
from dateutil.relativedelta import WE as WEDNESDAY
from dateutil.relativedelta import relativedelta as delta

from did import utils
from did.utils import DEFAULT_SEPARATOR, MAX_WIDTH, log

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

WEEKDAY_MAP = {
    "monday": MONDAY(-1),
    "tuesday": TUESDAY(-1),
    "wednesday": WEDNESDAY(-1),
    "thursday": THURSDAY(-1),
    "friday": FRIDAY(-1),
    "saturday": SATURDAY(-1),
    "sunday": SUNDAY(-1),
    }

# Config file location
CONFIG = os.path.expanduser("~/.did")

# Today's date
TODAY = datetime.date.today()

TEST_CONFIG = """
[general]
width = 79
email = Petr Šplíchal <psplicha@redhat.com>

[koji]
type = koji
url = https://koji.fedoraproject.org/kojihub
weburl = https://koji.fedoraproject.org/koji
login = psss
name = Fedora Build System
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Exceptions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GeneralError(Exception):
    """ General stats error """


class ConfigError(GeneralError):
    """ Stats configuration problem """


class ConfigFileError(ConfigError):
    """ Problem with the config file """


class OptionError(GeneralError):
    """ Invalid command line """


class ReportError(GeneralError):
    """ Report generation error """

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Functions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@contextlib.contextmanager
def setlocale(*args, **kw):
    saved = locale.setlocale(locale.LC_ALL)
    yield locale.setlocale(*args, **kw)
    locale.setlocale(locale.LC_ALL, saved)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Config
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Config():
    """ User config file """

    parser = None

    def __init__(self, config=None, path=None):
        """
        Read the config file

        Parse config from given string (config) or file (path).
        If no config or path given, default to "~/.did/config" which
        can be overridden by the ``DID_DIR`` environment variable.
        """
        # Read the config only once (unless explicitly provided)
        if self.parser is not None and config is None and path is None:
            return
        Config.parser = configparser.ConfigParser(interpolation=None)
        # If config provided as string, parse it directly
        if config is not None:
            log.info("Inspecting config file from string")
            log.debug(utils.pretty(config))
            self.parser.read_file(io.StringIO(config))
            return
        # Check the environment for config file override
        # (unless path is explicitly provided)
        if path is None:
            path = Config.path()
        # Parse the config from file
        try:
            log.info("Inspecting config file '%s'.", path)
            with codecs.open(path, "r", "utf8") as config_file:
                self.parser.read_file(config_file)
        except IOError as error:
            log.debug(error)
            Config.parser = None
            raise ConfigFileError(
                f"Unable to read the config file '{path}'.") from error

    @property
    def plugins(self):
        """ Custom plugins """
        try:
            return self.parser.get("general", "plugins")
        except configparser.Error:
            # No custom plugin listed within the configuration
            return None

    @property
    def quarter(self):
        """ The first month of the quarter, 1 by default """
        month = self.parser.get("general", "quarter", fallback=1)
        try:
            month = int(month) % 3
        except ValueError as exc:
            raise ConfigError(
                f"Invalid quarter start '{month}', should be integer.") from exc
        return month

    @property
    def email(self):
        """ User email(s) """
        try:
            return self.parser.get("general", "email")
        except NoSectionError as error:
            log.debug(error)
            raise ConfigFileError(
                "No general section found in the config file.") from error
        except NoOptionError as error:
            log.debug(error)
            raise ConfigFileError(
                "No email address defined in the config file.") from error

    @property
    def width(self):
        """ Maximum width of the report """
        try:
            return int(self.parser.get("general", "width"))
        except (NoOptionError, NoSectionError):
            return MAX_WIDTH

    @property
    def separator(self):
        """ Separator character to use for the report """
        try:
            return self.parser.get("general", "separator")
        except (NoOptionError, NoSectionError):
            return DEFAULT_SEPARATOR

    @property
    def separator_width(self):
        """ Number of separator characters to use for the report """
        try:
            return int(self.parser.get("general", "separator_width"))
        except (NoOptionError, NoSectionError):
            return MAX_WIDTH

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
                except NoOptionError:
                    continue
            result.append(section)
        return result

    def section(self, section, skip=('type', 'order')):
        """
        Return section items, skip selected (type/order by default)
        """
        return [(key, val) for key, val in self.parser.items(section)
                if key not in skip]

    def item(self, section, it):
        """ Return content of given item in selected section """
        for key, value in self.section(section, skip=[]):
            if key == it:
                return value
        raise ConfigError(f"Item '{it}' not found in section '{section}'")

    @staticmethod
    def path():
        """ Detect config file path """
        # Detect config directory
        try:
            directory = os.environ["DID_DIR"]
        except KeyError:
            directory = CONFIG
        # Detect config file (even before options are parsed)
        filename = "config"
        matched = re.search(r"--confi?g?[ =](\S+)", " ".join(sys.argv))
        if matched:
            filepath, filename = os.path.split(matched.groups()[0])
            if filepath:
                directory = filepath
        return os.path.join(directory.rstrip("/"), filename)

    @staticmethod
    def example():
        """ Return config example """
        return "[general]\nemail = Name Surname <email@example.org>\n"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Date
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Date():
    """ Date parsing for common word formats """

    def __init__(self, date=None):
        """ Parse the date string """
        if isinstance(date, datetime.date):
            self.date = date
        elif date is None or date.lower() == "today":
            self.date = TODAY
        elif date.lower() == "yesterday":
            self.date = TODAY - delta(days=1)
        else:
            try:
                self.date = datetime.date(*[int(i) for i in date.split("-")])
            except ValueError as error:
                log.debug(error)
                raise OptionError(
                    f"Invalid date format: '{date}', use YYYY-MM-DD.") from error
        self.datetime = datetime.datetime(
            self.date.year, self.date.month, self.date.day, 0, 0, 0)

    def __str__(self):
        """ String format for printing """
        return str(self.date)

    def __add__(self, addend):
        """ 'addend' days after the date """
        return self.date + timedelta(days=addend)

    def __sub__(self, subtrahend):
        """ 'subtrahend' days before the date """
        return self.date - timedelta(days=subtrahend)

    @staticmethod
    def get_week(last):
        # Return start and end date of the current week.
        since = TODAY + delta(weekday=MONDAY(-1))
        until = since + delta(weeks=1)
        if last:
            # Return start and end date of the last week instead.
            since = TODAY + delta(weekday=MONDAY(-2))
            until = since + delta(weeks=1)
        period = f"the week {since.strftime('%V')}"
        return Date(since), Date(until), period

    @staticmethod
    def get_month(last):
        # Return start and end date of this month.
        since = TODAY + delta(day=1)
        until = since + delta(months=1)
        if last:
            # Return start and end date of this month.
            since = TODAY + delta(day=1, months=-1)
            until = since + delta(months=1)
        with setlocale(locale.LC_TIME, "C"):
            period = since.strftime("%B")
        return Date(since), Date(until), period

    @staticmethod
    def get_quarter(last):
        # Return start and end date of this quarter.
        since = TODAY + delta(day=1)
        while since.month % 3 != Config().quarter:
            since -= delta(months=1)
        until = since + delta(months=3)
        period = "this quarter"
        if last:
            # Return start and end date of last quarter instead
            since = since - delta(months=3)
            until = until - delta(months=3)
            period = "the last quarter"
        return Date(since), Date(until), period

    @staticmethod
    def get_year(last):
        # Return start and end date of this year
        since = TODAY
        while since.month != 1 or since.day != 1:
            since -= delta(days=1)
        until = since + delta(years=1)
        period = "this year"
        if last:
            # Return start and end date of the last year instead
            since = since - delta(years=1)
            until = until - delta(years=1)
            period = "the last year"
        return Date(since), Date(until), period

    @staticmethod
    def period(argument):
        """ Detect desired time period for the argument """
        def get_weekday_details(arg):
            for day, weekday in WEEKDAY_MAP.items():
                if day in arg:
                    return weekday, f"the last {day}"
            return None, None  # pragma: no cover

        def calculate_since_until_for_weekday(weekday):
            today = Date("today")
            since = Date("today")
            until = Date()
            since.date += delta(weekday=weekday)
            if since.date == today.date:
                since.date -= delta(days=7)
            until.date = since.date + delta(days=1)
            return since, until

        if "today" in argument:
            since, until = Date("today"), Date("today")
            until.date += delta(days=1)
            period = "today"

        elif "yesterday" in argument:
            since, until = Date("yesterday"), Date("yesterday")
            until.date += delta(days=1)
            period = "yesterday"

        elif any(day in argument for day in WEEKDAY_MAP):
            weekday, period = get_weekday_details(argument)
            since, until = calculate_since_until_for_weekday(weekday)

        elif "year" in argument:
            since, until, period = Date.get_year("last" in argument)

        elif "quarter" in argument:
            since, until, period = Date.get_quarter("last" in argument)

        elif "month" in argument:
            since, until, period = Date.get_month("last" in argument)

        else:  # Default to week
            since, until, period = Date.get_week("last" in argument)

        return since, until, period


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  User
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class User():
    """
    User information

    The User object holds name, login and email which are used for
    performing queries by individual plugins. This information is
    parsed from given email address. Both short & full email format
    are supported::

        some@email.org
        Name Surname <some@email.org>

    In addition, it's possible to provide email and login aliases for
    individual stats. This is useful if you use different email/login
    for different services. The syntax consists of ``stats: login`` or
    ``stats: email`` pairs appended at the end of the email address::

        some@email.org; bz: bugzilla@email.org; gh: githublogin

    Use config section name to identify stats where given alias should
    be used. The exactly same syntax can be used both in the config file
    and on the command line. Finally it's also possible to include the
    alias directly in the respective config section::

        [github]
        type = github
        url = https://api.github.com/
        login = psss
    """

    def __init__(self, email, stats=None):
        """ Detect name, login and email """
        # Make sure we received the email string, save the original for
        # cloning
        if not email:
            raise ConfigError("Email required for user initialization.")
        self._original = email.strip()
        # Separate aliases if provided
        try:
            email, aliases = re.split(r"\s*;\s*", self._original, maxsplit=1)
        except ValueError:
            email = self._original
            aliases = None
        # Extract everything from the email string provided
        parts = utils.EMAIL_REGEXP.search(email)
        if parts is None:
            raise ConfigError(f"Invalid email address '{email}'")
        self.name = parts.groups()[0]
        self.email = parts.groups()[1]
        self.login = self.email.split('@')[0]
        # Check for possible aliases
        self.alias(aliases, stats)

    def __str__(self):
        """ Use name & email for string representation. """
        if not self.name:
            return self.email
        return f"{self.name} <{self.email}>"

    def clone(self, stats):
        """ Create a user copy with alias enabled for given stats. """
        return User(self._original, stats)

    def alias(self, aliases, stats):
        """ Apply the login/email alias if configured. """
        login = email = None
        if stats is None:
            return
        # Attempt to use alias directly from the config section
        try:
            config = dict(Config().section(stats))
            email = config.get("email", None)
            login = config.get("login", None)
        except (ConfigFileError, NoSectionError) as e:
            log.error("Error accessing config section for stats '%s': %s",
                      stats, str(e))
        # Check for aliases specified in the email string
        if aliases is not None:
            try:
                aliases = dict([
                    re.split(r"\s*:\s*", definition, maxsplit=1)
                    for definition in re.split(r"\s*;\s*", aliases.strip())])
            except ValueError as exc:
                raise ConfigError(f"Invalid alias definition: '{aliases}'") from exc
            if stats in aliases:
                if "@" in aliases[stats]:
                    email = aliases[stats]
                else:
                    login = aliases[stats]
        # Update login/email if alias detected
        if email is not None:
            self.email = email
            log.info("Using email alias '%s' for '%s'", email, stats)
            if login is None:
                login = email.split("@")[0]
        if login is not None:
            self.login = login
            log.info("Using login alias '%s' for '%s'", login, stats)


def get_token(
        config: dict,
        token_key: str = "token",
        token_file_key: str = "token_file") -> Optional[str]:
    """
    Extract the authentication token from config or token file

    Returns the contents of `config[token_key]`, or the file contents of
    `config[token_file_key]` if no `config[token]` exists. If neither
    keys exist, `None` is returned.

    Sometimes you want to be able to store a token in a file rather than
    in the your plain config file. Use this function to support a system
    wide mechanism to retrieve tokens or secrets either directly from
    the config file as plain text or from an outsourced file.

    :param config:
        A configuration dictionary.
    :param token_key:
        The dict entry to look for when the token is stored as plain
        text in the config.
    :param token_file_key:
        The dict entry to look for when the token is supposed to be read
        from file.
    :returns:
        The stripped token or `None` if no or only empty entries were
        found in the `config` dict.

    """
    token = None

    if token_key in config:
        token = str(config[token_key]).strip()
    elif token_file_key in config:
        file_path = os.path.expanduser(config[token_file_key])
        with open(file_path, encoding="utf-8") as token_file:
            token = token_file.read().strip()

    if token == "":
        token = None

    return token
