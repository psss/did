# coding: utf-8
"""
Sentry stats such as commented, resolved issues

Configuration example::

    [sentry]
    type = sentry
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

URL = "http://sentry.usersys.redhat.com/api/0/organizations/"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Sentry Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class SentryAPI(object):
    """ Sentry API """

    def __init__(self, stats, config):
        """ Initialize API """
        self.stats = stats
        self.token = config['token']
        self.organization = config['organization']
        
    def get_data(self):
        """ Get organization activity in JSON representation """
        url = URL + self.organization + "/activity/"
        headers = {'Authorization': 'Bearer {0}'.format(self.token)}
        request = urllib2.Request(url, None, headers)
        try:
            response = urllib2.urlopen(request)
        except urllib2.URLError as e:
            raise ReportError(e.reason)

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
        status = ""
        count = 0
        for activity in self.sentry.get_data():
            if activity['dateCreated'][:10] > str(self.options.since.date) \
            and activity['dateCreated'][:10] < str(self.options.until.date) \
            and activity['user']['email'] == self.user.email \
            and activity["type"] == 'set_resolved':
                status += "\t{0} - {1}\n".format(activity['issue']['shortId'], activity['issue']['title'])
                count += 1
        self.stats.append(status)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Sentry Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class AssignedIssues(SentryStats):
    """ Assigned issues """

    def fetch(self):
        status = ""
        count = 0
        for activity in self.sentry.get_data():
            if activity['dateCreated'][:10] > str(self.options.since.date) \
            and activity['dateCreated'][:10] < str(self.options.until.date) \
            and activity['user']['email'] == self.user.email \
            and activity["type"] == 'assigned' \
            and activity['data']['assigneeEmail'] == self.user.email:
                status += "\t{0} - {1}\n".format(activity['issue']['shortId'], activity['issue']['title'])
                count += 1
        self.stats.append(status)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Sentry Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CommentedIssues(SentryStats):
    """ Comments on issues """

    def fetch(self):
        status = ""
        count = 0
        for activity in self.sentry.get_data():
            if activity['dateCreated'][:10] > str(self.options.since.date) \
            and activity['dateCreated'][:10] < str(self.options.until.date) \
            and activity['user']['email'] == self.user.email \
            and activity["type"] == 'note':
                status += "\t{0} - {1}\n".format(activity['issue']['shortId'], activity['issue']['title'])
                count += 1
        self.stats.append(status)


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
        # Check Sentry rganization
        try:
            self.organization = config["organization"]
        except KeyError:
            raise ReportError(
                "No organization set in the [{0}] section".format(option))
        # Set up the Bugzilla investigator
        sentry = SentryAPI(stats=self, config=config)
        # Construct the list of stats
        self.stats = [
            AssignedIssues(sentry=sentry, option=option + '-assigned', parent=self),
            ResolvedIssues(sentry=sentry, option=option + '-resolved', parent=self),
            CommentedIssues(sentry=sentry, option=option + '-commented', parent=self),
            ]
