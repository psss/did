# coding: utf-8
""" Tests for the Google plugin """

import os
import tempfile
from unittest.mock import patch

import pytest

import did.base
import did.cli
from did.plugins import google

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

INTERVAL = "--since 2016-11-07 --until 2016-11-13"
INTERVAL2 = "--since 2018-12-18 --until 2018-12-19"
EMAIL = "the.did.tester@gmail.com"

CONFIG = f"""
[general]
email = "The Did Tester" <{EMAIL}>

[google]
type = google
apps = calendar, tasks
client_id = 389009292292-c130a3j6gpgs4677qlt3qil1kbs6gvel.apps.googleusercontent.com
client_secret = vGlqWk35qnF2pj0qoYxNByrH
storage = tests/unit/plugins/google-api-credentials.json
"""

FULL_DAY_EVENT_DICT = {
    'kind': 'calendar#event',
    'etag': '"3412057767766000"',
    'id': 'this_does_not_exist_20250217',
    'status': 'confirmed',
    'htmlLink': 'https://www.google.com/calendar/event?eid=this_does_not_exist',
    'created': '2023-07-26T08:08:07.000Z',
    'updated': '2024-01-23T16:54:43.883Z',
    'summary': 'Home',
    'creator': {'email': EMAIL, 'self': True},
    'organizer': {'email': EMAIL, 'self': True},
    'start': {'date': '2025-02-17'},
    'end': {'date': '2025-02-18'},
    'recurringEventId': 'this_does_not_exist',
    'originalStartTime': {'date': '2025-02-17'},
    'transparency': 'transparent',
    'visibility': 'public',
    'iCalUID': 'this_does_not_exist@google.com',
    'sequence': 0,
    'reminders': {'useDefault': False},
    'workingLocationProperties': {'type': 'homeOffice', 'homeOffice': {}},
    'eventType': 'workingLocation'
    }


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Unit Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def test_calendar_full_day_event():
    # Unattended full day event organized by user
    event = google.Event(FULL_DAY_EVENT_DICT, "markdown")
    assert not event.attended_by(EMAIL)
    assert event.created_by(EMAIL)
    assert event.organized_by(EMAIL)
    assert str(event) == "2025-02-17 - *Home*"
    event._format = "text"  # pylint: disable=protected-access
    assert str(event) == "Home"
    attended_event = google.Event(
        FULL_DAY_EVENT_DICT |
        {"attendees": [{"email": EMAIL, "responseStatus": "accepted"}]},
        "markdown"
        )
    assert attended_event.attended_by(EMAIL)


def test_task():
    untitled_task = google.Task({}, "text")
    assert str(untitled_task) == "(No title)"
    assert untitled_task["title"] is None
    titled_task = google.Task({"title": "Task Title"}, "markdown")
    assert str(titled_task) == "Task Title"


def test_empty_google_stats_base():
    """ Tests empty GoogleStatsBase """
    did.base.Config(CONFIG)
    stats = google.GoogleStatsBase("google")
    assert stats.events is None
    assert stats.tasks is None
    with pytest.raises(NotImplementedError):
        stats.fetch()


@patch('oauth2client.client.OAuth2WebServerFlow')
@patch("oauth2client.tools.run_flow")
def test_authorized_http(mock_run_flow, mock_flow):
    config = dict(did.base.Config(CONFIG).section("google"))
    client_id = did.base.get_token(
        config, token_key="client_id", token_file_key="client_id_file")
    client_secret = did.base.get_token(
        config, token_key="client_secret", token_file_key="client_secret_file")
    apps = ["calendar", "tasks"]
    with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8") as file_handle:
        file_handle.flush()
        service = google.authorized_http(
            client_id, client_secret, apps, file=file_handle.name)
        mock_flow.assert_called_once()
        mock_run_flow.assert_called_once()
        assert service
    with tempfile.TemporaryDirectory() as new_cred_dir:
        old_cred_dir = google.CREDENTIAL_DIR
        google.CREDENTIAL_DIR = os.path.join(new_cred_dir, "missing")
        assert not os.path.exists(google.CREDENTIAL_DIR)
        google.authorized_http(client_id, client_secret, apps)
        assert os.path.exists(google.CREDENTIAL_DIR)
        google.CREDENTIAL_DIR = old_cred_dir


def test_google_calendar():
    gcal = google.GoogleCalendar((), None)
    assert gcal


class EventList:
    # pylint: disable=too-few-public-methods
    def execute(self):
        clean = FULL_DAY_EVENT_DICT.copy()
        clean["summary"] = 'Pick up dry cleaning'
        dentist = FULL_DAY_EVENT_DICT.copy()
        dentist["summary"] = 'Dentist'
        return {
            "items": [clean, dentist]
            }


class Events:
    # pylint: disable=too-few-public-methods
    def list(self, **kwargs):  # pylint: disable=unused-argument
        return EventList()


class MockedService:

    # pylint: disable=unused-argument
    def tasks(self, **kwargs):
        return Events()

    # pylint: disable=unused-argument
    def events(self, **kwargs):
        return Events()


@patch('oauth2client.client.OAuth2WebServerFlow')
@patch("oauth2client.tools.run_flow")
@patch('googleapiclient.discovery.build')
def test_google_events_organized(mock_build, _mock_flow, _mock_run_flow):  # noqa: PT019
    mock_build.return_value = MockedService()
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[0].stats
    summaries = [stat["summary"] for stat in stats]
    assert summaries == ['Pick up dry cleaning', 'Dentist']

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Functional Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@pytest.mark.functional
def test_google_events_organized_functional():
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[0].stats
    summaries = [stat["summary"] for stat in stats]
    assert summaries == ['Pick up dry cleaning', 'Dentist']


@pytest.mark.functional
def test_google_events_attended():
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[1].stats
    summaries = [stat["summary"] for stat in stats]
    assert summaries == ['Party!']


@pytest.mark.functional
def test_google_tasks_completed():
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL2)[0][0].stats[0].stats[2].stats
    summaries = [stat["title"] for stat in stats]
    assert summaries == ['The First Task']
