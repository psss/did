# coding: utf-8

"""
Bugzilla stats such as filed, fixed or verified bugs

This plugin uses ``python-bugzilla`` module to gather the stats.
Use the ``bugzilla login`` command to initialize Bugzilla cookies
which then will be used for authentication. Reports will contain
only publicly available issues if cookies are not properly set.

Config example::

    [bz]
    type = bugzilla
    prefix = BZ
    url = https://bugzilla.redhat.com/xmlrpc.cgi
    resolutions = notabug, duplicate

Resolutions:
    List of resolutions to be displayed at the end of the summary
    if bug is closed. By default ``notabug`` and ``duplicate`` are
    shown.  Use ``all`` to always display resolution if available
    or ``none`` to turn off the feature completely.

Available options:

    --bz-filed          Bugs filed
    --bz-patched        Bugs patched
    --bz-posted         Bugs posted
    --bz-fixed          Bugs fixed
    --bz-returned       Bugs returned
    --bz-verified       Bugs verified
    --bz-commented      Bugs commented
    --bz-closed         Bugs closed
    --bz                All above
"""

from __future__ import absolute_import, unicode_literals

import bugzilla
import xmlrpclib

import did.base
from did.stats import Stats, StatsGroup
from did.utils import log, pretty, split


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DEFAULT_RESOLUTIONS = ["notabug", "duplicate"]


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
            if self.parent.url:
                self._server = bugzilla.Bugzilla(url=self.parent.url)
            else:
                raise did.base.ConfigError('Bugzilla url not set!')
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
            # Ignore non-existent users (this is necessary for users with
            # several email aliases to allow them using --merge/--total)
            if "not a valid username" in unicode(error):
                log.debug(error)
                return []
            # Otherwise suggest to bake bugzilla cookies
            log.error("An error encountered, while searching for bugs.")
            log.debug(error)
            raise did.base.ReportError(
                "Have you baked cookies using the 'bugzilla login' command?")
        log.debug("Search result:")
        log.debug(pretty(result))
        bugs = dict((bug.id, bug) for bug in result)
        # Fetch bug history
        # FIXME: This is slow, do we always need COMMENTS for EVERY bug?
        # FIXME: How to make this lazy?
        log.debug("Fetching bug history")
        result = self.server._proxy.Bug.history({'ids': bugs.keys()})
        log.debug(pretty(result))
        history = dict((bug["id"], bug["history"]) for bug in result["bugs"])
        # Fetch bug comments
        # FIXME: This is slow, do we always need COMMENTS for EVERY bug?
        # FIXME: How to make this lazy?
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
        self.bug = bug
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
    def summary(self):
        """ Bug summary including resolution if enabled """
        if not self.bug.resolution:
            return self.bug.summary
        if (self.bug.resolution.lower() in self.parent.resolutions
                or "all" in self.parent.resolutions):
            return "{0} [{1}]".format(
                self.bug.summary, self.bug.resolution.lower())
        return self.bug.summary

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
        """ Moved to ASSIGNED by given user (but not from NEW) """
        for who, record in self.logs:
            if (record["field_name"] == "status"
                    and record["added"] == "ASSIGNED"
                    and record["removed"] != "NEW"
                    and who == user.email or who == user.name):
                return True
        return False

    def fixed(self):
        """ Moved to MODIFIED and not later moved to ASSIGNED """
        decision = False
        for record in self.history:
            # Completely ignore older changes
            if record["when"] < self.options.since.date:
                continue
            # Look for status change to MODIFIED (unless already found)
            if not decision and record["when"] < self.options.until.date:
                for change in record["changes"]:
                    if (change["field_name"] == "status"
                            and change["added"] == "MODIFIED"
                            and change["removed"] != "CLOSED"):
                        decision = True
            # Make sure that the bug has not been later moved to ASSIGNED.
            # (This would mean the issue has not been fixed properly.)
            else:
                for change in record["changes"]:
                    if (change["field_name"] == "status"
                            and change["added"] == "ASSIGNED"):
                        decision = False
        return decision

    def closed(self, user):
        """ Moved to CLOSED and not later moved to ASSIGNED """
        decision = False
        for record in self.history:
            # Completely ignore older changes
            if record["when"] < self.options.since.date:
                continue
            # Look for status change to CLOSED (unless already found)
            if not decision and record["when"] < self.options.until.date:
                for change in record["changes"]:
                    if (change["field_name"] == "status"
                            and change["added"] == "CLOSED"
                            and record["who"] in [user.email, user.name]):
                        decision = True
            # Make sure that the bug has not been later moved from CLOSED.
            # (This would mean the bug was not closed for a proper reason.)
            else:
                for change in record["changes"]:
                    if (change["field_name"] == "status"
                            and change["removed"] == "CLOSED"):
                        decision = False
        return decision

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
    """
    Bugs verified

    Bugs with ``QA Contact`` field set to given user and having
    their status changed to ``VERIFIED``.
    """
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
    """
    Bugs returned

    Returned bugs are those which were returned by given user to
    the ``ASSIGNED`` status, meaning the fix for the issue is not
    correct or complete.
    """
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
    """
    Bugs filed

    Newly created bugs by given user, marked as the ``Reporter``.
    """
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
    """
    Bugs fixed

    Bugs which have been moved to the ``MODIFIED`` state in given
    time frame and later have not been moved back to the
    ``ASSIGNED`` state (which would suggest an incomplete fix).
    """

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


class ClosedBugs(Stats):
    """
    Bugs closed

    Bugs which have been moved to the ``CLOSED`` state in given
    time frame and later have not been moved back to the
    ``ASSIGNED`` state (which would suggest the bug was not closed
    for a proper reason).
    """

    def fetch(self):
        log.info(u"Searching for bugs closed by {0}".format(self.user))
        query = {
            # User is the assignee
            "field0-0-0": "assigned_to",
            "type0-0-0": "equals",
            "value0-0-0": self.user.email,
            # Status changed to CLOSED
            "field0-1-0": "bug_status",
            "type0-1-0": "changedto",
            "value0-1-0": "CLOSED",
            # Since date
            "field0-2-0": "bug_status",
            "type0-2-0": "changedafter",
            "value0-2-0": str(self.options.since),
            # Until date
            "field0-3-0": "bug_status",
            "type0-3-0": "changedbefore",
            "value0-3-0": str(self.options.until),
            # Status is now CLOSED
            "field0-4-0": "bug_status",
            "type0-4-0": "equals",
            "value0-4-0": "CLOSED",
        }
        self.stats = [
            bug for bug in self.parent.bugzilla.search(
                query, options=self.options)
            if bug.closed(self.user)]


class PostedBugs(Stats):
    """
    Bugs posted

    Bugs with patches posted for review, detected by their status
    change to ``POST`` and given user set as ``Assignee``.
    """
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
    """
    Bugs patched

    Gathers bugs with keyword ``Patch`` added by given user,
    denoting the patch for the issue is available (e.g. attached
    to the bug or pushed to a feature git branch).
    """
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
    """
    Bugs commented

    All bugs commented by given user in requested time frame.
    """
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

    def __init__(self, option, name=None, parent=None, user=None):
        super(BugzillaStats, self).__init__(option, name, parent, user)
        config = dict(self.config.section(option))

        # If basic config variables aren't set, only warn at init
        # so startup doesn't fail even when we don't actually intend to use the
        # plugin ...

        # Check Bugzilla instance url
        self.url = config.get("url")
        if not self.url:
            log.warn("Bugzilla url not set in [{0}] section".format(option))

        # Use custom prefix set or default to 'BZ'
        self.prefix = config.get("prefix") or 'BZ'
        if not self.prefix:
            log.warn("Bugzilla prefix not set in [{0}] section".format(option))

        # Check for customized list of resolutions
        resolutions = config.get("resolutions") or DEFAULT_RESOLUTIONS
        self.resolutions = [_r.lower() for _r in split(resolutions)]

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
            ClosedBugs(option=option + "-closed", parent=self),
        ]
