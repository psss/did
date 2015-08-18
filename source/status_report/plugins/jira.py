# coding: utf-8
""" Comfortably generate reports - Jira """

import re
from urllib import urlencode
import requests as rq
from requests_kerberos import HTTPKerberosAuth, DISABLED
import dateutil.parser
import warnings

from status_report.base import Stats, StatsGroup
from status_report.utils import Config, ReportError, log, pretty, listed

# Output warnings ONE time, then supress
warnings.simplefilter('default')

# Default identifier width
DEFAULT_WIDTH = 4

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Issue Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Issue(Stats):
    """ Jira issue investigator """

    def __init__(self, issue=None, prefix=None):
        """ Initialize issue """
        # FIXME: return in __init__ doesn't seem to be very pythonic
        # http://stackoverflow.com/questions/11981368/ raise an error instead?
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
        return u"{0}-{1} - {2}".format(
            self.prefix, self.identifier.zfill(DEFAULT_WIDTH), self.summary)

    @staticmethod
    def search(query, stats):
        """ Perform issue search for given stats instance """
        log.debug("Search query: {0}".format(query))
        result = stats.parent.session.get(
            "{0}/rest/api/latest/search?{1}".format(
                stats.parent.url, urlencode(
                    {"jql": query, "fields": "summary,comment"})))
        issues = result.json()
        log.debug(
            "Search result: {0} found".format(
                listed(issues["total"], "issue")))
        log.data(pretty(issues))
        # Return the list of issue objects
        return [
            Issue(issue, prefix=stats.parent.prefix)
            for issue in issues["issues"]]

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
        log.info(u"Searching for issues created in {0} by {1}".format(
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
        log.info(u"Searching for issues updated in {0} by {1}".format(
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
        log.info(u"Searching for issues resolved in {0} by {1}".format(
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

    def __init__(self, option, name=None, parent=None, user=None,
                 options=None):
        super(JiraStats, self).__init__(
            option=option, name=name, parent=parent, user=user,
            options=options)
        self._session = None
        # Make sure there is an url provided
        config = dict(Config().section(option))
        if "url" not in config:
            raise ReportError(
                "No Jira url set in the [{0}] section".format(option))
        self.url = config["url"].rstrip("/")
        # Make sure we have project set
        if "project" not in config:
            raise ReportError(
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
            # OLD
            # http://stackoverflow.com/questions/8811269/
            # http://www.techchorus.net/using-cookie-jar-urllib2
            #self._session = urllib2.build_opener(
            #    urllib2.HTTPSHandler(debuglevel=0),
            #    urllib2.HTTPRedirectHandler,
            #    urllib2.HTTPCookieProcessor(cookie),
            #    urllib2_kerberos.HTTPKerberosAuthHandler)
            #self._session.open(self.url + "/step-auth-gss")

            # http://stackoverflow.com/questions/21578699/
            auth = HTTPKerberosAuth(mutual_authentication=DISABLED)
            self._session = rq.Session()
            url = self.url + "/step-auth-gss"
            # FIXME: not verifying SSL is a hack...
            self._session.get(url, auth=auth, verify=False,
                              allow_redirects=True)
        return self._session
