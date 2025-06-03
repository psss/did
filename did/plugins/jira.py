"""
Jira stats such as created, updated or resolved issues

Configuration example (token)::

    [issues]
    type = jira
    url = https://issues.redhat.com/
    auth_type = token
    token_file = ~/.did/jira-token
    token_expiration = 7
    token_name = did-token

Notes:
Either ``token`` or ``token_file`` has to be defined.

token
    Token string directly included in the config.
    Has a higher priority over ``token_file``.

token_file
    Path to the file where the token is stored.

token_expiration
    Print warning if token with provided ``token_name`` expires within
    specified number of ``days``.

token_name
    Name of the token to check for expiration in ``token_expiration``
    days. This has to match the name as seen in your Jira profile.

transition_status
    Name of the issue status we want to report transitions to.
    Defaults to ``Release Pending`` (marking "verified" issues).

Configuration example (GSS authentication)::

    [issues]
    type = jira
    url = https://issues.redhat.org/
    ssl_verify = true

Configuration example (basic authentication)::

    [issues]
    type = jira
    url = https://issues.redhat.org/
    auth_url = https://issues.redhat.org/rest/auth/latest/session
    auth_type = basic
    auth_username = username
    auth_password = password
    auth_password_file = ~/.did/jira_password

Keys ``auth_username``, ``auth_password`` and ``auth_password_file`` are
only valid for ``basic`` authentication. Either ``auth_password`` or
``auth_password_file`` must be provided, ``auth_password`` has a higher
priority.

Configuration example limiting report only to a list of projects, using
an alternative username and a custom identifier prefix::

    [issues]
    type = jira
    project = ORG1, ORG2
    prefix = JIRA
    login = alt_username
    url = https://issues.redhat.org/
    ssl_verify = true

Notes:

* If your JIRA does not have scriptrunner installed you must set
  ``use_scriptrunner`` to false.
* You must provide ``login`` variable that matches username if it
  doesn't match email/JIRA account.
* Optional parameter ``ssl_verify`` can be used to enable/disable
  SSL verification (default: true).
* ``auth_url`` parameter is optional. If not provided,
  ``/step-auth-gss`` endpoint on ``url`` will be used
  for authentication.
  Its value is ignored for ``token`` auth_type.
* The ``auth_type`` parameter is optional, default value is ``gss``.
  Other values are ``basic`` and ``token``.

It's also possible to set a timeout, if not specified it defaults to
60 seconds.

    timeout = 10
"""

import os
import re
import time
import urllib.parse
from datetime import datetime

import dateutil.parser
import requests
import urllib3
from requests_gssapi import DISABLED, HTTPSPNEGOAuth

from did.base import Config, ReportError, get_token
from did.stats import Stats, StatsGroup
from did.utils import listed, log, pretty, strtobool

# Maximum number of results fetched at once
MAX_RESULTS = 200

# Maximum number of batches
MAX_BATCHES = 500

# Supported authentication types
AUTH_TYPES = ["gss", "basic", "token"]

# Enable ssl verify
SSL_VERIFY = True

# Default number of seconds waiting on Sentry before giving up
TIMEOUT = 60

# State we are interested in
DEFAULT_TRANSITION_TO = "Release Pending"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Issue Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Issue():
    """ Jira issue investigator """

    def __init__(self, issue=None, parent=None):
        """ Initialize issue """
        if issue is None:
            return
        self.parent = parent
        self.options = parent.options
        self.issue = issue
        self.key = issue["key"]
        self.summary = issue["fields"]["summary"]
        self.comments = issue["fields"]["comment"]["comments"]
        if "changelog" in issue:
            self.histories = issue["changelog"]["histories"]
        else:
            self.histories = {}
        matched = re.match(r"(\w+)-(\d+)", self.key)
        self.identifier = matched.groups()[1]
        if parent.prefix is not None:
            self.prefix = parent.prefix
        else:
            self.prefix = matched.groups()[0]

    def __str__(self):
        """ Jira key and summary for displaying """
        label = f"{self.prefix}-{self.identifier}"
        if self.options.format == "markdown":
            href = f"{self.parent.url}/browse/{self.issue['key']}"
            return f"[{label}]({href}) - {self.summary}"
        return f"{label} - {self.summary}"

    def __eq__(self, other):
        """ Compare issues by key """
        return self.key == other.key

    @staticmethod
    def search(query, stats, expand="", timeout=TIMEOUT):
        """ Perform issue search for given stats instance """
        log.debug("Search query: %s", query)
        issues = []
        # Fetch data from the server in batches of MAX_RESULTS issues
        for batch in range(MAX_BATCHES):
            encoded_query = urllib.parse.urlencode(
                {
                    "jql": query,
                    "fields": "summary,comment",
                    "maxResults": MAX_RESULTS,
                    "startAt": batch * MAX_RESULTS,
                    "expand": expand
                    }
                )
            current_url = f"{stats.parent.url}/rest/api/latest/search?{encoded_query}"
            log.debug("Fetching %s", current_url)
            while True:
                try:
                    response = stats.parent.session.get(
                        current_url,
                        timeout=timeout)
                    # Handle the exceeded rate limit
                    if response.status_code == 429:
                        if response.headers.get("X-RateLimit-Remaining") == "0":
                            # Wait at least a second.
                            retry_after = max(int(response.headers["retry-after"]), 1)
                            log.warning("Jira rate limit exceeded.")
                            log.warning("Sleeping now for %s.",
                                        listed(retry_after, 'second'))
                            time.sleep(retry_after)
                            continue

                    response.raise_for_status()
                except requests.Timeout:
                    log.warning(
                        "Timed out fetching %s",
                        current_url)
                    continue
                except (requests.exceptions.ConnectionError,
                        urllib3.exceptions.NewConnectionError,
                        requests.exceptions.HTTPError
                        ) as error:
                    log.error("Error fetching '%s': %s", current_url, error)
                    raise ReportError(
                        f"Failed to connect to Jira at {stats.parent.url}."
                        ) from error
                break
            try:
                data = response.json()
            except requests.exceptions.JSONDecodeError as error:
                log.debug(error)
                raise ReportError(f"JIRA JSON failed: {response.text}.") from error
            if not response.ok:
                try:
                    error = " ".join(data["errorMessages"])
                except KeyError:
                    error = "unknown"
                raise ReportError(
                    f"Failed to fetch jira issues for query '{query}'. "
                    f"The reason was '{response.reason}' "
                    f"and the error was '{error}'.")
            log.debug(
                "Batch %s result: %s fetched",
                batch,
                listed(data["issues"], "issue")
                )
            log.data(pretty(data))
            issues.extend(data["issues"])
            # If all issues fetched, we're done
            if len(issues) >= data["total"]:
                break
            log.info("Batch %s: fetched %s issues out of %s",
                     batch, len(issues), data["total"])
        # Return the list of issue objects
        return [
            Issue(issue, parent=stats.parent)
            for issue in issues
            ]

    def commented(self, user, options):
        """ True if the issue was commented by given user """
        for comment in self.comments:
            created = dateutil.parser.parse(comment["created"]).date()
            if (comment["author"]["emailAddress"] == user.email and
                    options.since.date < created < options.until.date):
                return True
        return False

    def changed(self, user, options):
        """ True if the issue was commented by given user """
        for history in self.histories:
            created = dateutil.parser.parse(history["created"]).date()
            if (
                    "author" in history and
                    "emailAddress" in history["author"] and
                    history["author"]["emailAddress"] == user.email and
                    options.since.date <= created <= options.until.date
                    ):
                return True
        return False

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class JiraCreated(Stats):
    """ Created issues """

    def fetch(self):
        log.info(
            "[%s] Searching for issues created in %s by %s",
            self.option,
            self.parent.project if self.parent.project is not None else "any project",
            self.user)
        query = (
            f"creator = '{self.user.login or self.user.email}' "
            f"AND created >= {self.options.since} "
            f"AND created <= {self.options.until}"
            )
        if self.parent.project:
            query = query + f" AND project in ({self.parent.project})"
        self.stats = Issue.search(query, stats=self, timeout=self.parent.timeout)
        log.info("[%s] done issues created", self.option)


class JiraCommented(Stats):
    """ Commented issues """

    def fetch(self):
        log.info(
            "[%s] Searching for issues commented in %s by %s",
            self.option,
            self.parent.project if self.parent.project is not None else "any project",
            self.user)
        if self.parent.use_scriptrunner:
            query = (
                f"issueFunction in commented('by {self.user.login or self.user.email} "
                f"after {self.options.since} "
                f"before {self.options.until}')"
                )
            if self.parent.project:
                query = query + f" AND project in ({self.parent.project})"
            self.stats = Issue.search(query, stats=self, timeout=self.parent.timeout)
        else:
            query = (
                f"project in ({self.parent.project}) "
                f"AND updated >= {self.options.since} "
                f"AND updated <= {self.options.until}"
                )
            # Filter only issues commented by given user
            self.stats = [
                issue for issue in Issue.search(query, stats=self,
                                                timeout=self.parent.timeout)
                if issue.commented(self.user, self.options)]
        log.info("[%s] done issues commented", self.option)


class JiraUpdated(Stats):
    """ Updated issues """

    def fetch(self):
        if self.parent.project is None:
            log.warning(
                "Skipping searching for issues updated as not restricting "
                "to a project will lead to an excessive amount of data")
            self.stats = []
            return
        log.info("[%s] Searching for issues updated in %s by %s",
                 self.option, self.parent.project, self.user)
        query = f"updated >= {self.options.since} AND updated <= {self.options.until}"
        if self.parent.project:
            query = query + f" AND project in ({self.parent.project})"
        # Filter only issues updated by given user
        self.stats = [issue for issue
                      in Issue.search(query, stats=self, expand="changelog",
                                      timeout=self.parent.timeout)
                      if issue.changed(self.user, self.options)]
        log.info("[%s] done issues updated", self.option)


class JiraResolved(Stats):
    """ Resolved issues """

    def fetch(self):
        log.info(
            "[%s] Searching for issues resolved in %s by %s",
            self.option,
            self.parent.project if self.parent.project is not None else "any project",
            self.user)
        query = (
            f"assignee = '{self.user.login or self.user.email}' "
            f"AND resolved >= {self.options.since} "
            f"AND resolved <= {self.options.until}"
            )
        if self.parent.project:
            query = query + f" AND project in ({self.parent.project})"
        self.stats = Issue.search(query, stats=self, timeout=self.parent.timeout)
        log.info("[%s] done issues resolved", self.option)


class JiraTested(Stats):
    """ Tested issues """

    def fetch(self):
        log.info(
            "[%s] Searching for issues resolved in %s tested by %s",
            self.option,
            self.parent.project if self.parent.project is not None else "any project",
            self.user)
        query = (
            f"tester = '{self.user.login or self.user.email}' "
            f"AND resolved >= {self.options.since} "
            f"AND resolved <= {self.options.until}"
            )
        if self.parent.project:
            query = query + f" AND project in ({self.parent.project})"
        self.stats = Issue.search(query, stats=self, timeout=self.parent.timeout)
        log.info("[%s] done issues tested", self.option)


class JiraContributed(Stats):
    """ Contributed issues """

    def fetch(self):
        log.info(
            "[%s] Searching for issues resolved in %s with %s as contributor",
            self.option,
            self.parent.project if self.parent.project is not None else "any project",
            self.user)
        query = (
            f"contributors in ('{self.user.login or self.user.email}') "
            f"AND resolved >= {self.options.since} "
            f"AND resolved <= {self.options.until}"
            )
        if self.parent.project:
            query = query + f" AND project in ({self.parent.project})"
        self.stats = Issue.search(query, stats=self, timeout=self.parent.timeout)
        log.info("[%s] done issues contributed to", self.option)


class JiraTransition(Stats):
    """ Issues transitioned to specified state """

    def fetch(self):
        log.info(
            "[%s] Searching for issues transitioned to '%s' by '%s'",
            self.option,
            self.parent.transition_status,
            self.user.login or self.user.email)
        query = (
            f"status changed to '{self.parent.transition_status}' "
            f"and status changed by '{self.user.login or self.user.email}' "
            f"after {self.options.since} before {self.options.until}"
            )
        if self.parent.project:
            query = query + f" AND project = '{self.parent.project}'"
        self.stats = Issue.search(query, stats=self)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class JiraStats(StatsGroup):
    """ Jira stats """

    # Default order
    order = 600

    def _basic_auth(self, option, config):
        if "auth_username" not in config:
            raise ReportError(f"`auth_username` not set in the [{option}] section")
        self.auth_username = config["auth_username"]
        if "auth_password" in config:
            self.auth_password = config["auth_password"]
        elif "auth_password_file" in config:
            file_path = os.path.expanduser(config["auth_password_file"])
            with open(file_path, encoding="utf-8") as password_file:
                self.auth_password = password_file.read().strip()
        else:
            raise ReportError(
                "`auth_password` or `auth_password_file` must be set "
                f"in the [{option}] section.")

    def _token_auth(self, option, config):
        self.token = get_token(config)
        if self.token is None:
            raise ReportError(
                "The `token` or `token_file` key must be set "
                f"in the [{option}] section.")
        if "token_expiration" in config or "token_name" in config:
            try:
                self.token_expiration = int(config["token_expiration"])
                self.token_name = config["token_name"]
            except KeyError as key_err:
                raise ReportError(
                    "The ``token_name`` and ``token_expiration`` must be set at"
                    f" the same time in [{option}] section.") from key_err
            except ValueError as val_err:
                raise ReportError(
                    "The ``token_expiration`` must contain number, "
                    f"used in [{option}] section.") from val_err
        else:
            self.token_expiration = self.token_name = None

    def _set_ssl_verification(self, config):
        # SSL verification
        if "ssl_verify" in config:
            try:
                self.ssl_verify = strtobool(
                    config["ssl_verify"])
            except Exception as error:
                raise ReportError(
                    f"Error when parsing 'ssl_verify': {error}") from error
        else:
            self.ssl_verify = SSL_VERIFY

    def _handle_scriptrunner(self, config):
        if "use_scriptrunner" in config:
            self.use_scriptrunner = strtobool(
                config["use_scriptrunner"])
        else:
            self.use_scriptrunner = True

        if not self.use_scriptrunner and not self.project:
            raise ReportError(
                "When scriptrunner is disabled with 'use_scriptrunner=False', "
                "'project' has to be defined for each JIRA section.")

    def __init__(self, option, name=None, parent=None, user=None):
        StatsGroup.__init__(self, option, name, parent, user)
        self._session = None
        # Make sure there is an url provided
        config = dict(Config().section(option))
        self.timeout = config.get("timeout", TIMEOUT)
        if "url" not in config:
            raise ReportError(f"No Jira url set in the [{option}] section")
        self.url = config["url"].rstrip("/")
        # Optional authentication url
        if "auth_url" in config:
            self.auth_url = config["auth_url"]
        else:
            self.auth_url = f"{self.url}/step-auth-gss"
        # Authentication type
        if "auth_type" in config:
            if config["auth_type"] not in AUTH_TYPES:
                raise ReportError(
                    f'Unsupported authentication type: {config["auth_type"]}')
            self.auth_type = config["auth_type"]
        else:
            self.auth_type = "gss"
        # Authentication credentials
        if self.auth_type == "basic":
            self._basic_auth(option, config)
        else:
            if "auth_username" in config:
                raise ReportError(
                    "`auth_username` is only valid for basic authentication "
                    f"(section [{option}])")
            if "auth_password" in config or "auth_password_file" in config:
                raise ReportError(
                    "`auth_password` and `auth_password_file` are only valid for"
                    f" basic authentication (section [{option}])")
        # Token
        self.token_expiration = None
        if self.auth_type == "token":
            self._token_auth(option, config)
        self._set_ssl_verification(config)

        # Make sure we have project set
        self.project = config.get("project", None)
        self._handle_scriptrunner(config)
        self.login = config.get("login", None)

        # Check for custom prefix
        self.prefix = config["prefix"] if "prefix" in config else None

        # State transition to count
        self.transition_status = config.get("transition_status", DEFAULT_TRANSITION_TO)

        # Create the list of stats
        self.stats = [
            JiraCreated(
                option=f"{option}-created", parent=self,
                name=f"Issues created in {option}"),
            JiraCommented(
                option=f"{option}-commented", parent=self,
                name=f"Issues commented in {option}"),
            JiraResolved(
                option=f"{option}-resolved", parent=self,
                name=f"Issues resolved in {option}"),
            JiraTested(
                option=f"{option}-tested", parent=self,
                name=f"Issues tested in {option}"),
            JiraContributed(
                option=f"{option}-contributed", parent=self,
                name=f"Issues to contributed in {option}"),
            JiraUpdated(
                option=f"{option}-updated", parent=self,
                name=f"Issues updated in {option}"),
            JiraTransition(
                option=option + "-transitioned", parent=self,
                name=f"Issues transitioned in {option}"),
            ]

    def _basic_auth_session(self):
        log.debug("Connecting to %s for basic auth", self.auth_url)
        basic_auth = (self.auth_username, self.auth_password)
        try:
            response = self._session.get(
                self.auth_url, auth=basic_auth, verify=self.ssl_verify,
                timeout=self.timeout)
        except (requests.exceptions.ConnectionError,
                urllib3.exceptions.NewConnectionError,
                requests.Timeout) as error:
            log.error(error)
            raise ReportError(
                f"Failed to connect to Jira at {self.auth_url}."
                ) from error
        return response

    def _token_auth_session(self):
        log.debug("Connecting to %s", f"{self.url}/rest/api/2/myself")
        self.session.headers["Authorization"] = f"Bearer {self.token}"
        while True:
            try:
                response = self._session.get(
                    f"{self.url}/rest/api/2/myself",
                    verify=self.ssl_verify,
                    timeout=self.timeout)
            except urllib3.exceptions.ProtocolError as error:
                log.warning(
                    "Jira server dropped connection with %s, retrying", error)
                continue
            except (requests.exceptions.ConnectionError,
                    urllib3.exceptions.NewConnectionError,
                    requests.Timeout) as error:
                log.error(error)
                raise ReportError(
                    f"Failed to connect to Jira at {self.auth_url}."
                    ) from error
            break
        return response

    def _gss_api_auth_session(self):
        log.debug("Connecting to %s for gssapi auth", self.auth_url)
        gssapi_auth = HTTPSPNEGOAuth(mutual_authentication=DISABLED)
        try:
            response = self._session.get(
                self.auth_url, auth=gssapi_auth, verify=self.ssl_verify,
                timeout=self.timeout)
        except (requests.exceptions.ConnectionError,
                urllib3.exceptions.NewConnectionError,
                requests.Timeout) as error:
            log.error(error)
            raise ReportError(
                f"Failed to connect to Jira at {self.auth_url}."
                ) from error
        return response

    @property
    def session(self):
        """ Initialize the session """
        # pylint: disable=too-many-branches
        if self._session is not None:
            return self._session
        self._session = requests.Session()
        # Disable SSL warning when ssl_verify is False
        if not self.ssl_verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        while True:
            if self.auth_type == 'basic':
                response = self._basic_auth_session()
            elif self.auth_type == "token":
                response = self._token_auth_session()
            else:
                response = self._gss_api_auth_session()
            if response.status_code == 429:
                retry_after = 1
                if response.headers.get("X-RateLimit-Remaining") == "0":
                    retry_after = max(int(response.headers["retry-after"]), 1)
                    log.warning("Jira rate limit exceeded.")
                    log.warning("Sleeping now for %s.",
                                listed(retry_after, 'second'))
                time.sleep(retry_after)
                continue
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as error:
                log.error(error)
                raise ReportError(
                    "Jira authentication failed. Check credentials or kinit."
                    ) from error
            break
        if self.token_expiration:
            while True:
                try:
                    response = self._session.get(
                        f"{self.url}/rest/pat/latest/tokens",
                        verify=self.ssl_verify,
                        timeout=self.timeout)

                    response.raise_for_status()
                    token_found = None
                    for token in response.json():
                        if token["name"] == self.token_name:
                            token_found = token
                            break
                    if token_found is None:
                        raise ValueError(
                            f"Can't check validity for the '{self.token_name}' "
                            f"token as it doesn't exist.")
                    expiring_at = datetime.strptime(
                        token_found["expiringAt"], r"%Y-%m-%dT%H:%M:%S.%f%z")
                    delta = (
                        expiring_at.astimezone() - datetime.now().astimezone())
                    if delta.days < self.token_expiration:
                        log.warning("Jira token '%s' expires in %s days.",
                                    self.token_name, delta.days)
                except (requests.exceptions.HTTPError,
                        KeyError, ValueError, requests.Timeout) as error:
                    log.warning(error)
                    time.sleep(1)
                    continue
                break
        return self._session
