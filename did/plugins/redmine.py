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


class Activity():
    """ Redmine Activity """
    # pylint: disable=too-few-public-methods

    def __init__(self, data):
        self.data = data
        self.title = data.title

    def __str__(self):
        """ String representation """
        return str(self.title)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class RedmineActivity(Stats):
    """ Redmine Activity Stats """

    def fetch(self):
        log.info("Searching for activity by %s", self.user)
        results = []

        from_date = self.options.until.date
        while from_date > self.options.since.date:
            feed_url = (
                f"{self.parent.url}/activity.atom?"
                f"user_id={self.user.login}"
                f"&from={from_date.strftime('%Y-%m-%d')}"
                )
            log.debug("Feed url: %s", feed_url)
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
        name = f"Redmine activity on {option}"
        super().__init__(option=option, name=name, parent=parent, user=user)
        config = dict(Config().section(option))
        # Check server url
        try:
            self.url = config["url"]
        except KeyError as exc:
            raise ReportError(f"No Redmine url set in the [{option}] section") from exc
        try:
            self.activity_days = datetime.timedelta(config["activity_days"])
        except KeyError:
            # 30 is value of activity_days_default
            self.activity_days = datetime.timedelta(30)
        # Create the list of stats
        self.stats = [
            RedmineActivity(
                option=f"{option}-activity", parent=self,
                name=f"Redmine activity on {option}"),
            ]
