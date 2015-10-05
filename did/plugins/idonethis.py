# coding: utf-8
"""
Export Idonethis.com Dones

Config example::

    [idonethis]
    type = idonethis
    apitoken = ...

apitoken
    https://idonethis.com/api/token/
"""

# Possible API methods to add:
# http://developers.trello.com/advanced-reference/member

from __future__ import unicode_literals, absolute_import

try:
    import requests
except ImportError:
    raise NotImplementedError("urllib2 version is not yet implemented!")

from did.base import Config, ConfigError
from did.utils import log
from did.stats import Stats, StatsGroup

ROOT_URI = 'https://idonethis.com/api/v0.1/dones'


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Idonethis Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class IdonethisStats(Stats):
    """ Idonethis.com stats """
    def fetch(self, page_size=100):
        log.info(
            "Searching for idonethis.com dones in {}".format(
                self.parent.option))

        # FIXME: add support for pagination (eg, done >= page_size)
        # FIXME: filter out all 'planned' dones (eg, prefixed with '[ ]')

        params = {
            'done_date_after': unicode(self.parent.options.since),
            'done_date_before': unicode(self.parent.options.until),
            'page_size': page_size,
        }
        response = self.parent.session.get(ROOT_URI, params=params)

        if response.status_code not in (400, 401):
            response.raise_for_status()

        payload = response.json()

        if not payload.get('ok'):
            detail = payload.get('detail') or 'UNKNOWN ERROR'
            raise RuntimeError(detail)

        k = payload['count']
        log.info('Found {} dones'.format(k))
        msg = '[{}] <{}> {}'
        results = payload.get('results') or []
        stats = [msg.format(x['done_date'], x['owner'], x['raw_text'])
                 for x in results]
        self.stats = sorted(stats)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Idonethis Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class IdonethisStatsGroup(StatsGroup):
    """ Idonethis stats group """

    # Default order
    order = 801

    _session = None

    def __init__(self, option, name=None, parent=None, user=None):
        name = "Idonethis.com dones {0}".format(option)
        super(IdonethisStatsGroup, self).__init__(
            option=option, name=name, parent=parent, user=user)

        self.config = dict(Config().section(option))

        self.apitoken = self.config.get('apitoken')
        if not self.apitoken:
            raise ConfigError('apitoken must be defined!')

        self.stats = [
            IdonethisStats(option=option + '-dones', parent=self)
        ]

    @property
    def session(self):
        """ Initialize the session """
        if self._session is None:
            _s = requests.Session()
            _s.headers['Authorization'] = 'Token {}'.format(self.apitoken)
            self._session = _s
        return self._session

    # urllib2 version
    # self._session = urllib2.build_opener(urllib2.HTTPHandler)
