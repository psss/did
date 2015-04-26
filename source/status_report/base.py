#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Comfortably generate reports - Base """

from __future__ import unicode_literals, absolute_import

import optparse
import xmlrpclib

from status_report import utils
from status_report import plugins


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Stats(object):
    """ General statistics """
    _name = None
    _error = None
    _enabled = None
    option = None
    dest = None
    parent = None
    stats = None

    def __init__(
            self, option, name=None, parent=None, user=None, options=None):
        """ Set the name, indent level and initialize data.  """
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
        utils.log.debug(
            'Loading {0} Stats instance for {1}'.format(option, self.user))
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
        if self._enabled is None:
            if self.parent is not None and self.parent.enabled():
                self._enabled = True
            else:
                # Default to Enabled if not otherwise disabled
                self._enabled = getattr(self.options, self.dest, True)
        utils.log.debug(
            "{0} Enabled? {1}".format(self.option, self._enabled))
        return self._enabled

    def fetch(self):
        """ Fetch the stats (to be implemented by respective class). """
        raise NotImplementedError()

    def check(self):
        """ Check the stats if enabled. """
        # Backwards compatability; use .enabled() and .get_status()
        return self.enabled()

    def get_stats(self):
        '''
        Run the stat's fetch method to get the stats we're looking for
        '''
        if not self.enabled():
            return

        try:
            self.fetch()
        except (xmlrpclib.Fault, utils.ConfigError) as error:
            utils.log.error(error)
            self._error = True
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
        utils.item("{0}: {1}".format(self.name, count, 0), options=self.options)

    def show(self):
        """ Display indented statistics. """
        self.header()
        if self._error is not None:
            utils.log.error("Error detected: {0}".format(self._error))
        if not self.stats:
            utils.log.warn("No Stats available!")
            return
        for stat in self.stats:
            utils.item(stat, level=1, options=self.options)

    def merge(self, other):
        """ Merge another stats. """
        if not other.stats:
            utils.log.debug('Merge: stats is empty for {0}'.format(other))
            return
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
        if not (other and other.stats):
            utils.log.debug('Merge: stats is empty for {0}'.format(other))
            return
        for this, other in zip(self.stats, other.stats):
            this.merge(other)

    def fetch(self):
        '''
        default is to assume self.stats has been filled with a list of Stats
        instances that we can call fetch() on to load the stats we're
        looking for into each instance. Otherwise, overloading this method
        is necessary.
        '''
        [s.fetch() for s in self.stats]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  User Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class UserStats(StatsGroup):
    """ User statistics in one place """

    def __init__(self, user=None, options=None):
        """ Initialize stats objects. """
        super(UserStats, self).__init__(option="all", user=user,
                                        options=options)
        self.stats = []
        for section, statsgroup in plugins.detect():
            try:
                stats = statsgroup(option=section, parent=self,
                                   options=options, user=self.user)
            except Exception:
                utils.log.error("Failed to load plugin instance {0}".format(
                                statsgroup))
                raise
            else:
                if stats:
                    self.stats.append(stats)

    def add_option(self, parser):
        """ Add options for each stats group. """
        for stat in self.stats:
            stat.add_option(parser)

    def get_stats(self):
        """
        Explitly fetch stats for each stat instance in self.stats. Replace
        self.stats with the result of those calls, which should be a list
        of stat (snippet) strings.
        """
        stats = []
        # FIXME: DON"T RUN THIS MORE THAN ONCE! set _dirty? or something
        # to indicate .stats no longer contains Stat classes but actual stats
        for stat in self.stats:
            stat.get_stats()
            stats.extend(stat.stats)
        self.stats = stats


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Header & Footer
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class EmptyStats(Stats):
    """ Custom stats group for header & footer """
    def __init__(self, option, name=None, parent=None):
        Stats.__init__(self, option, name, parent)

    def show(self):
        """ Name only for empty stats """
        utils.item(self.name, options=self.options)

    def fetch(self):
        """ Nothing to do for empty stats """
        pass


class EmptyStatsGroup(StatsGroup):
    """ Header & Footer stats group """
    def __init__(self, option, name=None, parent=None):
        StatsGroup.__init__(self, option, name, parent=parent)
        for opt, name in sorted(utils.Config().section(option)):
            self.stats.append(EmptyStats(opt, name, parent=self))
