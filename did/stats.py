# coding: utf-8

""" Stats & StatsGroup, the core of the data gathering """

from __future__ import unicode_literals, absolute_import

import xmlrpclib

import did.base
from did import utils
from did.utils import log


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Stats(object):
    """ General statistics """
    _name = None
    _error = None
    _enabled = None
    config = None
    dest = None
    option = None
    parent = None
    stats = None
    user = None

    def __init__(
            self, option, name=None, parent=None, user=None, options=None):
        """ Set the name, indent level and initialize data.  """
        self.config = did.base.get_config()
        self.option = option.replace(" ", "-")
        self.dest = self.option.replace("-", "_")
        self._name = name
        self.parent = parent
        self.stats = []
        # Save user and options (get it directly or from parent)
        self.options = options or getattr(self.parent, 'options', None)
        if user is None and self.parent is not None:
            self.user = self.parent.user
        else:
            self.user = user
        log.debug(
            'Loading {0} Stats instance for {1}'.format(option, self.user))

    @property
    def name(self):
        """ Use the first line of docs string unless name set. """
        if self._name:
            return self._name
        return [
            line.strip() for line in self.__doc__.split("\n")
            if line.strip()][0]

    def add_option(self, group):
        """ Add option for self to the parser group object. """
        group.add_argument(
            "--{0}".format(self.option), action="store_true", help=self.name)

    def enabled(self):
        """ Check whether we're enabled (or if parent is). """
        # Cache into ._enabled
        if self._enabled is None:
            if self.parent is not None and self.parent.enabled():
                self._enabled = True
            else:
                # Default to Enabled if not otherwise disabled
                self._enabled = getattr(self.options, self.dest, True)
        return self._enabled

    def fetch(self):
        """ Fetch the stats (to be implemented by respective class). """
        raise NotImplementedError()

    def check(self):
        """ Check the stats if enabled. """
        if not self.enabled():
            return
        try:
            self.fetch()
        # FIXME: This exception is checked even though .fetch() isn't
        # always going to use xmlrpc... or return xmlrpclib.Fault anyway
        # Catch exceptions in the subclass, not here at this level?
        except (xmlrpclib.Fault, did.base.ConfigError) as error:
            log.error(error)
            self._error = True
            # FIXME: This already happens at the bin/did mail level
            # Raise the exception if debugging
            if not self.options or self.options.debug:
                raise
        # Show the results stats (unless merging)
        if self.options and not self.options.merge:
            self.show()

    def header(self):
        """ Show summary header. """
        # Show question mark instead of count when errors encountered
        count = "? (error encountered)" if self._error else len(self.stats)
        utils.item("{0}: {1}".format(self.name, count), options=self.options)

    def show(self):
        """ Display indented statistics. """
        if not self._error and not self.stats:
            return
        self.header()
        for stat in self.stats:
            utils.item(stat, level=1, options=self.options)

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

        group = parser.add_argument_group(self.name)
        for stat in self.stats:
            stat.add_option(group)

        group.add_argument(
            "--{0}".format(self.option), action="store_true", help="All above")

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
        """ Stats groups do not fetch anything """
        pass


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  User Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class UserStats(StatsGroup):
    """ User statistics in one place """

    def __init__(self, user=None, options=None):
        """ Initialize stats objects. """
        super(UserStats, self).__init__(
            option="all", user=user, options=options)

        # FIXME
        # DOESN"T THIS OVERWRITE self.stats set in parent class Stats.__init__?
        self.stats = []

        # import here to avoid recursive imports at startup
        import did.plugins

        # Missing config file is NOT OK if building options (--help).
        # since we want to get --help for all available plugins and
        # if we hit an exception because of missing config then
        # we don't load the plugin and it's not going to add its
        # args to argparser
        for section, statsgroup in did.plugins.detect():
            self.stats.append(statsgroup(
                option=section, parent=self,
                user=self.user.clone(section) if self.user else None))

    def add_option(self, parser):
        """ Add options for each stats group. """
        for stat in self.stats:
            stat.add_option(parser)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Header & Footer
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class EmptyStats(Stats):
    """ Custom stats group for header & footer """
    def show(self):
        """ Name only for empty stats """
        utils.item(self.name, options=self.options)

    def fetch(self):
        """ Nothing to do for empty stats """
        pass


class EmptyStatsGroup(StatsGroup):
    """ Header & Footer stats group """
    def __init__(self, option, name=None, parent=None, user=None):
        super(EmptyStatsGroup, self).__init__(option, name, parent, user)
        _config = did.base.get_config()
        for opt, name in sorted(_config.section(option)):
            self.stats.append(
                EmptyStats(option + "-" + opt, name, parent=self))
