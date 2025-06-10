# coding: utf-8
""" Tests for the Sentry plugin """

import logging

import pytest
from _pytest.logging import LogCaptureFixture

import did.base
import did.cli

BASIC_CONFIG = """
[general]
email = "Did Tester" <the.did.tester@gmail.com>

[sentry]
type = sentry
url = https://sentry.io/api/0/
organization = did-tester
"""

BAD_TOKEN_CONFIG = f"""
{BASIC_CONFIG}
token = bad-token
"""
# test token for <the.did.tester@gmail.com>
OK_CONFIG = f"""
{BASIC_CONFIG}
token = 40163646c3aa42d898674d836a1f17595217ccf5f50c409fbd343be72be351b0
"""

# Three issues should be present
INTERVAL = "--since 2023-01-20 --until 2023-01-20"
# No issues should be present
INTERVAL_EMPTY1 = "--since 2023-01-01 --until 2023-01-19"
INTERVAL_EMPTY2 = "--since 2023-01-21 --until 2023-01-30"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Smoke tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_missing_token():
    """ Missing Sentry token results in Exception """
    did.base.Config(BASIC_CONFIG)
    with pytest.raises(did.base.ConfigError):
        did.cli.main(INTERVAL)


def test_invalid_token(caplog: LogCaptureFixture):
    """ Invalid Sentry token """
    did.base.Config(BAD_TOKEN_CONFIG)
    with caplog.at_level(logging.ERROR):
        did.cli.main(INTERVAL)
        assert "Failed to fetch Sentry activities" in caplog.text


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Acceptance tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@pytest.mark.skip("did-tester organization doesn't exist?")
def test_sentry_resolved():
    """ Check expected resolved issues """
    did.base.Config(OK_CONFIG)
    stats = did.cli.main(f"""
        --sentry-resolved {INTERVAL}""")[0][0].stats[0].stats[0].stats
    assert len(stats) == 1
    assert "PYTHON-E - AttributeError" in stats[0]


@pytest.mark.skip("did-tester organization doesn't exist?")
def test_sentry_commented():
    """ Check expected commented issues """
    did.base.Config(OK_CONFIG)
    stats = did.cli.main(f"""
        --sentry-commented {INTERVAL}""")[0][0].stats[0].stats[1].stats
    assert len(stats) == 1
    assert "PYTHON-F - IndexError" in stats[0]


@pytest.mark.skip("did-tester organization doesn't exist?")
def test_sentry_no_issues():
    """ Check for no issues """
    did.base.Config(OK_CONFIG)
    stats = did.cli.main(INTERVAL_EMPTY1)[0][0].stats[0].stats[0].stats
    assert not stats
    stats = did.cli.main(INTERVAL_EMPTY2)[0][0].stats[0].stats[0].stats
    assert not stats
