# coding: utf-8
""" Comfortably generate reports - Trac """

import re
import xmlrpclib

import status_report.utils as utils
from status_report.base import Stats, StatsGroup
from status_report.utils import Config, ReportError, log, pretty

INTERESTING_RESOLUTIONS = ["canceled"]
MAX_TICKETS = 1000000

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Trac Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Trac(object):
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

    def __unicode__(self):
        """ Consistent identifier and summary for displaying """
        # Show only interesting resolutions to be more concise
        if self.resolution and self.resolution in INTERESTING_RESOLUTIONS:
            resolution = " ({0})".format(self.resolution)
        else:
            resolution = ""
        # Urlify the identifier when using the wiki format
        if self.options.format == "wiki":
            identifier = u"[[{0}/ticket/{1}|{2}#{3}]]".format(
                self.parent.url, self.id,
                self.parent.prefix, str(self.id).zfill(4))
        else:
            identifier = u"{0}#{1}".format(
                self.parent.prefix, str(self.id).zfill(4))
        # Join identifier with summary and optional resolution
        return u"{0} - {1}{2}".format(identifier, self.summary, resolution)

    @staticmethod
    def search(query, parent, options):
        """ Perform Trac search """
        # Extend the default max number of tickets to be fetched
        query = "{0}&max={1}".format(query, MAX_TICKETS)
        log.debug("Search query: {0}".format(query))
        try:
            result = parent.proxy.ticket.query(query)
        except xmlrpclib.Fault as error:
            log.error("An error encountered, while searching for tickets.")
            raise ReportError(error)
        log.debug("Search result: {0}".format(result))
        # Fetch tickets and their history using multicall
        multicall = xmlrpclib.MultiCall(parent.proxy)
        for ticket_id in sorted(result):
            multicall.ticket.get(ticket_id)
            multicall.ticket.changeLog(ticket_id)
        log.debug(u"Fetching trac tickets and their history")
        result = list(multicall())
        tickets = result[::2]
        changelogs = result[1::2]
        # Print debugging info
        for ticket, changelog in zip(tickets, changelogs):
            log.debug("Fetched ticket #{0}".format(ticket[0]))
            log.debug(pretty(ticket))
            log.debug("Changelog:")
            log.debug(pretty(changelog))
        # Return the list of ticket objects
        return [
            Trac(ticket, changelg, parent=parent, options=options)
            for ticket, changelg in zip(tickets, changelogs)]

    def history(self, user=None):
        """ Return relevant who-did-what logs from the ticket history """
        for event in self.changelog:
            when, who, what, old, new, ignore = event
            if (when >= self.options.since.date and
                    when <= self.options.until.date):
                if user is None or who.startswith(user.login):
                    yield who, what, old, new

    def accepted(self, user):
        """ True if ticket was accepted in given time frame """
        for who, what, old, new in self.history(user):
            if what == "status" and new == "accepted":
                return True
        return False

    def updated(self, user):
        """ True if the user commented the ticket in given time frame """
        for who, what, old, new in self.history(user):
            if what == "comment" and new != "":
                return True
        return False

    def closed(self):
        """ True if ticket was closed in given time frame """
        for who, what, old, new in self.history():
            if what == "status" and new == "closed":
                return True
        return False

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Trac Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TracCommon(Stats):
    """ Common Trac Stats object for saving prefix & proxy """
    def __init__(self, option, name=None, parent=None):
        self.parent = parent
        Stats.__init__(self, option, name, parent)


class TracCreated(TracCommon):
    """ Created tickets """
    def fetch(self):
        log.info(u"Searching for tickets created by {0}".format(self.user))
        query = "reporter=~{0}&time={1}..{2}".format(
            self.user.login, self.options.since, self.options.until)
        self.stats = Trac.search(query, self.parent, self.options)


class TracAccepted(TracCommon):
    """ Accepted tickets """
    def fetch(self):
        log.info(u"Searching for tickets accepted by {0}".format(self.user))
        query = "time=..{2}&modified={1}..&owner=~{0}".format(
                self.user.login, self.options.since, self.options.until)
        self.stats = [
            ticket for ticket in Trac.search(query, self.parent, self.options)
            if ticket.accepted(self.user)]


class TracUpdated(TracCommon):
    """ Updated tickets """
    def fetch(self):
        log.info(u"Searching for tickets updated by {0}".format(self.user))
        query = "time=..{2}&modified={1}..".format(
            self.user.login, self.options.since, self.options.until)
        self.stats = [
            ticket for ticket in Trac.search(query, self.parent, self.options)
            if ticket.updated(self.user)]


class TracClosed(TracCommon):
    """ Closed tickets """
    def fetch(self):
        log.info(u"Searching for tickets closed by {0}".format(self.user))
        query = "owner=^{0}@&time=..{2}&modified={1}..".format(
            self.user.login, self.options.since, self.options.until)
        self.stats = [
            ticket for ticket in Trac.search(query, self.parent, self.options)
            if ticket.closed()]


class TracStats(StatsGroup):
    """ Trac stats group """

    # Default order
    order = 400

    def __init__(self, option, name=None, parent=None):
        name = "Tickets in {0}".format(option)
        StatsGroup.__init__(self, option, name, parent)
        # Initialize the server proxy
        config = dict(Config().section(option))
        if "url" not in config:
            raise ReportError(
                "No trac url set in the [{0}] section".format(option))
        self.url = re.sub("/rpc$", "", config["url"])
        self.proxy = xmlrpclib.ServerProxy(self.url + "/rpc")
        # Make sure we have prefix set
        if "prefix" not in config:
            raise ReportError(
                "No prefix set in the [{0}] section".format(option))
        self.prefix = config["prefix"]
        # Create the list of stats
        self.stats = [
            TracCreated(
                option=option + "-created", parent=self,
                name="Tickets created in {0}".format(option)),
            TracAccepted(
                option=option + "-accepted", parent=self,
                name="Tickets accepted in {0}".format(option)),
            TracUpdated(
                option=option + "-updated", parent=self,
                name="Tickets updated in {0}".format(option)),
            TracClosed(
                option=option + "-closed", parent=self,
                name="Tickets closed in {0}".format(option)),
            ]
