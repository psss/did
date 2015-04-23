# coding: utf-8
""" Comfortably generate reports - Base """

from __future__ import absolute_import

import datetime
import optparse
import xmlrpclib
from dateutil.relativedelta import MO as MONDAY
from dateutil.relativedelta import relativedelta as delta

import status_report.utils as utils
from status_report.utils import log, item

TODAY = datetime.date.today()

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
            self.date = datetime.date(*[int(i) for i in date.split("-")])
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

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  User
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class User(object):
    """ User info """

    def __init__(self, email, name=None, login=None):
        """ Set user email, name and login values. """
        if not email:
            raise utils.ReportError(
                "Email required for user initialization.")
        else:
            # extract everything from the email string provided
            # eg, "My Name" <bla@email.com>
            parts = utils.EMAIL_REGEXP.search(email)
            self.email = parts.groups()[1]
            self.login = login or self.email.split('@')[0]
            self.name = name or parts.groups()[0] or u"Unknown"

    def __unicode__(self):
        """ Use name & email for string representation. """
        return u"{0} <{1}>".format(self.name, self.email)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Stats(object):
    """ General statistics """

    def __init__(
            self, option, name=None, parent=None, user=None, options=None):
        """ Set the name, indent level and initialize data.  """
        self.option = option.replace(" ", "-")
        self.dest = self.option.replace("-", "_")
        self._name = name
        self.parent = parent
        self.stats = []
        # Save user and options (get it directly or from parent)
        self.options = options
        if self.options is None and self.parent is not None:
            self.options = self.parent.options
        self.user = user
        if self.user is None and self.parent is not None:
            self.user = self.parent.user
        # True if error encountered when generating stats
        self._error = False
        # If user provided, let's check the data right now
        if self.user is not None:
            self.check()

    @property
    def name(self):
        """ Use docs string unless name set. """
        return self._name or self.__doc__.strip()

    def add_option(self, group):
        """ Add option for self to the parser group object. """
        group.add_option(
            "--{0}".format(self.option), action="store_true", help=self.name)

    def enabled(self):
        """ Check whether we're enabled (or if parent is). """
        if self.parent is not None and self.parent.enabled():
            return True
        return getattr(self.options, self.dest)

    def fetch(self):
        """ Fetch the stats (to be implemented by respective class). """
        raise NotImplementedError()

    def check(self):
        """ Check the stats if enabled. """
        if self.enabled():
            try:
                self.fetch()
            except (xmlrpclib.Fault, utils.ConfigError) as error:
                log.error(error)
                self._error = True
                # Raise the exception if debugging
                if self.options.debug:
                    raise
            # Show the results stats (unless merging)
            if not self.options.merge:
                self.show()

    def header(self):
        """ Show summary header. """
        # Show question mark instead of count when errors encountered
        count = "? (error encountered)" if self._error else len(self.stats)
        item("{0}: {1}".format(self.name, count, 0), options=self.options)

    def show(self):
        """ Display indented statistics. """
        if not self._error and not self.stats:
            return
        self.header()
        for stat in self.stats:
            item(stat, level=1, options=self.options)

    def merge(self, other):
        """ Merge another stats. """
        self.stats.extend(other.stats)
        if other._error:
            self._error = True

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class StatsGroup(Stats):
    """ Stats group """

    # Default order
    order = 500

    def add_option(self, parser):
        """ Add option group and all children options. """

        group = optparse.OptionGroup(parser, self.name)
        for stat in self.stats:
            stat.add_option(group)
        group.add_option(
            "--{0}".format(self.option), action="store_true", help="All above")
        parser.add_option_group(group)

    def check(self):
        """ Check all children stats. """
        for stat in self.stats:
            stat.check()

    def show(self):
        """ List all children stats. """
        for stat in self.stats:
            stat.show()

    def merge(self, other):
        """ Merge all children stats. """
        for this, other in zip(self.stats, other.stats):
            this.merge(other)

    def fetch(self):
        """ Stats group do not fetch anything """
        pass

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Header & Footer
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class EmptyStats(Stats):
    """ Custom stats group for header & footer """
    def __init__(self, option, name=None, parent=None):
        Stats.__init__(self, option, name, parent)

    def show(self):
        """ Name only for empty stats """
        item(self.name, options=self.options)

    def fetch(self):
        """ Nothing to do for empty stats """
        pass


class EmptyStatsGroup(StatsGroup):
    """ Header & Footer stats group """
    def __init__(self, option, name=None, parent=None):
        StatsGroup.__init__(self, option, name, parent=parent)
        for opt, name in sorted(utils.Config().section(option)):
            self.stats.append(EmptyStats(opt, name, parent=self))
