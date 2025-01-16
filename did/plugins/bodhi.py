"""
Bodhi stats

Config example::

    [bodhi]
    type = bodhi
    url = https://bodhi.fedoraproject.org/
    login = <username>

"""

from bodhi.client.bindings import BodhiClient

from did.base import Config, ReportError
from did.stats import Stats, StatsGroup
from did.utils import listed, log, pretty

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Bodhi(object):
    """ Bodhi """

    def __init__(self, url):
        """ Initialize url """
        self.url = url

    def search(self, query):
        """ Perform Bodhi query """
        result = []
        current_page = 1
        original_query = query
        while current_page:
            log.debug("Bodhi query: %s", query)
            client = BodhiClient(self.url)
            data = client.send_request(query, verb='GET')
            objects = data['updates']
            log.debug("Result: %s fetched", listed(len(objects), "item"))
            log.data(pretty(data))
            result.extend(objects)
            if current_page < data['pages']:
                current_page = current_page + 1
                query = f"{original_query}&page={current_page}"
            else:
                current_page = None
        return result


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Update
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Update(object):
    """ Bodhi update """

    def __init__(self, data, format):
        self.data = data
        self.format = format
        self.title = data['title']
        self.project = data['release']['name']
        self.identifier = data['alias']
        self.created = data['date_submitted']
        self.url = data['url']
        log.details('[{0}] {1}'.format(self.created, self))

    def __str__(self):
        """ String representation """
        if self.format == "markdown":
            return f'[{self.identifier}]({self.url}) - {self.title} [{self.project}]'
        return f'{self.identifier} - {self.title} [{self.project}]'


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class UpdatesCreated(Stats):
    """ Updates created """

    def fetch(self):
        log.info('Searching for updates created by %s', self.user)
        self.stats = [
            Update(update, self.parent.options.format)
            for update in self.parent.bodhi.search(
                query='updates/?user={0}&submitted_before={1}'
                '&submitted_since={2}'.format(
                      self.user.login, self.options.until.date,
                      self.options.since.date))]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class BodhiStats(StatsGroup):
    """ Bodhi work """

    # Default order
    order = 410

    def __init__(self, option, name=None, parent=None, user=None):
        StatsGroup.__init__(self, option, name, parent, user)
        config = dict(Config().section(option))
        # Check server url
        try:
            self.url = config['url']
        except KeyError:
            raise ReportError(
                'No Bodhi url set in the [{0}] section'.format(option))
        self.bodhi = Bodhi(self.url)
        # Create the list of stats
        self.stats = [
            UpdatesCreated(
                option=option + '-updates-created', parent=self,
                name='Updates created on {0}'.format(option)),
            ]
