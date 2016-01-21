# coding: utf-8

""" Config, Date, User and Exceptions """

from __future__ import unicode_literals, absolute_import

import os
import re
import sys
import codecs
import datetime
import optparse
import StringIO
import xmlrpclib
import ConfigParser
from dateutil.relativedelta import MO as MONDAY
from ConfigParser import NoOptionError, NoSectionError
from dateutil.relativedelta import relativedelta as delta

from did import utils
from did.utils import log


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Config file location
CONFIG = os.path.expanduser("~/.did")

# Default maximum width
MAX_WIDTH = 79

# Today's date
TODAY = datetime.date.today()


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
#  Config
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Config(object):
    """ User config file """

    parser = None

    def __init__(self, config=None, path=None):
        """
        Read the config file

        Parse config from given string (config) or file (path).
        If no config or path given, default to "~/.did/config" which
        can be overrided by the ``DID_DIR`` environment variable.
        """
        # Read the config only once (unless explicitly provided)
        if self.parser is not None and config is None and path is None:
            return
        Config.parser = ConfigParser.SafeConfigParser()
        # If config provided as string, parse it directly
        if config is not None:
            log.info("Inspecting config file from string")
            log.debug(utils.pretty(config))
            self.parser.readfp(StringIO.StringIO(config))
            return
        # Check the environment for config file override
        # (unless path is explicitly provided)
        if path is None:
            path = Config.path()
        # Parse the config from file
        try:
            log.info("Inspecting config file '{0}'.".format(path))
            self.parser.readfp(codecs.open(path, "r", "utf8"))
        except IOError as error:
            log.debug(error)
            Config.parser = None
            raise ConfigFileError(
                "Unable to read the config file '{0}'.".format(path))

    @property
    def email(self):
        """ User email(s) """
        try:
            return self.parser.get("general", "email")
        except NoSectionError as error:
            log.debug(error)
            raise ConfigFileError(
                "No general section found in the config file.")
        except NoOptionError as error:
            log.debug(error)
            raise ConfigFileError(
                "No email address defined in the config file.")

    @property
    def width(self):
        """ Maximum width of the report """
        try:
            return int(self.parser.get("general", "width"))
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
        matched = re.search("--confi?g?[ =](\S+)", " ".join(sys.argv))
        if matched:
            filename = matched.groups()[0]
        return directory.rstrip("/") + "/" + filename

    @staticmethod
    def example():
        """ Return config example """
        return "[general]\nemail = Name Surname <email@example.org>\n"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Date
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Date(object):
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
            except StandardError as error:
                log.debug(error)
                raise OptionError(
                    "Invalid date format: '{0}', use YYYY-MM-DD.".format(date))
        self.datetime = datetime.datetime(
            self.date.year, self.date.month, self.date.day, 0, 0, 0)

    def __str__(self):
        """ Ascii version of the string representation """
        return utils.ascii(unicode(self))

    def __unicode__(self):
        """ String format for printing """
        return unicode(self.date)

    @staticmethod
    def this_week():
        """ Return start and end date of the current week. """
        since = TODAY + delta(weekday=MONDAY(-1))
        until = since + delta(weeks=1)
        return Date(since), Date(until)

    @staticmethod
    def last_week():
        """ Return start and end date of the last week. """
        since = TODAY + delta(weekday=MONDAY(-2))
        until = since + delta(weeks=1)
        return Date(since), Date(until)

    @staticmethod
    def this_month():
        """ Return start and end date of this month. """
        since = TODAY + delta(day=1)
        until = since + delta(months=1)
        return Date(since), Date(until)

    @staticmethod
    def last_month():
        """ Return start and end date of this month. """
        since = TODAY + delta(day=1, months=-1)
        until = since + delta(months=1)
        return Date(since), Date(until)

    @staticmethod
    def this_quarter():
        """ Return start and end date of this quarter. """
        since = TODAY + delta(day=1)
        while since.month % 3 != 0:
            since -= delta(months=1)
        until = since + delta(months=3)
        return Date(since), Date(until)

    @staticmethod
    def last_quarter():
        """ Return start and end date of this quarter. """
        since, until = Date.this_quarter()
        since = since.date - delta(months=3)
        until = until.date - delta(months=3)
        return Date(since), Date(until)

    @staticmethod
    def this_year():
        """ Return start and end date of this fiscal year """
        since = TODAY
        while since.month != 3 or since.day != 1:
            since -= delta(days=1)
        until = since + delta(years=1)
        return Date(since), Date(until)

    @staticmethod
    def last_year():
        """ Return start and end date of the last fiscal year """
        since, until = Date.this_year()
        since = since.date - delta(years=1)
        until = until.date - delta(years=1)
        return Date(since), Date(until)

    @staticmethod
    def period(argument):
        """ Detect desired time period for the argument """
        since, until, period = None, None, None
        if "today" in argument:
            since = Date("today")
            until = Date("today")
            until.date += delta(days=1)
            period = "today"
        elif "yesterday" in argument:
            since = Date("yesterday")
            until = Date("yesterday")
            until.date += delta(days=1)
            period = "yesterday"
        elif "year" in argument:
            if "last" in argument:
                since, until = Date.last_year()
                period = "the last fiscal year"
            else:
                since, until = Date.this_year()
                period = "this fiscal year"
        elif "quarter" in argument:
            if "last" in argument:
                since, until = Date.last_quarter()
                period = "the last quarter"
            else:
                since, until = Date.this_quarter()
                period = "this quarter"
        elif "month" in argument:
            if "last" in argument:
                since, until = Date.last_month()
                period = "the last month"
            else:
                since, until = Date.this_month()
                period = "this month"
        else:
            if "last" in argument:
                since, until = Date.last_week()
                period = "the last week"
            else:
                since, until = Date.this_week()
                period = "this week"
        return since, until, period


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  User
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class User(object):
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
        # Make sure we received the email string, save the original for cloning
        if not email:
            raise ConfigError("Email required for user initialization.")
        self._original = email.strip()
        # Separate aliases if provided
        try:
            email, aliases = re.split(r"\s*;\s*", self._original, 1)
        except ValueError:
            email = self._original
            aliases = None
        # Extract everything from the email string provided
        parts = utils.EMAIL_REGEXP.search(email)
        if parts is None:
            raise ConfigError("Invalid email address '{0}'".format(email))
        self.name = parts.groups()[0]
        self.email = parts.groups()[1]
        self.login = self.email.split('@')[0]
        # Check for possible aliases
        self.alias(aliases, stats)

    def __unicode__(self):
        """ Use name & email for string representation. """
        if not self.name:
            return self.email
        return "{0} <{1}>".format(self.name, self.email)

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
            try:
                email = config["email"]
            except KeyError:
                pass
            try:
                login = config["login"]
            except KeyError:
                pass
        except (ConfigFileError, NoSectionError):
            pass
        # Check for aliases specified in the email string
        if aliases is not None:
            try:
                aliases = dict([
                    re.split(r"\s*:\s*", definition, 1)
                    for definition in re.split(r"\s*;\s*", aliases.strip())])
            except ValueError:
                raise ConfigError(
                    "Invalid alias definition: '{0}'".format(aliases))
            if stats in aliases:
                if "@" in aliases[stats]:
                    email = aliases[stats]
                else:
                    login = aliases[stats]
        # Update login/email if alias detected
        if email is not None:
            self.email = email
            log.info("Using email alias '{0}' for '{1}'".format(email, stats))
            if login is None:
                login = email.split("@")[0]
        if login is not None:
            self.login = login
            log.info("Using login alias '{0}' for '{1}'".format(login, stats))
