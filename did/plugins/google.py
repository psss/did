# coding: utf-8

"""
Google Apps stats such as attended events or sent emails

Config example::

    [google]
    type = google
    client_id = <client_id>
    client_secret = <client_secret>
    apps = calendar
    storage = /home/diduser/.did/google-api-credentials.json

To retrieve data via Google API, you will need to create access credentials
(``client_id`` and ``client_secret``) first. Perform the following steps to
create such a pair:

    1. Open https://console.developers.google.com/flows/enableapi?apiid=calendar
    2. In the drop-down menu, select *Create project* and click *Continue*
    3. Click *Go to credentials*
    4. In the *Where will you be calling the API from?* drop-down menu, choose
       *Other UI (e.g. Windows, CLI tool)*
    5. In *What data will you be accessing?*, choose *User data*
    6. Click *What credentials do I need?*
    7. Input 'did credentials' in the *Name* field and click *Create client ID*
    8. In *Product name shown to users*, type 'did'
    9. Click *Continue*, then *Done*
    10. Click the *did credentials* link to display the credentials

The ``apps`` configuration option defines the scope of user data the
application will request (read-only) access to. Currently, the only supported
value is ``calendar``.

During the first run, user will be asked to grant the plugin access rights to
selected apps. If the user approves the request, this decision is remembered by
creating a *credential storage* file. The path to the storage can be customized
by configuring the ``storage`` option.
"""

import os
import httplib2

from apiclient import discovery
from oauth2client import tools
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow

from did.base import Config, ReportError, CONFIG
from did.utils import log, pretty, listed, split
from did.stats import Stats, StatsGroup

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DEFAULT_APPS = ["calendar"]

REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"

CREDENTIAL_DIR = CONFIG
CREDENTIAL_FILE = "google-api-credentials.json"
CREDENTIAL_PATH = os.path.join(CREDENTIAL_DIR, CREDENTIAL_FILE)

USER_AGENT = "did"

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Authorized HTTP session
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def authorized_http(client_id, client_secret, apps, file=None):
    """
    Start an authorized HTTP session.

    Try fetching valid user credentials from storage. If nothing has been
    stored, or if the stored credentials are invalid, complete the OAuth2 flow
    to obtain new credentials.
    """
    if not os.path.exists(CREDENTIAL_DIR):
        os.makedirs(CREDENTIAL_DIR)

    credential_path = file or CREDENTIAL_PATH
    storage = Storage(credential_path)
    credentials = storage.get()

    scopes = set([
        "https://www.googleapis.com/auth/{0}.readonly".format(app)
        for app in apps
        ])

    if (not credentials or credentials.invalid
            or not scopes <= credentials.scopes):
        flow = OAuth2WebServerFlow(
            client_id=client_id,
            client_secret=client_secret,
            scope=scopes,
            redirect_uri=REDIRECT_URI)
        flow.user_agent = USER_AGENT

        # Do not parse did command-line options by OAuth client
        flags = tools.argparser.parse_args(args=[])
        credentials = tools.run_flow(flow, storage, flags)

    return credentials.authorize(httplib2.Http())

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Google Calendar
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GoogleCalendar(object):
    """ Google Calendar functions """
    def __init__(self, http):
        self.service = discovery.build("calendar", "v3", http=http)

    def events(self, **kwargs):
        """ Fetch events meeting specified criteria """
        events_result = self.service.events().list(**kwargs).execute()
        return [Event(event) for event in events_result.get("items", [])]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Event
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Event(object):
    """ Googe Calendar Event """
    def __init__(self, dict):
        """ Create Event object from dictionary returned by Google API """
        self.__dict__ = dict

    def __unicode__(self):
        """ String representation """
        return self.summary if hasattr(self, "summary") else "(No title)"

    def __getitem__(self, name):
        return self.__dict__.get(name, None)

    def created_by(self, email):
        """ Check if user created the event """
        return self["creator"]["email"] == email

    def organized_by(self, email):
        """ Check if user created the event """
        return self["organizer"]["email"] == email

    def attended_by(self, email):
        """ Check if user attended the event """
        for attendee in self["attendees"] or []:
            if (attendee["email"] == email
                    and attendee["responseStatus"] == "accepted"):
                return True
        return False

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GoogleStatsBase(Stats):
    """ Base class containing common code """
    def __init__(self, option, name=None, parent=None):
        super(GoogleStatsBase, self).__init__(
            option=option, name=name, parent=parent)
        try:
            self.since = self.options.since.datetime.isoformat() + "Z"
            self.until = self.options.until.datetime.isoformat() + "Z"
        except AttributeError:
            log.debug("Failed to initialize time range, skipping")
        self._events = None

    @property
    def events(self):
        """ All events in calendar within specified time range """
        if self._events is None:
            self._events = self.parent.calendar.events(
                calendarId="primary", singleEvents=True, orderBy="startTime",
                timeMin=self.since, timeMax=self.until)
        return self._events

class GoogleEventsOrganized(GoogleStatsBase):
    """ Events organized """
    def fetch(self):
        log.info(u"Searching for events organized by {0}".format(self.user))
        self.stats = [
            event for event in self.events
            if event.organized_by(self.user.email)
            ]

class GoogleEventsAttended(GoogleStatsBase):
    """ Events attended """
    def fetch(self):
        log.info(u"Searching for events attended by {0}".format(self.user))
        self.stats = [
            event for event in self.events
            if event.attended_by(self.user.email)
            ]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Google Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GoogleStatsGroup(StatsGroup):
    """ Google stats group """

    # Default order
    order = 50

    def __init__(self, option, name=None, parent=None, user=None):
        super(GoogleStatsGroup, self).__init__(option, name, parent, user)
        config = dict(Config().section(option))
        client_id = config["client_id"]
        client_secret = config["client_secret"]
        storage = config.get("storage")
        try:
            apps = [app.lower() for app in split(config["apps"])]
        except KeyError:
            apps = DEFAULT_APPS

        http = authorized_http(client_id, client_secret, apps, storage)
        self.calendar = GoogleCalendar(http)

        self.stats = [
            GoogleEventsOrganized(
                option=option + "-events-organized", parent=self),
            GoogleEventsAttended(
                option=option + "-events-attended", parent=self),
            ]
