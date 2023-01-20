# coding: utf-8
"""
Redmine stats

Config example::

    [redmine]
    type = redmine
    url = https://redmine.example.com/
    login = <user_db_id>
    activity_days = 30

Use ``login`` to set the database user id in Redmine (number not login
name).  See the :doc:`config` docs for details on using aliases.  Use
``activity_days`` to override the default 30 days of activity paging,
this has to match to the server side setting, otherwise the plugin will
miss entries.

"""

import datetime

import dateutil
import feedparser

from did.base import Config, ReportError
from did.stats import Stats, StatsGroup
from did.utils import log

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Activity
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Activity(object):
    """ Redmine Activity """

    def __init__(self, data):
        self.data = data
        self.title = data.title

    def __str__(self):
        """ String representation """
        return "{0}".format(self.title)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class RedmineActivity(Stats):
    """ Redmine Activity Stats """

    def fetch(self):
        log.info("Searching for activity by {0}".format(self.user))
        results = []

        from_date = self.options.until.date
        while from_date > self.options.since.date:
            feed_url = '{0}/activity.atom?user_id={1}&from={2}'.format(
                self.parent.url, self.user.login,
                from_date.strftime('%Y-%m-%d'))
            log.debug(f"Feed url: {feed_url}")
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                updated = dateutil.parser.parse(entry.updated).date()
                if updated >= self.options.since.date:
                    results.append(entry)
            from_date = from_date - self.parent.activity_days

        self.stats = [Activity(activity) for activity in results]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class RedmineStats(StatsGroup):
    """ Redmine Stats """

    # Default order
    order = 550

    def __init__(self, option, name=None, parent=None, user=None):
        name = "Redmine activity on {0}".format(option)
        super(RedmineStats, self).__init__(
            option=option, name=name, parent=parent, user=user)
        StatsGroup.__init__(self, option, name, parent, user)
        config = dict(Config().section(option))
        # Check server url
        try:
            self.url = config["url"]
        except KeyError:
            raise ReportError(
                "No Redmine url set in the [{0}] section".format(option))
        try:
            self.activity_days = datetime.timedelta(config["activity_days"])
        except KeyError:
            # 30 is value of activity_days_default
            self.activity_days = datetime.timedelta(30)
        # Create the list of stats
        self.stats = [
            RedmineActivity(
                option="{0}-activity".format(option), parent=self,
                name="Redmine activity on {0}".format(option)),
            ]
