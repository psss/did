# coding: utf-8
"""
Export did Logg's

Config example::

    [logg]
    type = logg
    engine = txt  # alternative: git

    [joy]
    desc = Joy of the Day

Default git repo store for logg's is ~/.did/loggs/did-$USER.git
"""

from __future__ import unicode_literals, absolute_import

from dateutil.relativedelta import relativedelta as delta
import re

import git

import did.base
import did.logg
from did.utils import log
from did.stats import Stats, StatsGroup
from did.logg import LOGG_CONFIG_KEY

DATE_RE = re.compile('(\d\d\d\d-\d\d-\d\d)')


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Did Logg Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class LoggStats(Stats):
    """ Logg stats """
    def fetch(self):
        stats = []

        author = self.user.email
        path = self.parent.path
        # # DATE INCLUSIVE SEARCH IS USED ##
        # search for anything that has a date that
        # is equal to or greater than the since date
        since = self.options.since.date.date()
        # search for anything that has a date that
        # is equal to or less than the since date
        until = self.options.until.date.date()
        option = self.parent.option

        log.info(
            "Searching GitLogg {0} entries [> {1} < {2}] for {3}".format(
                option, since, until, author))

        # complile the search for target topic lines
        target_re = re.compile(r'\[{0}\]$'.format(option))

        with open(path) as statsf:
            for l in statsf:
                l = l.strip()

                # match matching target lines only
                matched = target_re.search(l)
                if not matched:
                    continue
                matched = DATE_RE.match(l)
                if not matched:
                    log.warn('Invalid Logg line encountered: {0}'.format(l))
                    continue
                dt = matched.group(1)
                # grab a a normalized tz aware datetime
                dt = did.base.Date(dt).date.date()
                if dt >= since and dt <= until:
                    stats.append(l)
        self.stats = stats


class GitLoggStats(Stats):
    """ Git Logg stats """
    def fetch(self):
        # FIXME: this needs to be pulled and parsed from config
        r = git.Repo(self.parent.path)
        # FIXME: add a '...' to the end of the summary if there
        # is more text in the body after the SUBJ
        fmt = '%s'

        # # git search doesn't include the date, only those after... so
        # # start one before
        # from git log --help
        # --since=<date>, --after=<date>
        #   Show commits more recent than a specific date.
        since = self.options.since.date.date() - delta(days=1)

        # # git search doesn't include the date, only those before... so
        # # start one before
        # --until=<date>, --before=<date>
        #   Show commits older than a specific date.
        until = self.options.until.date.date() - delta(days=1)

        author = self.user.email
        option = self.parent.option
        log.info(
            "Searching GitLogg {0} entries [> {1} < {2}] for {3}".format(
                option, since, until, author))

        try:
            stats = r.git.log(option, since=since, until=until, pretty=fmt,
                              author=author)
        except Exception as err:
            log.error('Unable to load loggs for {0}: {1}'.format(option, err))
            self.stats = []
        else:
            # remove empty entries
            _stats = [x.strip() for x in stats.split('\n')]
            _stats = filter(bool, _stats)
            self.stats = _stats


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Did Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class LoggStatsGroup(StatsGroup):
    """ Idonethis stats group """

    # Default order
    order = 1000

    def __init__(self, option, name=None, parent=None, user=None):
        name = "Loggs {0}".format(option)
        super(LoggStatsGroup, self).__init__(
            option=option, name=name, parent=parent, user=user)

        logg_config = dict(self.config.section(LOGG_CONFIG_KEY))
        config = dict(self.config.section(option))

        # get the name/description of the logg stat, if defined
        desc = config.get('desc')

        # Detect the type of backend based on the engine uri and
        # return the StatsGroup expected backend class automatically
        self.engine = logg_config.get('engine') or did.logg.DEFAULT_ENGINE_URI

        # Determine what type of backend we should load
        self.backend, self.path = did.logg.Logg._parse_engine(self.engine)
        StatsCls = GitLoggStats if self.backend == 'git' else LoggStats
        log.debug(' ... Backend Type: {0}'.format(StatsCls))

        self.stats = [
            StatsCls(option=option + '-loggs', parent=self, name=desc)
        ]
