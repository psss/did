# coding: utf-8
"""
GitHub stats such as created and closed issues

Config example::

    [github]
    type = github
    url = https://api.github.com/
    token = <authentication-token>
    login = <username>

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

import requests

from did.base import Config, ReportError, get_token
from did.stats import Stats, StatsGroup
from did.utils import listed, log, pretty

# Identifier padding
PADDING = 3

# Number of issues to be fetched per page
PER_PAGE = 100


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
        result = []
        url = self.url + "/" + query + f"&per_page={PER_PAGE}"

        while True:
            # Fetch the query
            log.debug(f"GitHub query: {url}")
            try:
                response = requests.get(url, headers=self.headers)
                log.debug(f"Response headers:\n{response.headers}")
            except requests.exceptions.RequestException as error:
                log.debug(error)
                raise ReportError(f"GitHub search on {self.url} failed.")

            # Check if credentials are valid
            log.debug(f"GitHub status code: {response.status_code}")
            if response.status_code == 401:
                raise ReportError(
                    "Defined token is not valid. "
                    "Either update it or remove it.")

            # Parse fetched json data
            try:
                data = json.loads(response.text)["items"]
                result.extend(data)
            except KeyError:
                if json.loads(response.text)["message"].startswith(
                        "API rate limit exceeded"):
                    raise ReportError(
                        "GitHub API rate limit exceeded. "
                        "Consider creating an access token.")
            except requests.exceptions.JSONDecodeError as error:
                log.debug(error)
                raise ReportError(f"GitHub JSON failed: {response.text}.")

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

    def __init__(self, data):
        self.data = data
        self.title = data["title"]
        matched = re.search(
            r"/repos/([^/]+)/([^/]+)/issues/(\d+)", data["url"])
        self.owner = matched.groups()[0]
        self.project = matched.groups()[1]
        self.id = matched.groups()[2]

    def __str__(self):
        """ String representation """
        return "{0}/{1}#{2} - {3}".format(
            self.owner, self.project,
            str(self.id).zfill(PADDING), self.data["title"])


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class IssuesCreated(Stats):
    """ Issues created """

    def fetch(self):
        log.info("Searching for issues created by {0}".format(self.user))
        query = "search/issues?q=author:{0}+created:{1}..{2}".format(
            self.user.login, self.options.since, self.options.until)
        query += "+type:issue"
        self.stats = [
            Issue(issue) for issue in self.parent.github.search(query)]


class IssuesClosed(Stats):
    """ Issues closed """

    def fetch(self):
        log.info("Searching for issues closed by {0}".format(self.user))
        query = "search/issues?q=assignee:{0}+closed:{1}..{2}".format(
            self.user.login, self.options.since, self.options.until)
        query += "+type:issue"
        self.stats = [
            Issue(issue) for issue in self.parent.github.search(query)]


class IssueCommented(Stats):
    """ Issues commented """

    def fetch(self):
        log.info("Searching for issues commented on by {0}".format(self.user))
        query = "search/issues?q=commenter:{0}+updated:{1}..{2}".format(
            self.user.login, self.options.since, self.options.until)
        query += "+type:issue"
        self.stats = [
            Issue(issue) for issue in self.parent.github.search(query)]


class PullRequestsCreated(Stats):
    """ Pull requests created """

    def fetch(self):
        log.info("Searching for pull requests created by {0}".format(
            self.user))
        query = "search/issues?q=author:{0}+created:{1}..{2}".format(
            self.user.login, self.options.since, self.options.until)
        query += "+type:pr"
        self.stats = [
            Issue(issue) for issue in self.parent.github.search(query)]


class PullRequestsCommented(Stats):
    """ Pull requests commented """

    def fetch(self):
        log.info("Searching for pull requests commented on by {0}".format(
            self.user))
        query = "search/issues?q=commenter:{0}+updated:{1}..{2}".format(
            self.user.login, self.options.since, self.options.until)
        query += "+type:pr"
        self.stats = [
            Issue(issue) for issue in self.parent.github.search(query)]


class PullRequestsClosed(Stats):
    """ Pull requests closed """

    def fetch(self):
        log.info("Searching for pull requests closed by {0}".format(
            self.user))
        query = "search/issues?q=assignee:{0}+closed:{1}..{2}".format(
            self.user.login, self.options.since, self.options.until)
        query += "+type:pr"
        self.stats = [
            Issue(issue) for issue in self.parent.github.search(query)]


class PullRequestsReviewed(Stats):
    """ Pull requests reviewed """

    def fetch(self):
        log.info("Searching for pull requests reviewed by {0}".format(
            self.user))
        query = "search/issues?q=reviewed-by:{0}+closed:{1}..{2}".format(
            self.user.login, self.options.since, self.options.until)
        query += "+type:pr"
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
        self.github = GitHub(self.url, self.token)
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
