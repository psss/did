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


It's also possible to set a timeout, if not specified it defaults to 60 seconds.

    timeout = 10

"""  # noqa: W505,E501

import json
import re
import time

import requests

from did.base import Config, ReportError, get_token
from did.stats import Stats, StatsGroup
from did.utils import listed, log, pretty

# Identifier padding
PADDING = 3

# Number of issues to be fetched per page
PER_PAGE = 100

# Default number of seconds waiting on GitHub before giving up
TIMEOUT = 60


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GitHub():
    """ GitHub Investigator """

    def __init__(self, url, token=None, user=None,
                 org=None, repo=None, timeout=TIMEOUT):
        """ Initialize url and headers """
        self.url = url.rstrip("/")
        self.timeout = timeout
        if token is not None:
            self.headers = {'Authorization': f'token {token}'}
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

    def search(self, query):
        """ Perform GitHub query """
        result = []
        url = f"{self.url}/{query}{self.filter}&per_page={PER_PAGE}"

        while True:
            # Fetch the query
            log.debug("GitHub query: %s", url)
            try:
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
                log.debug("Response headers:\n%s", response.headers)
            except requests.exceptions.RequestException as error:
                log.debug(error)
                raise ReportError(f"GitHub search on {self.url} failed.") from error

            # Check if credentials are valid
            log.debug("GitHub status code: %s", response.status_code)
            if response.status_code == 401:
                raise ReportError(
                    "Defined token is not valid. "
                    "Either update it or remove it.")

            # Handle the exceeded rate limit
            if response.status_code in [403, 429]:
                if response.headers.get("X-RateLimit-Remaining") == "0":
                    reset_time = int(response.headers["X-RateLimit-Reset"])
                    sleep_time = int(max(reset_time - time.time(), 0)) + 1
                    log.warning("GitHub rate limit exceeded, use token to speed up.")
                    log.warning("Sleeping now for %s.", listed(sleep_time, 'second'))
                    time.sleep(sleep_time)
                    continue
                raise ReportError(f"GitHub query failed: {response.text}")

            # Parse fetched json data
            try:
                data = json.loads(response.text)["items"]
                result.extend(data)
            except requests.exceptions.JSONDecodeError as error:
                log.debug(error)
                raise ReportError(f"GitHub JSON failed: {response.text}.") from error

            # Update url to the next page, break if no next page
            # provided
            if 'next' in response.links:
                url = response.links['next']['url']
            else:
                break

        log.debug("Result: %s fetched", listed(len(result), "item"))
        log.data(pretty(result))
        return result


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Issue
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Issue():
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
        label = f"{self.owner}/{self.project}#{str(self.id).zfill(PADDING)}"
        if self.options.format == "markdown":
            return f"[{label}]({self.data["html_url"]}) - {self.data["title"].strip()}"
        else:
            return f"{label} - {self.data["title"]}"

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
        log.info("Searching for issues created by %s", self.user)
        query = (
            f"search/issues?q=author:{self.user.login}"
            f"+created:{self.options.since}..{self.options.until}"
            "+type:issue"
            )
        self.stats = [
            Issue(issue, self.parent) for issue in self.parent.github.search(query)]


class IssuesClosed(Stats):
    """ Issues closed """

    def fetch(self):
        log.info("Searching for issues closed by %s", self.user)
        query = (
            f"search/issues?q=assignee:{self.user.login}"
            f"+closed:{self.options.since}..{self.options.until}"
            "+type:issue"
            )
        self.stats = [
            Issue(issue, self.parent) for issue in self.parent.github.search(query)]


class IssueCommented(Stats):
    """ Issues commented """

    def fetch(self):
        log.info("Searching for issues commented on by %s", self.user)
        query = (
            f"search/issues?q=commenter:{self.user.login}"
            f"+updated:{self.options.since}..{self.options.until}"
            "+type:issue"
            )
        self.stats = [
            Issue(issue, self.parent) for issue in self.parent.github.search(query)]


class PullRequestsCreated(Stats):
    """ Pull requests created """

    def fetch(self):
        log.info("Searching for pull requests created by %s", self.user)
        query = (
            f"search/issues?q=author:{self.user.login}"
            f"+created:{self.options.since}..{self.options.until}"
            "+type:pr"
            )
        self.stats = [
            Issue(issue, self.parent) for issue in self.parent.github.search(query)]


class PullRequestsCommented(Stats):
    """ Pull requests commented """

    def fetch(self):
        log.info("Searching for pull requests commented on by %s", self.user)
        query = (
            f"search/issues?q=commenter:{self.user.login}"
            f"+updated:{self.options.since}..{self.options.until}"
            "+type:pr"
            )
        self.stats = [
            Issue(issue, self.parent) for issue in self.parent.github.search(query)]


class PullRequestsClosed(Stats):
    """ Pull requests closed """

    def fetch(self):
        log.info("Searching for pull requests closed by %s", self.user)
        query = (
            f"search/issues?q=assignee:{self.user.login}"
            f"+closed:{self.options.since}..{self.options.until}"
            "+type:pr"
            )
        self.stats = [
            Issue(issue, self.parent) for issue in self.parent.github.search(query)]


class PullRequestsReviewed(Stats):
    """ Pull requests reviewed """

    def fetch(self):
        log.info("Searching for pull requests reviewed by %s", self.user)
        query = (
            f"search/issues?q=reviewed-by:{self.user.login}"
            f"+-author:{self.user.login}"
            f"+closed:{self.options.since}..{self.options.until}"
            "+type:pr"
            )
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
        except KeyError as keyerr:
            raise ReportError(
                f"No github url set in the [{option}] section") from keyerr

        # Check authorization token
        self.token = get_token(config)
        self.github = GitHub(
            url=self.url,
            token=self.token,
            org=config.get("org"),
            user=config.get("user"),
            repo=config.get("repo"),
            timeout=config.get("timeout"))

        # Create the list of stats
        self.stats = [
            IssuesCreated(
                option=f"{option}-issues-created", parent=self,
                name=f"Issues created on {option}"),
            IssueCommented(
                option=f"{option}-issues-commented", parent=self,
                name=f"Issues commented on {option}"),
            IssuesClosed(
                option=f"{option}-issues-closed", parent=self,
                name=f"Issues closed on {option}"),
            PullRequestsCreated(
                option=f"{option}-pull-requests-created", parent=self,
                name=f"Pull requests created on {option}"),
            PullRequestsCommented(
                option=f"{option}-pull-requests-commented", parent=self,
                name=f"Pull requests commented on {option}"),
            PullRequestsClosed(
                option=f"{option}-pull-requests-closed", parent=self,
                name=f"Pull requests closed on {option}"),
            PullRequestsReviewed(
                option=f"{option}-pull-requests-reviewed", parent=self,
                name=f"Pull requests reviewed on {option}"),
            ]
