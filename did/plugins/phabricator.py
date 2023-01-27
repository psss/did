# coding: utf-8
"""
Phabricator stats for authored and reviewed differentials, aka reviews.

Config example::

    [phabricator]
    type = phabricator
    url = https://reviews.llvm.org/api/
    token = <authentication-token>
    token_file = <file-with-authentication-token>
    login = <username1>,<username2>

The authentication token is *not* optional. Go to
https://reviews.llvm.org/settings/user/<username>/page/apitokens/ and
get yourself a "Conduit API token". The token and the actual users for
which we query stats are decoupled, allowing you to specify more than
one username.

We use these endpoints for the most part:

* https://secure.phabricator.com/conduit/method/differential.revision.search/
* https://secure.phabricator.com/conduit/method/transaction.search/
* https://secure.phabricator.com/conduit/method/user.search/

"""  # noqa: W505

import datetime
from enum import Enum
from functools import total_ordering
from multiprocessing import cpu_count
from threading import Thread
from typing import Any, Dict, List, Set
from urllib.parse import urlencode

import requests

from did.base import Config, ConfigError, ReportError, get_token
from did.stats import Stats, StatsGroup
from did.utils import listed, log, pretty

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Phabricator:
    """ Phabricator Investigator """

    # Maximum number of entries to be fetched per page
    # See "Paging and Limits" section here for example:
    # https://reviews.llvm.org/conduit/method/differential.revision.search/
    MAX_PAGE_SIZE = 100

    def __init__(self, url, token, logins):
        """ Initialize url and headers """
        self.url = url.rstrip("/")
        self.token = token
        self.logins = logins
        self._login_phids = []

    @property
    def login_phids(self) -> List[str]:
        """
        Returns the PHIDs for the login usernames.

        Returns:
            List[str]: The phabricator PHIDs for the login names

        TODO(kwk): The return type could be just `list[str]` but the
                   Copr epel builder currently only has python 3.6 where
                   this is not possible.
        """
        if self._login_phids is None or self._login_phids == []:
            log.debug("Resolving logins to Phabricator PHIDs: %s", self.logins)
            # Resolve logins to phids for users
            # see https://reviews.llvm.org/conduit/method/user.search/
            url = self.url + "/user.search"
            data_dict = {}
            for idx, login in enumerate(self.logins):
                data_dict[f'constraints[usernames][{idx}]'] = login

            results = self._get_all_pages(url, data_dict)
            self._login_phids = [user["phid"] for user in results]
        return self._login_phids

    def search_diffs(
            self,
            since: datetime.date = None,
            until: datetime.date = None,
            author_phids: List[str] = None,
            subscriber_phids: List[str] = None,
            responsible_phids: List[str] = None,
            reviewer_phids: List[str] = None) -> Set["Differential"]:
        """ Find Phabricator Differentials """
        url = self.url + "/differential.revision.search"
        data_dict = {}
        if author_phids is not None:
            for idx, phid in enumerate(author_phids):
                data_dict[f'constraints[authorPHIDs][{idx}]'] = phid
        if subscriber_phids is not None:
            for idx, phid in enumerate(subscriber_phids):
                data_dict[f'constraints[subscribers][{idx}]'] = phid
        if responsible_phids is not None:
            for idx, phid in enumerate(responsible_phids):
                data_dict[f'constraints[responsiblePHIDs][{idx}]'] = phid
        if reviewer_phids is not None:
            for idx, phid in enumerate(reviewer_phids):
                data_dict[f'constraints[reviewerPHIDs][{idx}]'] = phid
        if since is not None:
            # modifiedStart: Find revisions modified at
            #                or after a particular time.
            data_dict['constraints[modifiedStart]'] = since.strftime("%s")
        if until is not None:
            # createdEnd: Find revisions created at
            #             or before a particular time.
            data_dict['constraints[createdEnd]'] = until.strftime("%s")
        result = (Differential(diff) for diff in self._get_all_pages(url, data_dict))
        log.data(pretty(result))
        return result

    def search_transactions(
            self,
            diff: "Differential",
            author_phids: List[str] = None) -> Set["TransactionEvent"]:
        """
        Returns all the transaction events for a given differential
        object. If given you can search for events by certain authors.
        """
        url = self.url + "/transaction.search"
        data_dict = {}
        data_dict["objectIdentifier"] = diff.phid
        if author_phids is not None:
            for idx, phid in enumerate(set(author_phids)):
                data_dict[f'constraints[authorPHIDs][{idx}]'] = phid
        log.data(pretty(url))
        log.data(pretty(data_dict))
        events = self._get_all_pages(url, data_dict)
        return (TransactionEvent(event) for event in events)

    def _get_all_pages(self, url: str, data_dict: Dict[str, Any]):
        """
        Gets all pages of a Phabricator Conduit API request; given that
        the API is pageable.
        """
        if data_dict is None:
            data_dict = {}
        data_dict['after'] = None
        results = []
        while True:
            if data_dict['after'] is None:
                del data_dict['after']
            res = self._get_page(url, data_dict)
            if "result" not in res:
                raise ReportError("Mising key Phabricator dict: result")
            results.extend(res["result"]["data"])
            # Define offset of next differentials to fetch
            if "cursor" in res["result"]:
                if res["result"]["cursor"]["after"] is None:
                    break
                data_dict['after'] = res["result"]["cursor"]["after"]
            else:
                break
        log.debug("Results: %s fetched", listed(len(results), "item"))
        return results

    def _get_page(self, url: str, data_dict: Dict[str, Any]):
        """
        Gets a single page of a Phabricator Conduit API request
        """
        if data_dict is None:
            data_dict = {}
        if "limit" not in data_dict:
            data_dict['limit'] = Phabricator.MAX_PAGE_SIZE
        if "api.token" not in data_dict:
            data_dict['api.token'] = self.token
        try:
            response = requests.post(url, data=data_dict)
            log.debug("Response headers: %s", response.headers)
            log.debug(f"MANUAL REQ: curl -sL -X POST {url} -d '"
                      f"{urlencode(data_dict)}' | jq .")
        except requests.exceptions.RequestException as error:
            log.debug(error)
            raise ReportError(
                f"Phabricator search on '{url}' failed.") from error

        if response.status_code != 200:
            log.debug("Phabricator status code: {response.status.code}")
            raise RuntimeError(
                "Phabricator request exited with status code "
                f"{response.status_code} rather than 200.")

        try:
            decoded = response.json()
            # Handle API errors
            if decoded["error_info"] is not None:
                raise RuntimeError(
                    f"Phabricator error encountered: {decoded['error_info']}")
        except requests.exceptions.JSONDecodeError as error:
            log.debug(error)
            raise ReportError(
                "Phabricator failed to parse JSON response.") from error
        return decoded


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Differential
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@total_ordering
class Differential:  # pylint: disable=too-few-public-methods
    """
    Phabricator Differential

    Here's an example::

        {
         "id": 134852,
         "type": "DREV",
         "phid": "PHID-DREV-6vyvvzlqatx6a4oveqkw",
         "fields":
         {
          "title": "[clang-format][NFC] Clean up class HeaderIncludes",
          "uri": "https://reviews.llvm.org/D134852",
          "authorPHID": "PHID-USER-vou2cb5rty2zlopptj5z",
          "status":
          {
            "value": "published",
            "name": "Closed",
            "closed": true,
            "color.ansi": "cyan"
          },
          "repositoryPHID": "PHID-REPO-f4scjekhnkmh7qilxlcy",
          "diffPHID": "PHID-DIFF-6qic23rkxpwvkp6g4wdg",
          "summary": "",
          "testPlan": "",
          "isDraft": false,
          "holdAsDraft": false,
          "dateCreated": 1664433452,
          "dateModified": 1665032091,
          "policy":
          {
           "view": "public",
           "edit": "users"
          }
         },
         "attachments": {}
        }

    """

    def __init__(self, data):
        self._phid = data["phid"]
        self._uri = data["fields"]["uri"]
        self._title = data["fields"]["title"]
        self._id = data["id"]
        self.events = set()

    @property
    def phid(self) -> str:
        """
        Returns the Phabricator ID for the differential as a string
        """
        return self._phid

    @property
    def uri(self) -> str:
        """
        Returns the Phabricator URI for the differential as a string
        """
        return self._uri

    @property
    def title(self) -> str:
        """
        Returns the Phabricator title for the differential as a string
        """
        return self._title

    @property
    def id(self) -> str:
        """
        Returns the Phabricator ID for the differential as a string
        """
        return self._id

    def __str__(self):
        """ String representation """
        if DifferentialsBaseStats.verbose:
            return f'{self.uri} - {self.title}'
        return f'D{self.id} - {self.title}'

    def __hash__(self):
        return hash(self.phid)

    def __eq__(self, other):
        if not isinstance(other, Differential):
            return False
        return self.uri == other.uri

    def __lt__(self, other):
        return self.uri < other.uri

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  TransactionEvent
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class EventType(Enum):
    """
    EventType defines what type of transaction events we support.
    """
    ACCEPT = "accept"
    REQUEST_CHANGES = "request-changes"
    COMMENT = "comment"
    INLINE = "inline"
    CREATE = "create"
    CLOSE = "close"
    UPDATE = "update"
    SUMMARY = "summary"
    TITLE = "title"
    PROJECTS = "projects"
    REQUEST_REVIEW = "request-review"
    REVIEWERS = "reviewers"
    SUBSCRIBERS = "subscribers"
    STATUS = "status"
    UNDEFINED = ""

    def __str__(self):
        """ String representation """
        return self.value


class TransactionEvent:
    """
    Phabricator Transaction event.

    See https://reviews.llvm.org/conduit/method/transaction.search/.

    Here're examples::

        {
            "id": 4077171,
            "phid": "PHID-XACT-DREV-7grkcftntvxf24c",
            "type": "create",
            "authorPHID": "PHID-USER-m46saogacat2jslbykue",
            "objectPHID": "PHID-DREV-ypgxje4hhhdefuy4d6sz",
            "dateCreated": 1674573526,
            "dateModified": 1674573526,
            "groupID": "dr3e2g6tx6ztr6zivk343kytk7uk7yng",
            "comments": [],
            "fields": {}
        }

        {
            "id": 4077175,
            "phid": "PHID-XACT-DREV-zconyio2dw2y7ne",
            "type": "reviewers",
            "authorPHID": "PHID-USER-m46saogacat2jslbykue",
            "objectPHID": "PHID-DREV-ypgxje4hhhdefuy4d6sz",
            "dateCreated": 1674573526,
            "dateModified": 1674573526,
            "groupID": "dr3e2g6tx6ztr6zivk343kytk7uk7yng",
            "comments": [],
            "fields": {
                "operations": [
                {
                    "operation": "add",
                    "phid": "PHID-USER-aigeqxvzdke5r36hodix",
                    "oldStatus": null,
                    "newStatus": "added",
                    "isBlocking": false
                },
                {
                    "operation": "add",
                    "phid": "PHID-USER-7rdtwvftotyrjl5bf7gy",
                    "oldStatus": null,
                    "newStatus": "added",
                    "isBlocking": false
                },
                {
                    "operation": "add",
                    "phid": "PHID-USER-icssaf6rtj6ahq4lchay",
                    "oldStatus": null,
                    "newStatus": "added",
                    "isBlocking": false
                }
                ]
            }
        },

    """

    def __init__(self, data):
        self._type = data["type"]
        self._author_phid = data["authorPHID"]
        self._date_modified = data['dateModified']
        self._id = data["id"]

    def is_in_date_range(
            self,
            since: datetime.date = None,
            until: datetime.date = None) -> bool:
        """
        Returns true if the event happend in the given timestamp range,
        including the boundaries.
        """
        date_modified = datetime.date.fromtimestamp(self._date_modified)
        if since is not None:
            if not date_modified >= since:
                return False
        if until is not None:
            if not date_modified <= until:
                return False
        return True

    def is_type(self, event_type: EventType) -> bool:
        """
        Returns true if the transaction refers to an event of the given
        type.
        """
        if event_type == EventType.UNDEFINED:
            if self._type is None or self._type == "":
                return True
            return False
        return self._type == str(event_type)

    @property
    def event_type(self) -> EventType:
        """ Returns the type of event """
        return self._type

    @property
    def author_phid(self) -> str:
        """ Returns the author's PHID """
        return self._author_phid

    def __str__(self):
        """ String representation """
        return f"{self.author_phid} - {self.event_type} - {self._dateModified}"

    def __hash__(self):
        return hash(self._id)

    def __eq__(self, other):
        if not isinstance(other, TransactionEvent):
            return False
        return self._id == other._id

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class DifferentialsBaseStats(Stats):
    """
    Represent the base class of phabricator statistics
    """

    # Shared state for all stats
    got_diffs = False
    diffs_accepted = set()
    diffs_requested_changes = set()
    diffs_commented = set()
    diffs_created = set()
    diffs_closed = set()

    # if stats are supposed to be printed in verbose mode or not.
    verbose = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def fetch(self):
        """ To be implemented by subclasses """
        pass

    def fetch_all_relevant_diffs(self):
        """
        Fetches all differentials that we possibly need for all
        phabricator stats.
        """

        # Update verbosity
        DifferentialsBaseStats.verbose = self.options.verbose

        if DifferentialsBaseStats.got_diffs:
            return
        DifferentialsBaseStats.got_diffs = True
        opts = {
            "since": self.options.since.date,
            "until": self.options.until.date,
            }
        phab = self.parent.phabricator
        diffs = set()
        diffs.update(phab.search_diffs(**opts, author_phids=phab.login_phids))
        diffs.update(phab.search_diffs(**opts, subscriber_phids=phab.login_phids))
        diffs.update(phab.search_diffs(**opts, reviewer_phids=phab.login_phids))
        diffs.update(phab.search_diffs(**opts, responsible_phids=phab.login_phids))

        diff_list = list(diffs)

        def process(diff_list, start, end):
            for diff in diff_list[start:end]:
                diff.events = self.parent.phabricator.search_transactions(
                    diff=diff, author_phids=self.parent.phabricator.login_phids)

        threads = []
        n_jobs = max(cpu_count() * 2 - 2, 1)
        split_size = len(diff_list) // n_jobs
        for i in range(n_jobs):
            # determine the indices of the list this thread will handle
            start = i * split_size
            # special case on the last chunk to account
            # for uneven splits
            end = None if i + 1 == n_jobs else (i + 1) * split_size
            # create the thread
            threads.append(Thread(target=process, args=(diff_list, start, end)))
            threads[-1].start()

        # wait for all threads to finish
        for t in threads:
            t.join()

        for diff in diff_list:
            for event in diff.events:
                if not event.is_in_date_range(
                        self.options.since.date,
                        self.options.until.date):
                    continue
                if event.is_type(EventType.COMMENT) or event.is_type(EventType.INLINE):
                    DifferentialsBaseStats.diffs_commented.add(diff)
                elif event.is_type(EventType.CREATE):
                    DifferentialsBaseStats.diffs_created.add(diff)
                elif event.is_type(EventType.CLOSE):
                    DifferentialsBaseStats.diffs_closed.add(diff)
                elif event.is_type(EventType.ACCEPT):
                    DifferentialsBaseStats.diffs_accepted.add(diff)
                    # NOTE: There's usually also a STATUS event
                    # happening when there's an ACCEPT event but it is
                    # enough to just use the ACCEPT event here.
                elif event.is_type(EventType.REQUEST_CHANGES):
                    DifferentialsBaseStats.diffs_requested_changes.add(diff)


class DifferentialsAccepted(DifferentialsBaseStats):
    """ Differentials accepted """

    def fetch(self):
        log.info("Searching for differentials accepted by '%s'.", self.user)
        self.fetch_all_relevant_diffs()
        self.stats = sorted(DifferentialsBaseStats.diffs_accepted)


class DifferentialsRequestedChanges(DifferentialsBaseStats):
    """ Differentials where changes were requested """

    def fetch(self):
        log.info(
            "Searching for differentials where changes were requested by '%s'.",
            self.user)
        self.fetch_all_relevant_diffs()
        self.stats = sorted(DifferentialsBaseStats.diffs_requested_changes)


class DifferentialsCommented(DifferentialsBaseStats):
    """ Differentials commented """

    def fetch(self):
        log.info("Searching for differentials commented by '%s'.", self.user)
        self.fetch_all_relevant_diffs()
        self.stats = sorted(DifferentialsBaseStats.diffs_commented)


class DifferentialsClosed(DifferentialsBaseStats):
    """ Differentials closed """

    def fetch(self):
        log.info("Searching for differentials closed by '%s'.", self.user)
        self.fetch_all_relevant_diffs()
        self.stats = sorted(DifferentialsBaseStats.diffs_closed)


class DifferentialsCreated(DifferentialsBaseStats):
    """ Differentials created """

    def fetch(self):
        log.info("Searching for differentials created by '%s'.", self.user)
        self.fetch_all_relevant_diffs()
        self.stats = sorted(DifferentialsBaseStats.diffs_created)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class PhabricatorStats(StatsGroup):
    """ Phabricator work """

    # Default order
    order = 360

    def __init__(self, option, name=None, parent=None, user=None):
        StatsGroup.__init__(self, option, name, parent, user)
        config = dict(Config().section(option))

        # Check server url
        if "url" not in config:
            raise ConfigError(
                f"No phabricator url set in the [{option}] section")
        self.url = config["url"]

        # Check authorization token.
        self.token = get_token(config)
        if self.token is None:
            raise ConfigError(
                f"No token or token_file set in the [{option}] section")
        if "login" not in config:
            raise ConfigError(f"No login set in the [{option}] section")
        self.logins = [
            login.strip() for login in str(
                config["login"]).split(",")]
        if self.logins == []:
            raise ConfigError(f"Empty login found in [{option}] setion")
        self.phabricator = Phabricator(self.url, self.token, self.logins)

        # Create the list of stats
        self.stats = [
            DifferentialsCreated(
                option=option + "-differentials-created", parent=self,
                name=f"Differentials created on {option}"),
            DifferentialsAccepted(
                option=option + "-differentials-accepted", parent=self,
                name=f"Differentials accepted on {option}"),
            DifferentialsCommented(
                option=option + "-differentials-commented", parent=self,
                name=f"Differentials commented on {option}"),
            DifferentialsRequestedChanges(
                option=option + "-differentials-changes-requested", parent=self,
                name=f"Differentials for which changes were requested on {option}"),
            DifferentialsClosed(
                option=option + "-differentials-closed", parent=self,
                name=f"Differentials closed on {option}"),
            ]
