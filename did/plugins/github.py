# coding: utf-8
"""
GitHub stats such as created and closed issues

Config example::

    [github]
    type = github
    url = https://api.github.com/
    token = <authentication-token>

The authentication token is optional. However, unauthenticated
queries are limited. For more details see `GitHub API`__ docs.

__ https://developer.github.com/guides/getting-started/#authentication
"""

import re
import json
import urllib2

import did.base
from did.utils import log, pretty, listed
from did.stats import Stats, StatsGroup

# Identifier padding
PADDING = 3


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GitHub(object):
    """ GitHub Investigator """

    def __init__(self, url, token):
        """ Initialize url and headers """
        self.url = url.rstrip("/")
        if token is not None:
            self.headers = {'Authorization': 'token {0}'.format(token)}
        else:
            self.headers = {}

        self.token = token

    def search(self, query):
        """ Perform GitHub query """
        url = self.url + "/" + query
        log.debug("GitHub query: {0}".format(url))
        try:
            request = urllib2.Request(url, headers=self.headers)
            response = urllib2.urlopen(request)
            log.debug("Response headers:\n{0}".format(
                unicode(response.info()).strip()))
        except urllib2.URLError as error:
            log.debug(error)
            raise did.base.ReportError(
                "GitHub search on {0} failed.".format(self.url))
        result = json.loads(response.read())["items"]
        log.debug("Result: {0} fetched".format(listed(len(result), "item")))
        log.data(pretty(result))
        return result


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Issue
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Issue(object):
    """ GitHub Issue """
    def __init__(self, data):
        self.data = data
        self.title = data["title"]
        matched = re.search(
            r"/repos/([^/]+)/([^/]+)/issues/(\d+)", data["url"])
        self.owner = matched.groups()[0]
        self.project = matched.groups()[1]
        self.id = matched.groups()[2]

    def __unicode__(self):
        """ String representation """
        return "{0}/{1}#{2} - {3}".format(
            self.owner, self.project,
            unicode(self.id).zfill(PADDING), self.data["title"])


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class IssuesCreated(Stats):
    """ Issues created """
    def fetch(self):
        log.info(u"Searching for issues created by {0}".format(self.user))
        query = "search/issues?q=author:{0}+created:{1}..{2}".format(
            self.user.login, self.options.since, self.options.until)
        self.stats = [
            Issue(issue) for issue in self.parent.github.search(query)]


class IssuesClosed(Stats):
    """ Issues closed """
    def fetch(self):
        log.info(u"Searching for issues closed by {0}".format(self.user))
        query = "search/issues?q=assignee:{0}+closed:{1}..{2}".format(
            self.user.login, self.options.since, self.options.until)
        self.stats = [
            Issue(issue) for issue in self.parent.github.search(query)]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GitHubStats(StatsGroup):
    """ GitHub work """

    # Default order
    order = 330

    def __init__(self, option, name=None, parent=None, user=None):
        super(GitHubStats, self).__init__(option, name, parent, user)
        config = dict(self.config.section(option))
        # Check server url
        try:
            self.url = config["url"]
        except KeyError:
            raise did.base.ReportError(
                "No github url set in the [{0}] section".format(option))
        # Check authorization token
        try:
            self.token = config["token"]
        except KeyError:
            self.token = None
        self.github = GitHub(self.url, self.token)
        # Create the list of stats
        self.stats = [
            IssuesCreated(
                option=option + "-created", parent=self,
                name="Issues created on {0}".format(option)),
            IssuesClosed(
                option=option + "-closed", parent=self,
                name="Issues closed on {0}".format(option)),
            ]
