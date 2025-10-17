"""
Bodhi stats

Config example::

    [bodhi]
    type = bodhi
    url = https://bodhi.fedoraproject.org/
    login = <username>

"""

from argparse import Namespace
from typing import Any, Optional

from bodhi.client.bindings import BodhiClient  # type: ignore[import-untyped]
from bodhi.client.bindings import BodhiClientException

from did.base import Config, ReportError, User
from did.stats import Stats, StatsGroup
from did.utils import listed, log, pretty

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Bodhi():
    """ Bodhi """
    # pylint: disable=too-few-public-methods

    def __init__(self, url: str):
        """ Initialize url """
        self.url = url
        self.client: BodhiClient

    def connect(self) -> None:
        """
        Establish connection to Bodhi and make the client available.
        """
        self.client = BodhiClient(self.url)

    def search(self, query: str) -> list[dict[str, Any]]:
        """ Perform Bodhi query """
        result: list[dict[str, Any]] = []
        current_page: int = 1
        original_query: str = query
        while current_page:
            log.debug("Bodhi query: %s", query)
            try:
                data: Any = self.client.send_request(
                    query, verb='GET')
            except BodhiClientException as e:
                log.debug("Bodhi error: %s", e.errno)
                raise ReportError('Error connecting to Bodhi server') from e
            objects: list[dict[str, Any]] = data['updates']
            log.debug("Result: %s fetched", listed(len(objects), "item"))
            log.data(pretty(data))
            result.extend(objects)
            if current_page < data['pages']:
                current_page = current_page + 1
                query = f"{original_query}&page={current_page}"
            else:
                current_page = 0
        return result


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Update
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Update():
    """ Bodhi update """
    # pylint: disable=too-few-public-methods

    def __init__(self, data: dict[str, Any], output_format: str) -> None:
        self.data = data
        self.format = output_format
        self.title = data['title']
        self.project = data['release']['name']
        self.identifier = data['alias']
        self.created = data['date_submitted']
        self.url = data['url']
        log.details(f'[{self.created}] {self}')

    def __str__(self) -> str:
        """ String representation """
        if self.format == "markdown":
            return f'[{self.identifier}]({self.url}) - {self.title} [{self.project}]'
        return f'{self.identifier} - {self.title} [{self.project}]'


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class UpdatesCreated(Stats):
    """ Updates created """

    def __init__(self, /,
                 option: str,
                 name: Optional[str] = None,
                 parent: Optional["BodhiStats"] = None,
                 user: Optional[User] = None, *,
                 options: Optional[Namespace] = None) -> None:
        self.parent: BodhiStats
        self.user: User
        self.options: Namespace
        super().__init__(option, name, parent, user, options=options)

    def fetch(self) -> None:
        if self.parent.options is None:
            raise RuntimeError("BodhiStats not properly initialized")
        try:
            response: list[dict[str, Any]] = self.parent.bodhi.search(query=(
                f'updates/?user={self.user.login}'
                f'&submitted_before={self.options.until.date}'
                f'&submitted_since={self.options.since.date}'
                ))
        except BodhiClientException as e:
            log.debug("Bodhi error: %s", e.errno)
            raise ReportError('Error connecting to Bodhi server') from e
        self.stats = [
            Update(update, self.parent.options.format)
            for update in response
            ]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class BodhiStats(StatsGroup):
    """ Bodhi work """

    # Default order
    order = 410

    def __init__(self,
                 option: str,
                 name: Optional[str] = None,
                 parent: Optional[StatsGroup] = None,
                 user: Optional[User] = None) -> None:
        StatsGroup.__init__(self, option, name, parent, user)
        config = dict(Config().section(option))
        # Check server url
        self.url = config.get('url')
        if not self.url:
            raise ReportError(f'No Bodhi url set in the [{option}] section')
        self.bodhi = Bodhi(self.url)
        # Create the list of stats
        self.stats = [
            UpdatesCreated(
                option=f'{option}-updates-created', parent=self,
                name=f'Updates created on {option}'),
            ]

    def check(self) -> None:
        """
        Connects to bodhi and check stats
        """
        self.bodhi.connect()
        super().check()
