"""
Finished Koji builds

Config example::

    [koji]
    type = koji
    url = https://koji.example.org/kojihub
    login = testuser
    name = Example koji server

"""

import koji

import did.base
from did.stats import Stats, StatsGroup
from did.utils import log

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class KojiBuilds(Stats):
    """ Finished koji builds """

    def __init__(self, option, name=None, parent=None, user=None, options=None,
                 server=None, userinfo=None):
        Stats.__init__(self, option, name, parent, userinfo, options)
        self.server = server
        self.userinfo = userinfo

    def fetch(self):
        log.info("Searching for builds by %s", self.user)
        builds = self.server.listBuilds(
            userID=self.user['id'],
            completeAfter=str(self.options.since),
            completeBefore=str(self.options.until))
        self.stats = [build['nvr'] for build in builds]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class KojiStats(StatsGroup):
    """ Koji work """

    # Default order
    order = 420

    def __init__(self, option, name=None, parent=None, user=None):
        StatsGroup.__init__(self, option, name, parent, user)
        config = dict(did.base.Config().section(option))
        try:
            url = config['url']
        except KeyError:
            raise did.base.ReportError(
                "No koji url set in the [{0}] section".format(option))
        server = koji.ClientSession(url, opts=config)
        try:
            user = server.getUser(config['login'], strict=True)
        except KeyError:
            raise did.base.ReportError(
                "No koji user set in the [{0}] section".format(option))
        except koji.GenericError:
            raise did.base.ReportError(
                "Non-existent koji user set in the [{0}] section".format(option))

        name = config.get('name', url)

        self.stats = [
            KojiBuilds(option=option + "-builds",
                       name='Completed builds in {0}'.format(name),
                       server=server,
                       userinfo=user,
                       parent=self)
            ]
