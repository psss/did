"""
Pagure stats such as created/closed issues and pull requests.

Config example::

    [pagure]
    type = pagure
    url = https://pagure.io/api/0/
    login = <username>
    token = <authentication-token>

Use ``login`` to override the default email address for searching.
See the :doc:`config` documentation for details on using aliases.
The authentication token is optional and can be stored in a file
pointed to by ``token_file`` instead of ``token``.

It's also possible to set a timeout, if not specified it defaults to
60 seconds.

    timeout = 10

"""

import datetime

import requests

from did.base import Config, ReportError, get_token
from did.stats import Stats, StatsGroup
from did.utils import listed, log, pretty

# Default number of seconds waiting on Pagure before giving up
TIMEOUT = 60

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Pagure():
    """ Pagure Investigator """

    def __init__(self, url, token, timeout=TIMEOUT):
        """ Initialize url and headers """
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout
        if token is not None:
            self.headers = {'Authorization': f'token {token}'}
        else:
            self.headers = {}

    def search(self, query, pagination, result_field):
        """ Perform Pagure query """
        result = []
        url = "/".join((self.url, query))
        while url:
            log.debug("Pagure query: %s", url)
            try:
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
                log.data(f"Response headers:\n{response.headers}")
            except requests.RequestException as error:
                log.error(error)
                raise ReportError(f"Pagure search {self.url} failed.") from error
            data = response.json()
            objects = data[result_field]
            log.debug("Result: %s fetched", listed(len(objects), "item"))
            log.data(pretty(data))
            # FIXME later:
            # Work around https://pagure.io/pagure/issue/4057
            if not objects:
                break
            result.extend(objects)
            url = data[pagination]['next']
        return result

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Issue
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Issue():
    """ Pagure Issue or Pull Request """

    def __init__(self, data, options):
        self.options = options
        self.data = data
        self.title = data['title']
        self.project = data['project']['fullname']
        self.identifier = data['id']
        self.created = datetime.datetime.fromtimestamp(
            float(data['date_created'])).date()
        try:
            self.closed = datetime.datetime.fromtimestamp(
                float(data['closed_at'])).date()
        except TypeError:
            self.closed = None
        log.details(f'[{self.created}] {self}')

    def __str__(self):
        """ String representation """
        label = f"{self.project}#{self.identifier}"
        if self.options.format == "markdown":
            return f"[{label}]({self.data["full_url"]}) - {self.title}"
        else:
            return f'{label} - {self.title}'

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class IssuesCreated(Stats):
    """ Issues created """

    def fetch(self):
        log.info('Searching for issues created by %s', self.user)
        issues = [Issue(issue, self.options) for issue in self.parent.pagure.search(
            query=(
                f'user/{self.user.login}/issues?status=all'
                f'&created={self.options.since}..{self.options.until}'),
            pagination='pagination_issues_created',
            result_field='issues_created')]
        self.stats = sorted(issues, key=lambda i: str(i))


class IssuesClosed(Stats):
    """ Issues closed """

    def fetch(self):
        log.info('Searching for issues closed by %s', self.user)
        issues = [Issue(issue, self.options) for issue in self.parent.pagure.search(
            query=(
                f'user/{self.user.login}/issues?status=all'
                f'&author=false&since={self.options.since}'),
            pagination='pagination_issues_assigned',
            result_field='issues_assigned')]
        self.stats = sorted([
            issue for issue in issues
            if issue.closed
            and issue.closed < self.options.until.date
            and issue.closed >= self.options.since.date],
            key=lambda i: str(i))


class PullRequestsCreated(Stats):
    """ Pull requests created """

    def fetch(self):
        log.info('Searching for pull requests created by %s', self.user)
        issues = [Issue(issue, self.options) for issue in self.parent.pagure.search(
            query=(
                f'user/{self.user.login}/requests/filed?'
                f'status=all&created={self.options.since}..{self.options.until}'),
            pagination='pagination',
            result_field='requests')]
        self.stats = sorted(issues, key=lambda i: str(i))

# FIXME: Blocked by https://pagure.io/pagure/issue/4329
# class PullRequestsClosed(Stats):
#    """ Pull requests closed """
#    def fetch(self):
#        log.info(u'Searching for pull requests closed by {0}'.format(
#            self.user))
#        issues = [Issue(issue) for issue in self.parent.pagure.search(
#            query='user/{0}/requests/actionable?'
#                'status=all&closed={1}..{2}'.format(
#                self.user.login, self.options.since,
#                self.options.until),
#            pagination='pagination',
#            result_field='requests')]
#        self.stats = sorted(issues, key=lambda i: unicode(i))

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class PagureStats(StatsGroup):
    """ Pagure work """

    # Default order
    order = 390

    def __init__(self, option, name=None, parent=None, user=None):
        StatsGroup.__init__(self, option, name, parent, user)
        config = dict(Config().section(option))
        # Check server url
        try:
            self.url = config['url']
        except KeyError as key_err:
            raise ReportError(
                f'No Pagure url set in the [{option}] section') from key_err
        # Check authorization token
        self.token = get_token(config)
        self.pagure = Pagure(self.url, self.token, timeout=config.get("timeout"))
        # Create the list of stats
        self.stats = [
            IssuesCreated(
                option=f'{option}-issues-created', parent=self,
                name=f'Issues created on {option}'),
            IssuesClosed(
                option=f'{option}-issues-closed', parent=self,
                name=f'Issues closed on {option}'),
            PullRequestsCreated(
                option=f'{option}-pull-requests-created', parent=self,
                name=f'Pull requests created on {option}'),
            # FIXME: Blocked by https://pagure.io/pagure/issue/4329
            # PullRequestsClosed(
            #     option=f'{option}-pull-requests-closed', parent=self,
            #     name=f'Pull requests closed on {option}'),
            ]
