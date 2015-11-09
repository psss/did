# coding: utf-8
"""
Gerrit stats such as submitted, review or merged changes

Config example::

    [gerrit]
    type = gerrit
    url = https://example.org/gerrit/#/
    prefix = GR
"""

import json
import urllib
import urlparse

from did.utils import log, pretty
from did.stats import Stats, StatsGroup
from did.base import TODAY, Date


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Change
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Change(object):
    """ Request gerrit change """

    def __init__(self, ticket, prefix, changelog=None):
        """ Initialize the change from the record.
        changelog['messages'] could be useful for collecting changes.
        """
        self.id = ticket['_number']
        self.change_id = ticket['change_id']
        self.subject = ticket['subject']
        self.ticket = ticket
        self.changelog = changelog
        self.prefix = prefix

    def __unicode__(self):
        """ Consistent identifier and subject for displaying """
        return u"{0}#{1} - {2}".format(self.prefix, self.id, self.subject)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Gerrit Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Gerrit(object):
    """
     curl -s 'https://REPOURL/gerrit/changes/?q=is:abandoned+age:7d'
    """
    def __init__(self, baseurl, prefix):
        self.opener = urllib.FancyURLopener()
        self.baseurl = baseurl
        self.prefix = prefix

    @staticmethod
    def join_URL_frags(base, query):
        split = list(urlparse.urlsplit(base))
        split[2] = (split[2] + query).replace('//', '/')
        return urlparse.urlunsplit(split)

    def get_query_result(self, url):
        log.debug('url = {0}'.format(url))
        res = self.opener.open(url)
        if res.getcode() != 200:
            raise IOError(
                'Cannot retrieve list of changes ({0})'.format(res.getcode()))

        # see https://code.google.com/p/gerrit/issues/detail?id=2006
        # for explanation of skipping first four characters
        json_str = res.read()[4:].strip()
        try:
            data = json.loads(json_str)
        except ValueError:
            log.exception('Cannot parse JSON data:\n%s', json_str)
            raise
        res.close()

        return data

    def get_changelog(self, chg):
        messages_url = self.join_URL_frags(
            self.baseurl, '/changes/{0}/detail'.format(chg.change_id))
        changelog = self.get_query_result(messages_url)
        log.debug("changelog = {0}".format(changelog))
        return changelog

    def search(self, query):
        full_url = self.join_URL_frags(self.baseurl, '/changes/?q=' + query)
        log.debug('full_url = {0}'.format(full_url))
        tickets = []

        # Get tickets
        tickets = self.get_query_result(full_url)

        # When using multiple queries at once, we get list of lists
        # so we need to merge them
        if '&' in query:
            tmplist = []
            for sublist in tickets:
                tmplist.extend(sublist)
            tickets = tmplist[:]

        return tickets


class GerritUnit(Stats):
    """
        General mother class offering general services for querying
        Gerrit repo.
    """
    def __init__(
            self, option, name=None, parent=None, base_url=None, prefix=None):
        self.base_url = base_url if base_url is not None else parent.repo_url
        self.prefix = prefix if prefix is not None else parent.prefix
        self.repo = Gerrit(baseurl=self.base_url, prefix=self.prefix)
        self.since_date = None

        Stats.__init__(self, option, name, parent)

    @staticmethod
    def get_gerrit_date(instr):
        return Date(instr).date

    def fetch(self, query_string="", common_query_options=None,
              limit_since=False):
        """
        Backend for the actual gerrit query.

        query_string:
            basic query terms, e.g., 'status:abandoned'
        common_query_options:
            [optional] rest of the query string; if omitted, the default
            one is used (limit by the current user and since option);
            if empty, nothing will be added to query_string
        limit_since:
            [optional] Boolean (defaults to False) post-process the results
            to eliminate items created after since option.
        """
        work_list = []
        log.info(u"Searching for changes abandoned by {0}".format(self.user))
        log.debug('query_string = {0}, common_query_options = {1}'.format(
            query_string, common_query_options))

        self.since_date = self.get_gerrit_date(self.options.since)

        if common_query_options is None:
            # Calculate age from self.options.since
            #
            # Amount of time that has expired since the change was last
            # updated with a review comment or new patch set.
            #
            # Meaning that the last time we changed the review is
            # GREATER than the given age.
            # For age SMALLER we need -age:<time>

            common_query_options = '+owner:{0}'.format(
                self.user.login)
            if not limit_since:
                age = (TODAY - self.since_date).days
                common_query_options += '+-age:{0}d'.format(age)

        if isinstance(common_query_options, basestring) and \
                len(common_query_options) > 0:
            query_string += common_query_options

        log.debug('query_string = {0}'.format(query_string))
        log.debug('self.prefix = {0}'.format(self.prefix))
        log.debug('[fetch] self.base_url = {0}'.format(self.base_url))
        work_list = self.repo.search(query_string)

        if limit_since:
            tmplist = []
            log.debug('Limiting by since option')
            self.stats = []
            for chg in work_list:
                log.debug('chg = {0}'.format(chg))
                chg_created = self.get_gerrit_date(chg['created'][:10])
                log.debug('chg_created = {0}'.format(chg_created))
                if chg_created >= self.since_date:
                    tmplist.append(chg)
            work_list = tmplist[:]
        log.debug(u"work_list = {0}".format(work_list))

        # Return the list of tick_data objects
        return [Change(ticket, prefix=self.prefix) for ticket in work_list]


class AbandonedChanges(GerritUnit):
    # curl -s 'https://REPOURL/changes/?q=status:abandoned+-age:1d'
    """
    Changes abandoned
    """
    def fetch(self):
        log.info(u"Searching for changes abandoned by {0}".format(self.user))
        self.stats = GerritUnit.fetch(self, 'status:abandoned')
        log.debug(u"self.stats = {0}".format(self.stats))


class MergedChanges(GerritUnit):
    # curl -s 'https://REPOURL/changes/?q=status:merged'
    """
    Changes succesfully merged
    """
    def fetch(self):
        log.info(u"Searching for changes abandoned by {0}".format(self.user))
        self.stats = GerritUnit.fetch(self, 'status:merged')
        log.debug(u"self.stats = {0}".format(self.stats))


class SubmitedChanges(GerritUnit):
    # <mcepl> do I have to go through all opeend changes and
    # eliminated those which were opened before the last week?
    # <zaro> mcepl: yeah, i think you'll need to do additional
    # processing. i think you can use the sortkey_before or
    # after to put results in order so it'll be easier to
    # process though.
    # curl -s 'https://REPOURL/changes/?q=status:opened'
    #    + postprocessing
    """
    Changes submitted for review
    """
    def fetch(self):
        log.info(u"Searching for changes opened by {0}".format(self.user))
        self.stats = GerritUnit.fetch(self, 'status:open', limit_since=True)
        log.debug(u"self.stats = {0}".format(self.stats))


class PublishedDrafts(GerritUnit):
    # curl -s 'https://REPOURL/changes/?q=is:draft'
    """
    Draft changes published
    """
    def fetch(self):
        log.info(u"Searching for drafts published by {0}".format(self.user))
        self.stats = GerritUnit.fetch(self, 'is:draft', limit_since=True)
        log.debug(u"self.stats = {0}".format(self.stats))


class AddedPatches(GerritUnit):
    # curl -s 'https://REPOURL\
    #    /changes/?q=is:closed+owner:mcepl&q=is:open+owner:mcepl
    """
    Additional patches added to existing changes
    """
    def fetch(self):
        log.info(u"Searching for patches added to changes by {0}".format(
            self.user))
        reviewer = self.user.login
        self.stats = []
        tickets = GerritUnit.fetch(
            self, 'owner:{0}+is:closed&q=owner:{0}+is:open'.format(
                reviewer),
            '', limit_since=True)
        for tck in tickets:
            log.debug("ticket = {0}".format(tck))
            try:
                changes = self.repo.get_changelog(tck)
            except IOError:
                log.debug('Failing to retrieve details for {0}'.format(
                    tck.change_id))
                continue

            owner = changes['owner']['email']

            log.debug("changes.messages = {0}".format(
                pretty(changes['messages'])))
            cmnts_by_user = []
            for chg in changes['messages']:
                # TODO This is a very bad algorithm for recognising
                # patch setts added by the owner of the change, but
                # I don’t know how to find a list of all revisions for
                # the particular change.
                if 'author' not in chg:
                    continue
                if 'email' not in chg['author']:
                    continue
                comment_date = self.get_gerrit_date(chg['date'][:10])
                if (owner == chg['author']['email'] and
                        comment_date >= self.since_date and
                        'uploaded patch' in chg['message'].lower()):
                    cmnts_by_user.append(chg)
            if len(cmnts_by_user) > 0:
                self.stats.append(
                    Change(tck.ticket, changelog=changes,
                           prefix=self.prefix))
        log.debug(u"self.stats = {0}".format(self.stats))


class ReviewedChanges(GerritUnit):
    # curl -s 'https://REPOURL\
    #    /changes/?q=is:closed+reviewer:mcepl&q=is:open+reviewer:mcepl
    """
    Review of a change (for reviewers)
    """
    def fetch(self):
        log.info(u"Searching for changes reviewed by {0}".format(self.user))
        # Collect ALL changes opened (and perhaps now closed) after
        # given date and collect all reviews from them ... then limit by
        # actual reviewer (not reviewer:<login> because that doesn’t
        # that the person actually did a review, only that it has
        # a right to do so).
        self.stats = []
        reviewer = self.user.login
        tickets = GerritUnit.fetch(
            self, 'reviewer:{0}+is:closed&q=reviewer:{0}+is:open'.format(
                self.user.login),
            '', limit_since=True)
        for tck in tickets:
            log.debug("ticket = {0}".format(tck))
            try:
                changes = self.repo.get_changelog(tck)
            except IOError:
                log.debug('Failing to retrieve details for {0}'.format(
                    tck.change_id))
                continue
            log.debug("changes.messages = {0}".format(
                pretty(changes['messages'])))
            cmnts_by_user = []
            for chg in changes['messages']:
                if 'author' not in chg:
                    continue
                if 'email' not in chg['author']:
                    continue
                if reviewer in chg['author']['email']:
                    comment_date = self.get_gerrit_date(chg['date'][:10])
                    if comment_date >= self.since_date:
                        cmnts_by_user.append(chg)
            if len(cmnts_by_user) > 0:
                self.stats.append(
                    Change(tck.ticket, changelog=changes,
                           prefix=self.prefix))
        log.debug(u"self.stats = {0}".format(self.stats))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GerritStats(StatsGroup):
    """
    Gerrit
    """

    # Don't we just want a list of all reviews
    # CLOSED AFTER the given time (age:)
    # ||
    # OPENED AFTER the given time ... or perhaps ALL OPENED changes
    # (and then manually eliminate all changes not conforming)
    #
    # Roles:
    #     owner:self ... find changes owned by the caller.
    #     reviewer:self ... find changes where the caller has been added
    #         as a reviewer.
    #     (instead of 'self' use users' login and it doesn't require
    #      authentication)
    #
    # I.e.
    # curl -v 'https://REPOURL/changes/?q=status:merged+owner:mcepl+-age:1y'

    # Default order
    order = 350

    def __init__(self, option, name=None, parent=None, user=None):
        super(GerritStats, self).__init__(option, name, parent, user)
        config = dict(self.config.section(option))
        self.repo_url = config.get('url')
        if not self.repo_url:
            log.warn('No gerrit URL set in the [{0}] section'.format(option))
        log.debug('repo_url = {0}'.format(self.repo_url))

        # set custom prefix or use default 'GR' prefix value
        self.prefix = config.get('prefix') or 'GR'

        self.stats = [
            AbandonedChanges(option=option + '-abandoned', parent=self),
            MergedChanges(option=option + '-merged', parent=self),
            SubmitedChanges(option=option + '-submitted', parent=self),
            PublishedDrafts(option=option + '-drafts', parent=self),
            AddedPatches(option=option + '-added-patches', parent=self),
            ReviewedChanges(option=option + '-reviewed', parent=self),
        ]
