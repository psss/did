# coding: utf-8
""" Comfortably generate reports - Wiki """

import xmlrpclib
#from reports.utils import Config, item
from status_report.base import Stats, StatsGroup
from status_report.utils import Config, item

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


class WikiStats(StatsGroup):
    """ Wiki stats group """
    def __init__(self, option, name=None, parent=None):
        StatsGroup.__init__(self, option, name, parent)
        for wiki, url in Config().section(option):
            self.stats.append(WikiChanges(
                option=wiki, parent=self, url=url,
                name="Updates on {0}".format(wiki)))
