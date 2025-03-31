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
    # pylint: disable=too-few-public-methods

    def __init__(self, url, token, timeout=TIMEOUT):
        """ Initialize url and headers """
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout
        if token is not None:
            self.headers = {'Authorization': f'token {token}'}
        else:
            self.headers = {}

    def get_activities(self,
                       username: str,
                       date: str,
                       grouped: bool = False) -> list:
        """
        Get activities for days in requested range

        :param username: (mandatory) the username of the user
                         whose activity you are interested in.
        :type username:	str
        :param date: (mandatory) the date of interest in ISO
                     format: YYYY-MM-DD
        :type date: str
        :param grouped: (optional) whether or not to group the commits.
                        Default to False.
        :type grouped: bool
        :returns: a list with activities done on the given date.
                  Sample response:

                  .. code-block:: python

                    [
                        {
                            "date": "<iso date>",
                            "date_created": "<timestamp>",
                            "description_mk": "<some markdown text>",
                            "id": <action id>,
                            "ref_id": "<ref id>",
                            "type": "commented",
                            "user": {
                                "full_url": "<pagure url>/user/<user>",
                                "fullname": "<user full name>",
                                "name": "<user>",
                                "url_path": "user/<user>"
                            }
                        }
                    ]


        """
        query = f"{self.url}/user/{username}/activity/{date}"
        if grouped:
            query = f"{query}?grouped=true"
        log.debug("Pagure get_activities query: %s", query)
        try:
            response = requests.get(query, headers=self.headers, timeout=self.timeout)
            log.data(f"Response headers:\n{response.headers}")
        except (requests.Timeout, requests.RequestException) as error:
            log.error(error)
            raise ReportError(
                f"Pagure get_activities {self.url} failed with error:{error}."
                ) from error
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as error:
            log.debug(error)
            raise ReportError(f"Pagure JSON failed: {response.text}.") from error
        return data.get("activities", [])

    def search(self, query, pagination, result_field):
        """ Perform Pagure query """
        result = []
        url = "/".join((self.url, query))
        while url:
            log.debug("Pagure query: %s", url)
            try:
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
                log.data(f"Response headers:\n{response.headers}")
            except (requests.Timeout, requests.RequestException) as error:
                log.error(error)
                raise ReportError(
                    f"Pagure search {self.url} failed with error {error}."
                    ) from error
            try:
                data = response.json()
            except requests.JSONDecodeError as error:
                log.error(error)
                raise ReportError(
                    f"Pagure invalid response from search {self.url} failed."
                    ) from error

            objects = data[result_field]
            log.debug("Result: %s fetched", listed(len(objects), "item"))
            log.data(pretty(data))
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
    # pylint: disable=too-few-public-methods

    def __init__(self, data: dict, options):
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
        try:
            self.closed_by = data["closed_by"]["name"]
        except TypeError:
            self.closed_by = None

        log.details(f'[{self.created}] {self}')

    def __str__(self):
        """ String representation """
        label = f"{self.project}#{self.identifier}"
        if self.options.format == "markdown":
            return f'[{label}]({self.data["full_url"]}) - {self.title}'
        # plain text
        return f'{label} - {self.title}'


class Comment():
    """ Pagure comment activity """
    # pylint: disable=too-few-public-methods

    def __init__(self, data, options, url):
        self.options = options
        self.date = data["date"]
        self.text = data["description_mk"].replace(
            'href="',
            f'href="{url.replace("/api/0", "")}').replace(
            '<div class="markdown"><p>',
            '').replace(
            '</p></div>',
            '')

    def __str__(self):
        """ String representation """
        return f'{self.date} - {self.text}'

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
        self.stats = sorted(issues, key=str)


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
            key=str)


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
        self.stats = sorted(issues, key=str)


class Commented(Stats):
    """ Commented """

    def fetch(self):
        log.info('Searching for comments by %s', self.user)
        log.debug('Search activity stats for %s', self.user)
        requested_range = [
            self.options.since.date + datetime.timedelta(days=x)
            for x in range((self.options.until.date - self.options.since.date).days)
            ]
        activity_stats = []
        for current_date in requested_range:
            activity_stats += self.parent.pagure.get_activities(
                self.user.login, current_date)
        for activity in activity_stats:
            if activity["type"] != "commented":
                continue

        self.stats = sorted([
            Comment(activity, self.options, self.parent.pagure.url)
            for activity in activity_stats
            if activity["type"] == "commented"
            ], key=str)


class PullRequestsClosed(Stats):
    """
    Pull requests closed.
    Results may be incomplete due to unfixed issue
    https://pagure.io/pagure/issue/4329.
    """

    def fetch(self):
        log.info('Searching for pull requests closed by %s', self.user)
        issues = [Issue(issue, self.options) for issue in self.parent.pagure.search(
            query=(f'user/{self.user.login}/requests/actionable?'
                  f'status=all&closed={self.options.since}..{self.options.until}'),
            pagination='pagination',
            result_field='requests')
            ]
        self.stats = sorted(
            [stat for stat in issues if stat.closed_by == self.user.login],
            key=str
            )

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
        self.pagure = Pagure(
            self.url,
            self.token,
            timeout=config.get(
                "timeout",
                TIMEOUT))
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
            Commented(
                option=f'{option}-commented', parent=self,
                name=f'Pull requests commented on {option}'),
            PullRequestsClosed(
                option=f'{option}-pull-requests-closed', parent=self,
                name=f'Pull requests closed on {option}'),
            ]
