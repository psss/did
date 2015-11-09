# coding: utf-8
"""
MoinMoin wiki stats about updated pages

Config example::

    [wiki]
    type = wiki
    wiki test = http://moinmo.in/
"""

import xmlrpclib

from did.utils import item
from did.stats import Stats, StatsGroup


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Wiki Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class WikiChanges(Stats):
    """ Wiki changes """
    def __init__(self, option, name=None, parent=None, url=None):
        self.url = url
        self.changes = 0
        self.proxy = xmlrpclib.ServerProxy("{0}?action=xmlrpc2".format(url))
        Stats.__init__(self, option, name, parent)

    def fetch(self):
        for change in self.proxy.getRecentChanges(
                self.options.since.datetime):
            if (change["author"] == self.user.login
                    and change["lastModified"] < self.options.until.date):
                self.changes += 1
                url = self.url + change["name"]
                if url not in self.stats:
                    self.stats.append(url)
        self.stats.sort()

    def header(self):
        """ Show summary header. """
        # Different header for wiki: Updates on xxx: x changes of y pages
        item(
            "{0}: {1} change{2} of {3} page{4}".format(
                self.name, self.changes, "" if self.changes == 1 else "s",
                len(self.stats), "" if len(self.stats) == 1 else "s"),
            level=0, options=self.options)

    def merge(self, other):
        """ Merge another stats. """
        Stats.merge(self, other)
        self.changes += other.changes


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class WikiStats(StatsGroup):
    """ Wiki stats """

    # Default order
    order = 700

    def __init__(self, option, name=None, parent=None, user=None):
        super(WikiStats, self).__init__(option, name, parent, user)
        for wiki, url in self.config.section(option):
            self.stats.append(WikiChanges(
                option=wiki, parent=self, url=url,
                name="Updates on {0}".format(wiki)))
