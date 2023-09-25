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

from datetime import datetime

from did.base import Config, ReportError, get_token
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

    def __init__(self, url, token):
        """ Initialize url and headers """
        self.url = url.rstrip("/")
        if token is not None:
            self.headers = {'Authorization': f'Token token={token}'}
        else:
            self.headers = {}

        self.token = token

    def search(self, query: str) -> dict:
        """ Perform Zammad query """
        url = f"{self.url}/{query}"
        log.debug("Zammad query: %s", url)
        try:
            request = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(request) as response:
                log.debug("Response headers:\n%s", str(response.info()).strip())
                result = json.loads(response.read())["assets"]
        except urllib.error.URLError as error:
            log.debug(error)
            raise ReportError(
                f"Zammad search on {self.url} failed.") from error
        try:
            result = result["Ticket"]
        except KeyError:
            result = {}
        log.debug("Result: %s fetched", listed(len(result), "item"))
        log.data(pretty(result))
        return result

    def get_articles(self, ticket_id):
        """ Perform Zammad query """
        url = self.url + "/ticket_articles/by_ticket/" + str(ticket_id)
        log.debug("Zammad query: {0}".format(url))
        try:
            request = urllib.request.Request(url, headers=self.headers)
            response = urllib.request.urlopen(request)
            log.debug("Response headers:\n{0}".format(
                str(response.info()).strip()))
        except urllib.error.URLError as error:
            log.debug(error)
            raise ReportError(
                "Zammad search on {0} failed.".format(self.url))
        result = json.loads(response.read())
        log.debug("Result: %s fetched", listed(len(result), "item"))
        log.data(pretty(result))
        return result


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Ticket
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Ticket():
    """ Zammad Ticket """
    # pylint: disable=too-few-public-methods

    def __init__(self, data):
        self.data = data
        self.title = data["title"]
        self.id = data["id"]

    def __str__(self):
        """ String representation """
        return f"{str(self.id).zfill(PADDING)} - {self.title}"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TicketsUpdated(Stats):
    """ Tickets updated """

    def fetch(self):
        log.info("Searching for tickets updated by %s", self.user)
        search = (
            f"article.from:\"{self.user.name}\" and "
            f"article.created_at:[{self.options.since} TO {self.options.until}]"
            )
        query = f"tickets/search?query={urllib.parse.quote(search)}"
        self.stats = []
        for _,ticket in self.parent.zammad.search(query).items():
            for article in self.parent.zammad.get_articles(ticket["id"]):
                updated_at = datetime.fromisoformat(article["updated_at"].replace('Z', '+00:00')).date()
                if (article["created_by"] == self.user.email) and (updated_at >= self.options.since.date) and (updated_at <= self.options.until.date):
                    self.stats.append(Ticket(ticket))
                    break

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class ZammadStats(StatsGroup):
    """ Zammad work """

    # Default order
    order = 680

    def __init__(self, option, name=None, parent=None, user=None):
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
