"""
GitLab stats such as created and closed issues

Config example::

    [gitlab]
    type = gitlab
    url = https://gitlab.com/
    token = <authentication-token>
    token_file = <authentication-token-file>
    login = <username>
    ssl_verify = true

The authentication token is required. Create it in the GitLab web
interface (select ``api`` as the desired scope). See the `GitLab API`__
documentation for details.

Use ``login`` to override user name detected from the email address.
See the :doc:`config` documentation for details on using aliases.
Use ``ssl_verify`` to enable/disable SSL verification (default: true)

It's also possible to set a timeout, if not specified it defaults to 60
seconds.

    timeout = 10


__ https://docs.gitlab.com/ce/api/

"""

from __future__ import annotations

from time import sleep
from typing import Any, Optional

import dateutil
import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

from did.base import Config, ReportError, get_token
from did.stats import Stats, StatsGroup
from did.utils import listed, log, pretty, strtobool

GITLAB_SSL_VERIFY = True
GITLAB_API = 4

# Retry fetching
GITLAB_ATTEMPTS = 5
GITLAB_INTERVAL = 5
GITLAB_MAX_PAGE_LIST = 20

# Identifier padding
PADDING = 3

# Default number of seconds waiting on GitLab before giving up
TIMEOUT = 60.0


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GitLab():
    """ GitLab Investigator """

    def __init__(self,
                 url: str,
                 token: str,
                 ssl_verify: bool = GITLAB_SSL_VERIFY,
                 timeout: float = TIMEOUT):
        """ Initialize url and headers """
        self.url = url.rstrip("/")
        self.headers = {'PRIVATE-TOKEN': token}
        self.token = token
        self.ssl_verify = ssl_verify
        self.user: Optional[dict[str, Any]] = None
        self.events: Optional[list[dict[str, Any]]] = None
        self.projects: dict[str, list[dict[str, Any]]] = {}
        self.project_mrs: dict[str, list[dict[str, Any]]] = {}
        self.project_issues: dict[str, list[dict[str, Any]]] = {}
        self.timeout = timeout

    def _get_gitlab_api_raw(self, url):
        log.debug("Connecting to GitLab API at '%s'.", url)
        retries = 0
        while True:
            try:
                api_raw = requests.get(
                    url, headers=self.headers, verify=self.ssl_verify,
                    timeout=self.timeout)
                api_raw.raise_for_status()
                return api_raw
            except requests.exceptions.HTTPError as http_err:
                result = api_raw.json()
                if "error" in result:
                    raise ReportError(
                        f'Error \"{result["error"]}\" '
                        f'connecting to GitLab: {result["error_description"]}'
                        ) from http_err
                raise ReportError(
                    f"Unable to access '{url}'. Error: {http_err}"
                    ) from http_err
            except requests.exceptions.ConnectionError as connection_error:
                retries += 1
                if retries > GITLAB_ATTEMPTS:
                    raise ReportError(
                        f"Unable to connect to '{url}'. Error: {connection_error}"
                        ) from connection_error
                log.debug(
                    "Retrying connection to '%s' in %s seconds due to %s.",
                    url,
                    GITLAB_INTERVAL,
                    connection_error
                    )
                sleep(GITLAB_INTERVAL)

    def _get_gitlab_api(self, endpoint):
        url = f'{self.url}/api/v{GITLAB_API}/{endpoint}'
        return self._get_gitlab_api_raw(url)

    def _get_gitlab_api_json(self, endpoint):
        log.debug("Query: %s", endpoint)
        result = self._get_gitlab_api(endpoint).json()
        log.data(pretty(result))
        return result

    def _get_gitlab_api_list(
            self, endpoint, since=None, get_all_results=False):
        results = []
        result = self._get_gitlab_api(endpoint)
        result.raise_for_status()
        results.extend(result.json())
        while ('next' in result.links and 'url' in result.links['next'] and
                get_all_results):
            log.debug("-> Fetching more paginated data")
            result = self._get_gitlab_api_raw(result.links['next']['url'])
            json_result = result.json()
            results.extend(json_result)
            if since is not None:
                # check if the last result is older than the since date
                created_at = dateutil.parser.parse(
                    json_result[-1]['created_at']).date()
                if created_at < since.date:
                    return results
        return results

    def get_user(self, username):
        query = f'users?username={username}'
        try:
            result = self._get_gitlab_api_json(query)
        except requests.exceptions.JSONDecodeError as jde:
            raise ReportError(
                f"Unable to query user '{username}' on {self.url}."
                ) from jde
        try:
            return result[0]
        except (IndexError, KeyError) as exc:
            raise ReportError(
                f"Unable to find user '{username}' on {self.url}.") from exc

    def get_project(self, project_id):
        if project_id not in self.projects:
            query = f'projects/{project_id}'
            self.projects[project_id] = self._get_gitlab_api_json(query)
        return self.projects[project_id]

    def get_project_mr(self, project_id, mr_id):
        mrs = self.get_project_mrs(project_id)
        mr = next(filter(lambda x: x['id'] == mr_id, mrs), None)
        return mr

    def get_project_mrs(self, project_id):
        if project_id not in self.project_mrs:
            query = f'projects/{project_id}/merge_requests'

            # Check that this will not return more then 20 pages;
            # if it does, skip rather than spending a large amount
            # of time to query all of the results.
            result = self._get_gitlab_api(query)
            result.raise_for_status()
            log.debug(
                "Page count for %s: %s",
                query,
                result.headers.get('x-total-pages')
                )
            if int(
                result.headers.get(
                    'x-total-pages',
                    GITLAB_MAX_PAGE_LIST +
                    1)) > GITLAB_MAX_PAGE_LIST:
                self.project_mrs[project_id] = []
                return []

            self.project_mrs[project_id] = self._get_gitlab_api_list(
                query, get_all_results=True)
        return self.project_mrs[project_id]

    def get_project_issue(self, project_id, issue_id):
        issues = self.get_project_issues(project_id)
        issue = next(filter(lambda x: x['id'] == issue_id, issues), None)
        return issue

    def get_project_issues(self, project_id):
        if project_id not in self.project_issues:
            query = f'projects/{project_id}/issues'

            # Check that this will not return more then 20 pages;
            # if it does, skip rather than spending a large amount
            # of time to query all of the results.
            result = self._get_gitlab_api(query)
            result.raise_for_status()
            log.debug(
                "Page count for %s: %s",
                query,
                result.headers.get('x-total-pages')
                )
            if int(
                result.headers.get(
                    'x-total-pages',
                    GITLAB_MAX_PAGE_LIST +
                    1)) > GITLAB_MAX_PAGE_LIST:
                self.project_issues[project_id] = []
                return []

            self.project_issues[project_id] = self._get_gitlab_api_list(
                query, get_all_results=True)
        return self.project_issues[project_id]

    def user_events(self, user_id, since, until):
        if GITLAB_API < 4:
            # Not supported
            return []
        query = f'users/{user_id}/events?after={since - 1}&before={until}'
        return self._get_gitlab_api_list(query, since, True)

    def search(self, user, since, until, *, target_type, action_name):
        """ Perform GitLab query """
        if not self.user:
            self.user = self.get_user(user)
        if self.events is None:
            self.events = self.user_events(self.user['id'], since, until)
        result = []
        for event in self.events:
            created_at = dateutil.parser.parse(event['created_at']).date()
            if (
                event['target_type'] == target_type and
                event['action_name'] == action_name and
                since.date <= created_at <= until.date
                    ):
                result.append(event)
        log.debug("Result: %s fetched", listed(len(result), "item"))
        return result


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Issue
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Issue():
    """ GitLab Issue """

    def __init__(self, data: dict, parent: "GitLabStats", set_id=None):
        self.parent = parent
        self.data = data
        self.gitlabapi: GitLab = parent.gitlab
        self.project = self.gitlabapi.get_project(data['project_id'])
        self.id = set_id
        if set_id is None:
            self.id = self.iid()
        self.title = data['target_title']
        self._body: Optional[str] = None

    def iid(self):
        issue = self.gitlabapi.get_project_issue(
            self.data['project_id'], self.data['target_id'])

        if issue is not None:
            return issue['iid']
        return "unknown"

    @property
    def body(self) -> str:
        """Get full issue description (lazy-loaded)"""
        if self._body is None:
            issue_data = self.gitlabapi.get_project_issue(
                self.data['project_id'], self.data['target_id'])
            self._body = issue_data.get('description', '') if issue_data else ''
        return self._body

    def __str__(self):
        """ String representation """
        # Determine endpoint for URL
        endpoint = "merge_requests"
        if self.data['target_type'] == 'Issue' or (
                self.data['target_type'] == 'Note'
                and self.data['note']['noteable_type'] == 'Issue'
                ):
            endpoint = "issues"

        label = f"{self.project['path_with_namespace']}#{str(self.id)}"

        # Check for full-message mode
        if getattr(self.parent.options, 'full_message', False) and self.body:
            body_text = self.body.strip()
            body_lines = [line for line in body_text.split("\n") if line.strip()]
            formatted_body = "\n        ".join(body_lines)

            if self.parent.options.format == "markdown":
                href = (
                    f"{self.gitlabapi.url}/{self.project['path_with_namespace']}"
                    f"/-/{endpoint}/{str(self.id)}"
                    )
                return (f"[{label}]({href}) - {self.title}"
                        f"\n        {formatted_body}")
            return (f"{self.project['path_with_namespace']}"
                    f"#{str(self.id).zfill(PADDING)} - {self.title}"
                    f"\n        {formatted_body}")

        # Default: title only
        if self.parent.options.format == "markdown":
            href = (
                f"{self.gitlabapi.url}/{self.project['path_with_namespace']}"
                f"/-/{endpoint}/{str(self.id)}"
                )
            return f"[{label}]({href}) - {self.title}"
        return (
            f"{self.project['path_with_namespace']}"
            f"#{str(self.id).zfill(PADDING)} - {self.title}"
            )


class MergeRequest(Issue):
    # pylint: disable=too-few-public-methods

    def __init__(self, data, parent, set_id=None):
        if set_id is None:
            merge_request = parent.gitlab.get_project_mr(
                data['project_id'], data['target_id'])
            if merge_request is not None:
                set_id = merge_request['iid']
        super().__init__(data, parent, set_id)

    @property
    def body(self) -> str:
        """Get full MR description (lazy-loaded)"""
        if self._body is None:
            mr_data = self.gitlabapi.get_project_mr(
                self.data['project_id'], self.data['target_id'])
            self._body = mr_data.get('description', '') if mr_data else ''
        return self._body


class Note(Issue):
    # pylint: disable=too-few-public-methods

    def __init__(self, data, parent, set_id=None):
        if set_id is None:
            set_id = self.note_iid(data, parent.gitlab)
        super().__init__(data, parent, set_id)

    def note_iid(self, data, gitlabapi):
        if data['note']['noteable_type'] == 'Issue':
            issue = gitlabapi.get_project_issue(
                data['project_id'],
                data['note']['noteable_id'])

            # `noteable_type` is `Issue` even for `WorkItem`s, which
            # aren't returned by `get_project_issue()`
            if issue is not None:
                return issue['iid']
            return 'unknown'
        if data['note']['noteable_type'] == 'MergeRequest':
            merge_request = gitlabapi.get_project_mr(
                data['project_id'],
                data['note']['noteable_id'])
            if merge_request is not None:
                return merge_request['iid']
        return "unknown"

    @property
    def body(self) -> str:
        """Get full issue/MR description (lazy-loaded)"""
        if self._body is None:
            noteable_type = self.data['note']['noteable_type']
            noteable_id = self.data['note']['noteable_id']
            if noteable_type == 'Issue':
                item_data = self.gitlabapi.get_project_issue(
                    self.data['project_id'], noteable_id)
            elif noteable_type == 'MergeRequest':
                item_data = self.gitlabapi.get_project_mr(
                    self.data['project_id'], noteable_id)
            else:
                item_data = None
            self._body = item_data.get('description', '') if item_data else ''
        return self._body


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class IssuesCreated(Stats):
    """ Issue created """

    def fetch(self):
        log.info("Searching for Issues created by %s", self.user)
        results = self.parent.gitlab.search(
            self.user.login, self.options.since, self.options.until,
            target_type='Issue',
            action_name='opened')
        self.stats = [
            Issue(issue, self.parent)
            for issue in results]


class IssuesCommented(Stats):
    """ Issue commented """

    def fetch(self):
        log.info("Searching for Issues commented by %s", self.user)
        results = self.parent.gitlab.search(
            self.user.login, self.options.since, self.options.until,
            target_type='Note',
            action_name='commented on')
        self.stats = [
            Note(issue, self.parent)
            for issue in results
            if issue['note']['noteable_type'] == 'Issue']


class IssuesClosed(Stats):
    """ Issue closed """

    def fetch(self):
        log.info("Searching for Issues closed by %s", self.user)
        results = self.parent.gitlab.search(
            self.user.login, self.options.since, self.options.until,
            target_type='Issue',
            action_name='closed')
        self.stats = [
            Issue(issue, self.parent)
            for issue in results]


class MergeRequestsCreated(Stats):
    """ Merge requests created """

    def fetch(self):
        log.info("Searching for Merge requests created by %s", self.user)
        results = self.parent.gitlab.search(
            self.user.login, self.options.since, self.options.until,
            target_type='MergeRequest',
            action_name='opened')
        self.stats = [
            MergeRequest(mr, self.parent)
            for mr in results]


class MergeRequestsCommented(Stats):
    """ MergeRequests commented """

    def fetch(self):
        log.info("Searching for MergeRequests commented by %s", self.user)
        results = self.parent.gitlab.search(
            self.user.login, self.options.since, self.options.until,
            target_type='Note',
            action_name='commented on')
        self.stats = [
            Note(issue, self.parent)
            for issue in results
            if issue['note']['noteable_type'] == 'MergeRequest']


class MergeRequestsClosed(Stats):
    """ Merge requests closed """

    def fetch(self):
        log.info("Searching for Merge requests closed by %s", self.user)
        results = self.parent.gitlab.search(
            self.user.login, self.options.since, self.options.until,
            target_type='MergeRequest',
            action_name='accepted')
        self.stats = [
            MergeRequest(mr, self.parent)
            for mr in results]


class MergeRequestsApproved(Stats):
    """ Merge requests approved """

    def fetch(self):
        log.info("Searching for Merge requests approved by %s", self.user)
        results = self.parent.gitlab.search(
            self.user.login, self.options.since, self.options.until,
            target_type='MergeRequest',
            action_name='approved')
        self.stats = [
            MergeRequest(mr, self.parent)
            for mr in results]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GitLabStats(StatsGroup):
    """ GitLab work """

    # Default order
    order = 380

    def __init__(self, option, name=None, parent=None, user=None):
        StatsGroup.__init__(self, option, name, parent, user)
        config = dict(Config().section(option))
        # Check server url
        try:
            self.url = config["url"]
        except KeyError as exc:
            raise ReportError(f"No GitLab url set in the [{option}] section") from exc
        # Check authorization token
        self.token = get_token(config)
        if self.token is None:
            raise ReportError(f"No GitLab token set in the [{option}] section")
        # Check SSL verification
        try:
            self.ssl_verify = bool(
                strtobool(
                    config.get("ssl_verify", str(GITLAB_SSL_VERIFY))
                    )
                )
        except ValueError as ve:
            raise ReportError(
                f"Invalid ssl_verify option for GitLab in [{option}] section"
                ) from ve
        if not self.ssl_verify:
            urllib3.disable_warnings(InsecureRequestWarning)
        self.gitlab = GitLab(
            self.url,
            self.token,
            self.ssl_verify,
            timeout=float(config.get("timeout", TIMEOUT)))
        # Create the list of stats
        self.stats = [
            IssuesCreated(
                option=f"{option}-issues-created", parent=self,
                name=f"Issues created on {option}"),
            IssuesCommented(
                option=f"{option}-issues-commented", parent=self,
                name=f"Issues commented on {option}"),
            IssuesClosed(
                option=f"{option}-issues-closed", parent=self,
                name=f"Issues closed on {option}"),
            MergeRequestsCreated(
                option=f"{option}-merge-requests-created", parent=self,
                name=f"Merge requests created on {option}"),
            MergeRequestsCommented(
                option=f"{option}-merge-requests-commented", parent=self,
                name=f"Merge requests commented on {option}"),
            MergeRequestsApproved(
                option=f"{option}-merge-requests-approved", parent=self,
                name=f"Merge requests approved on {option}"),
            MergeRequestsClosed(
                option=f"{option}-merge-requests-closed", parent=self,
                name=f"Merge requests closed on {option}"),
            ]
