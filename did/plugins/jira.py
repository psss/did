# coding: utf-8
"""
Jira stats such as created, updated or resolved issues

Configuration example (GSS authentication)::

    [jboss]
    type = jira
    prefix = JIRA
    project = ORG
    url = https://issues.jboss.org/

Configuration example (basic authentication)::

    [jboss]
    type = jira
    prefix = JIRA
    project = ORG
    url = https://issues.jboss.org/
    auth_url = https://issues.jboss.org/rest/auth/latest/session
    auth_type = basic
    auth_username = username
    auth_password = password

Notes:

* ``auth_url`` parameter is optional. If not provided,
  ``url + "/step-auth-gss"`` will be used for authentication.
* ``auth_type`` parameter is optional, default value is 'gss'.
* ``auth_username`` and ``auth_password`` are only valid for
  basic authentication.
"""

from __future__ import absolute_import, unicode_literals

import re
import json
import urllib
import urllib2
import cookielib
import dateutil.parser
import urllib2_kerberos

import did.base
from did.utils import log, pretty, listed
from did.stats import Stats, StatsGroup

# Default identifier width
DEFAULT_WIDTH = 4

# Maximum number of results fetched at once
MAX_RESULTS = 1000

# Maximum number of batches
MAX_BATCHES = 100

# Supported authentication types
AUTH_TYPES = ["gss", "basic"]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Issue Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Issue(object):
    """ Jira issue investigator """

    def __init__(self, issue=None, prefix=None):
        """ Initialize issue """
        if issue is None:
            return
        self.issue = issue
        self.key = issue["key"]
        self.summary = issue["fields"]["summary"]
        self.comments = issue["fields"]["comment"]["comments"]
        matched = re.match(r"(\w+)-(\d+)", self.key)
        self.identifier = matched.groups()[1]
        if prefix is not None:
            self.prefix = prefix
        else:
            self.prefix = matched.groups()[0]

    def __unicode__(self):
        """ Jira key and summary for displaying """
        return "{0}-{1} - {2}".format(
            self.prefix, self.identifier.zfill(DEFAULT_WIDTH), self.summary)

    @staticmethod
    def search(query, stats):
        """ Perform issue search for given stats instance """
        log.debug("Search query: {0}".format(query))
        issues = []
        # Fetch data from the server in batches of MAX_RESULTS issues
        for batch in range(MAX_BATCHES):
            result = stats.parent.session.open(
                "{0}/rest/api/latest/search?{1}".format(
                    stats.parent.url, urllib.urlencode({
                        "jql": query,
                        "fields": "summary,comment",
                        "maxResults": MAX_RESULTS,
                        "startAt": batch * MAX_RESULTS})))
            data = json.loads(result.read())
            log.debug("Batch {0} result: {1} fetched".format(
                batch, listed(data["issues"], "issue")))
            log.data(pretty(data))
            issues.extend(data["issues"])
            # If all issues fetched, we're done
            if len(issues) >= data["total"]:
                break
        # Return the list of issue objects
        return [Issue(issue, prefix=stats.parent.prefix) for issue in issues]

    def updated(self, user, options):
        """ True if the issue was commented by given user """
        for comment in self.comments:
            created = dateutil.parser.parse(comment["created"]).date()
            if (comment["author"]["name"] == user.login and
                    created >= options.since.date and
                    created < options.until.date):
                return True
        return False


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class JiraCreated(Stats):
    """ Created issues """
    def fetch(self):
        log.info("Searching for issues created in {0} by {1}".format(
            self.parent.project, self.user))
        query = (
            "project = '{0}' AND creator = '{1}' AND "
            "created >= {2} AND created <= {3}".format(
                self.parent.project, self.user.login,
                self.options.since, self.options.until))
        self.stats = Issue.search(query, stats=self)


class JiraUpdated(Stats):
    """ Updated issues """
    def fetch(self):
        log.info("Searching for issues updated in {0} by {1}".format(
            self.parent.project, self.user))
        query = (
            "project = '{0}' AND "
            "updated >= {1} AND created <= {2}".format(
                self.parent.project,
                self.options.since, self.options.until))
        # Filter only issues commented by given user
        self.stats = [
            issue for issue in Issue.search(query, stats=self)
            if issue.updated(self.user, self.options)]


class JiraResolved(Stats):
    """ Resolved issues """
    def fetch(self):
        log.info("Searching for issues resolved in {0} by {1}".format(
            self.parent.project, self.user))
        query = (
            "project = '{0}' AND assignee = '{1}' AND "
            "resolved >= {2} AND resolved <= {3}".format(
                self.parent.project, self.user.login,
                self.options.since, self.options.until))
        self.stats = Issue.search(query, stats=self)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class JiraStats(StatsGroup):
    """ Jira stats """

    # Default order
    order = 600

    def __init__(self, option, name=None, parent=None, user=None):
        super(JiraStats, self).__init__(option, name, parent, user)
        self._session = None
        # Make sure there is an url provided
        config = dict(self.config.section(option))
        if "url" not in config:
            raise did.base.ReportError(
                "No Jira url set in the [{0}] section".format(option))
        self.url = config["url"].rstrip("/")
        # Optional authentication url
        if "auth_url" in config:
            self.auth_url = config["auth_url"]
        else:
            self.auth_url = self.url + "/step-auth-gss"
        # Authentication type
        if "auth_type" in config:
            if config["auth_type"] not in AUTH_TYPES:
                raise did.base.ReportError(
                    "Unsupported authentication type: {0}"
                    .format(config["auth_type"]))
            self.auth_type = config["auth_type"]
        else:
            self.auth_type = "gss"
        # Authentication credentials
        if self.auth_type == "basic":
            if "auth_username" not in config:
                raise did.base.ReportError(
                    "`auth_username` not set in the [{0}] section"
                    .format(option))
            self.auth_username = config["auth_username"]
            if "auth_password" not in config:
                raise did.base.ReportError(
                    "`auth_password` not set in the [{0}] section"
                    .format(option))
            self.auth_password = config["auth_password"]
        else:
            if "auth_username" in config:
                raise did.base.ReportError(
                    "`auth_username` is only valid for basic authentication"
                    + " (section [{0}])".format(option))
            if "auth_password" in config:
                raise did.base.ReportError(
                    "`auth_password` is only valid for basic authentication"
                    + " (section [{0}])".format(option))
        # Make sure we have project set
        if "project" not in config:
            raise did.base.ReportError(
                "No project set in the [{0}] section".format(option))
        self.project = config["project"]
        # Check for custom prefix
        self.prefix = config["prefix"] if "prefix" in config else None
        # Create the list of stats
        self.stats = [
            JiraCreated(
                option=option + "-created", parent=self,
                name="Issues created in {0}".format(option)),
            JiraUpdated(
                option=option + "-updated", parent=self,
                name="Issues updated in {0}".format(option)),
            JiraResolved(
                option=option + "-resolved", parent=self,
                name="Issues resolved in {0}".format(option)),
        ]

    @property
    def session(self):
        """ Initialize the session """
        if self._session is None:
            # http://stackoverflow.com/questions/8811269/
            # http://www.techchorus.net/using-cookie-jar-urllib2
            cookie = cookielib.CookieJar()
            self._session = urllib2.build_opener(
                urllib2.HTTPSHandler(debuglevel=0),
                urllib2.HTTPRedirectHandler,
                urllib2.HTTPCookieProcessor(cookie),
                urllib2_kerberos.HTTPKerberosAuthHandler)

            log.debug("Connecting to {0}".format(self.auth_url))
            if self.auth_type == 'basic':
                req = urllib2.Request(self.auth_url)
                req.add_data(
                    '{ "username" : "%s", "password" : "%s" }' % (
                        self.auth_username, self.auth_password))
                req.add_header("Content-type", "application/json")
                req.add_header("Accept", "application/json")
                self._session.open(req)
            else:
                self._session.open(self.auth_url)
        return self._session
