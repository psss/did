# coding: utf-8
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

__ https://docs.gitlab.com/ce/api/

"""

import distutils.util

import dateutil
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from did.base import Config, ReportError, get_token
from did.stats import Stats, StatsGroup
from did.utils import listed, log, pretty

GITLAB_SSL_VERIFY = True
GITLAB_API = 4

# Identifier padding
PADDING = 3


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GitLab(object):
    """ GitLab Investigator """

    def __init__(self, url, token, ssl_verify=GITLAB_SSL_VERIFY):
        """ Initialize url and headers """
        self.url = url.rstrip("/")
        self.headers = {'PRIVATE-TOKEN': token}
        self.token = token
        self.ssl_verify = ssl_verify
        self.user = None
        self.events = None
        self.projects = {}
        self.project_mrs = {}
        self.project_issues = {}

    def _get_gitlab_api_raw(self, url):
        return requests.get(url, headers=self.headers, verify=self.ssl_verify)

    def _get_gitlab_api(self, endpoint):
        url = '{0}/api/v{1}/{2}'.format(self.url, GITLAB_API, endpoint)
        return self._get_gitlab_api_raw(url)

    def _get_gitlab_api_json(self, endpoint):
        log.debug("Query: {0}".format(endpoint))
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
        query = 'users?username={0}'.format(username)
        result = self._get_gitlab_api_json(query)
        try:
            return result[0]
        except IndexError:
            raise ReportError(
                "Unable to find user '{0}' on GitLab.".format(username))

    def get_project(self, project_id):
        if project_id not in self.projects:
            query = 'projects/{0}'.format(project_id)
            self.projects[project_id] = self._get_gitlab_api_json(query)
        return self.projects[project_id]

    def get_project_mr(self, project_id, mr_id):
        mrs = self.get_project_mrs(project_id)
        mr = next(filter(lambda x: x['id'] == mr_id, mrs))
        return mr

    def get_project_mrs(self, project_id):
        if project_id not in self.project_mrs:
            query = 'projects/{0}/merge_requests'.format(project_id)
            self.project_mrs[project_id] = self._get_gitlab_api_list(
                query, get_all_results=True)
        return self.project_mrs[project_id]

    def get_project_issue(self, project_id, issue_id):
        issues = self.get_project_issues(project_id)
        issue = next(filter(lambda x: x['id'] == issue_id, issues))
        return issue

    def get_project_issues(self, project_id):
        if project_id not in self.project_issues:
            query = 'projects/{0}/issues'.format(project_id)
            self.project_issues[project_id] = self._get_gitlab_api_list(
                query, get_all_results=True)
        return self.project_issues[project_id]

    def user_events(self, user_id, since, until):
        if GITLAB_API >= 4:
            query = 'users/{0}/events?after={1}&before={2}'.format(
                user_id, since - 1, until)
            return self._get_gitlab_api_list(query, since, True)
        else:
            return []

    def search(self, user, since, until, target_type, action_name):
        """ Perform GitLab query """
        if not self.user:
            self.user = self.get_user(user)
        if not self.events:
            self.events = self.user_events(self.user['id'], since, until)
        result = []
        for event in self.events:
            created_at = dateutil.parser.parse(event['created_at']).date()
            if (event['target_type'] == target_type and
                    event['action_name'] == action_name and
                    since.date <= created_at and until.date >= created_at):
                result.append(event)
        log.debug("Result: {0} fetched".format(listed(len(result), "item")))
        return result


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Issue
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Issue(object):
    """ GitLab Issue """

    def __init__(self, data, gitlabapi):
        self.data = data
        self.gitlabapi = gitlabapi
        self.project = self.gitlabapi.get_project(data['project_id'])
        self.id = self.iid()
        self.title = data['target_title']

    def iid(self):
        return self.gitlabapi.get_project_issue(
            self.data['project_id'], self.data['target_id'])['iid']

    def __str__(self):
        """ String representation """
        return "{0}#{1} - {2}".format(
            self.project['path_with_namespace'],
            str(self.id).zfill(PADDING), self.title)


class MergeRequest(Issue):

    def iid(self):
        return self.gitlabapi.get_project_mr(
            self.data['project_id'], self.data['target_id'])['iid']


class Note(Issue):

    def iid(self):
        if self.data['note']['noteable_type'] == 'Issue':
            return self.gitlabapi.get_project_issue(
                self.data['project_id'],
                self.data['note']['noteable_id'])['iid']
        elif self.data['note']['noteable_type'] == 'MergeRequest':
            return self.gitlabapi.get_project_mr(
                self.data['project_id'],
                self.data['note']['noteable_id'])['iid']
        else:
            return "unknown"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class IssuesCreated(Stats):
    """ Issue created """

    def fetch(self):
        log.info("Searching for Issues created by {0}".format(
            self.user))
        results = self.parent.gitlab.search(
            self.user.login, self.options.since, self.options.until,
            'Issue', 'opened')
        self.stats = [
            Issue(issue, self.parent.gitlab)
            for issue in results]


class IssuesCommented(Stats):
    """ Issue commented """

    def fetch(self):
        log.info("Searching for Issues commented by {0}".format(
            self.user))
        results = self.parent.gitlab.search(
            self.user.login, self.options.since, self.options.until,
            'Note', 'commented on')
        self.stats = [
            Note(issue, self.parent.gitlab)
            for issue in results
            if issue['note']['noteable_type'] == 'Issue']


class IssuesClosed(Stats):
    """ Issue closed """

    def fetch(self):
        log.info("Searching for Issues closed by {0}".format(
            self.user))
        results = self.parent.gitlab.search(
            self.user.login, self.options.since, self.options.until,
            'Issue', 'closed')
        self.stats = [
            Issue(issue, self.parent.gitlab)
            for issue in results]


class MergeRequestsCreated(Stats):
    """ Merge requests created """

    def fetch(self):
        log.info("Searching for Merge requests created by {0}".format(
            self.user))
        results = self.parent.gitlab.search(
            self.user.login, self.options.since, self.options.until,
            'MergeRequest', 'opened')
        self.stats = [
            MergeRequest(mr, self.parent.gitlab)
            for mr in results]


class MergeRequestsCommented(Stats):
    """ MergeRequests commented """

    def fetch(self):
        log.info("Searching for MergeRequests commented by {0}".format(
            self.user))
        results = self.parent.gitlab.search(
            self.user.login, self.options.since, self.options.until,
            'Note', 'commented on')
        self.stats = [
            Note(issue, self.parent.gitlab)
            for issue in results
            if issue['note']['noteable_type'] == 'MergeRequest']


class MergeRequestsClosed(Stats):
    """ Merge requests closed """

    def fetch(self):
        log.info("Searching for Merge requests closed by {0}".format(
            self.user))
        results = self.parent.gitlab.search(
            self.user.login, self.options.since, self.options.until,
            'MergeRequest', 'accepted')
        self.stats = [
            MergeRequest(mr, self.parent.gitlab)
            for mr in results]


class MergeRequestsApproved(Stats):
    """ Merge requests approved """

    def fetch(self):
        log.info("Searching for Merge requests approved by {0}".format(
            self.user))
        results = self.parent.gitlab.search(
            self.user.login, self.options.since, self.options.until,
            'MergeRequest', 'approved')
        self.stats = [
            MergeRequest(mr, self.parent.gitlab)
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
        except KeyError:
            raise ReportError(
                "No GitLab url set in the [{0}] section".format(option))
        # Check authorization token
        self.token = get_token(config)
        if self.token is None:
            raise ReportError(
                "No GitLab token set in the [{0}] section".format(option))
        # Check SSL verification
        try:
            self.ssl_verify = bool(distutils.util.strtobool(
                config["ssl_verify"]))
        except KeyError:
            self.ssl_verify = GITLAB_SSL_VERIFY
        if not self.ssl_verify:
            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        self.gitlab = GitLab(self.url, self.token, self.ssl_verify)
        # Create the list of stats
        self.stats = [
            IssuesCreated(
                option=option + "-issues-created", parent=self,
                name="Issues created on {0}".format(option)),
            IssuesCommented(
                option=option + "-issues-commented", parent=self,
                name="Issues commented on {0}".format(option)),
            IssuesClosed(
                option=option + "-issues-closed", parent=self,
                name="Issues closed on {0}".format(option)),
            MergeRequestsCreated(
                option=option + "-merge-requests-created", parent=self,
                name="Merge requests created on {0}".format(option)),
            MergeRequestsCommented(
                option=option + "-merge-requests-commented", parent=self,
                name="Issues commented on {0}".format(option)),
            MergeRequestsApproved(
                option=option + "-merge-requests-approved", parent=self,
                name="Merge requests approved on {0}".format(option)),
            MergeRequestsClosed(
                option=option + "-merge-requests-closed", parent=self,
                name="Merge requests closed on {0}".format(option)),
            ]
