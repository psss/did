#!/usr/bin/env python
# coding: utf-8
# Author: "Chris Ward" <cward@redhat.com>

"""
Bit.ly stats such as:

  *  links saved

Config example::

    [bitly]
    type = bitly
    token = ...

To get a token, see: https://bitly.com/a/oauth_apps

Available options:

    --bitly-saved          Links Saved
    --bitly                All above
"""

from __future__ import absolute_import, unicode_literals

import time

from bitly_api import Connection

from did.stats import Stats, StatsGroup
from did.utils import log, pretty
from did.base import Config, ReportError, ConfigError

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  bit.ly
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

######
# NOTES
# bitly_api Usage
#    import bitly_api
#    c = bitly_api.Connection(access_token='...')
#    hist = c.user_link_history(created_)

# user_link_history arguments
#    created_before=None, created_after=None,
#    archived=None, limit=None, offset=None, private=None
######


class Bitly(object):
    """ Bit.ly Link History """

    _connection = None

    def __init__(self, parent, token=None):
        """ Initialize bit.ly OAuth Connection """
        self.parent = parent
        self.token = token or getattr(parent, 'token')
        if not self.token:
            raise ConfigError("bitly requires token to be defined in config")

    @property
    def api(self):
        if not self._connection:
            self._connection = Connection(access_token=self.token)
        return self._connection

    def user_link_history(self, created_before=None, created_after=None,
                          limit=100, **kwargs):
        """  Bit.ly API - user_link_history wrapper"""
        """ Bit.ly link

        Link History Keys
        -----------------

            [u'aggregate_link', u'archived', u'campaign_ids',
             u'client_id', u'created_at', u'keyword_link',
             u'link', u'long_url', u'modified_at',
             u'private', u'tags', u'title', u'user_ts']
        """
        # bit.ly API doesn't seem to like anything other than int's
        limit = int(limit)
        created_after = int(created_after)
        created_before = int(created_before)
        hist = self.api.user_link_history(
            limit=limit, created_before=created_before,
            created_after=created_after)

        # FIXME: if we have more than 100 objects we need to PAGINATE
        record = "{0} - {1}"
        links = []
        for r in hist:
            link = r.get('keyword_link') or r['link']
            title = r['title'] or '<< NO TITLE >>'
            links.append(record.format(link, title))
        log.debug("First 3 Links fetched:")
        log.debug(pretty(hist[0:3], indent=4))
        return links


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Bit.ly Link Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class SavedLinks(Stats):
    """ Links saved """
    def fetch(self):
        '''
        Bit.ly API expect unix timestamps
        '''
        since = time.mktime(self.options.since.datetime.timetuple())
        until = time.mktime(self.options.until.datetime.timetuple())
        log.info("Searching for links saved by {0}".format(self.user))
        self.stats = self.parent.bitly.user_link_history(created_after=since,
                                                         created_before=until)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Bit.ly Link Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class BitlyStats(StatsGroup):
    """ Bit.ly """

    # Default order
    order = 750

    def __init__(self, option, name=None, parent=None, user=None):
        """ Process config, prepare investigator, construct stats """

        # Check Request Tracker instance url and custom prefix
        super(BitlyStats, self).__init__(option, name, parent, user)
        config = dict(Config().section(option))

        try:
            self.token = config["token"]
        except KeyError:
            raise ConfigError("No token in the [{0}] section".format(option))

        self.bitly = Bitly(parent=self)
        # Construct the list of stats
        self.stats = [
            SavedLinks(option=option + "-saved", parent=self),
            ]
