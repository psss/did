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

try:
    import requests as rq
    from requests_kerberos import HTTPKerberosAuth, DISABLED
    import warnings
    # Output warnings ONE time, then supress
    warnings.simplefilter('default')
    has_requests = True
except ImportError:
    has_requests = False
    import urllib2
    import urllib2_kerberos
    import json

import cookielib
import urllib
import re
import dateutil.parser

from did.utils import log, pretty, listed, as_bool
from did.base import Config, ReportError
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

            # Load the results; requests comes with json built-in
            if has_requests:
                data = result.json()
            else:
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

    cookiejar = None
    config = None
    auth_type = None
    auth_username = None
    auth_password = None
    url = None
    prefix = None
    project = None
    _option = None
    _session = None

    def __init__(self, option, name=None, parent=None, user=None):
        '''
        Load Jira module with config. Check that we have all the
        essential arguments set and raise exceptions if not.
        '''
        super(JiraStats, self).__init__(option, name, parent, user)
        # Make sure there is an url provided
        self._option = option
        self.config = dict(Config().section(option))
        # jira base url
        self.url = self.config["url"].rstrip("/")
        # Authentication credentials
        self.auth_type = self.config.get('auth_type') or "gss"
        self.auth_username = self.config.get("auth_username")
        self.auth_password = self.config.get("auth_password")
        # Optional authentication url
        _default = self.url + "/step-auth-gss"
        self.auth_url = self.config.get('auth_url') or _default
        # Check for custom prefix
        if not self.url:
            # FIXME: This is a config issue, raise ConfigError?
            raise ReportError(
                "No Jira url set in [{0}] section".format(self._option))
        self.prefix = self.config.get("prefix")
        # Make sure we have project set
        self.project = self.config.get("project")
        if not self.project:
            raise ReportError(
                "No project set in the [{0}] section".format(self._option))

        # check that auth_type is configured correctly
        self._auth_type_check()

        self.ssl_verify = as_bool(self.config.get('ssl_verify', True))

        # http://www.techchorus.net/using-cookie-jar-urllib2
        self.cookiejar = cookielib.CookieJar()

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
    def _ssl_handler(self):
        '''
        Property to generate urllib2 ssl context workaround to avoid
        ssl verification
        '''
        if self.ssl_verify:
            # requires ssl verification
            ssl_hdlr = urllib2.HTTPSHandler(debuglevel=0)
        else:
            # skip ssl verification
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            #urllib2.urlopen("https://your-test-server.local", context=ctx)
            ssl_hdlr = urllib2.HTTPSHandler(debuglevel=0, context=ctx)
        return ssl_hdlr

    def _auth_type_check(self):
        # check that we have the auth config configured correctly
        # username and password are only useful in the context of 'basic' auth
        auth_username = self.auth_username
        auth_password = self.auth_password
        if self.auth_type not in AUTH_TYPES:
            raise ReportError(
                "Unsupported authentication type: {0}".format(self._auth_type))
        if self.auth_type == "basic":
            if not auth_username:
                raise ReportError(
                    "`auth_username` not set in the [{0}] section"
                    .format(self._option))
            if not auth_password:
                raise ReportError(
                    "`auth_password` not set in the [{0}] section"
                    .format(self._option))
        else:  # self.auth_type == "gss"
            if auth_username:
                raise ReportError(
                    "`auth_username` is only valid for basic authentication"
                    + " (section [{0}])".format(self._option))
            if auth_password:
                raise ReportError(
                    "`auth_password` is only valid for basic authentication"
                    + " (section [{0}])".format(self._option))

    def _basic_session(self):
        # use urllib2 sessions by default here
        self._session = urllib2.build_opener(
            urllib2.HTTPSHandler(debuglevel=0),
            urllib2.HTTPRedirectHandler,
            urllib2.HTTPCookieProcessor(self.cookiejar),
            urllib2.HTTPBasicAuthHandler)
        req = urllib2.Request(self.auth_url)
        req.add_data('{ "username" : "%s", "password" : "%s" }' % (
            self.auth_username, self.auth_password))
        req.add_header("Content-type", "application/json")
        req.add_header("Accept", "application/json")
        self._session.open(req)

    def _gss_session(self):
        # For some reason, GSSAPI isn't working as expected in some cases
        # so use requests if available.
        if has_requests:
            # http://stackoverflow.com/questions/21578699/
            auth = HTTPKerberosAuth(mutual_authentication=DISABLED)
            self._session = rq.Session()
            url = self.url + "/step-auth-gss"
            self._session.get(url, auth=auth, verify=self.ssl_verify,
                              allow_redirects=True)
            # compat with urllib2
            self._session.open = self._session.get
        else:
            # http://stackoverflow.com/questions/8811269/
            self._session = urllib2.build_opener(
                urllib2.HTTPSHandler(debuglevel=0),
                urllib2.HTTPRedirectHandler,
                urllib2.HTTPCookieProcessor(self.cookiejar),
                urllib2_kerberos.HTTPKerberosAuthHandler)
            self._session.open(self.auth_url)

    @property
    def session(self):
        """ Initialize the session """
        if self._session is None:
            log.debug("Connecting to {0}".format(self.auth_url))
            if self.auth_type == 'basic':
                self._basic_session()
            else:
                assert self.auth_type == 'gss'
                self._gss_session()
        return self._session
