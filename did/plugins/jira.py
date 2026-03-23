# pylint: disable=too-many-lines
"""
Jira stats such as created, updated or resolved issues, and worklogs

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

worklog_enable
    Whether or not to fetch worklogs. Default: off.

worklog_show_time_spent
    Whether or not to show how much time was recorded for each
    worklog. (Has no effect when ``worklog_enable`` is ``off``).

Configuration example (GSS authentication)::

    [issues]
    type = jira
    url = https://issues.redhat.org/
    ssl_verify = true

Configuration example (basic authentication for Jira
Server/Data Center)::

    [issues]
    type = jira
    url = https://issues.redhat.org/
    auth_url = https://issues.redhat.org/rest/auth/latest/session
    auth_type = basic
    auth_username = username
    auth_password = password
    auth_password_file = ~/.did/jira_password

Configuration example (basic authentication for Jira Cloud)::

    [issues]
    type = jira
    url = https://your-instance.atlassian.net/
    auth_type = basic
    auth_username = your-email@example.com
    token = your-api-token
    token_file = ~/.did/jira_api_token
    api_version = 3

Keys ``auth_username``, ``token`` and ``token_file`` are
used for Jira Cloud with ``basic`` authentication. Either ``token`` or
``token_file`` must be provided, ``token`` has a higher priority.

For Jira Server/Data Center with ``basic`` authentication, use
``auth_password`` or ``auth_password_file`` instead.

For Jira Cloud, ``auth_username`` must be your email address and
``token`` must be an API token (not your account password).
Generate an API token at:
https://id.atlassian.com/manage-profile/security/api-tokens

Optional ``api_version`` parameter can be set to ``2`` or ``3``
to specify the Jira API version. Defaults to ``3`` for Jira Cloud
and ``latest`` for Jira Server/Data Center.

Note: As of May 2025, Jira Cloud uses the new ``/rest/api/3/search/jql``
endpoint which has a different pagination model than the deprecated
``/rest/api/3/search`` endpoint. The plugin automatically handles both.

Configuration example limiting report only to a list of projects, using
an alternative username and a custom identifier prefix::

    [issues]
    type = jira
    project = ORG1, ORG2
    prefix = JIRA
    login = alt_username
    url = https://issues.redhat.org/
    ssl_verify = true

For Jira Cloud, ``login`` is typically not needed as it uses
email addresses from your user profile. For Jira Server/Data
Center, ``login`` can be used to override the username if it
differs from your email address.

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
import threading
import time
import urllib.parse
from argparse import Namespace
from datetime import datetime
from http import HTTPStatus
from typing import Any, Optional, cast

import dateutil.parser
import requests
import urllib3
import urllib3.exceptions
from requests_gssapi import DISABLED  # type: ignore[import-untyped]
from requests_gssapi import HTTPSPNEGOAuth

from did.base import Config, ReportError, User, get_token
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
TIMEOUT = 60.0

# State we are interested in
DEFAULT_TRANSITION_TO = "Release Pending"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Issue Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Issue():
    """ Jira issue investigator """

    def __init__(self,
                 issue: dict[str, Any],
                 parent: "JiraStatsGroup"):
        """ Initialize issue """
        if issue is None:
            return
        self.parent = parent
        self.options: Namespace = cast(Namespace, parent.options)
        self.issue = issue
        self.key: str = issue["key"]
        self.summary = issue["fields"]["summary"]
        self.comments = issue["fields"]["comment"]["comments"]
        self.worklogs = []
        if "worklog" in issue["fields"]:
            worklog_data = issue["fields"].get("worklog", {})
            self.worklogs = worklog_data.get("worklogs", [])
        if "changelog" in issue:
            self.histories = issue["changelog"]["histories"]
        else:
            self.histories = {}
        matched = re.match(r"(\w+)-(\d+)", self.key)
        if matched is None:
            raise RuntimeError("invalid key format detected")
        self.identifier = matched.groups()[1]
        if parent.prefix is not None:
            self.prefix = parent.prefix
        else:
            self.prefix = matched.groups()[0]

    def __str__(self) -> str:
        """ Jira key and summary for displaying """
        res = ""
        label = f"{self.prefix}-{self.identifier}"
        worklogs = ""
        for worklog in self.worklogs:
            created = dateutil.parser.parse(
                worklog["created"]).strftime('%A, %B %d, %Y')
            worklogs += "\n\n"
            time_spent = ""
            if self.parent.worklog_show_time_spent:
                time_spent_value = worklog.get('timeSpent', '')
                if time_spent_value:
                    time_spent = f" ({time_spent_value})"

            worklogs += f"      * Worklog: {created}{time_spent}\n\n"
            comment = worklog.get("comment", "")
            if comment:
                worklogs += "\n".join(
                    [f"        {line}" for line in comment.splitlines()])
        if self.options.format == "markdown":
            href = f"{self.parent.url}/browse/{self.issue['key']}"
            res = f"[{label}]({href}) - {self.summary}"
        else:
            res = f"{label} - {self.summary}"

        return res + worklogs

    def __eq__(self, other: object) -> bool:
        """ Compare issues by key """
        if not isinstance(other, Issue):
            # Not using Issue as typing to avoid violating
            # Liskov substitution principle.
            return NotImplemented
        return self.key == other.key

    @staticmethod
    def search(query: str,
               stats: "JiraStats",
               expand: str = "",
               timeout: float = TIMEOUT,
               with_worklog: bool = False) -> list["Issue"]:
        """ Perform issue search for given stats instance """
        # pylint: disable=too-many-branches,too-many-locals
        # pylint: disable=too-many-statements
        log.debug("Search query: %s", query)
        issues = []
        # Fetch data from the server in batches of MAX_RESULTS issues
        fields = "summary,comment"
        if with_worklog:
            fields += ",worklog"
        # Use new /search/jql endpoint for Jira Cloud
        # (required as of May 2025)
        # https://developer.atlassian.com/changelog/#CHANGE-2046
        search_endpoint = (
            "search/jql" if stats.parent.is_jira_cloud else "search")
        base_url = (
            f"{stats.parent.url}/rest/api/"
            f"{stats.parent.api_version}/{search_endpoint}")
        next_page_token: Optional[str] = None
        for batch in range(MAX_BATCHES):
            if stats.parent.is_jira_cloud:
                # Jira Cloud: pass params as dict and use
                # nextPageToken pagination
                params: dict[str, Any] = {
                    "jql": query,
                    "fields": fields.split(","),
                    "maxResults": MAX_RESULTS,
                    }
                if expand:
                    params["expand"] = expand
                if next_page_token:
                    params["nextPageToken"] = next_page_token
                current_url = base_url
            else:
                # Server/DC: URL-encode params and use
                # startAt pagination
                params = None
                encoded_query = urllib.parse.urlencode(
                    {
                        "jql": query,
                        "fields": fields,
                        "maxResults": MAX_RESULTS,
                        "startAt": batch * MAX_RESULTS,
                        "expand": expand})
                current_url = f"{base_url}?{encoded_query}"
            log.debug("Fetching %s (Jira Cloud: %s, API version: %s)",
                      current_url, stats.parent.is_jira_cloud, stats.parent.api_version)
            while True:
                try:
                    response = stats.parent.session.get(
                        current_url,
                        params=params,
                        timeout=timeout)
                    log.debug("Response status: %s", response.status_code)
                    # Handle the exceeded rate limit
                    if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                        if response.headers.get("X-RateLimit-Remaining") == "0":
                            # Wait at least a second.
                            retry_after = max(int(response.headers["retry-after"]), 1)
                            log.debug("Jira rate limit exceeded.")
                            log.debug("Sleeping now for %s.",
                                      listed(retry_after, 'second'))
                            time.sleep(retry_after)
                            continue
                    if response.status_code == HTTPStatus.UNAUTHORIZED:
                        stats.parent.renew_session()

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
                    if 'Connection aborted' in str(error):
                        log.debug("Connection aborted. Sleeping for 10 seconds.")
                        time.sleep(10)
                        continue
                    log.error("Error fetching '%s': %s", current_url, error)
                    if response.status_code == HTTPStatus.GONE:
                        raise ReportError(
                            f"Jira API endpoint returned 410 Gone. "
                            f"This may indicate: "
                            f"1) The API version is not supported "
                            f"(try api_version=2 in your config), "
                            f"2) A field in the query doesn't exist "
                            f"(e.g., 'tester' field), or "
                            f"3) Your Jira instance has disabled "
                            f"this endpoint. URL: {current_url}"
                            ) from error
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
                    response_error = " ".join(data["errorMessages"])
                except KeyError:
                    response_error = "unknown"
                raise ReportError(
                    f"Failed to fetch jira issues for query '{query}'. "
                    f"The reason was '{response.reason}' "
                    f"and the error was '{response_error}'.")
            log.debug(
                "Batch %s result: %s fetched",
                batch,
                listed(data["issues"], "issue")
                )
            log.data(pretty(data))
            issues.extend(data["issues"])

            # Check if we're done fetching
            if stats.parent.is_jira_cloud:
                # Jira Cloud: use nextPageToken for pagination
                next_page_token = data.get("nextPageToken")
                if data.get("isLast", False) or not next_page_token:
                    break
                log.info("Batch %s: fetched %s issues",
                         batch, len(issues))
            elif "total" in data:
                # Server/DC: use total + startAt
                if len(issues) >= data["total"]:
                    break
                log.info("Batch %s: fetched %s issues out of %s",
                         batch, len(issues), data["total"])
            else:
                if len(data["issues"]) < MAX_RESULTS:
                    break
                log.info("Batch %s: fetched %s issues",
                         batch, len(issues))
        # Return the list of issue objects
        return [
            Issue(issue, parent=stats.parent)
            for issue in issues
            ]

    def commented(self, user: User, options: Namespace) -> bool:
        """ True if the issue was commented by given user """
        for comment in self.comments:
            created = dateutil.parser.parse(comment["created"]).date()
            if (
                    "author" in comment and
                    "emailAddress" in comment["author"] and
                    comment["author"]["emailAddress"] == user.email and
                    options.since.date < created < options.until.date
                    ):
                return True
        return False

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class JiraStats(Stats):
    def __init__(self, /,
                 option: str,
                 name: Optional[str] = None,
                 parent: Optional["JiraStatsGroup"] = None,
                 user: Optional[User] = None, *,
                 options: Optional[Namespace] = None):
        self.parent: "JiraStatsGroup"
        self.options: Namespace
        self.user: User
        super().__init__(option, name, parent, user, options=options)

    def _get_user_aaid(self) -> str:
        """
        Get the user's Atlassian Account ID (AAID) for Jira Cloud.
        """
        query = urllib.parse.quote(self.user.email)
        search_url = f"{self.parent.url}/rest/api/3/user/search?query={query}"

        log.debug("Fetching user AAID for %s from %s", self.user.email, search_url)

        try:
            response = self.parent.session.get(
                search_url,
                timeout=self.parent.timeout
                )
            response.raise_for_status()
            users = response.json()

            if not users:
                raise ReportError(
                    f"No user found for email '{self.user.email}' in Jira Cloud."
                    )

            # Return the accountId of the first matching user
            return users[0]["accountId"]

        except requests.exceptions.RequestException as error:
            log.error("Failed to fetch user AAID: %s", error)
            raise ReportError(
                f"Failed to fetch user AAID for {self.user.email}"
                ) from error

    def _get_user_identifier(self) -> str:
        """
        Get the correct user identifier for JQL queries.
        Jira Cloud requires email addresses, Server/DC uses usernames.
        """
        if self.parent.is_jira_cloud:
            return self.user.email
        return self.user.login or self.user.email

    def fetch(self) -> None:
        raise NotImplementedError()


class JiraCreated(JiraStats):
    """ Created issues """

    def fetch(self) -> None:
        self.parent: JiraStatsGroup
        log.info(
            "[%s] Searching for issues created in %s by %s",
            self.option,
            self.parent.project if self.parent.project is not None else "any project",
            self.user)
        user_id = self._get_user_identifier()
        query = (
            f"creator = '{user_id}' "
            f"AND created >= {self.options.since} "
            f"AND created <= {self.options.until}"
            )
        if self.parent.project:
            query = query + f" AND project in ({self.parent.project})"
        self.stats = Issue.search(query, stats=self, timeout=self.parent.timeout)
        log.info("[%s] done issues created", self.option)


class JiraCommented(JiraStats):
    """ Commented issues """

    def fetch(self) -> None:
        self.parent: JiraStatsGroup
        log.info(
            "[%s] Searching for issues commented in %s by %s",
            self.option,
            self.parent.project if self.parent.project is not None else "any project",
            self.user)
        user_id = self._get_user_identifier()

        precise = False
        if self.parent.use_scriptrunner:
            if self.parent.is_jira_cloud:
                # Jira Cloud ScriptRunner uses commentedBy field
                query = (
                    f"commentedBy = '{user_id}' "
                    f"AND updated >= {self.options.since}"
                    )
            else:
                # Jira Server/DC ScriptRunner uses issueFunction
                precise = True
                query = (
                    f"issueFunction in commented('by {user_id} "
                    f"after {self.options.since} "
                    f"before {self.options.until}')"
                    )
        else:
            query = f"updated >= {self.options.since}"

        if self.parent.project:
            query = query + f" AND project in ({self.parent.project})"

        self.stats = Issue.search(query, stats=self, timeout=self.parent.timeout)
        if not precise:
            # Loose query - results need filtering on the client side
            self.stats = [ issue for issue in self.stats
                           if issue.commented(self.user, self.options)]
        log.info("[%s] done issues commented", self.option)


class JiraUpdated(JiraStats):
    """ Updated issues """

    def fetch(self) -> None:
        self.parent: JiraStatsGroup
        if self.parent.project is None:
            log.warning(
                "Skipping searching for issues updated as not restricting "
                "to a project will lead to an excessive amount of data")
            self.stats = []
            return
        log.info("[%s] Searching for issues updated in %s by %s",
                 self.option, self.parent.project, self.user)
        user_id = self._get_user_identifier()
        query = (
            f"issuekey IN updatedBy('{user_id}', "
            f"'{self.options.since}', '{self.options.until - 1}')"
            )
        if self.parent.project:
            query = query + f" AND project in ({self.parent.project})"
        self.stats = Issue.search(query, stats=self,
                                  timeout=self.parent.timeout)
        log.info("[%s] done issues updated", self.option)


class JiraResolved(JiraStats):
    """ Resolved issues """

    def fetch(self) -> None:
        self.parent: JiraStatsGroup
        log.info(
            "[%s] Searching for issues resolved in %s by %s",
            self.option,
            self.parent.project if self.parent.project is not None else "any project",
            self.user)
        user_id = self._get_user_identifier()
        query = (
            f"assignee = '{user_id}' "
            f"AND resolved >= {self.options.since} "
            f"AND resolved <= {self.options.until}"
            )
        if self.parent.project:
            query = query + f" AND project in ({self.parent.project})"
        self.stats = Issue.search(query, stats=self, timeout=self.parent.timeout)
        log.info("[%s] done issues resolved", self.option)


class JiraTested(JiraStats):
    """ Tested issues """

    def fetch(self) -> None:
        self.parent: JiraStatsGroup
        log.info(
            "[%s] Searching for issues resolved in %s tested by %s",
            self.option,
            self.parent.project if self.parent.project is not None else "any project",
            self.user)
        user_id = self._get_user_identifier()
        query = (
            f"tester = '{user_id}' "
            f"AND resolved >= {self.options.since} "
            f"AND resolved <= {self.options.until}"
            )
        if self.parent.project:
            query = query + f" AND project in ({self.parent.project})"
        self.stats = Issue.search(query, stats=self, timeout=self.parent.timeout)
        log.info("[%s] done issues tested", self.option)


class JiraContributed(JiraStats):
    """ Contributed issues """

    def fetch(self) -> None:
        self.parent: JiraStatsGroup
        log.info(
            "[%s] Searching for issues resolved in %s with %s as contributor",
            self.option,
            self.parent.project if self.parent.project is not None else "any project",
            self.user)
        user_id = self._get_user_identifier()
        query = (
            f"contributors in ('{user_id}') "
            f"AND resolved >= {self.options.since} "
            f"AND resolved <= {self.options.until}"
            )
        if self.parent.project:
            query = query + f" AND project in ({self.parent.project})"
        self.stats = Issue.search(query, stats=self, timeout=self.parent.timeout)
        log.info("[%s] done issues contributed to", self.option)


class JiraTransition(JiraStats):
    """ Issues transitioned to specified state """

    def fetch(self) -> None:
        self.parent: JiraStatsGroup
        # For cloud we need AAID
        if self.parent.is_jira_cloud:
            user_id = self._get_user_aaid()
        else:
            user_id = self._get_user_identifier()
        log.info(
            "[%s] Searching for issues transitioned to '%s' by '%s'",
            self.option,
            self.parent.transition_status,
            user_id)
        query = (
            f"status changed to '{self.parent.transition_status}' "
            f"and status changed by '{user_id}' "
            f"after '{self.options.since} 00:00' before {self.options.until}"
            )
        if self.parent.project:
            query = query + f" AND project in ({self.parent.project})"
        self.stats = Issue.search(query, stats=self)


class JiraWorklog(JiraStats):
    """ Jira Issues for which a worklog entry was made """

    def fetch(self) -> None:
        user_id = self._get_user_identifier()
        log.info(
            "[%s] Searching for issues for which work was logged by '%s'",
            self.option,
            user_id)
        query = (
            f"worklogAuthor = '{user_id}' "
            f"and worklogDate >= {self.options.since} "
            f"and worklogDate < {self.options.until} "
            )
        if self.parent.project:
            query = query + f" AND project in ({self.parent.project})"
        try:
            issues = Issue.search(query, stats=self, with_worklog=True)
        except ReportError as error:
            log.error("Failed to fetch worklogs: %s", error)
            self.error = True
            # Leave self.stats as empty list (already initialized)
            return
        # Now we have just the issues which have work logs but we
        # want to limit what worklogs we include in the report.
        # Filter out worklogs that were not done in the given
        # time frame.
        log.debug("Found issues: %d", len(issues))
        for issue in issues:
            log.debug("Found worklogs: %s", len(issue.worklogs))
            # For Jira Cloud, use email; for Server/DC,
            # use login name or email
            if self.parent.is_jira_cloud:
                issue.worklogs = [wl for wl in issue.worklogs if
                                  ("emailAddress" in wl["author"]
                                   and wl["author"]["emailAddress"] == self.user.email)
                                  and self.options.since.date <=
                                  dateutil.parser.parse(wl["created"]).date()
                                  < self.options.until.date]
            else:
                issue.worklogs = [wl for wl in issue.worklogs if
                                  (("name" in wl["author"]
                                    and wl["author"]["name"] ==
                                    self.user.login)
                                   or ("emailAddress" in wl["author"]
                                       and wl["author"]["emailAddress"] ==
                                       self.user.email))
                                  and self.options.since.date <=
                                  dateutil.parser.parse(wl["created"]).date()
                                  < self.options.until.date]
            log.debug("Num worklogs after filtering: %d", len(issue.worklogs))
        self.stats = [issue for issue in issues if len(issue.worklogs) > 0]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class JiraStatsGroup(StatsGroup):
    """ Jira stats """

    # Default order
    order = 600

    def _basic_auth(self, option: str, config: dict[str, str]) -> None:
        if "auth_username" not in config:
            raise ReportError(f"`auth_username` not set in the [{option}] section")
        self.auth_username = config["auth_username"]

        # For Jira Cloud, use token/token_file; for Server/DC, use
        # auth_password/auth_password_file
        if self.is_jira_cloud:
            if "token" in config:
                self.auth_password = config["token"]
            elif "token_file" in config:
                file_path = os.path.expanduser(config["token_file"])
                with open(file_path, encoding="utf-8") as token_file:
                    self.auth_password = token_file.read().strip()
            else:
                raise ReportError(
                    "`token` or `token_file` must be set "
                    f"for Jira Cloud in the [{option}] section.")
        else:
            if "auth_password" in config:
                self.auth_password = config["auth_password"]
            elif "auth_password_file" in config:
                file_path = os.path.expanduser(config["auth_password_file"])
                with open(file_path, encoding="utf-8") as password_file:
                    self.auth_password = password_file.read().strip()
            else:
                raise ReportError(
                    "`auth_password` or `auth_password_file` must be set "
                    f"for Jira Server/Data Center in the [{option}] section.")

    def _token_auth(self, option: str, config: dict[str, str]) -> None:
        self.token = get_token(config)
        if self.token is None:
            raise ReportError(
                "The `token` or `token_file` key must be set "
                f"in the [{option}] section.")
        if "token_expiration" in config or "token_name" in config:
            try:
                self.token_expiration: Optional[int] = int(config["token_expiration"])
                self.token_name: Optional[str] = config["token_name"]
            except KeyError as key_err:
                raise ReportError(
                    "The ``token_name`` and ``token_expiration`` must be set at"
                    f" the same time in [{option}] section.") from key_err
            except ValueError as val_err:
                raise ReportError(
                    "The ``token_expiration`` must contain number, "
                    f"used in [{option}] section.") from val_err
        else:
            self.token_expiration = None
            self.token_name = None

    def _set_ssl_verification(self, config: dict[str, str]) -> None:
        # SSL verification
        if "ssl_verify" in config:
            try:
                self.ssl_verify = bool(strtobool(config["ssl_verify"]))
            except Exception as error:
                raise ReportError(
                    f"Error when parsing 'ssl_verify': {error}") from error
        else:
            self.ssl_verify = SSL_VERIFY

    def _handle_scriptrunner(self, config: dict[str, str]) -> None:
        if "use_scriptrunner" in config:
            self.use_scriptrunner: bool = bool(
                strtobool(config["use_scriptrunner"]))
        else:
            self.use_scriptrunner = True

        if not self.use_scriptrunner and not self.project:
            raise ReportError(
                "When scriptrunner is disabled with 'use_scriptrunner=False', "
                "'project' has to be defined for each JIRA section.")

    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    def __init__(self,
                 option: str,
                 name: Optional[str] = None,
                 parent: Optional[StatsGroup] = None,
                 user: Optional[User] = None) -> None:
        StatsGroup.__init__(self, option, name, parent, user)
        self._session: Optional[requests.Session] = None
        self._session_lock = threading.Lock()
        # Make sure there is an url provided
        config = dict(Config().section(option))
        self.timeout: float = float(config.get("timeout", TIMEOUT))
        if "url" not in config:
            raise ReportError(f"No Jira url set in the [{option}] section")
        self.url = config["url"].rstrip("/")
        # Detect if this is Jira Cloud (*.atlassian.net)
        parsed_url = urllib.parse.urlparse(self.url)
        hostname = (parsed_url.hostname or "").lower()
        self.is_jira_cloud = hostname == "atlassian.net" or hostname.endswith(
            ".atlassian.net")
        # API version: default to 3 for Cloud, latest for Server/DC
        if "api_version" in config:
            self.api_version = config["api_version"]
        else:
            self.api_version = "3" if self.is_jira_cloud else "latest"
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
        self.token_name = None
        if self.auth_type == "token":
            self._token_auth(option, config)
        self._set_ssl_verification(config)

        # Make sure we have project set
        self.project: Optional[str] = config.get("project", None)
        self._handle_scriptrunner(config)
        self.login = config.get("login", None)

        # Check for custom prefix
        self.prefix = config["prefix"] if "prefix" in config else None

        # State transition to count
        self.transition_status = config.get("transition_status", DEFAULT_TRANSITION_TO)

        if "worklog_enable" in config:
            try:
                self.worklog_enable = strtobool(
                    config["worklog_enable"])
            except Exception as error:
                raise ReportError(
                    f"Error when parsing 'worklog_enable': {error}") from error
        else:
            self.worklog_enable = False

        if "worklog_show_time_spent" in config:
            try:
                self.worklog_show_time_spent = strtobool(
                    config["worklog_show_time_spent"])
            except Exception as error:
                raise ReportError(
                    f"Error when parsing 'worklog_show_time_spent': {error}") from error
        else:
            self.worklog_show_time_spent = True

        if not self.worklog_enable and self.worklog_show_time_spent:
            log.debug(
                "'worklog_show_time_spent' is on but has no effect "
                "because 'worklog_enable' is off")

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
                name=f"Issues transitioned in {option}")
            ]

        if self.worklog_enable:
            self.stats.append(JiraWorklog(
                option=f"{option}-worklog", parent=self,
                name=f"Issues with worklogs in {option}"))

    def _basic_auth_session(self, _session) -> requests.Response:
        _session.auth = (self.auth_username, self.auth_password)

        if self.is_jira_cloud:
            # For Jira Cloud, verify credentials by calling
            # the /myself endpoint
            log.debug("Connecting to Jira Cloud at %s for basic auth", self.url)
            test_url = f"{self.url}/rest/api/{self.api_version}/myself"
            try:
                response = _session.get(
                    test_url, verify=self.ssl_verify,
                    timeout=self.timeout)
            except (requests.exceptions.ConnectionError,
                    urllib3.exceptions.NewConnectionError,
                    requests.Timeout) as error:
                log.error(error)
                raise ReportError(
                    f"Failed to connect to Jira Cloud at {self.url}. "
                    "Make sure you're using your email as username and an API token "
                    "(not your password). Generate one at: "
                    "https://id.atlassian.com/manage-profile/security/api-tokens"
                    ) from error
        else:
            # For Jira Server/Data Center, use session-based auth
            log.debug("Connecting to %s for basic auth", self.auth_url)
            try:
                response = _session.get(
                    self.auth_url, verify=self.ssl_verify,
                    timeout=self.timeout)
            except (requests.exceptions.ConnectionError,
                    urllib3.exceptions.NewConnectionError,
                    requests.Timeout) as error:
                log.error(error)
                raise ReportError(
                    f"Failed to connect to Jira at {self.auth_url}."
                    ) from error
        return response

    def _token_auth_session(self, _session) -> requests.Response:
        myself_url = f"{self.url}/rest/api/{self.api_version}/myself"
        log.debug("Connecting to %s", myself_url)
        _session.headers["Authorization"] = f"Bearer {self.token}"
        while True:
            try:
                response = _session.get(
                    myself_url,
                    verify=self.ssl_verify,
                    timeout=self.timeout)
            except urllib3.exceptions.ProtocolError as error:
                log.debug(
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

    def _gss_api_auth_session(self, _session) -> requests.Response:
        log.debug("Connecting to %s for gssapi auth", self.auth_url)
        gssapi_auth = HTTPSPNEGOAuth(mutual_authentication=DISABLED)
        try:
            response: requests.Response = _session.get(
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

    def renew_session(self) -> requests.Session:
        with self._session_lock:
            self._session = None
        return self.session

    @property
    def session(self) -> requests.Session:
        """ Initialize the session """
        # pylint: disable=too-many-branches
        # If session already exists, return it
        if self._session is not None:
            return self._session

        # Acquire lock to initialize session
        with self._session_lock:
            # Double-check: another thread might have initialized it
            # while we were waiting for the lock
            if self._session is not None:
                return self._session

            # Do not set it to self._session until it is fully ready
            _session = requests.Session()
            # Disable SSL warning when ssl_verify is False
            if not self.ssl_verify:
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            while True:
                if self.auth_type == 'basic':
                    response = self._basic_auth_session(_session)
                elif self.auth_type == "token":
                    response = self._token_auth_session(_session)
                else:
                    response = self._gss_api_auth_session(_session)
                if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                    retry_after = 1
                    if response.headers.get("X-RateLimit-Remaining") == "0":
                        retry_after = max(int(response.headers["retry-after"]), 1)
                        log.debug("Jira rate limit exceeded.")
                        log.debug("Sleeping now for %s.",
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
                        response = _session.get(
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
            self._session = _session
            return self._session
