# coding: utf-8
"""
Confluence stats such as created pages and comments

Configuration example (GSS authentication)::

    [confluence]
    type =  confluence
    url = https://docs.jboss.org/

Configuration example (basic authentication)::

    [jboss]
    type = confluence
    url = https://docs.jboss.org/
    auth_url = https://docs.jboss.org/rest/auth/latest/session
    auth_type = basic
    auth_username = username
    auth_password = password

Notes:
* Optional parameter ``ssl_verify`` can be used to enable/disable
  SSL verification (default: true)
* ``auth_url`` parameter is optional. If not provided,
  ``url + "/step-auth-gss"`` will be used for authentication.
* ``auth_type`` parameter is optional, default value is 'gss'.
* ``auth_username`` and ``auth_password`` are only valid for
  basic authentication.
"""

from __future__ import absolute_import, unicode_literals

import re
import urllib
import requests
import distutils.util
from requests_gssapi import HTTPSPNEGOAuth, DISABLED
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from did.utils import log, pretty, listed
from did.base import Config, ReportError
from did.stats import Stats, StatsGroup

# Maximum number of results fetched at once
MAX_RESULTS = 1000

# Maximum number of batches
MAX_BATCHES = 100

# Supported authentication types
AUTH_TYPES = ["gss", "basic"]

# Enable ssl verify
SSL_VERIFY = True

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Issue Investigator
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Confluence(object):
    """ Confluence investigator """

    @staticmethod
    def search(query, content_type, stats):
        """ Perform page/comment search for given stats instance """
        log.debug("Search query: {0}".format(query))
        content = []
        expand = None

        if content_type == ConfluenceComment:
            expand = "body.editor"
            query = query + " AND type=comment"
        elif content_type == ConfluencePage:
            query = query + " AND type=page"

        # Fetch data from the server in batches of MAX_RESULTS issues
        for batch in range(MAX_BATCHES):
            response = stats.parent.session.get(
                "{0}/rest/api/content/search?{1}".format(
                    stats.parent.url,
                    urllib.urlencode(
                        {
                            "cql": query,
                            "limit": MAX_RESULTS,
                            "expand": expand,
                            "startAt": batch * MAX_RESULTS,
                        }
                    ),
                )
            )
            data = response.json()
            log.debug(
                "Batch {0} result: {1} fetched".format(
                    batch, listed(data["results"], "title")
                )
            )
            log.data(pretty(data))
            content.extend(data["results"])
            # If all issues fetched, we're done
            if len(data) >= data["size"]:
                break
        ret_data = []
        for c in content:
            if content_type == ConfluenceComment:
                ret_data.append(
                    ConfluenceComment(c["body"]["editor"]["value"], c["title"])
                )
            elif content_type == ConfluencePage:
                ret_data.append(ConfluencePage(c["title"]))
        return ret_data


class ConfluencePage(Confluence):
    """ Confluence page results """

    def __init__(self, title=None):
        """ Initialize issue """
        self.title = title

    def __unicode__(self):
        """  Confluence title for displaying """
        return "{}".format(self.title)


class ConfluenceComment(Confluence):
    """ Confluence comment results """

    def __init__(self, body=None, title=None):
        """ Initialize issue """
        self.title = title
        self.body = body

    def __unicode__(self):
        """ Confluence title & comment snippet for displaying """
        # remove "Re: " and html tags
        return "{}: {}".format(
            self.title[3:], re.sub("<[^<]+?>", "", self.body)
        )


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class PageCreated(Stats):
    """ Created pages """

    def fetch(self):
        log.info("Searching for pages created by {0}".format(self.user))
        query = (
            "creator = '{0}' AND type=page "
            "AND created >= {1} AND created <= {2}".format(
                self.parent.login, self.options.since, self.options.until
            )
        )
        self.stats = Confluence.search(query, ConfluencePage, self)


class CommentAdded(Stats):
    def fetch(self):
        log.info("Searching for comments added by {0}".format(self.user))
        query = (
            "creator = '{0}' AND type=comment "
            "AND created >= {1} AND created <= {2}".format(
                self.parent.login, self.options.since, self.options.until
            )
        )
        self.stats = Confluence.search(query, ConfluenceComment, self)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class ConfluenceStats(StatsGroup):
    """ Confluence stats """

    # Default order
    order = 600

    def __init__(self, option, name=None, parent=None, user=None):
        StatsGroup.__init__(self, option, name, parent, user)
        self._session = None
        # Make sure there is an url provided
        config = dict(Config().section(option))
        if "url" not in config:
            raise ReportError(
                "No Confluence url set in the [{0}] section".format(option)
            )
        self.url = config["url"].rstrip("/")
        # Optional authentication url
        if "auth_url" in config:
            self.auth_url = config["auth_url"]
        else:
            self.auth_url = self.url + "/step-auth-gss"
        # Authentication type
        if "auth_type" in config:
            if config["auth_type"] not in AUTH_TYPES:
                raise ReportError(
                    "Unsupported authentication type: {0}".format(
                        config["auth_type"]
                    )
                )
            self.auth_type = config["auth_type"]
        else:
            self.auth_type = "gss"
        # Authentication credentials
        if self.auth_type == "basic":
            if "auth_username" not in config:
                raise ReportError(
                    "`auth_username` not set in the [{0}] section".format(
                        option
                    )
                )
            self.auth_username = config["auth_username"]
            if "auth_password" not in config:
                raise ReportError(
                    "`auth_password` not set in the [{0}] section".format(
                        option
                    )
                )
            self.auth_password = config["auth_password"]
        else:
            if "auth_username" in config:
                raise ReportError(
                    "`auth_username` is only valid for basic authentication"
                    + " (section [{0}])".format(option)
                )
            if "auth_password" in config:
                raise ReportError(
                    "`auth_password` is only valid for basic authentication"
                    + " (section [{0}])".format(option)
                )
        # SSL verification
        if "ssl_verify" in config:
            try:
                self.ssl_verify = distutils.util.strtobool(
                    config["ssl_verify"]
                )
            except Exception as error:
                raise ReportError(
                    "Error when parsing 'ssl_verify': {0}".format(error)
                )
        else:
            self.ssl_verify = SSL_VERIFY

        self.login = config.get("login", None)
        # Check for custom prefix
        self.prefix = config["prefix"] if "prefix" in config else None
        # Create the list of stats
        self.stats = [
            PageCreated(
                option=option + "-created",
                parent=self,
                name="Confluence pages created in {}".format(option),
            ),
            CommentAdded(
                option=option + "-comment-added",
                parent=self,
                name="Confluence comments added in {}".format(option),
            ),
        ]

    @property
    def session(self):
        """ Initialize the session """
        if self._session is None:
            self._session = requests.Session()
            log.debug("Connecting to {0}".format(self.auth_url))
            # Disable SSL warning when ssl_verify is False
            if not self.ssl_verify:
                requests.packages.urllib3.disable_warnings(
                    InsecureRequestWarning
                )
            if self.auth_type == "basic":
                basic_auth = (self.auth_username, self.auth_password)
                response = self._session.get(
                    self.auth_url, auth=basic_auth, verify=self.ssl_verify
                )
            else:
                gssapi_auth = HTTPSPNEGOAuth(mutual_authentication=DISABLED)
                response = self._session.get(
                    self.auth_url, auth=gssapi_auth, verify=self.ssl_verify
                )
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as error:
                log.error(error)
                raise ReportError(
                    "Confluence authentication failed. Try kinit."
                )
        return self._session
