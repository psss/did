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

    def get_data(self):
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

    def get_next_page(self):
        """ Get next page in paginated activity """


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
        next_page = True
        while next_page:
            for activity in self.sentry.get_data():
                date = self.get_date(activity)
                if (date > str(self.options.until.date)):
                    continue
                if (date < str(self.options.since.date)):
                    next_page = False
                    break
                if (activity['type'] != "set_regression"):
                    stats.append(activity)
        # erase cursor, so next stats will be search from the start
        self.sentry.cursor = ''
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
                record = "{0} - {1}".format(
                    activity['issue']['shortId'], activity['issue']['title'])
                # skip if the issue is in the stats already
                if record in self.stats:
                    continue
                self.stats.append(record)


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
                record = "{0} - {1}".format(
                    activity['issue']['shortId'], activity['issue']['title'])
                # skip if the issue is in the stats already
                if record in self.stats:
                    continue
                self.stats.append(record)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Sentry Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class SentryGroupStats(StatsGroup):
    """ Sentry aggregated stats """

    # Default order
    order = 601

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
