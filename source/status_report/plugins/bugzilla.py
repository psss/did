""" Comfortably generate reports - Bugzilla """
# coding: utf-8

from __future__ import absolute_import, unicode_literals

import re
import bugzilla
import xmlrpclib

from status_report.base import Stats, StatsGroup
from status_report.utils import Config, log, pretty, ReportError

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Bugzilla
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Bugzilla(object):
    """ Bugzilla investigator """

    def __init__(self, parent):
        """ Initialize url """
        self.parent = parent
        self._server = None

    @property
    def server(self):
        """ Connection to the server """
        if self._server is None:
            self._server = bugzilla.Bugzilla(url=self.parent.url)
        return self._server

    def search(self, query, options):
        """ Perform Bugzilla search """
        query["query_format"] = "advanced"
        log.debug("Search query:")
        log.debug(pretty(query))
        # Fetch bug info
        try:
            result = self.server.query(query)
        except xmlrpclib.Fault as error:
            log.error("An error encountered, while searching for bugs.")
            log.error("Exception:\n{0}".format(error))
            log.error("Have you prepared your cookies by 'bugzilla login'?")
            raise
        log.debug("Search result:")
        log.debug(pretty(result))
        bugs = dict((bug.id, bug) for bug in result)
        # Fetch bug history
        log.debug("Fetching bug history")
        result = self.server._proxy.Bug.history({'ids': bugs.keys()})
        log.debug(pretty(result))
        history = dict((bug["id"], bug["history"]) for bug in result["bugs"])
        # Fetch bug comments
        log.debug("Fetching bug comments")
        result = self.server._proxy.Bug.comments({'ids': bugs.keys()})
        log.debug(pretty(result))
        comments = dict(
            (int(bug), data["comments"])
            for bug, data in result["bugs"].items())
        # Create bug objects
        return [
            self.parent.bug(
                bugs[id], history[id], comments[id], parent=self.parent)
            for id in bugs]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Bug
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Bug(object):
    """ Bugzilla search """

    def __init__(self, bug, history, comments, parent):
        """ Initialize bug info and history """
        self.id = bug.id
        self.summary = bug.summary
        self.history = history
        self.comments = comments
        self.options = parent.options
        self.prefix = parent.prefix
        self.parent = parent

    def __unicode__(self):
        """ Consistent identifier and summary for displaying """
        if self.options.format == "wiki":
            return u"<<Bug({0})>> - {1}".format(self.id, self.summary)
        else:
            return u"{0}#{1} - {2}".format(
                self.prefix, unicode(self.id).rjust(7, "0"), self.summary)

    @property
    def logs(self):
        """ Return relevant who-did-what pairs from the bug history """
        for record in self.history:
            if (record["when"] >= self.options.since.date
                    and record["when"] < self.options.until.date):
                for change in record["changes"]:
                    yield record["who"], change

    def verified(self):
        """ True if bug was verified in given time frame """
        for who, record in self.logs:
            if record["field_name"] == "status" \
                    and record["added"] == "VERIFIED":
                return True
        return False

    def returned(self, user):
        """ True if the bug was returned to ASSIGNED by given user """
        for who, record in self.logs:
            if (record["field_name"] == "status"
                    and record["added"] == "ASSIGNED"
                    and who == user.email):
                return True
        return False

    def fixed(self):
        """ True if bug was moved to MODIFIED in given time frame """
        for who, record in self.logs:
            if (record["field_name"] == "status"
                    and record["added"] == "MODIFIED"
                    and record["removed"] != "CLOSED"):
                return True
        return False

    def posted(self):
        """ True if bug was moved to POST in given time frame """
        for who, record in self.logs:
            if record["field_name"] == "status" and record["added"] == "POST":
                return True
        return False

    def patched(self, user):
        """ True if Patch was added to Keywords field by given user """
        for who, record in self.logs:
            if (record["field_name"] == "keywords" and
                    "Patch" in record["added"] and who == user.email):
                return True
        return False

    def commented(self, user):
        """ True if comment was added in given time frame """
        for comment in self.comments:
            # Description (comment #0) is not considered as a comment
            if comment["count"] == 0:
                continue
            if (comment["author"] == user.email and
                    comment["creation_time"] >= self.options.since.date and
                    comment["creation_time"] < self.options.until.date):
                return True
        return False

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Bugzilla Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class VerifiedBugs(Stats):
    """ Bugs verified """
    def fetch(self):
        log.info(u"Searching for bugs verified by {0}".format(self.user))
        query = {
            # User is the QA contact
            "field0-0-0": "qa_contact",
            "type0-0-0": "equals",
            "value0-0-0": self.user.email,
            # Status changed to VERIFIED
            "field0-1-0": "bug_status",
            "type0-1-0": "changedto",
            "value0-1-0": "VERIFIED",
            # Since date
            "field0-2-0": "bug_status",
            "type0-2-0": "changedafter",
            "value0-2-0": str(self.options.since),
            # Until date
            "field0-3-0": "bug_status",
            "type0-3-0": "changedbefore",
            "value0-3-0": str(self.options.until)
            }
        self.stats = [
            bug for bug in self.parent.bugzilla.search(
                query, options=self.options)
            if bug.verified()]


class ReturnedBugs(Stats):
    """ Bugs returned """
    def fetch(self):
        log.info(u"Searching for bugs returned by {0}".format(self.user))
        query = {
            # User is not the assignee
            "field0-0-0": "assigned_to",
            "type0-0-0": "notequals",
            "value0-0-0": self.user.email,
            # Status changed to ASSIGNED
            "field0-1-0": "bug_status",
            "type0-1-0": "changedto",
            "value0-1-0": "ASSIGNED",
            # Changed by the user
            "field0-4-0": "bug_status",
            "type0-4-0": "changedby",
            "value0-4-0": self.user.email,
            # Since date
            "field0-2-0": "bug_status",
            "type0-2-0": "changedafter",
            "value0-2-0": str(self.options.since),
            # Until date
            "field0-3-0": "bug_status",
            "type0-3-0": "changedbefore",
            "value0-3-0": str(self.options.until),
            }
        self.stats = [
            bug for bug in self.parent.bugzilla.search(
                query, options=self.options)
            if bug.returned(self.user)]


class FiledBugs(Stats):
    """ Bugs filed """
    def fetch(self):
        log.info(u"Searching for bugs filed by {0}".format(self.user))
        query = {
            # User is the reporter
            "field0-0-0": "reporter",
            "type0-0-0": "equals",
            "value0-0-0": self.user.email,
            # Since date
            "field0-1-0": "creation_ts",
            "type0-1-0": "greaterthan",
            "value0-1-0": str(self.options.since),
            # Until date
            "field0-2-0": "creation_ts",
            "type0-2-0": "lessthan",
            "value0-2-0": str(self.options.until),
            }
        self.stats = self.parent.bugzilla.search(query, options=self.options)


class FixedBugs(Stats):
    """ Bugs fixed """
    def fetch(self):
        log.info(u"Searching for bugs fixed by {0}".format(self.user))
        query = {
            # User is the assignee
            "field0-0-0": "assigned_to",
            "type0-0-0": "equals",
            "value0-0-0": self.user.email,
            # Status changed to MODIFIED
            "field0-1-0": "bug_status",
            "type0-1-0": "changedto",
            "value0-1-0": "MODIFIED",
            # Since date
            "field0-2-0": "bug_status",
            "type0-2-0": "changedafter",
            "value0-2-0": str(self.options.since),
            # Until date
            "field0-3-0": "bug_status",
            "type0-3-0": "changedbefore",
            "value0-3-0": str(self.options.until),
            }
        self.stats = [
            bug for bug in self.parent.bugzilla.search(
                query, options=self.options)
            if bug.fixed()]


class PostedBugs(Stats):
    """ Bugs posted """
    def fetch(self):
        log.info(u"Searching for bugs posted by {0}".format(self.user))
        query = {
            # User is the assignee
            "field0-0-0": "assigned_to",
            "type0-0-0": "equals",
            "value0-0-0": self.user.email,
            # Status changed to POST
            "field0-1-0": "bug_status",
            "type0-1-0": "changedto",
            "value0-1-0": "POST",
            # Since date
            "field0-2-0": "bug_status",
            "type0-2-0": "changedafter",
            "value0-2-0": str(self.options.since),
            # Until date
            "field0-3-0": "bug_status",
            "type0-3-0": "changedbefore",
            "value0-3-0": str(self.options.until),
            }
        self.stats = [
            bug for bug in self.parent.bugzilla.search(
                query, options=self.options)
            if bug.posted()]


class PatchedBugs(Stats):
    """ Bugs patched """
    def fetch(self):
        log.info(u"Searching for bugs patched by {0}".format(self.user))
        query = {
            # Keywords field changed by the user
            "field0-0-0": "keywords",
            "type0-0-0": "changedby",
            "value0-0-0": self.user.email,
            # Patch keyword added
            "field0-1-0": "keywords",
            "type0-1-0": "changedto",
            "value0-1-0": "Patch",
            # Since date
            "field0-2-0": "keywords",
            "type0-2-0": "changedafter",
            "value0-2-0": str(self.options.since),
            # Until date
            "field0-3-0": "keywords",
            "type0-3-0": "changedbefore",
            "value0-3-0": str(self.options.until),
            }
        self.stats = [
            bug for bug in self.parent.bugzilla.search(
                query, options=self.options)
            if bug.patched(self.user)]


class CommentedBugs(Stats):
    """ Bugs commented """
    def fetch(self):
        log.info(u"Searching for bugs commented by {0}".format(self.user))
        query = {
            # Commented by the user
            "f1": "longdesc",
            "o1": "changedby",
            "v1": self.user.email,
            # Since date
            "f3": "longdesc",
            "o3": "changedafter",
            "v3": str(self.options.since),
            # Until date
            "f4": "longdesc",
            "o4": "changedbefore",
            "v4": str(self.options.until),
            }
        self.stats = [
            bug for bug in self.parent.bugzilla.search(
                query, options=self.options)
            if bug.commented(self.user)]


class BugzillaStats(StatsGroup):
    """ Bugzilla stats """

    # Default order
    order = 200

    def __init__(self, option, name=None, parent=None):
        StatsGroup.__init__(self, option, name, parent)
        config = dict(Config().section(option))
        # Check Bugzilla instance url
        try:
            self.url = config["url"]
        except KeyError:
            raise ReportError(
                "No bugzilla url set in the [{0}] section".format(option))
        # Make sure we have prefix set
        try:
            self.prefix = config["prefix"]
        except KeyError:
            raise ReportError(
                "No prefix set in the [{0}] section".format(option))
        # Save Bug class as attribute to allow customizations by
        # descendant class and set up the Bugzilla investigator
        self.bug = Bug
        self.bugzilla = Bugzilla(parent=self)
        # Construct the list of stats
        self.stats = [
            FiledBugs(option=option + "-filed", parent=self),
            PatchedBugs(option=option + "-patched", parent=self),
            PostedBugs(option=option + "-posted", parent=self),
            FixedBugs(option=option + "-fixed", parent=self),
            ReturnedBugs(option=option + "-returned", parent=self),
            VerifiedBugs(option=option + "-verified", parent=self),
            CommentedBugs(option=option + "-commented", parent=self),
            ]
