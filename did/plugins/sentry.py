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
from datetime import datetime

import json
import urllib2

from did.base import Config, ReportError
from did.stats import Stats, StatsGroup
from did.utils import log, pretty, split


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
        try:
            response = urllib2.urlopen(request)
        except urllib2.URLError as e:
            raise ReportError("Could not get data. API HTTP response: " + e.reason)

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

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Sentry Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class ResolvedIssues(SentryStats):
    """ Resolved Issues """

    def fetch(self):
        count = 0
        for activity in self.sentry.get_data():
            if activity['dateCreated'][:10] > str(self.options.since.date) \
            and activity['dateCreated'][:10] < str(self.options.until.date) \
            and activity['user']['email'] == self.user.email \
            and activity["type"] == 'set_resolved':
                self.stats.append("\t{0} - {1}".format(activity['issue']['shortId'], activity['issue']['title']))
                count += 1


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Sentry Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class AssignedIssues(SentryStats):
    """ Assigned issues to myself """

    def fetch(self):
        count = 0
        for activity in self.sentry.get_data():
            if activity['dateCreated'][:10] > str(self.options.since.date) \
            and activity['dateCreated'][:10] < str(self.options.until.date) \
            and activity["type"] == 'assigned' \
            and activity['data']['assigneeEmail'] == self.user.email \
            and activity['issue']['assignedTo']['email'] == self.user.email:
                self.stats.append("\t{0} - {1}".format(activity['issue']['shortId'], activity['issue']['title']))
                count += 1


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Sentry Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CommentedIssues(SentryStats):
    """ Commented on issues """

    def fetch(self):
        count = 0
        for activity in self.sentry.get_data():
            if activity['dateCreated'][:10] > str(self.options.since.date) \
            and activity['dateCreated'][:10] < str(self.options.until.date) \
            and activity['user']['email'] == self.user.email \
            and activity["type"] == 'note':
                self.stats.append("\t{0} - {1}".format(activity['issue']['shortId'], activity['issue']['title']))
                count += 1


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
            raise ReportError(
                "No url set in the [{0}] section".format(option))
        # Check Sentry organization
        if "organization" not in config:
            raise ReportError(
                "No organization set in the [{0}] section".format(option))
        # Set up the Bugzilla investigator
        sentry = SentryAPI(config=config)
        # Construct the list of stats
        self.stats = [
            AssignedIssues(sentry=sentry, option=option + '-assigned', parent=self),
            ResolvedIssues(sentry=sentry, option=option + '-resolved', parent=self),
            CommentedIssues(sentry=sentry, option=option + '-commented', parent=self),
            ]
