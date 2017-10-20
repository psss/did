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
        self.cursor = ''

    def get_page(self):
        """ Get organization activity in JSON representation """
        url = (self.url + "organizations/" + self.organization
                + "/activity/" + self.cursor)
        headers = {'Authorization': 'Bearer {0}'.format(self.token)}
        request = urllib2.Request(url, None, headers)
        log.debug("Getting activity data from server.")
        try:
            response = urllib2.urlopen(request)
        except urllib2.URLError as e:
            log.error("An error encountered while getting data from server.")
            log.debug(e)
            raise ReportError("Could not get data. {0}.".format(str(e)))

        # get another page when paginating
        link_header = response.info().getheader('Link').split(', ')
        # will ALWAYS return prev and next in response
        # if there is content on next page then results is set to true
        if link_header[1].find('results="true"') > 0:
            # set cursor for next page
            self.cursor = '?&cursor=' + link_header[1].split('; ')[-1][8:-1]
        else:
            self.cursor = ''
        return json.load(response)

    def get_data(self, since, until):
        next_page = True
        data = []
        while next_page:
            for activity in self.get_page():
                # log.debug("Actvity: {0}".format(activity))
                date = self.get_date(activity)
                if (date > until):
                    continue
                if (date < since):
                    next_page = False
                    break
                if (activity['type'] != "set_regression"):
                    data.append(activity)
        # erase cursor, so next stats will search from the start
        self.cursor = ''
        return data

    @staticmethod
    def get_date(activity):
        return activity['dateCreated'][:10]


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

    def filter_data(self, kind=['set_resolved', 'note']):
        stats = []
        log.debug("Query: Date range {0} - {1}".format(
            str(self.options.since.date), str(self.options.until.date)))
        for activity in self.issues:
            if activity['type'] == kind:
                stats.append(activity)
        return stats

    def append(self, record):
        """ Append only if unique """

        if record not in self.stats:
            self.stats.append(record)

    @property
    def issues(self):
        """ All issues in sentry under group """

        return self.sentry.get_data(str(self.options.since.date),
            str(self.options.until.date))

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Sentry Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class ResolvedIssues(SentryStats):
    """ Resolved Issues """

    def fetch(self):
        log.info(u"Searching for resolved issues by {0}".format(self.user))
        for activity in self.filter_data('set_resolved'):
            if activity['user']['email'] == self.user.email:
                record = "{0} - {1}".format(
                    activity['issue']['shortId'], activity['issue']['title'])
                self.append(record)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Sentry Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CommentedIssues(SentryStats):
    """ Commented on issues """

    def fetch(self):
        log.info(u"Searching for comments on issues by {0}".format(self.user))
        for activity in self.filter_data('note'):
            if activity['user']['email'] == self.user.email:
                record = "{0} - {1}".format(
                    activity['issue']['shortId'], activity['issue']['title'])
                self.append(record)


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
