# coding: utf-8
""" Comfortably generate reports - Bugzilla """

from __future__ import absolute_import

import re
import bugzilla
import xmlrpclib
from status_report.base import Stats, StatsGroup
from status_report.utils import Config, log, pretty
from status_report.plugins.bugzilla import VerifiedBugs, ReturnedBugs, FiledBugs, FixedBugs, PostedBugs, CommentedBugs
import status_report.plugins.bugzilla as bugzilla_plugin

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Bug
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Bug(bugzilla_plugin.Bug):
    """ Bugzilla search """

    _server = None
    _url = None

    def __init__(self, bug=None, history=None, comments=None, options=None):
        """ Initialize bug info and history (Red Hat specific) """
        if bug is not None:
            bugzilla_plugin.Bug.__init__(self,bug=bug, history=history, comments=comments, options=options)
            # Get the bug grade
            matched = re.search("grade([A-D])", bug.cf_qa_whiteboard, re.I)
            self.grade = matched.groups()[0].upper() if matched else " "

    @property
    def server(self):
        """ Shared connection to the server. """
        if Bug._server is None:
            log.info("Connecting to bugzilla server: {0}".format(Bug._url))
            Bug._server = bugzilla.Bugzilla(url=Bug._url)
        return Bug._server

    @staticmethod
    def search(query, options):
        """ Perform Bugzilla search. """
        # TODO: This method should be shared with bugzilla module
        query["query_format"] = "advanced"
        log.debug("Search query:")
        log.debug(pretty(query))
        server = Bug().server
        # Fetch bug info
        try:
            result = server.query(query)
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
        result = server._proxy.Bug.history({'ids': bugs.keys()})
        log.debug(pretty(result))
        history = dict((bug["id"], bug["history"]) for bug in result["bugs"])
        # Fetch bug comments
        log.debug("Fetching bug comments")
        result = server._proxy.Bug.comments({'ids': bugs.keys()})
        log.debug(pretty(result))
        comments = dict(
            (int(bug), data["comments"])
            for bug, data in result["bugs"].items())
        # Create bug objects
        return [
            Bug(bugs[id], history[id], comments[id], options=options)
            for id in bugs]


    def sanitized(self, user):
        """ True if SanityOnly was added to Verified field by given user """
        for who, record in self.logs:
            if (record["field_name"] == "cf_verified"
                    and "SanityOnly" in record["added"] and who == user.email):
                return True
        return False

    def patched(self, user):
        """ True if Patch was added to Keywords field by given user """
        for who, record in self.logs:
            if (record["field_name"] == "keywords" and
                    "Patch" in record["added"] and who == user.email):
                return True
        return False

    def acked(self, user):
        """ True if qa_ack+ flag was added in given time frame """
        for who, record in self.logs:
            if (record["field_name"] == "flagtypes.name"
                    and "qa_ack+" in record["added"] and who == user.email):
                return True
        return False

    def graded(self, user):
        """ True if the grade was added in a given time frame """
        for who, record in self.logs:
            if (record["field_name"] == "cf_qa_whiteboard"
                    and "grade" in record["added"]
                    and "grade" not in record["removed"]
                    and who == user.email):
                return True
        return False


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Bugzilla Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class VerifiedBugs(bugzilla_plugin.Stats):
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
            "value0-3-0": str(self.options.until),
            # Skip SanityOnly bugs
            "field0-4-0": "cf_verified",
            "type0-4-0": "notsubstring",
            "value0-4-0": "SanityOnly",
            }
        self.stats = [
            bug for bug in Bug.search(query, options=self.options)
            if bug.verified()]


class SanityBugs(Stats):
    """ SanityOnly bugs """
    def fetch(self):
        log.info(u"Searching for SanityOnly bugs by {0}".format(self.user))
        query = {
            # Verified field changed by the user
            "field0-0-0": "cf_verified",
            "type0-0-0": "changedby",
            "value0-0-0": self.user.email,
            # Verified changed to SanityOnly
            "field0-1-0": "cf_verified",
            "type0-1-0": "changedto",
            "value0-1-0": "SanityOnly",
            # Since date
            "field0-2-0": "cf_verified",
            "type0-2-0": "changedafter",
            "value0-2-0": str(self.options.since),
            # Until date
            "field0-3-0": "cf_verified",
            "type0-3-0": "changedbefore",
            "value0-3-0": str(self.options.until),
            }
        self.stats = [
            bug for bug in Bug.search(query, options=self.options)
            if bug.sanitized(self.user)]


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
            bug for bug in Bug.search(query, options=self.options)
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
        self.stats = Bug.search(query, options=self.options)


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
            bug for bug in Bug.search(query, options=self.options)
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
            bug for bug in Bug.search(query, options=self.options)
            if bug.posted()]


class PatchesWritten(Stats):
    """ Patches written """
    def fetch(self):
        log.info(u"Searching for bugs patched by {0}".format(self.user))
        query = {
            # Keywords field changed by the user
            "field0-0-0": "keywords",
            "type0-0-0": "changedby",
            "value0-0-0": self.user.email,
            # Verified changed to SanityOnly
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
            bug for bug in Bug.search(query, options=self.options)
            if bug.patched(self.user)]


class AckedBugs(Stats):
    """ Bugs acked """
    def fetch(self):
        log.info(u"Searching for bugs acked by {0}".format(self.user))
        query = {
            # Acked by the user
            "f1": "flagtypes.name",
            "o1": "changedby",
            "v1": self.user.email,
            # Changed to qa_ack+
            "f2": "flagtypes.name",
            "o2": "changedto",
            "v2": "qa_ack+",
            # Since date
            "f3": "flagtypes.name",
            "o3": "changedafter",
            "v3": str(self.options.since),
            # Until date
            "f4": "flagtypes.name",
            "o4": "changedbefore",
            "v4": str(self.options.until),
            }
        self.stats = [
            bug for bug in Bug.search(query, options=self.options)
            if bug.acked(self.user)]


class GradedBugs(Stats):
    """ Bugs graded """
    def fetch(self):
        log.info(u"Searching for bugs graded by {0}".format(self.user))
        query = {
            # Graded by the user
            "f1": "cf_qa_whiteboard",
            "o1": "changedby",
            "v1": self.user.email,
            # Changed to grade*
            "f2": "cf_qa_whiteboard",
            "o2": "changedto",
            "v2": "",
            # Since date
            "f3": "cf_qa_whiteboard",
            "o3": "changedafter",
            "v3": str(self.options.since),
            # Until date
            "f4": "cf_qa_whiteboard",
            "o4": "changedbefore",
            "v4": str(self.options.until),
            }
        self.stats = [
            bug for bug in Bug.search(query, options=self.options)
            if bug.graded(self.user)]

class BugzillaStats(StatsGroup):
    """ Red Hat Bugzilla stats """

    # Default order
    order = 200

    def __init__(self, option, name=None, parent=None):
        StatsGroup.__init__(self, option, name, parent)
        config = dict(Config().section(option))
        if "url" not in config:
            raise ReportError(
                "No bugzilla url set in the [{0}] section".format(option))
        Bug._url=config["url"]
        self.stats = [
            VerifiedBugs(option="verified", parent=self),
            ReturnedBugs(option="returned", parent=self),
            FiledBugs(option="filed", parent=self),
            FixedBugs(option="fixed", parent=self),
            PostedBugs(option="posted", parent=self),
            CommentedBugs(option="commented", parent=self),
            SanityBugs(option="sanity", parent=self),
            PatchesWritten(option="patches", parent=self),
            AckedBugs(option="acked", parent=self),
            GradedBugs(option="graded", parent=self),
            ]
