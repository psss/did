"""
Forgejo stats such as submitted, reviewed or merged changes

Config example::

    [forgejo]
    type = forgejo
    url = https://forge.fedoraproject.org
    token = <authentication-token>
    login = <username>

Use ``login`` to override the default email address for searching.
See the :doc:`config` documentation for details on using aliases.

The authentication token is *not* optional: you can either provide it
directly or store it in a file pointed to by ``token_file``.
Go to https://forge.fedoraproject.org/user/settings/applications and
generate a new token.

It's also possible to set a timeout, if not specified it defaults to
60 seconds.

    timeout = 10

"""
import json
from argparse import Namespace
from http import HTTPStatus
from typing import Any, Optional

import requests
from tenacity import (RetryCallState, RetryError, Retrying,
                      retry_if_exception_type, stop_after_attempt)

from did.base import Config, ReportError, User, get_token
from did.stats import Stats, StatsGroup
from did.utils import log

TIMEOUT = 60.0


class Forgejo():
    """ Forgejo """

    def __init__(self,
                 url: str,
                 user: Optional[User],
                 token: Optional[str],
                 timeout: float = TIMEOUT):
        self.url = f'{url}/api/v1/'
        self.user = user
        self.headers = {'Authorization': f'token {token}'}
        self.timeout = timeout

    def request(self, url: str) -> requests.Response:
        def forgejo_before_sleep(_retry_state: RetryCallState) -> None:
            log.debug("Trying to connect to Forgejo...")
        while True:
            try:
                for attempt in Retrying(
                        stop=stop_after_attempt(3),
                        retry=retry_if_exception_type(
                            requests.exceptions.ConnectionError),
                        before_sleep=forgejo_before_sleep,
                        reraise=True):
                    with attempt:
                        response = requests.get(
                            url, headers=self.headers, timeout=self.timeout
                            )
                log.debug("Response headers:\n%s", response.headers)
            except (requests.exceptions.RequestException, RetryError) as error:
                log.debug(error)
                raise ReportError(f"Forgejo request on {self.url} failed.") from error
            # Check if credentials are valid
            log.debug("Forgejo status code: %s", response.status_code)
            if response.status_code == HTTPStatus.UNAUTHORIZED:
                raise ReportError(
                    "Defined token is not valid. "
                    "Either update it or remove it.")
            # all good!
            break

        return response

    def search(self, query: str) -> list[Any]:
        """
        Perform Forgejo query
        """
        url = f'{self.url}{query}'
        response = self.request(url)
        if not response.ok:
            try:
                error = json.loads(response.text)["errors"][0]["message"]
            except KeyError:
                error = "Unexpected error response structure"
            raise ReportError(
                f"Failed to fetch Forgejo data at '{url}'. "
                f"The reason was '{response.reason}' "
                f"and the error was '{error}'.")
        return list(response.json())


class Issue():
    """ Issue """
    # pylint: disable=too-few-public-methods

    def __init__(self, issue: dict[str, Any], options: Namespace):
        self.options = options
        self.issue = issue
        self.number: int = issue["number"]
        self.url: str = issue["html_url"]
        self.title: str = issue["title"]
        self.repository: str = issue["repository"]["full_name"]

    def __str__(self) -> str:
        """ String representation """
        if self.options.format == "markdown":
            return f"[{self.repository}#{str(self.number)}]({self.url}) - {self.title}"

        return f"{self.repository}#{str(self.number)} - {self.title}"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class ForgejoStats(Stats):
    """ Forgejo Stats """

    def __init__(self,
                 option: str,
                 name: Optional[str] = None,
                 parent: Optional["ForgejoStatsGroup"] = None,
                 user: Optional[User] = None):
        self.parent: ForgejoStatsGroup
        self.user: User
        self.options: Namespace
        super().__init__(option, name, parent, user)

    def fetch(self) -> None:
        raise NotImplementedError("fetch() not implemented")


class IssuesCreated(ForgejoStats):
    """ Issues created """

    def fetch(self) -> None:
        log.info("Searching for issues created on %s by %s", self.option, self.user)
        since = f'{self.options.since}T00:00:00Z'
        until = f'{self.options.until}T23:59:59Z'
        query = (f'repos/issues/search?state=all&type=issues&since={since}'
                 f'&before={until}&created=true')
        self.stats = [
            str(Issue(result, self.options))
            for result in self.parent.forgejo.search(query)]


class PullRequestsCreated(ForgejoStats):
    """ Pull requests created """

    def fetch(self) -> None:
        log.info("Searching for issues created on %s by %s", self.option, self.user)
        since = f'{self.options.since}T00:00:00Z'
        until = f'{self.options.until}T23:59:59Z'
        query = (f'repos/issues/search?state=all&type=pulls&since={since}'
                 f'&before={until}&created=true')
        self.stats = [
            str(Issue(result, self.options))
            for result in self.parent.forgejo.search(query)]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class ForgejoStatsGroup(StatsGroup):
    """ Forgejo work """

    # Default order
    order = 430

    def __init__(self,
                 option: str,
                 name: Optional[str] = None,
                 parent: Optional[StatsGroup] = None,
                 user: Optional[User] = None
                 ) -> None:
        StatsGroup.__init__(self, option, name, parent, user)
        config = dict(Config().section(option))
        # Check server url
        try:
            self.url = config['url']
        except KeyError as key_err:
            raise ReportError(
                f'No Forgejo url set in the [{option}] section') from key_err
        # Check authorization token
        self.token = get_token(config)
        self.forgejo = Forgejo(
            self.url,
            self.user,
            self.token,
            timeout=float(config.get("timeout", TIMEOUT)))
        self.stats = [
            IssuesCreated(
                option=f'{option}-issues-created', parent=self,
                name=f'Issues created on {option}'),
            PullRequestsCreated(
                option=f'{option}-pull-requests-created', parent=self,
                name=f'Pull requests created on {option}'),
            ]
