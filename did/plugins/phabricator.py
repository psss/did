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

We use this endpoint for the most part
https://reviews.llvm.org/conduit/method/differential.revision.search/.

"""

from typing import Any, Dict, List

import requests

from did.base import Config, ConfigError, ReportError, get_token
from did.stats import Stats, StatsGroup
from did.utils import listed, log, pretty

# Number of differentials to be fetched per page
PER_PAGE = 100

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Phabricator:
    """ Phabricator Investigator """

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
            self._login_phids = self._resolve_logins_to_phids(self.logins)
        return self._login_phids

    def _resolve_logins_to_phids(self, logins: List[str]) -> List[str]:
        """
        Resolves the given login usernames to phabricator PHIDs and
        returns those PHIDs as a list of strings.

        Keyword Arguments:
            logins List[str]: The list of usernames to resolve to PHIDs

        Returns:
            List[str]: The phabricator PHIDs for the login names
        """
        log.debug("Resolving logins to Phabricator PHIDs: %s", logins)
        # Resolve logins to phids for users
        # see https://reviews.llvm.org/conduit/method/user.search/
        url = self.url + "/user.search"
        data = {
            'api.token': self.token,
            }
        for idx, login in enumerate(logins):
            data[f'constraints[usernames][{idx}]'] = login

        try:
            response = requests.post(url, data=data)
            log.debug("Response headers: %s", response.headers)
        except requests.exceptions.RequestException as error:
            log.debug(error)
            raise ReportError(
                f"Phabricator search on '{self.url}' failed.") from error
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
        return [user["phid"] for user in decoded["result"]["data"]]

    def search(self, query, data_dict: Dict[str, Any],
               verbose: bool = False) -> List["Differential"]:
        """ Perform Phabricator query """
        url = self.url + query
        data_dict['api.token'] = self.token
        data_dict['limit'] = PER_PAGE
        data_dict['after'] = None

        result = []
        while True:
            log.debug("Phabricator search")
            try:
                response = requests.post(url, data=data_dict)
                log.debug("Response headers: %s", response.headers)
            except requests.exceptions.RequestException as error:
                log.debug(error)
                raise ReportError(
                    f"Phabricator search on {self.url} failed") from error

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

            res = decoded["result"]
            result.extend(Differential(diff, verbose=verbose) for diff in res["data"])
            # Define offset of next differentials to fetch
            data_dict['after'] = res["cursor"]["after"]
            if data_dict['after'] is None:
                break

        log.debug("Result: %s fetched", listed(len(result), "item"))
        log.data(pretty(result))
        return result


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Differential
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

    def __init__(self, data, verbose: bool = False):
        if verbose:
            self.str = f'{data["fields"]["uri"]} {data["fields"]["title"]}'
        else:
            self.str = f'D{data["id"]} {data["fields"]["title"]}'

    def __str__(self):
        """ String representation """
        return self.str

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class DifferentialsCreated(Stats):
    """ Differentials authored """

    def fetch(self):
        log.info("Searching for differentials created by '%s'.", self.user)
        data_dict = {}
        for idx, login in enumerate(self.parent.phabricator.login_phids):
            data_dict[f'constraints[authorPHIDs][{idx}]'] = login
        data_dict['constraints[createdStart]'] = self.options.since.date.strftime("%s")
        data_dict['constraints[createdEnd]'] = self.options.until.date.strftime("%s")
        self.stats = self.parent.phabricator.search(
            "/differential.revision.search",
            data_dict=data_dict,
            verbose=self.options.verbose)


class DifferentialsReviewed(Stats):
    """ Differentials reviewed """

    def fetch(self):
        log.info("Searching for differentials reviewed by '%s'", self.user)
        data_dict = {}
        for idx, login in enumerate(self.parent.phabricator.login_phids):
            data_dict[f'constraints[reviewerPHIDs][{idx}]'] = login
        data_dict['constraints[modifiedStart]'] = self.options.since.date.strftime("%s")
        data_dict['constraints[modifiedEnd]'] = self.options.until.date.strftime("%s")
        self.stats = self.parent.phabricator.search(
            "/differential.revision.search",
            data_dict=data_dict,
            verbose=self.options.verbose)

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
                name=f"Reviews created on {option}"),
            DifferentialsReviewed(
                option=option + "-differentials-reviewed", parent=self,
                name=f"Reviews participated on {option}"),
            ]
