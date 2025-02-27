"""
Finished Koji builds

Config example::

    [koji]
    type = koji
    url = https://koji.example.org/kojihub
    weburl = https://koji.example.org/koji
    login = testuser
    name = Example koji server

"""

import koji
import requests.exceptions

import did.base
from did.stats import Stats, StatsGroup
from did.utils import log

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class KojiBuilds(Stats):
    """ Finished koji builds """

    def __init__(self, *, option, name=None,
                 parent=None, options=None):
        Stats.__init__(self, option, name, parent, options=options)

    def fetch(self):
        log.info("Searching for builds by %s", self.user)
        server = koji.ClientSession(self.parent.url, opts=self.parent.config)
        try:
            self.user = server.getUser(self.parent.config['login'], strict=True)
        except KeyError as keyerr:
            raise did.base.ReportError(
                f"No koji user set in the [{self.option}] section") from keyerr
        except koji.GenericError as ge_err:
            raise did.base.ReportError(
                f"Non-existent koji user set in the [{self.option}] section"
                ) from ge_err
        except (requests.exceptions.HTTPError,
                requests.exceptions.ConnectionError) as req_error:
            raise did.base.ReportError(
                f"Connection to koji server {self.parent.url} "
                f"failed for [{self.option}] section"
                ) from req_error

        builds = server.listBuilds(
            userID=self.user['id'],
            completeAfter=str(self.options.since),
            completeBefore=str(self.options.until))
        if self.options.format == "markdown":
            try:
                weburl = f"{self.parent.config['weburl']}/buildinfo?buildID="
                self.stats = [
                    f"[{build['nvr']}]({weburl}{build['build_id']})"
                    for build in builds
                    ]
            except KeyError as ke:
                log.warning(
                    "Missing `%s` option, markdown unavailable for '%s' section",
                    ke.args[0],
                    self.name
                    )
            else:
                return
        # else
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
        self.config = dict(did.base.Config().section(option))
        try:
            self.url = self.config['url']
        except KeyError as exc:
            raise did.base.ReportError(
                f"No koji url set in the [{option}] section") from exc
        name = self.config.get('name', self.url)

        self.stats = [
            KojiBuilds(option=f"{option}-builds",
                       name=f'Completed builds in {name}',
                       parent=self)
            ]
