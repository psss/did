
"""
Google stats such as attended events or completed tasks

Config example::

    [google]
    type = google
    client_id = <client_id>
    client_secret = <client_secret>
    apps = calendar,tasks
    storage = ~/.did/google-api-credentials.json
    skip = ["Lunch break", "Status deadline"]

Make sure you have additional dependencies of the google plugin
installed on your system::

    sudo dnf install python3-google-api-client python3-oauth2client  # dnf
    pip install did[google]                                          # pip

To retrieve data via Google API, you will need to create access
credentials (``client_id`` and ``client_secret``) first. Perform the
following steps to create such a pair:

    1. Open https://console.developers.google.com/flows/enableapi?apiid=calendar,tasks
    2. You will need to create new project first, select organization
       and location for it
    3. Enable both APIs (tasks and calendar) on the next page after you
       confirm
    4. From the left tab go to 'APIs & Services' and 'OAuth consent
       screen'
    5. In *What data will you be accessing?*, choose *User data*
    6. In there create new and fill at least an app name and emails
    7. On the next page select all scopes or at least all relevant to
       calendar and tasks, you will need to go through all the pages
    8. Save it and go to 'Credentials' tab
    9. Select 'Create credentials' and choose 'OAuth client ID'
    10. Choose app type, doesn't matter but Desktop is likely the
        correct choice and add a name
    11. With that created you will be presented with ``client_id`` and
        ``client_secret`` which you can save into your config file

The ``apps`` configuration option defines the scope of user data the
application will request (read-only) access to. Currently, the only
supported values are ``calendar`` and ``tasks``.

During the first run, user will be asked to grant the plugin access
rights to selected apps. If the user approves the request, this decision
is remembered by creating a *credential storage* file. The path to the
storage can be customized by configuring the ``storage`` option.

If you want to store the ``client_id`` and ``client_secret`` not as
plain text within your config file, use ``client_id_file`` and
``client_secret_file`` to point to files with the corresponding files.
"""  # noqa: W505

import os
from typing import Optional

import httplib2
# FIXME: https://github.com/psss/did/issues/415
import oauth2client.client  # type: ignore[import-untyped]
from googleapiclient import discovery  # type: ignore[import-untyped]
from oauth2client import tools
from oauth2client.file import Storage  # type: ignore[import-untyped]

from did.base import CONFIG, Config, get_token
from did.stats import Stats, StatsGroup
from did.utils import log, split

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

    Try fetching valid user credentials from storage. If nothing has
    been stored, or if the stored credentials are invalid, complete the
    OAuth2 flow to obtain new credentials.
    """
    if not os.path.exists(CREDENTIAL_DIR):
        os.makedirs(CREDENTIAL_DIR)

    credential_path = file or CREDENTIAL_PATH
    storage = Storage(credential_path)
    credentials = storage.get()

    scopes = {f"https://www.googleapis.com/auth/{app}.readonly" for app in apps}

    if (not credentials or credentials.invalid
            or not scopes <= credentials.scopes):
        flow = oauth2client.client.OAuth2WebServerFlow(
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

class GoogleCalendar():
    """ Google Calendar functions """
    # pylint: disable=too-few-public-methods

    def __init__(self, http_credentials, parent):
        self._credentials = http_credentials
        self.parent = parent

    def events(self, **kwargs):
        """ Fetch events meeting specified criteria """
        http = authorized_http(*self._credentials)
        service = discovery.build("calendar", "v3", http=http)
        # pylint: disable=no-member
        events_result = service.events().list(**kwargs).execute()
        # pylint: enable=no-member
        return [Event(event, self.parent.options.format)
                for event in events_result.get("items", [])]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Event
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Event():
    """ Google Calendar Event """

    def __init__(self, in_dict: dict, out_format: str):
        """ Create Event object from dict returned by Google API """
        self.__dict__ = in_dict
        self._format = out_format

    def __str__(self):
        """ String representation """
        # undefined properties are provided via __getitem__
        # pylint: disable=E1101
        if self._format == "markdown":
            date = (
                self.start["date"]
                if "date" in self.start
                else self.start["dateTime"][:10]
                )
            return f"{date} - *{self.summary}*"
        # plain text
        return self.summary

    def __getitem__(self, name: str):
        return self.__dict__.get(name, None)

    def created_by(self, email: str) -> bool:
        """ Check if user created the event """
        return self["creator"]["email"] == email

    def organized_by(self, email: str) -> bool:
        """ Check if user created the event """
        return self["organizer"]["email"] == email

    def attended_by(self, email: str) -> bool:
        """ Check if user attended the event """
        for attendee in self["attendees"] or []:
            if (attendee["email"] == email
                    and attendee["responseStatus"] == "accepted"):
                return True
        return False


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Google Tasks
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GoogleTasks():
    """ Google Tasks functions """
    # pylint: disable=too-few-public-methods

    def __init__(self, http_credentials, parent):
        self._credentials = http_credentials
        self.parent = parent

    def tasks(self, **kwargs):
        """ Fetch tasks specified criteria """
        http = authorized_http(*self._credentials)
        service = discovery.build("tasks", "v1", http=http)
        # pylint: disable=no-member
        tasks_result = service.tasks().list(**kwargs).execute()
        # pylint: enable=no-member
        return [Task(task, self.parent.options.format)
                for task in tasks_result.get("items", [])]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Task
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Task():
    """ Google Tasks task """

    def __init__(self, in_dict: dict, out_format: str):
        """ Create Task object from dict returned by Google API """
        self.__dict__ = in_dict
        self._format = out_format

    def __str__(self):
        """ String representation """
        # TODO: decide if there's something different we want
        #       to return in markdown
        return self.title if hasattr(self, "title") else "(No title)"

    def __getitem__(self, name: str):
        return self.__dict__.get(name, None)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GoogleStatsBase(Stats):
    """ Base class containing common code """

    def __init__(self, option: str, name=None, parent: Optional[StatsGroup] = None):
        super().__init__(option=option, name=name, parent=parent)
        try:
            if self.options is None:
                raise AttributeError("parent not ready yet")
            self.since = f"{self.options.since.datetime.isoformat()}Z"
            self.until = f"{self.options.until.datetime.isoformat()}Z"
        except AttributeError:
            log.debug("Failed to initialize time range, skipping")
        self._events = None
        self._tasks = None

    @property
    def events(self):
        """ All events in calendar within specified time range """
        if self._events is None and self.parent is not None:
            log.debug("Fetching calendar events since %s until %s",
                      self.since, self.until)
            self._events = self.parent.calendar.events(
                calendarId="primary", singleEvents=True, orderBy="startTime",
                timeMin=self.since, timeMax=self.until)
            self._events = [event for event in self._events
                            if str(event.summary) not in self.parent.skip]
        return self._events

    @property
    def tasks(self):
        """ All completed tasks within specified time range """
        if self._tasks is None and self.parent is not None:
            self._tasks = self.parent.tasks.tasks(
                tasklist="@default", showCompleted="true", showHidden="true",
                completedMin=self.since, completedMax=self.until)
        if self._tasks is not None:
            log.info("NB TASKS %s", len(self._tasks))
        return self._tasks

    def fetch(self):
        """ Fetch the stats (to be implemented by respective class). """
        raise NotImplementedError()


class GoogleEventsOrganized(GoogleStatsBase):
    """ Events organized """

    def fetch(self):
        log.info("Searching for events organized by %s", self.user)
        self.stats = [
            event for event in self.events
            if event.organized_by(self.user.email)
            ]


class GoogleEventsAttended(GoogleStatsBase):
    """ Events attended """

    def fetch(self):
        log.info("Searching for events attended by %s", self.user)
        self.stats = [
            event for event in self.events
            if event.attended_by(self.user.email)
            ]


class GoogleTasksCompleted(GoogleStatsBase):
    """ Tasks completed """

    def fetch(self):
        log.info("Searching for completed tasks by %s", self.user)
        self.stats = self.tasks


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Google Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GoogleStatsGroup(StatsGroup):
    """ Google stats group """

    # Default order
    order = 50

    def __init__(self, option, name=None, parent=None, user=None):
        super().__init__(option, name, parent, user)
        config = dict(Config().section(option))
        client_id = get_token(
            config, token_key="client_id", token_file_key="client_id_file")
        client_secret = get_token(
            config,
            token_key="client_secret",
            token_file_key="client_secret_file")
        storage = config.get("storage")
        if storage is not None:
            storage = os.path.expanduser(storage)
        try:
            apps = [app.lower() for app in split(config["apps"])]
        except KeyError:
            apps = DEFAULT_APPS
        self.skip = config.get("skip", [])

        http_credentials = (client_id, client_secret, apps, storage)
        self.calendar = GoogleCalendar(http_credentials, self)
        self.tasks = GoogleTasks(http_credentials, self)

        self.stats = [
            GoogleEventsOrganized(
                option=f"{option}-events-organized", parent=self),
            GoogleEventsAttended(
                option=f"{option}-events-attended", parent=self),
            GoogleTasksCompleted(
                option=f"{option}-tasks-completed", parent=self),
            ]
