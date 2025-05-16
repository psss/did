"""
GitHub stats such as created and closed issues

Config example::

    [github]
    type = github
    url = https://api.github.com/
    token = <authentication-token>
    login = <username>

Optionally the search query can be limited to repositories owned
by the given user or organization. You can also use the full name
of the project to only search in the given repository::

    user = <repository-owner>
    org = <organization-name>
    repo = <full-project-name>

Multiple users, organization or repositories can be searched as
well. Use ``,`` as the separator, for example::

    org = one,two,three

The authentication token is optional. However, unauthenticated
queries are limited. For more details see `GitHub API`__ docs.
Use ``login`` to override the default email address for searching.
See the :doc:`config` documentation for details on using aliases.

Alternatively to ``token`` you can use ``token_file`` to have the
token stored in a file rather than in your did config file.

__ https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token

"""  # noqa: W505,E501

import json
import re
import time

import requests

from did.base import Config, Date, ReportError, get_token
from did.stats import Stats, StatsGroup
from did.utils import listed, log, pretty

# Identifier padding
PADDING = 3

# Number of GH items to be fetched per page
PER_PAGE = 100


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GitHub(object):
    """ GitHub Investigator """

    def __init__(self, url, token=None, user=None, org=None, repo=None):
        """ Initialize url and headers """
        self.url = url.rstrip("/")
        if token is not None:
            self.headers = {'Authorization': 'token {0}'.format(token)}
        else:
            self.headers = {}

        # Prepare the org, user, repo filter
        def condition(key: str, names: str) -> list[str]:
            """ Prepare one or more conditions for given key & names """
            if not names:
                return []
            return [f"+{key}:{name}" for name in re.split(r"\s*,\s*", names)]

        self.filter = "".join(
            condition("user", user) +
            condition("org", org) +
            condition("repo", repo))

    @staticmethod
    def until(until):
        """Issue #362: until for GH should have - delta(day=1)"""
        return until - 1

    @staticmethod
    def request_data(url, headers):
        """Fetch the URL from GitHub API and deserialize it to JSON"""
        log.debug(f"GitHub URL: {url}")
        try:
            response = requests.get(url, headers=headers)
            log.debug(f"Response headers:\n{response.headers}")
        except requests.exceptions.RequestException as error:
            log.debug(error)
            raise ReportError(f"GitHub failed to request URL {url}.")

        # Check if credentials are valid
        log.debug(f"GitHub status code: {response.status_code}")
        if response.status_code == 401:
            raise ReportError(
                "Defined token is not valid. Either update it or remove it."
            )

        # Handle the exceeded rate limit
        if response.status_code in [403, 429]:
            if response.headers.get("X-RateLimit-Remaining") == "0":
                reset_time = int(response.headers["X-RateLimit-Reset"])
                sleep_time = int(max(reset_time - time.time(), 0)) + 1
                log.warning("GitHub rate limit exceeded, use token to speed up.")
                log.warning(f"Sleeping now for {listed(sleep_time, 'second')}.")
                time.sleep(sleep_time)
                # recursive retry
                return GitHub.request_data(url, headers)
            raise ReportError(f"GitHub query failed: {response.text}")

        # Parse fetched json data
        try:
            data = json.loads(response.text)
        except requests.exceptions.JSONDecodeError as error:
            log.debug(error)
            raise ReportError(f"GitHub JSON failed: {response.text}.") from error

        return data, response

    def has_comments(self, issue_data, user, since, until):
        url = issue_data["comments_url"]
        if not url:
            return False

        url = f"{url}?per_page={PER_PAGE}&sort=created&since={since}"

        while True:
            comments, response = self.request_data(url, self.headers)
            for comment in comments:
                date = Date(comment["created_at"].split("T", 1)[0])
                if date.date > until:
                    return False
                if user == comment["user"]["login"]:
                    return True
            # Update url to the next page, break if no next page
            # provided
            if "next" in response.links:
                url = response.links["next"]["url"]
            else:
                break
        return False

    def search(self, query):
        """ Perform GitHub query """
        result = []
        url = self.url + "/" + query + self.filter + f"&per_page={PER_PAGE}"

        while True:
            data, response = self.request_data(url, self.headers)
            result.extend(data["items"])
            # Update url to the next page, break if no next page
            # provided
            if 'next' in response.links:
                url = response.links['next']['url']
            else:
                break

        log.debug("Result: {0} fetched".format(listed(len(result), "item")))
        log.data(pretty(result))
        return result


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Issue
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Issue(object):
    """ GitHub Issue """

    def __init__(self, data, parent):
        self.data = data
        self.title = data["title"]
        matched = re.search(
            r"/repos/([^/]+)/([^/]+)/issues/(\d+)", data["url"])
        self.owner = matched.groups()[0]
        self.project = matched.groups()[1]
        self.id = matched.groups()[2]
        self.options = parent.options

    def __str__(self):
        """ String representation """
        if self.options.format == "markdown":
            return "[{0}/{1}#{2}]({3}) - {4}".format(
                self.owner, self.project,
                str(self.id), self.data["html_url"], self.data["title"].strip())
        else:
            return "{0}/{1}#{2} - {3}".format(
                self.owner, self.project,
                str(self.id).zfill(PADDING), self.data["title"])

    def __eq__(self, other):
        """ Equality comparison """
        if isinstance(other, Issue):
            return (
                self.owner == other.owner
                and self.project == other.project
                and self.id == other.id)
        return False

    def __hash__(self):
        """ Hash function """
        return hash((self.owner, self.project, self.id))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class IssuesCreated(Stats):
    """ Issues created """

    def fetch(self):
        log.info("Searching for issues created by {0}".format(self.user))
        user = self.user.login
        since = self.options.since
        until = GitHub.until(self.options.until)
        query = "search/issues?q=author:{0}+created:{1}..{2}".format(
            user, since, until)
        query += "+type:issue"
        self.stats = [
            Issue(issue, self.parent) for issue in self.parent.github.search(query)]


class IssuesClosed(Stats):
    """ Issues closed """

    def fetch(self):
        log.info("Searching for issues closed by {0}".format(self.user))
        user = self.user.login
        since = self.options.since
        until = GitHub.until(self.options.until)
        query = "search/issues?q=assignee:{0}+closed:{1}..{2}".format(
            user, since, until)
        query += "+type:issue"
        self.stats = [
            Issue(issue, self.parent) for issue in self.parent.github.search(query)]


class IssueCommented(Stats):
    """ Issues commented """

    def fetch(self):
        log.info("Searching for issues commented on by {0}".format(self.user))
        user = self.user.login
        since = self.options.since
        until = GitHub.until(self.options.until)
        query = "search/issues?q=commenter:{0}+updated:{1}..{2}".format(
            user, since, until)
        query += "+type:issue"
        approx = getattr(
            self.options, f"{self.parent.option}_approximate_commented", False)
        self.stats = [
            Issue(issue, self.parent)
            for issue in self.parent.github.search(query)
            # Additional filter for the comments by user in the interval
            if approx or self.parent.github.has_comments(issue, user, since, until)
        ]


class PullRequestsCreated(Stats):
    """ Pull requests created """

    def fetch(self):
        log.info("Searching for pull requests created by {0}".format(
            self.user))
        user = self.user.login
        since = self.options.since
        until = GitHub.until(self.options.until)
        query = "search/issues?q=author:{0}+created:{1}..{2}".format(
            user, since, until)
        query += "+type:pr"
        self.stats = [
            Issue(issue, self.parent) for issue in self.parent.github.search(query)]


class PullRequestsCommented(Stats):
    """ Pull requests commented """

    def fetch(self):
        log.info("Searching for pull requests commented on by {0}".format(
            self.user))
        user = self.user.login
        since = self.options.since
        until = GitHub.until(self.options.until)
        query = "search/issues?q=commenter:{0}+updated:{1}..{2}".format(
            user, since, until)
        query += "+type:pr"
        approx = getattr(
            self.options, f"{self.parent.option}_approximate_commented", False)
        self.stats = [
            Issue(issue, self.parent)
            for issue in self.parent.github.search(query)
            # Additional filter for the comments by user in the interval
            if approx or self.parent.github.has_comments(issue, user, since, until)
        ]


class PullRequestsClosed(Stats):
    """ Pull requests closed """

    def fetch(self):
        log.info("Searching for pull requests closed by {0}".format(
            self.user))
        user = self.user.login
        since = self.options.since
        until = GitHub.until(self.options.until)
        query = "search/issues?q=assignee:{0}+closed:{1}..{2}".format(
            user, since, until)
        query += "+type:pr"
        self.stats = [
            Issue(issue, self.parent) for issue in self.parent.github.search(query)]


class PullRequestsReviewed(Stats):
    """ Pull requests reviewed """

    def fetch(self):
        log.info("Searching for pull requests reviewed by {0}".format(
            self.user))
        user = self.user.login
        since = self.options.since
        until = GitHub.until(self.options.until)
        query = "search/issues?q=reviewed-by:{0}+-author:{0}+closed:{1}..{2}".format(
            user, since, until)
        query += "+type:pr"
        self.stats = [
            Issue(issue, self.parent) for issue in self.parent.github.search(query)]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GitHubStats(StatsGroup):
    """ GitHub work """

    # Default order
    order = 330

    def __init__(self, option, name=None, parent=None, user=None):
        StatsGroup.__init__(self, option, name, parent, user)
        config = dict(Config().section(option))

        # Check server url
        try:
            self.url = config["url"]
        except KeyError:
            raise ReportError(
                "No github url set in the [{0}] section".format(option))

        # Check authorization token
        self.token = get_token(config)
        self.github = GitHub(
            url=self.url,
            token=self.token,
            org=config.get("org"),
            user=config.get("user"),
            repo=config.get("repo"))

        self.github = GitHub(self.url, self.token)
        self.add_argument(
            f"--{option}-approximate-commented", action="store_true",
            help="If set, the filter to check if the user actually commented issues or "
            "pull requests is not applied. It is recommended for long reports")
        # Create the list of stats
        self.stats = [
            IssuesCreated(
                option=option + "-issues-created", parent=self,
                name="Issues created on {0}".format(option)),
            IssueCommented(
                option=option + "-issues-commented", parent=self,
                name="Issues commented on {0}".format(option)),
            IssuesClosed(
                option=option + "-issues-closed", parent=self,
                name="Issues closed on {0}".format(option)),
            PullRequestsCreated(
                option=option + "-pull-requests-created", parent=self,
                name="Pull requests created on {0}".format(option)),
            PullRequestsCommented(
                option=option + "-pull-requests-commented", parent=self,
                name="Pull requests commented on {0}".format(option)),
            PullRequestsClosed(
                option=option + "-pull-requests-closed", parent=self,
                name="Pull requests closed on {0}".format(option)),
            PullRequestsReviewed(
                option=option + "-pull-requests-reviewed", parent=self,
                name="Pull requests reviewed on {0}".format(option)),
            ]
