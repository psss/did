"""
Trac stats such as created, accepted, updated and closed tickets

Config example::

    [trac]
    type = trac
    prefix = TT
    url = https://some.trac.com/trac/project/rpc
"""

import re
import xmlrpc.client

from did.base import Config, ReportError
from did.stats import Stats, StatsGroup
from did.utils import log, pretty

INTERESTING_RESOLUTIONS = ["canceled"]
MAX_TICKETS = 1000000


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Trac Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Trac():
    """ Trac investigator """

    def __init__(
            self, ticket=None, changelog=None, parent=None, options=None):
        """ Initialize ticket info and history """
        if ticket is None:
            return
        self.id, self.created, self.modified, self.attributes = ticket
        self.parent = parent
        self.options = options
        self.changelog = changelog
        self.summary = self.attributes["summary"]
        self.resolution = self.attributes["resolution"]

    def __str__(self):
        """ Consistent identifier and summary for displaying """
        # Show only interesting resolutions to be more concise
        if self.resolution and self.resolution in INTERESTING_RESOLUTIONS:
            resolution = f" ({self.resolution})"
        else:
            resolution = ""
        # Urlify the identifier when using the wiki format
        if self.options.format == "wiki":
            identifier = (
                f"[[{self.parent.url}/ticket/{self.id}|"
                f"{self.parent.prefix}#{str(self.id).zfill(4)}]]"
                )
        else:
            identifier = f"{self.parent.prefix}#{str(self.id).zfill(4)}"
        # Join identifier with summary and optional resolution
        return f"{identifier} - {self.summary}{resolution}"

    @staticmethod
    def search(query, parent, options):
        """ Perform Trac search """
        # Extend the default max number of tickets to be fetched
        query = f"{query}&max={MAX_TICKETS}"
        log.debug("Search query: %s", query)
        try:
            result = parent.proxy.ticket.query(query)
        except xmlrpc.client.Fault as error:
            log.error("An error encountered, while searching for tickets.")
            raise ReportError(error) from error
        except (xmlrpc.client.ProtocolError, ConnectionError) as error:
            log.debug(error)
            log.error("Trac url: %s", parent.url)
            raise ReportError(
                "Unable to contact Trac server. Is the url above correct?") from error
        log.debug("Search result: %s", result)
        # Fetch tickets and their history using multicall
        multicall = xmlrpc.client.MultiCall(parent.proxy)
        for ticket_id in sorted(result):
            multicall.ticket.get(ticket_id)
            multicall.ticket.changeLog(ticket_id)
        log.debug("Fetching trac tickets and their history")
        result = list(multicall())
        tickets = result[::2]
        changelogs = result[1::2]
        # Print debugging info
        for ticket, changelog in zip(tickets, changelogs):
            log.debug("Fetched ticket #%s", ticket[0])
            log.debug(pretty(ticket))
            log.debug("Changelog:")
            log.debug(pretty(changelog))
        # Return the list of ticket objects
        return [
            Trac(ticket, changelg, parent=parent, options=options)
            for ticket, changelg in zip(tickets, changelogs)]

    def history(self, user=None):
        """
        Return relevant who-did-what logs from the ticket history
        """
        for event in self.changelog:
            when, who, what, old, new, _ignore = event
            if self.options.since.date <= when <= self.options.until.date:
                if user is None or who.startswith(user.login):
                    yield who, what, old, new

    def accepted(self, user):
        """ True if ticket was accepted in given time frame """
        for _who, what, _old, new in self.history(user):
            if what == "status" and new == "accepted":
                return True
        return False

    def updated(self, user):
        """
        True if the user commented the ticket in given time frame
        """
        for _who, what, _old, new in self.history(user):
            if (what in {"comment", "description"}) and (new != ""):
                return True
        return False

    def closed(self):
        """ True if ticket was closed in given time frame """
        for _who, what, _old, new in self.history():
            if what == "status" and new == "closed":
                return True
        return False


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Trac Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TracCommon(Stats):
    """ Common Trac Stats object for saving prefix & proxy """

    def __init__(self, option, name=None, parent=None):
        Stats.__init__(self, option, name, parent)

    def fetch(self):
        """ Fetch the stats (to be implemented by respective class). """
        raise NotImplementedError()


class TracCreated(TracCommon):
    """ Created tickets """

    def fetch(self):
        log.info("Searching for tickets created by %s", self.user)
        query = (
            f"reporter=~{self.user.login}"
            f"&time={self.options.since}..{self.options.until}"
            )
        self.stats = Trac.search(query, self.parent, self.options)


class TracAccepted(TracCommon):
    """ Accepted tickets """

    def fetch(self):
        log.info("Searching for tickets accepted by %s", self.user)
        query = (
            f"time=..{self.options.until}"
            f"&modified={self.options.since}.."
            f"&owner=~{self.user.login}"
            )
        self.stats = [
            ticket for ticket in Trac.search(query, self.parent, self.options)
            if ticket.accepted(self.user)]


class TracUpdated(TracCommon):
    """ Updated tickets """

    def fetch(self):
        log.info("Searching for tickets updated by %s", self.user)
        query = f"time=..{self.options.until}&modified={self.options.since}.."
        self.stats = [
            ticket for ticket in Trac.search(query, self.parent, self.options)
            if ticket.updated(self.user)]


class TracClosed(TracCommon):
    """ Closed tickets """

    def fetch(self):
        log.info("Searching for tickets closed by %s", self.user)
        query = (
            f"owner=~{self.user.login}"
            f"&time=..{self.options.until}"
            f"&modified={self.options.since}.."
            )
        self.stats = [
            ticket for ticket in Trac.search(query, self.parent, self.options)
            if ticket.closed()]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TracStats(StatsGroup):
    """ Trac stats group """

    # Default order
    order = 400

    def __init__(self, option, name=None, parent=None, user=None):
        name = f"Tickets in {option}"
        StatsGroup.__init__(self, option, name, parent, user)
        # Initialize the server proxy
        config = dict(Config().section(option))
        if "url" not in config:
            raise ReportError(f"No trac url set in the [{option}] section")
        self.url = re.sub("/rpc$", "", config["url"])
        self.proxy = xmlrpc.client.ServerProxy(f"{self.url}/rpc")
        # Make sure we have prefix set
        if "prefix" not in config:
            raise ReportError(f"No prefix set in the [{option}] section")
        self.prefix = config["prefix"]
        # Create the list of stats
        self.stats = [
            TracCreated(
                option=f"{option}-created", parent=self,
                name=f"Tickets created in {option}"),
            TracAccepted(
                option=f"{option}-accepted", parent=self,
                name=f"Tickets accepted in {option}"),
            TracUpdated(
                option=f"{option}-updated", parent=self,
                name=f"Tickets updated in {option}"),
            TracClosed(
                option=f"{option}-closed", parent=self,
                name=f"Tickets closed in {option}"),
            ]
