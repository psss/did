"""
Confluence stats such as created pages and comments

Configuration example (GSS authentication)::

    [confluence]
    type = confluence
    url = https://docs.jboss.org/

Configuration example (basic authentication)::

    [jboss]
    type = confluence
    url = https://docs.jboss.org/
    auth_url = https://docs.jboss.org/rest/auth/latest/session
    auth_type = basic
    auth_username = username
    auth_password = password
    auth_password_file = ~/.did/confluence_password

Notes:

* Optional parameter ``ssl_verify`` can be used to enable/disable
  SSL verification (default: true)
* ``auth_url`` parameter is optional. If not provided,
  ``/step-auth-gss`` endpoint on ``url`` will be used
  for authentication.
* ``auth_type`` parameter is optional, default value is ``gss``.
* ``auth_username``, ``auth_password`` and ``auth_password_file`` are
  only valid for basic authentication, ``auth_password`` or
  ``auth_password_file`` must be provided, ``auth_password`` has a
  higher priority.

Configuration example (token authentication)::

    [redhat-confluence]
    type = confluence
    url = https://spaces.redhat.com/
    auth_url = https://spaces.redhat.com/login.action
    auth_type = token
    token_file = ~/.did/confluence-token
    token_name = did
    token_expiration = 30

Notes:
Either ``token`` or ``token_file`` has to be defined.

token
    Token string directly included in the config.
    Has a higher priority over ``token_file``.

token_file
    Path to the file where the token is stored.

token_expiration
    Print warning if token with provided ``token_name`` expires within
    specified number of ``days``.

token_name
    Name of the token to check for expiration in ``token_expiration``
    days. This has to match the name as seen in your Confluence profile.

It's also possible to set a timeout, if not specified it defaults to
60 seconds.

    timeout = 10
"""

import os
import re
import time
import urllib.parse
from datetime import datetime

import requests
import urllib3
from requests_gssapi import DISABLED, HTTPSPNEGOAuth

from did.base import Config, ReportError, get_token
from did.stats import Stats, StatsGroup
from did.utils import listed, log, pretty, strtobool

# Maximum number of results fetched at once
MAX_RESULTS = 200

# Maximum number of batches
MAX_BATCHES = 500

# Supported authentication types
AUTH_TYPES = ["gss", "basic", "token"]

# Enable ssl verify
SSL_VERIFY = True

# Default number of seconds waiting on Sentry before giving up
TIMEOUT = 60

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Issue Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Confluence():
    """ Confluence investigator """
    # pylint: disable=too-few-public-methods

    @staticmethod
    def search(query, stats, expand=None, timeout=TIMEOUT):
        """ Perform page/comment search for given stats instance """
        log.debug("Search query: %s", query)
        content = []
        # Fetch data from the server in batches of MAX_RESULTS issues
        for batch in range(MAX_BATCHES):
            encoded_query = urllib.parse.urlencode(
                {
                    "cql": query,
                    "limit": MAX_RESULTS,
                    "expand": expand,
                    "start": batch * MAX_RESULTS
                    }
                )
            current_url = f"{stats.parent.url}/rest/api/content/search?{encoded_query}"
            log.debug("Fetching %s", current_url)
            while True:
                try:
                    response = stats.parent.session.get(
                        current_url,
                        timeout=timeout)
                    # Handle the exceeded rate limit
                    if response.status_code == 429:
                        if response.headers.get("X-RateLimit-Remaining") == "0":
                            # Wait at least a second.
                            retry_after = max(int(response.headers["retry-after"]), 1)
                            log.warning("Confluence rate limit exceeded.")
                            log.warning("Sleeping now for %s.",
                                        listed(retry_after, 'second'))
                            time.sleep(retry_after)
                            continue

                    response.raise_for_status()
                except requests.Timeout:
                    log.warning(
                        "Timed out fetching %s",
                        current_url)
                    continue
                except (requests.exceptions.ConnectionError,
                        urllib3.exceptions.NewConnectionError,
                        requests.exceptions.HTTPError
                        ) as error:
                    log.error("Error fetching '%s': %s", current_url, error)
                    raise ReportError(
                        f"Failed to connect to Confluence at {stats.parent.url}."
                        ) from error
                break
            try:
                data = response.json()
            except requests.exceptions.JSONDecodeError as error:
                log.debug(error)
                raise ReportError(
                    f"Confluence JSON failed: {response.text}."
                    ) from error
            if not response.ok:
                try:
                    error = " ".join(data["errorMessages"])
                except KeyError:
                    error = "unknown"
                raise ReportError(
                    f"Failed to fetch confluence data for query '{query}'. "
                    f"The reason was '{response.reason}' "
                    f"and the error was '{error}'.")
            log.debug(
                "Batch %s result: %s fetched",
                batch,
                listed(data["results"], "object")
                )
            log.data(pretty(data))
            content.extend(data["results"])
            # If all issues fetched, we're done
            if data['_links'].get('next') is None:
                break
        return content


class ConfluencePage(Confluence):
    """ Confluence page results """

    def __init__(self, page, url, myformat):
        """ Initialize the page """
        self.title = page['title']
        self.url = f"{url}{page['_links']['webui']}"
        self.format = myformat

    def __str__(self):
        """ Page title for displaying """
        if self.format == "markdown":
            return f"[{self.title}]({self.url})"
        return f"{self.title}"


class ConfluenceComment(Confluence):
    """ Confluence comment results """

    def __init__(self, comment, url, myformat):
        """ Initialize issue """
        # Remove the 'Re:' prefix
        self.title = re.sub('^Re: ', '', comment['title'])
        self.body = comment['body']['editor']['value']
        # Remove html tags
        self.body = re.sub('</p><p>', ' ', self.body)
        self.body = re.sub('<[^<]+?>', '', self.body)
        self.url = url
        self.format = myformat

    def __str__(self):
        """ Confluence title & comment snippet for displaying """
        # TODO: implement markdown output here
        return f"{self.title}: {self.body}"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class PageCreated(Stats):
    """ Created pages """

    def fetch(self):
        log.info("Searching for pages created by %s", self.user)
        query = (
            f"type=page AND creator = '{self.user.login}' "
            f"AND created >= {self.options.since} AND created < {self.options.until}")
        result = Confluence.search(query, self, timeout=self.parent.timeout)
        self.stats = [
            ConfluencePage(
                page,
                self.parent.url,
                self.options.format
                ) for page in result
            ]


class PageModified(Stats):
    """ Modified pages """

    def fetch(self):
        log.info("Searching for pages modified by %s", self.user)
        query = (
            f"type=page AND contributor = '{self.user.login}' "
            f"AND lastmodified >= {self.options.since} "
            f"AND lastmodified < {self.options.until}")
        result = Confluence.search(query, self, timeout=self.parent.timeout)
        self.stats = [
            ConfluencePage(
                page,
                self.parent.url,
                self.options.format
                ) for page in result
            ]


class CommentAdded(Stats):
    def fetch(self):
        log.info("Searching for comments added by %s", self.user)
        query = (
            f"type=comment AND creator = '{self.user.login}' "
            f"AND created >= {self.options.since} AND created < {self.options.until}")
        self.stats = [
            ConfluenceComment(
                comment,
                self.parent.url,
                self.options.format
                ) for comment in Confluence.search(
                query, self, expand="body.editor", timeout=self.parent.timeout)]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class ConfluenceStats(StatsGroup):
    """ Confluence stats """

    # Default order
    order = 600

    def _basic_auth(self, option, config):
        if "auth_username" not in config:
            raise ReportError(f"`auth_username` not set in the [{option}] section")
        self.auth_username = config["auth_username"]
        if "auth_password" in config:
            self.auth_password = config["auth_password"]
        elif "auth_password_file" in config:
            file_path = os.path.expanduser(config["auth_password_file"])
            with open(file_path, encoding="utf-8") as password_file:
                self.auth_password = password_file.read().strip()
        else:
            raise ReportError(
                "`auth_password` or `auth_password_file` must be set "
                f"in the [{option}] section.")

    def _token_auth(self, option, config):
        self.token = get_token(config)
        if self.token is None:
            raise ReportError(
                "The `token` or `token_file` key must be set "
                f"in the [{option}] section.")
        if "token_expiration" in config or "token_name" in config:
            try:
                self.token_expiration = int(config["token_expiration"])
                self.token_name = config["token_name"]
            except KeyError as key_err:
                raise ReportError(
                    "The ``token_name`` and ``token_expiration`` must be set at"
                    f" the same time in [{option}] section.") from key_err
            except ValueError as val_err:
                raise ReportError(
                    "The ``token_expiration`` must contain number, "
                    f"used in [{option}] section.") from val_err
        else:
            self.token_expiration = self.token_name = None

    def _set_ssl_verification(self, config):
        # SSL verification
        if "ssl_verify" in config:
            try:
                self.ssl_verify = strtobool(
                    config["ssl_verify"])
            except Exception as error:
                raise ReportError(
                    f"Error when parsing 'ssl_verify': {error}") from error
        else:
            self.ssl_verify = SSL_VERIFY

    def __init__(self, option, name=None, parent=None, user=None):
        StatsGroup.__init__(self, option, name, parent, user)
        self._session = None
        # Make sure there is an url provided
        config = dict(Config().section(option))
        self.timeout = config.get("timeout", TIMEOUT)
        if "url" not in config:
            raise ReportError(f"No Confluence url set in the [{option}] section")
        self.url = config["url"].rstrip("/")
        # Optional authentication url
        if "auth_url" in config:
            self.auth_url = config["auth_url"]
        else:
            self.auth_url = f"{self.url}/step-auth-gss"
        # Authentication type
        if "auth_type" in config:
            if config["auth_type"] not in AUTH_TYPES:
                raise ReportError(
                    f'Unsupported authentication type: {config["auth_type"]}')
            self.auth_type = config["auth_type"]
        else:
            self.auth_type = "gss"
        # Authentication credentials
        if self.auth_type == "basic":
            self._basic_auth(option, config)
        else:
            if "auth_username" in config:
                raise ReportError(
                    "`auth_username` is only valid for basic authentication "
                    f"(section [{option}])")
            if "auth_password" in config or "auth_password_file" in config:
                raise ReportError(
                    "`auth_password` and `auth_password_file` are only valid for"
                    f" basic authentication (section [{option}])")
        # Token
        self.token_expiration = None
        if self.auth_type == "token":
            self._token_auth(option, config)
        self._set_ssl_verification(config)
        self.login = config.get("login", None)

        # Check for custom prefix
        self.prefix = config["prefix"] if "prefix" in config else None
        # Create the list of stats
        self.stats = [
            PageCreated(
                option=f"{option}-pages-created",
                parent=self,
                name=f"Pages created in {option}"),
            PageModified(
                option=f"{option}-pages-updated",
                parent=self,
                name=f"Pages updated in {option}"),
            CommentAdded(
                option=f"{option}-comments",
                parent=self,
                name=f"Comments added in {option}"),
            ]

    def _basic_auth_session(self):
        log.debug("Connecting to %s for basic auth", self.auth_url)
        basic_auth = (self.auth_username, self.auth_password)
        try:
            response = self._session.get(
                self.auth_url, auth=basic_auth, verify=self.ssl_verify,
                timeout=self.timeout)
        except (requests.exceptions.ConnectionError,
                urllib3.exceptions.NewConnectionError,
                requests.Timeout) as error:
            log.error(error)
            raise ReportError(
                f"Failed to connect to Confluence at {self.auth_url}."
                ) from error
        return response

    def _token_auth_session(self):
        log.debug("Connecting to %s/rest/api/content for token auth", self.url)
        self.session.headers["Authorization"] = f"Bearer {self.token}"
        while True:
            try:
                response = self._session.get(
                    f"{self.url}/rest/api/content",
                    verify=self.ssl_verify,
                    timeout=self.timeout)
            except urllib3.exceptions.ProtocolError as error:
                log.warning(
                    "Confluence server dropped connection with %s, retrying", error)
                continue
            except (requests.exceptions.ConnectionError,
                    urllib3.exceptions.NewConnectionError,
                    requests.Timeout) as error:
                log.error(error)
                raise ReportError(
                    f"Failed to connect to Confluence at {self.auth_url}."
                    ) from error
            break
        return response

    def _gss_api_auth_session(self):
        log.debug("Connecting to %s for gssapi auth", self.auth_url)
        gssapi_auth = HTTPSPNEGOAuth(mutual_authentication=DISABLED)
        try:
            response = self._session.get(
                self.auth_url, auth=gssapi_auth, verify=self.ssl_verify,
                timeout=self.timeout)
        except (requests.exceptions.ConnectionError,
                urllib3.exceptions.NewConnectionError,
                requests.Timeout) as error:
            log.error(error)
            raise ReportError(
                f"Failed to connect to Confluence at {self.auth_url}."
                ) from error
        return response

    @property
    def session(self):
        """ Initialize the session """
        # pylint: disable=too-many-branches
        if self._session is not None:
            return self._session
        self._session = requests.Session()
        # Disable SSL warning when ssl_verify is False
        if not self.ssl_verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        while True:
            if self.auth_type == 'basic':
                response = self._basic_auth_session()
            elif self.auth_type == "token":
                response = self._token_auth_session()
            else:
                response = self._gss_api_auth_session()
            if response.status_code == 429:
                retry_after = 1
                if response.headers.get("X-RateLimit-Remaining") == "0":
                    retry_after = max(int(response.headers["retry-after"]), 1)
                    log.warning("Confluence rate limit exceeded.")
                    log.warning("Sleeping now for %s.",
                                listed(retry_after, 'second'))
                time.sleep(retry_after)
                continue
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as error:
                log.error(error)
                raise ReportError(
                    "Confluence authentication failed. Check credentials or kinit."
                    ) from error
            break
        if self.token_expiration:
            while True:
                try:
                    response = self._session.get(
                        f"{self.url}/rest/pat/latest/tokens",
                        verify=self.ssl_verify,
                        timeout=self.timeout)

                    response.raise_for_status()
                    token_found = None
                    for token in response.json():
                        if token["name"] == self.token_name:
                            token_found = token
                            break
                    if token_found is None:
                        raise ValueError(
                            f"Can't check validity for the '{self.token_name}' "
                            f"token as it doesn't exist.")
                    expiring_at = datetime.strptime(
                        token_found["expiringAt"], r"%Y-%m-%dT%H:%M:%S.%f%z")
                    delta = (
                        expiring_at.astimezone() - datetime.now().astimezone())
                    if delta.days < self.token_expiration:
                        log.warning("Confluence token '%s' expires in %s days.",
                                    self.token_name, delta.days)
                except (requests.exceptions.HTTPError,
                        KeyError, ValueError, requests.Timeout) as error:
                    log.warning(error)
                    time.sleep(1)
                    continue
                break
        return self._session
