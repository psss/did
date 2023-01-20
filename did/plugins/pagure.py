# coding: utf-8
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
"""

import datetime

import requests

from did.base import Config, ReportError, get_token
from did.stats import Stats, StatsGroup
from did.utils import listed, log, pretty

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Pagure(object):
    """ Pagure Investigator """

    def __init__(self, url, token):
        """ Initialize url and headers """
        self.url = url.rstrip("/")
        self.token = token
        if token is not None:
            self.headers = {'Authorization': 'token {0}'.format(token)}
        else:
            self.headers = {}

    def search(self, query, pagination, result_field):
        """ Perform Pagure query """
        result = []
        url = "/".join((self.url, query))
        while url:
            log.debug("Pagure query: {0}".format(url))
            try:
                response = requests.get(url, headers=self.headers)
                log.data("Response headers:\n{0}".format(response.headers))
            except requests.RequestException as error:
                log.error(error)
                raise ReportError("Pagure search {0} failed.".format(self.url))
            data = response.json()
            objects = data[result_field]
            log.debug("Result: {0} fetched".format(
                listed(len(objects), "item")))
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


class Issue(object):
    """ Pagure Issue or Pull Request """

    def __init__(self, data):
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
        log.details('[{0}] {1}'.format(self.created, self))

    def __str__(self):
        """ String representation """
        return '{0}#{1} - {2}'.format(
            self.project, self.identifier, self.title)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class IssuesCreated(Stats):
    """ Issues created """

    def fetch(self):
        log.info('Searching for issues created by {0}'.format(self.user))
        issues = [Issue(issue) for issue in self.parent.pagure.search(
            query='user/{0}/issues?assignee=false&created={1}..{2}'.format(
                self.user.login, self.options.since, self.options.until),
            pagination='pagination_issues_created',
            result_field='issues_created')]
        self.stats = sorted(issues, key=lambda i: str(i))


class IssuesClosed(Stats):
    """ Issues closed """

    def fetch(self):
        log.info('Searching for issues closed by {0}'.format(self.user))
        issues = [Issue(issue) for issue in self.parent.pagure.search(
            query='user/{0}/issues?status=all&author=false&since={1}'.format(
                self.user.login, self.options.since),
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
        log.info('Searching for pull requests created by {0}'.format(
            self.user))
        issues = [Issue(issue) for issue in self.parent.pagure.search(
            query='user/{0}/requests/filed?status=all&created={1}..{2}'.format(
                self.user.login, self.options.since, self.options.until),
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
        except KeyError:
            raise ReportError(
                'No Pagure url set in the [{0}] section'.format(option))
        # Check authorization token
        self.token = get_token(config)
        self.pagure = Pagure(self.url, self.token)
        # Create the list of stats
        self.stats = [
            IssuesCreated(
                option=option + '-issues-created', parent=self,
                name='Issues created on {0}'.format(option)),
            IssuesClosed(
                option=option + '-issues-closed', parent=self,
                name='Issues closed on {0}'.format(option)),
            PullRequestsCreated(
                option=option + '-pull-requests-created', parent=self,
                name='Pull requests created on {0}'.format(option)),
            # FIXME: Blocked by https://pagure.io/pagure/issue/4329
            # PullRequestsClosed(
            #     option=option + '-pull-requests-closed', parent=self,
            #     name='Pull requests closed on {0}'.format(option)),
            ]
