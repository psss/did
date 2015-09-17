# coding: utf-8

""" Config, Date, User and Exceptions """

from __future__ import unicode_literals, absolute_import

import os
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

class ConfigError(Exception):
    """ General problem with configuration file """
    pass


class OptionError(Exception):
    """ General problem with configuration file """
    pass


class ReportError(Exception):
    """ General problem with report generation """
    pass


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
        can be overrided by the DID_CONFIG environment variable.
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
            log.info("Inspecting config file '{0}'".format(path))
            self.parser.readfp(codecs.open(path, "r", "utf8"))
        except IOError as error:
            log.debug(error)
            raise ConfigError(
                "Unable to read the config file {0}".format(path))

    @property
    def email(self):
        """ User email(s) """
        try:
            return self.parser.get("general", "email")
        except (NoOptionError, NoSectionError) as error:
            log.debug(error)
            return []

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

    @staticmethod
    def path():
        """ Detect config file path """
        try:
            directory = os.environ["DID_CONFIG"]
        except KeyError:
            directory = CONFIG
        return directory.rstrip("/") + "/config"

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
    """ User info """

    def __init__(self, email, name=None, login=None):
        """ Set user email, name and login values. """
        if not email:
            raise ReportError("Email required for user initialization.")
        else:
            # Extract everything from the email string provided
            # eg, "My Name" <bla@email.com>
            parts = utils.EMAIL_REGEXP.search(email)
            if parts is None:
                raise ConfigError("Invalid email address '{0}'".format(email))
            self.email = parts.groups()[1]
            self.login = login or self.email.split('@')[0]
            self.name = name or parts.groups()[0] or u"Unknown"

    def __unicode__(self):
        """ Use name & email for string representation. """
        return u"{0} <{1}>".format(self.name, self.email)
