# coding: utf-8
"""
Trello actions such as created, moved or closed cards

Config example (public)::

    [tools]
    type = trello
    user = member

Config example (private)::

    [tools]
    type = trello
    apikey = ...
    token = ...

Optional arguments::

    board_links = g9mdhdzg
    filters = createCard, updateCard,
        updateCard:idList, updateCard:closed,
        updateCheckItemStateOnCard

    apikey
        https://trello.com/app-key

    token
        http://stackoverflow.com/questions/17178907

    token_file
        the token stored in a file

    boards
        default: all

    filters
        default: all
"""

# Possible API methods to add:
# http://developers.trello.com/advanced-reference/member

import json
import urllib.parse
import urllib.request

from did.base import Config, ReportError, get_token
from did.stats import Stats, StatsGroup
from did.utils import listed, log, pretty, split

DEFAULT_FILTERS = [
    "commentCard", "createCard", "updateCard",
    "updateCard:idList", "updateCard:closed",
    "updateCheckItemStateOnCard"]


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
    """ Trello API """

    def __init__(self, stats, config):
        self.stats = stats

        self.key = config['apikey']
        self.token = config['token']
        self.username = config['user'] if "user" in config else "me"
        self.board_links = split(config['board_links'])
        self.board_ids = self.board_links_to_ids()

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
                self.stats.url, self.username, urllib.parse.urlencode({
                    "key": self.key,
                    "token": self.token,
                    "filter": filters,
                    "limit": limit,
                    "since": str(since),
                    "before": str(before)})))

        actions = json.loads(resp.read())
        log.data(pretty(actions))
        # print[act for act in actions if "shortLink" not in
        # act['data']['board'].keys()]
        actions = [act for act in actions if act['data']
                   ['board']['id'] in self.board_ids]
        return actions

    def board_links_to_ids(self):
        """ Convert board links to ids """
        resp = self.stats.session.open(
            "{0}/members/{1}/boards?{2}".format(
                self.stats.url, self.username, urllib.parse.urlencode({
                    "key": self.key,
                    "token": self.token,
                    "fields": "shortLink"})))
        boards = json.loads(resp.read())

        return [board['id'] for board in boards if self.board_links == [""]
                or board['shortLink'] in self.board_links]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Trello createCard
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TrelloCardsCreated(TrelloStats):
    """ Trello cards created """

    def fetch(self):
        log.info(
            "Searching for cards created in %s by %s",
            self.parent.option, self.user)
        actions = [
            act['data']['card']['name']
            for act in self.trello.get_actions(
                filters=self.filt,
                since=self.options.since.date,
                before=self.options.until.date)]
        self.stats = sorted(list(set(actions)))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Trello updateCard
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TrelloCardsUpdated(TrelloStats):
    """ Trello cards updated"""

    def fetch(self):
        log.info(
            "Searching for cards updated in %s by %s",
            self.parent.option, self.user)
        actions = [
            act['data']['card']['name']
            for act in self.trello.get_actions(
                filters=self.filt,
                since=self.options.since.date,
                before=self.options.until.date)]
        self.stats = sorted(list(set(actions)))


class TrelloCardsCommented(TrelloStats):
    """ Trello cards commented"""

    def fetch(self):
        log.info(
            "Searching for cards commented in %s by %s",
            self.parent.option, self.user)
        actions = [
            act['data']['card']['name']
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
        log.info(
            "Searching for cards closed in %s by %s",
            self.parent.option, self.user)
        status = {True: 'closed',
                  False: 'opened'}
        actions = [
            "{0}: {1}".format(
                act['data']['card']['name'],
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
        log.info(
            "Searching for cards moved in %s by %s",
            self.parent.option, self.user)
        actions = [
            "[{0}] moved from [{1}] to [{2}]".format(
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
    """ Trello checklist items completed"""

    def fetch(self):
        log.info(
            "Searching for CheckItem completed in %s by %s",
            self.parent.option, self.user)
        actions = [
            "{0}: {1}".format(
                act['data']['card']['name'],
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
    order = 450

    def __init__(self, option, name=None, parent=None, user=None):
        name = "Trello updates for {0}".format(option)
        super(TrelloStatsGroup, self).__init__(
            option=option, name=name, parent=parent, user=user)

        # map appropriate API methods to Classes
        filter_map = {
            'Boards': {},
            'Lists': {},
            'Cards': {
                'commentCard': TrelloCardsCommented,
                'updateCard': TrelloCardsUpdated,
                'updateCard:closed': TrelloCardsClosed,
                'updateCard:idList': TrelloCardsMoved,
                'createCard': TrelloCardsCreated},
            'Checklists': {
                'updateCheckItemStateOnCard': TrelloCheckItem}
            }
        self._session = None
        self.url = "https://trello.com/1"
        config = dict(Config().section(option))

        config["token"] = get_token(config)
        positional_args = ['apikey', 'token']
        if (not set(positional_args).issubset(set(config.keys()))
                and "user" not in config):
            raise ReportError(
                "No ({0}) or 'user' set in the [{1}] section".format(
                    listed(positional_args, quote="'"), option))

        optional_args = ["board_links", "apikey"]
        for arg in optional_args:
            if arg not in config:
                config[arg] = ""

        # Skip API instance initialization when building options
        if self.options is None:
            trello = None
        else:
            trello = TrelloAPI(stats=self, config=config)

        try:
            filters = split(config["filters"])
        except KeyError:
            filters = DEFAULT_FILTERS
        for filt_group in sorted(filter_map):
            for filt in sorted(filter_map[filt_group]):
                if filters != [""] and filt not in filters:
                    continue
                self.stats.append(filter_map[filt_group][filt](
                    trello=trello,
                    filt=filt,
                    option=option + "-" + filt,
                    parent=self))

    @property
    def session(self):
        """ Initialize the session """
        if self._session is None:
            self._session = urllib.request.build_opener(
                urllib.request.HTTPHandler)
        return self._session
