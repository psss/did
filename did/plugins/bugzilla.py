# coding: utf-8

"""
Bugzilla stats such as filed, fixed or verified bugs

This plugin uses ``python-bugzilla`` module to gather the stats.
By default reports contain only publicly available issues. Use the
``bugzilla login`` command to initialize Bugzilla cookies or get
an API key from the Preferences_ and store it in the config file
``.config/python-bugzilla/bugzillarc``::

    [bugzilla.redhat.com]
    api_key=YOUR-API-KEY

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
    --bz-subscribed     Bugs subscribed
    --bz-closed         Bugs closed
    --bz                All above

.. _Preferences: https://bugzilla.redhat.com/userprefs.cgi?tab=apikey
"""

import xmlrpc.client

import bugzilla

from did.base import Config, ReportError
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
            self._server = bugzilla.Bugzilla(url=self.parent.url)
        return self._server

    def search(self, query, options):
        """ Perform Bugzilla search """
        query["query_format"] = "advanced"
        query["limit"] = "0"
        log.debug("Search query:")
        log.debug(pretty(query))
        # Fetch bug info
        try:
            result = self.server.query(query)
        except xmlrpc.client.Fault as error:
            # Ignore non-existent users (this is necessary for users
            # with several email aliases to allow them using
            # --merge/--total)
            if "not a valid username" in str(error):
                log.debug(error)
                return []
            # Otherwise suggest to bake bugzilla cookies
            log.error("An error encountered, while searching for bugs.")
            log.debug(error)
            raise ReportError(
                "Have you baked cookies using the 'bugzilla login' command?")
        log.debug("Search result:")
        log.debug(pretty(result))
        bugs = dict((bug.id, bug) for bug in result)
        # Fetch bug history
        log.debug("Fetching bug history")
        result = self.server._proxy.Bug.history({'ids': list(bugs.keys())})
        log.debug(pretty(result))
        history = dict((bug["id"], bug["history"]) for bug in result["bugs"])
        # Fetch bug comments
        log.debug("Fetching bug comments")
        result = self.server._proxy.Bug.comments({'ids': list(bugs.keys())})
        log.debug(pretty(result))
        comments = dict(
            (int(bug), data["comments"])
            for bug, data in list(result["bugs"].items()))
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

    def __str__(self):
        """ Consistent identifier and summary for displaying """
        if self.options.format == "wiki":
            return "<<Bug({0})>> - {1}".format(self.id, self.summary)
        else:
            return "{0}#{1} - {2}".format(
                self.prefix, str(self.id).rjust(7, "0"), self.summary)

    def __eq__(self, other):
        """ Compare bugs by their id """
        return self.id == other.id

    def __hash__(self):
        """ Use bug id for hashing """
        return self.id

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
            # Make sure that the bug has not been later moved to
            # ASSIGNED. (This would mean the issue has not been fixed
            # properly.)
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
            # Make sure that the bug has not been later moved from
            # CLOSED. (This would mean the bug was not closed for a
            # proper reason.)
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
            if (comment.get('author', comment.get('creator')) == user.email and
                    comment["creation_time"] >= self.options.since.date and
                    comment["creation_time"] < self.options.until.date):
                return True
        return False

    def subscribed(self, user):
        """ True if CC was added in given time frame """
        for who, record in self.logs:
            if (record["field_name"] == "cc" and
                    user.email in record["added"]):
                return True
        return False

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Bugzilla Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class VerifiedBugs(Stats):
    """
    Bugs verified

    Bugs with ``QA Contact`` field set to given user or changed by the
    given user and having their status changed to ``VERIFIED``.
    """

    def fetch(self):
        log.info("Searching for bugs verified by {0}".format(self.user))
        # Common query options
        query = {
            # Status changed to VERIFIED
            "f1": "bug_status",
            "o1": "changedto",
            "v1": "VERIFIED",
            # Since date
            "f2": "bug_status",
            "o2": "changedafter",
            "v2": str(self.options.since),
            # Until date
            "f3": "bug_status",
            "o3": "changedbefore",
            "v3": str(self.options.until),
            }
        # User is the QA contact
        query.update({
            "f4": "qa_contact",
            "o4": "equals",
            "v4": self.user.email,
            })
        bugs_by_contact = self.parent.bugzilla.search(
            query, options=self.options)
        # User changed the bug state
        query.update({
            "f4": "bug_status",
            "o4": "changedby",
            "v4": self.user.email,
            })
        bugs_by_changer = self.parent.bugzilla.search(
            query, options=self.options)
        # Merge the two queries
        self.stats = list(set(
            bug for bug in bugs_by_contact + bugs_by_changer
            if bug.verified()))


class ReturnedBugs(Stats):
    """
    Bugs returned

    Returned bugs are those which were returned by given user to
    the ``ASSIGNED`` status, meaning the fix for the issue is not
    correct or complete.
    """

    def fetch(self):
        log.info("Searching for bugs returned by {0}".format(self.user))
        query = {
            # User is not the assignee
            "f1": "assigned_to",
            "o1": "notequals",
            "v1": self.user.email,
            # Status changed to ASSIGNED
            "f2": "bug_status",
            "o2": "changedto",
            "v2": "ASSIGNED",
            # Changed by the user
            "f5": "bug_status",
            "o5": "changedby",
            "v5": self.user.email,
            # Since date
            "f3": "bug_status",
            "o3": "changedafter",
            "v3": str(self.options.since),
            # Until date
            "f4": "bug_status",
            "o4": "changedbefore",
            "v4": str(self.options.until),
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
        log.info("Searching for bugs filed by {0}".format(self.user))
        query = {
            # User is the reporter
            "f1": "reporter",
            "o1": "equals",
            "v1": self.user.email,
            # Since date
            "f2": "creation_ts",
            "o2": "greaterthan",
            "v2": str(self.options.since),
            # Until date
            "f3": "creation_ts",
            "o3": "lessthan",
            "v3": str(self.options.until),
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
        log.info("Searching for bugs fixed by {0}".format(self.user))
        query = {
            # User is the assignee
            "f1": "assigned_to",
            "o1": "equals",
            "v1": self.user.email,
            # Status changed to MODIFIED
            "f2": "bug_status",
            "o2": "changedto",
            "v2": "MODIFIED",
            # Since date
            "f3": "bug_status",
            "o3": "changedafter",
            "v3": str(self.options.since),
            # Until date
            "f4": "bug_status",
            "o4": "changedbefore",
            "v4": str(self.options.until),
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
        log.info("Searching for bugs closed by {0}".format(self.user))
        query = {
            # Status changed by the user
            "f1": "bug_status",
            "o1": "changedby",
            "v1": self.user.email,
            # Status changed to CLOSED
            "f2": "bug_status",
            "o2": "changedto",
            "v2": "CLOSED",
            # Since date
            "f3": "bug_status",
            "o3": "changedafter",
            "v3": str(self.options.since),
            # Until date
            "f4": "bug_status",
            "o4": "changedbefore",
            "v4": str(self.options.until),
            # Status is now CLOSED
            "f5": "bug_status",
            "o5": "equals",
            "v5": "CLOSED",
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
        log.info("Searching for bugs posted by {0}".format(self.user))
        query = {
            # User is the assignee
            "f1": "assigned_to",
            "o1": "equals",
            "v1": self.user.email,
            # Status changed to POST
            "f2": "bug_status",
            "o2": "changedto",
            "v2": "POST",
            # Since date
            "f3": "bug_status",
            "o3": "changedafter",
            "v3": str(self.options.since),
            # Until date
            "f4": "bug_status",
            "o4": "changedbefore",
            "v4": str(self.options.until),
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
        log.info("Searching for bugs patched by {0}".format(self.user))
        query = {
            # Keywords field changed by the user
            "f1": "keywords",
            "o1": "changedby",
            "v1": self.user.email,
            # Patch keyword added
            "f2": "keywords",
            "o2": "changedto",
            "v2": "Patch",
            # Since date
            "f3": "keywords",
            "o3": "changedafter",
            "v3": str(self.options.since),
            # Until date
            "f4": "keywords",
            "o4": "changedbefore",
            "v4": str(self.options.until),
            }
        self.stats = [
            bug for bug in self.parent.bugzilla.search(
                query, options=self.options)
            if bug.patched(self.user)]

        # When user adds the Patch keyword when creating a bug, there is
        # no action in the bug's history from which this would be
        # apparent. We therefore need to check if there are any bugs
        # reported by the user which contain the Patch keyword but have
        # no such action in their history.
        query = {
            # Reported by user
            "f1": "reporter",
            "o1": "equals",
            "v1": self.user.email,
            # Since date
            "f2": "creation_ts",
            "o2": "greaterthan",
            "v2": str(self.options.since),
            # Until date
            "f3": "creation_ts",
            "o3": "lessthan",
            "v3": str(self.options.until),
            # Keywords contain Patch
            "f4": "keywords",
            "o4": "substring",
            "v4": "Patch",
            # The keyword was added when creating the bug
            "n5": "1",
            "f5": "keywords",
            "o5": "changedto",
            "v5": "Patch",
            }
        self.stats += [
            bug for bug in self.parent.bugzilla.search(
                query, options=self.options)]


class CommentedBugs(Stats):
    """
    Bugs commented

    All bugs commented by given user in requested time frame.
    """

    def fetch(self):
        log.info("Searching for bugs commented by {0}".format(self.user))
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


class SubscribedBugs(Stats):
    """
    Bugs subscribed

    All bugs subscribed by given user in requested time frame.
    """

    def fetch(self):
        log.info("Searching for bugs subscribed by {0}".format(self.user))
        query = {
            # Subscribed by the user
            "f1": "cc",
            "o1": "anywordssubstr",
            "v1": self.user.email,
            # Since date
            "f2": "cc",
            "o2": "changedafter",
            "v2": str(self.options.since),
            # Until date
            "f3": "cc",
            "o3": "changedbefore",
            "v3": str(self.options.until),
            # Changed by
            "f4": "cc",
            "o4": "changedby",
            "v4": self.user.email,
            }
        bugs = self.parent.bugzilla.search(query, options=self.options)
        self.stats = [bug for bug in bugs if bug.subscribed(self.user)]


class BugzillaStats(StatsGroup):
    """ Bugzilla stats """

    # Default order
    order = 200

    def __init__(self, option, name=None, parent=None, user=None):
        StatsGroup.__init__(self, option, name, parent, user)
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
        # Check for customized list of resolutions
        try:
            self.resolutions = [
                resolution.lower()
                for resolution in split(config["resolutions"])]
        except KeyError:
            self.resolutions = DEFAULT_RESOLUTIONS
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
            SubscribedBugs(option=option + "-subscribed", parent=self),
            ClosedBugs(option=option + "-closed", parent=self),
            ]
