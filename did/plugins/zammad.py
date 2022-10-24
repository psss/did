# coding: utf-8
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

from did.base import Config, ReportError, get_token
from did.stats import Stats, StatsGroup
from did.utils import listed, log, pretty

# Identifier padding
PADDING = 3

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Zammad(object):
    """ Zammad Investigator """

    def __init__(self, url, token):
        """ Initialize url and headers """
        self.url = url.rstrip("/")
        if token is not None:
            self.headers = {'Authorization': 'Token token={0}'.format(token)}
        else:
            self.headers = {}

        self.token = token

    def search(self, query):
        """ Perform Zammad query """
        url = self.url + "/" + query
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
        result = json.loads(response.read())["assets"]
        try:
            result = result["Ticket"]
        except KeyError:
            result = dict()
        log.debug("Result: {0} fetched".format(listed(len(result), "item")))
        log.data(pretty(result))
        return result


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Ticket
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Ticket(object):
    """ Zammad Ticket """

    def __init__(self, data):
        self.data = data
        self.title = data["title"]
        self.id = data["id"]

    def __str__(self):
        """ String representation """
        return "{0} - {1}".format(
            str(self.id).zfill(PADDING), self.title)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TicketsUpdated(Stats):
    """ Tickets updated """

    def fetch(self):
        log.info("Searching for tickets updated by {0}".format(self.user))
        search = "article.from:\"{0}\" and article.created_at:[{1} TO {2}]".format(
            self.user.name, self.options.since, self.options.until)
        query = "tickets/search?query={0}".format(urllib.parse.quote(search))
        self.stats = [
            Ticket(ticket) for id,
            ticket in self.parent.zammad.search(query).items()]


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
        except KeyError:
            raise ReportError(
                "No zammad url set in the [{0}] section".format(option))
        # Check authorization token
        self.token = get_token(config)
        self.zammad = Zammad(self.url, self.token)
        # Create the list of stats
        self.stats = [
            TicketsUpdated(
                option=option + "-tickets-updated", parent=self,
                name="Tickets updated on {0}".format(option)),
            ]
