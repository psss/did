# coding: utf-8
""" Tests for the Google plugin """

from __future__ import unicode_literals, absolute_import

import pytest
import did.cli
import did.base


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

INTERVAL = "--since 2016-11-07 --until 2016-11-13"

CONFIG = """
[general]
email = "Let's Test Did" <letstestdid@gmail.com>

[google]
type = google
client_id = 598386917099-8tnnigaqjdrar7rju9uemgn1stcrlm17.apps.googleusercontent.com
client_secret = uRa81hwB2KA-veOeFthVAS-T
storage = tests/plugins/google-api-credentials.json
"""

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_google_events_organized():
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[0].stats
    summaries = [stat["summary"] for stat in stats]
    assert(summaries == [u'Pick up dry cleaning', u'Dentist'])

def test_google_events_attended():
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[1].stats
    summaries = [stat["summary"] for stat in stats]
    assert(summaries == [u'Party!'])
