# coding: utf-8
""" Tests for the Google plugin """

import did.base
import did.cli

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

INTERVAL = "--since 2016-11-07 --until 2016-11-13"
INTERVAL2 = "--since 2018-12-18 --until 2018-12-19"

CONFIG = """
[general]
email = "The Did Tester" <the.did.tester@gmail.com>

[google]
type = google
apps = calendar, tasks
client_id = 389009292292-c130a3j6gpgs4677qlt3qil1kbs6gvel.apps.googleusercontent.com
client_secret = vGlqWk35qnF2pj0qoYxNByrH
storage = tests/plugins/google-api-credentials.json
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_google_events_organized():
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[0].stats
    summaries = [stat["summary"] for stat in stats]
    assert summaries == ['Pick up dry cleaning', 'Dentist']


def test_google_events_attended():
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[1].stats
    summaries = [stat["summary"] for stat in stats]
    assert summaries == ['Party!']


def test_google_tasks_completed():
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL2)[0][0].stats[0].stats[2].stats
    summaries = [stat["title"] for stat in stats]
    assert summaries == ['The First Task']
