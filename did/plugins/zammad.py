"""
Zammad stats such as updated tickets

Config example::

    [zammad]
    type = zammad
    url = https://zammad.example.com/api/v1/
    token = <authentication-token>

Optionally use ``token_file`` to store the token in a file instead
of plain in the config file.

"""

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from typing import Any, Optional, cast

from did.base import Config, ReportError, User, get_token
from did.stats import Stats, StatsGroup
from did.utils import listed, log, pretty

# Identifier padding
PADDING = 3

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Zammad():
    """ Zammad Investigator """
    # pylint: disable=too-few-public-methods

    def __init__(self, url: str, token: Optional[str]) -> None:
        """ Initialize url and headers """
        self.url = url.rstrip("/")
        if token is not None:
            self.headers = {'Authorization': f'Token token={token}'}
        else:
            self.headers = {}

        self.token = token

    def perform_search(self, query: str) -> dict[str, Any]:
        """ Perform Zammad query """
        url = f"{self.url}/{query}"
        log.debug("Zammad query: %s", url)
        try:
            request = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(request) as response:
                log.debug("Response headers:\n%s", str(response.info()).strip())
                return cast(dict[str, Any], json.loads(response.read()))
        except urllib.error.URLError as error:
            log.debug(error)
            raise ReportError(
                f"Zammad search on {self.url} failed.") from error

    def search(self, query: str) -> dict[str, Any]:
        result: dict[str, Any] = self.perform_search(query)["assets"]
        try:
            result = result["Ticket"]
        except KeyError:
            result = {}
        log.debug("Result: %s fetched", listed(len(result), "item"))
        log.data(pretty(result))
        return result

    def get_articles(self, ticket_id: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = self.perform_search(
            f"/ticket_articles/by_ticket/{ticket_id}")["assets"]
        log.debug("Result: %s fetched", listed(len(result), "item"))
        log.data(pretty(result))
        return result


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Ticket
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Ticket:
    """ Zammad Ticket """
    # pylint: disable=too-few-public-methods

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.title = data["title"]
        self.id = data["id"]

    def __str__(self) -> str:
        """ String representation """
        return f"{str(self.id).zfill(PADDING)} - {self.title}"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TicketsUpdated(Stats):
    """ Tickets updated """

    def fetch(self) -> None:
        self.parent: ZammadStats
        self.user: User
        if self.options is None or self.user is None:
            raise RuntimeError("ZammadStats not properly initialized")
        log.info("Searching for tickets updated by %s", self.user)
        search = (
            f"article.from:\"{self.user.name}\" and "
            f"article.created_at:[{self.options.since} TO {self.options.until}]"
            )
        query = f"tickets/search?query={urllib.parse.quote(search)}"
        self.stats = []
        since = self.options.since.date
        until = self.options.until.date
        for _, ticket in self.parent.zammad.search(query).items():
            for article in self.parent.zammad.get_articles(ticket["id"]):
                date_str = article["updated_at"].replace('Z', '+00:00')
                updated_at: date = datetime.fromisoformat(date_str).date()
                if (str(article["created_by"]) == self.user.email and
                        since <= updated_at <= until):
                    self.stats.append(Ticket(ticket))
                    break

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class ZammadStats(StatsGroup):
    """ Zammad work """

    # Default order
    order = 680

    def __init__(self,
                 option: str,
                 name: Optional[str] = None,
                 parent: Optional[StatsGroup] = None,
                 user: Optional[User] = None) -> None:
        StatsGroup.__init__(self, option, name, parent, user)
        config = dict(Config().section(option))
        # Check server url
        try:
            self.url = config["url"]
        except KeyError as exc:
            raise ReportError(f"No zammad url set in the [{option}] section") from exc
        # Check authorization token
        self.token = get_token(config)
        self.zammad = Zammad(self.url, self.token)
        # Create the list of stats
        self.stats = [
            TicketsUpdated(
                option=f"{option}-tickets-updated",
                parent=self,
                name=f"Tickets updated on {option}"),
            ]
