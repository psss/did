# coding: utf-8
"""
Trello actions

Config example::
    
    [tools]
    type = trello
    apikey = ... [https://trello.com/app-key]
    token = ...  [http://stackoverflow.com/questions/17178907/how-to-get-a-permanent-user-token-for-writes-using-the-trello-api]
    boards = Tasks
    filters = updateCheckItemStateOnCard,updateCard
    user = member

    Positional arguments: apikey, token, user
    Optional arguments: boards(default:all), filters(default:all)

    Possible API methods to add:
    http://developers.trello.com/advanced-reference/member#get-1-members-idmember-or-username-actions
"""

from __future__ import unicode_literals, absolute_import

import json
import urllib
import urllib2

from did.base import Config, ReportError
from did.utils import log, pretty
from did.stats import Stats, StatsGroup


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Trello Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TrelloStats(Stats):

    """ Trello stats """

    def __init__(self, trello, filt, option, name=None, parent=None):
        super(TrelloStats, self).__init__(
            option=option, name=name, parent=parent)
        self.options = parent.options
        self.filt = filt
        self.trello = trello


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Trello API
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TrelloAPI(object):

    def __init__(self, stats, config):
        self.key = config['apikey']
        self.token = config['token']
        self.username = config['user']
        self.board_names = [b.strip() for b in config['boards'].split(',')]
        self.stats = stats

    def get_actions(self, filters, since=None, before=None, limit=1000):
        """
        Example of data structure:
        https://api.trello.com/1/members/ben/actions?limit=2
        """
        if limit > 1000:
            raise NotImplementedError(
                "Fetching more than 1000 items is not implemented")
        resp = self.stats.session.open(
            "{0}/members/{1}/actions?{2}".format(
                self.stats.url, self.username, urllib.urlencode({
                    "key": self.key,
                    "token": self.token,
                    "filter": filters,
                    "limit": limit,
                    "since": str(since),
                    "before": str(before)})))

        actions = json.loads(resp.read())
        log.data(pretty(actions))
        actions = [act for act in actions if act[
            'data']['board']['name'] in self.board_names or
            self.board_names == ['']]
        return actions


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Trello createCard
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TrelloCardsCreated(TrelloStats):

    """ Trello cards """

    def fetch(self):
        log.info(u"Searching for cards created in {0} by {1}".format(
            self.parent.option, self.user))
        actions = ["{0} was created".format(act['data']['card']['name'])
                   for act in self.trello.get_actions(
            filters=self.filt,
            since=self.options.since.date,
            before=self.options.until.date)]
        self.stats = sorted(list(set(actions)))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Trello updateCard
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TrelloCards(TrelloStats):

    """ Trello cards """

    def fetch(self):
        log.info(u"Searching for cards updated in {0} by {1}".format(
            self.parent.option, self.user))
        actions = [act['data']['card']['name']
                   for act in self.trello.get_actions(
            filters=self.filt,
            since=self.options.since.date,
            before=self.options.until.date)]
        self.stats = sorted(list(set(actions)))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Trello updateCard:closed
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TrelloCardsClosed(TrelloStats):

    """ Trello cards closed"""

    def fetch(self):
        log.info(u"Searching for cards closed in {0} by {1}".format(
            self.parent.option, self.user))
        status = {True: 'closed',
                  False: 'opened'}
        actions = ["{0}: {1}".format(act['data']['card']['name'],
                                     status[act['data']['card']['closed']])
                   for act in self.trello.get_actions(
            filters=self.filt,
            since=self.options.since.date,
            before=self.options.until.date)]

        self.stats = sorted(list(set(actions)))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Trello updateCard:idList
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TrelloCardsMoved(TrelloStats):

    """ Trello cards moved"""

    def fetch(self):
        log.info(u"Searching for cards moved in {0} by {1}".format(
            self.parent.option, self.user))
        actions = ["{0} moved from {1} to {2}".format(
            act['data']['card']['name'],
            act['data']['listBefore']['name'],
            act['data']['listAfter']['name'])
            for act in self.trello.get_actions(
            filters=self.filt,
            since=self.options.since.date,
            before=self.options.until.date)]

        self.stats = sorted(list(set(actions)))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Trello updateCheckItemStateOnCard
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TrelloCheckItem(TrelloStats):

    """ Trello cards """

    def fetch(self):
        log.info(u"Searching for CheckItem completed in {0} by {1}".format(
            self.parent.option, self.user))
        actions = ['{0}: {1}'.format(act['data']['card']['name'],
                                     act['data']['checkItem']['name'])
                   for act in self.trello.get_actions(
            filters=self.filt,
            since=self.options.since.date,
            before=self.options.until.date)]
        self.stats = sorted(list(set(actions)))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Trello Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TrelloStatsGroup(StatsGroup):

    """ Trello stats group """

    # Default order

    order = 800

    def __init__(self, option, name=None, parent=None):
        super(TrelloStatsGroup, self).__init__(
            option=option, name=name, parent=parent)

        # map appropriate API methods to Classes
        filter_map = {'Boards': {},
                      'Lists': {},
                      'Cards': {'updateCard': TrelloCards,
                                'updateCard:closed': TrelloCardsClosed,
                                'updateCard:idList': TrelloCardsMoved,
                                'createCard': TrelloCardsCreated},
                      'Checklists': {'updateCheckItemStateOnCard': TrelloCheckItem}
                      }
        self._session = None
        self.url = "https://trello.com/1"
        config = dict(Config().section(option))

        positional_args = ["apikey", "token", "user"]
        for arg in positional_args:
            if arg not in config:
                raise ReportError(
                    "No {0} set in the [{1}] section".format(arg, option))

        optional_args = ["boards", "filters"]
        for arg in optional_args:
            if arg not in config:
                config[arg] = ""

        trello = TrelloAPI(stats=self, config=config)

        filters = [filt.strip() for filt in config['filters'].split(',')]
        for filt_group in filter_map.keys():
            for filt in filter_map[filt_group].keys():
                if filters != [""] and filt not in filters:
                    continue
                self.stats.append(filter_map[filt_group][filt](
                    trello=trello,
                    filt=filt,
                    option=option + filt,
                    name="Actions in %s" % (filt_group),
                    parent=self))

    @property
    def session(self):
        """ Initialize the session """
        if self._session is None:
            self._session = urllib2.build_opener(urllib2.HTTPHandler)
        return self._session
