# coding: utf-8
"""
Request Tracker stats such as reported and resolved tickets

Config example::

    [rt]
    type = rt
    prefix = RT
    url = https://tracker.org/rt/Search/Results.tsv
"""

from __future__ import absolute_import, unicode_literals

import httplib
import urllib
import urlparse
import kerberos

import did.base
from did.utils import log, pretty
from did.stats import Stats, StatsGroup


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  RequestTracker
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class RequestTracker(object):
    """ Request Tracker Investigator """

    def __init__(self, parent):
        """ Initialize url and parent """
        self.parent = parent
        self.url = urlparse.urlsplit(parent.url)
        self.url_string = parent.url

    def get(self, path):
        """ Perform a GET request with Kerberos authentication """
        # Prepare Kerberos ticket granting ticket """
        _, ctx = kerberos.authGSSClientInit(
            'HTTP@{0}'.format(self.url.netloc))
        kerberos.authGSSClientStep(ctx, "")
        tgt = kerberos.authGSSClientResponse(ctx)

        # Make the connection
        connection = httplib.HTTPSConnection(self.url.netloc, 443)
        log.debug("GET {0}".format(path))
        connection.putrequest("GET", path)
        connection.putheader("Authorization", "Negotiate {0}".format(tgt))
        connection.putheader("Referer", self.url_string)
        connection.endheaders()

        # Perform the request, convert response into lines
        response = connection.getresponse()
        if response.status != 200:
            raise did.base.ReportError(
                "Failed to fetch tickets: {0}".format(response.status))
        lines = [
            line.decode("utf8")
            for line in response.read().strip().split("\n")[1:]]
        log.debug("Tickets fetched:")
        log.debug(pretty(lines))
        return lines

    def search(self, query):
        """ Perform request tracker search """
        # Prepare the path
        log.debug("Query: {0}".format(query))
        path = self.url.path + '?Format=__id__+__Subject__'
        path += "&Order=ASC&OrderBy=id&Query=" + urllib.quote(query)

        # Get the tickets
        lines = self.get(path)
        log.info(u"Fetched tickets: {0}".format(len(lines)))
        return [self.parent.ticket(line, self.parent) for line in lines]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Ticket
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Ticket(object):
    """ Request tracker ticket """

    def __init__(self, record, parent):
        """ Initialize the ticket from the record """
        self.id, self.subject = record.split("\t")
        self.parent = parent

    def __unicode__(self):
        """ Consistent identifier and subject for displaying """
        return u"{0}#{1} - {2}".format(
            self.parent.prefix, self.id, self.subject)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class ReportedTickets(Stats):
    """ Tickets reported """
    def fetch(self):
        log.info(u"Searching for tickets reported by {0}".format(self.user))
        query = "Requestor.EmailAddress = '{0}'".format(self.user.email)
        query += " AND Created > '{0}'".format(self.options.since)
        query += " AND Created < '{0}'".format(self.options.until)
        self.stats = self.parent.request_tracker.search(query)


class ResolvedTickets(Stats):
    """ Tickets resolved """
    def fetch(self):
        log.info(u"Searching for tickets resolved by {0}".format(self.user))
        query = "Owner.EmailAddress = '{0}'".format(self.user.email)
        query += "AND Resolved > '{0}'".format(self.options.since)
        query += "AND Resolved < '{0}'".format(self.options.until)
        self.stats = self.parent.request_tracker.search(query)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class RequestTrackerStats(StatsGroup):
    """ Request Tracker """

    # Default order
    order = 500

    def __init__(self, option, name=None, parent=None, user=None):
        """ Process config, prepare investigator, construct stats """

        # Check Request Tracker instance url and custom prefix
        StatsGroup.__init__(self, option, name, parent, user)
        config = dict(self.config.section(option))
        try:
            self.url = config["url"]
        except KeyError:
            raise did.base.ReportError(
                "No url in the [{0}] section".format(option))
        try:
            self.prefix = config["prefix"]
        except KeyError:
            raise did.base.ReportError(
                "No prefix set in the [{0}] section".format(option))

        # Save Ticket class as attribute to allow customizations by
        # descendant class and set up the RequestTracker investigator
        self.ticket = Ticket
        self.request_tracker = RequestTracker(parent=self)
        # Construct the list of stats
        self.stats = [
            ReportedTickets(option=option + "-reported", parent=self),
            ResolvedTickets(option=option + "-resolved", parent=self),
            ]
