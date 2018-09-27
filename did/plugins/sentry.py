# coding: utf-8
"""
Sentry stats such as commented, resolved issues

Configuration example::

    [sentry]
    type = sentry
    url = http://sentry.usersys.redhat.com/api/0/
    organization = baseos
    token = ...

You need to generate authentication token
at http://sentry.usersys.redhat.com/api/.
The only scope you need to check is `org:read`.
"""

from __future__ import absolute_import, unicode_literals

import json
import urllib2

from did.base import Config, ConfigError, ReportError
from did.stats import Stats, StatsGroup
from did.utils import log


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Sentry Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class SentryAPI(object):
    """ Sentry API """

    def __init__(self, config):
        """ Initialize API """
        self.token = config['token']
        self.organization = config['organization']
        self.url = config['url']

    def get_data(self):
        """ Get organization activity in JSON representation """
        url = self.url + "organizations/" + self.organization + "/activity/"
        headers = {'Authorization': 'Bearer {0}'.format(self.token)}
        request = urllib2.Request(url, None, headers)
        log.debug("Getting activity data from server.")
        try:
            response = urllib2.urlopen(request)
        except urllib2.URLError as e:
            log.error("An error encountered while getting data from server.")
            log.debug(e)
            raise ReportError("Could not get data. {0}.".format(str(e)))

        return json.load(response)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Sentry Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class SentryStats(Stats):
    """ Sentry stats """

    def __init__(self, sentry, option, name=None, parent=None):
        super(SentryStats, self).__init__(
            option=option, name=name, parent=parent)
        self.options = parent.options
        self.sentry = sentry

    def filter_data(self):
        stats = []
        log.debug("Query: Date range {0} - {1}".format(
            str(self.options.since.date), str(self.options.until.date)))
        for activity in self.sentry.get_data():
            date = self.get_date(activity)
            if (date >= str(self.options.since.date) and
                    date < str(self.options.until.date) and
                    activity['type'] != "set_regression"):
                stats.append(activity)
        return stats

    @staticmethod
    def get_date(activity):
        return activity['dateCreated'][:10]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Sentry Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class ResolvedIssues(SentryStats):
    """ Resolved Issues """

    def fetch(self):
        log.info(u"Searching for resolved issues by {0}".format(self.user))
        for activity in self.filter_data():
            if (activity['user']['email'] == self.user.email and
                    activity['type'] == 'set_resolved'):
                self.stats.append("{0} - {1}".format(
                    activity['issue']['shortId'], activity['issue']['title']))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Sentry Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CommentedIssues(SentryStats):
    """ Commented on issues """

    def fetch(self):
        log.info(u"Searching for comments on issues by {0}".format(self.user))
        for activity in self.filter_data():
            if (activity['user']['email'] == self.user.email and
                    activity['type'] == 'note'):
                self.stats.append("{0} - {1}".format(
                    activity['issue']['shortId'], activity['issue']['title']))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Sentry Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class SentryGroupStats(StatsGroup):
    """ Sentry aggregated stats """

    # Default order
    order = 650

    def __init__(self, option, name=None, parent=None, user=None):
        StatsGroup.__init__(self, option, name, parent, user)
        config = dict(Config().section(option))
        # Check Sentry url
        if "url" not in config:
            raise ConfigError(
                "No url set in the [{0}] section".format(option))
        # Check Sentry organization
        if "organization" not in config:
            raise ConfigError(
                "No organization set in the [{0}] section".format(option))
        # Check Sentry token
        if "token" not in config:
            raise ConfigError(
                "No token set in the [{0}] section".format(option))
        # Set up the Sentry API
        sentry = SentryAPI(config=config)
        # Construct the list of stats
        self.stats = [
            ResolvedIssues(sentry=sentry, option=option + '-resolved',
                           parent=self),
            CommentedIssues(sentry=sentry, option=option + '-commented',
                            parent=self),
            ]
