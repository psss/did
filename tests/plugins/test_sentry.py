# coding: utf-8
""" Tests for the Sentry plugin """

from __future__ import unicode_literals, absolute_import

import pytest

import did.cli
import did.base

BASIC_CONFIG = """
[general]
email = "Test Foo" <sentrydidplugin@gmail.com>

[sentry]
type = sentry
url = http://sentry.io/api/0/
organization = test-foo
"""

BAD_TOKEN_CONFIG = BASIC_CONFIG + "\ntoken = bad-token"
# test token for <sentrydidplugin@gmail.com>
OK_CONFIG = BASIC_CONFIG + \
    "\ntoken = 8d98bfcf781441aaa3a1ecda412ded0117f5ce0c2a4941a9bd8b3a2d62f77b6c"

# 6 issues should be present
INTERVAL = "--since 2017-09-04 --until 2017-09-10"
# No links should be present
INTERVAL_EMPTY = "--since 2017-09-11 --until 2017-09-17"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Smoke tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_missing_token():
    """ Missing Sentry token results in Exception """
    did.base.Config(BASIC_CONFIG)
    with pytest.raises(did.base.ConfigError):
        did.cli.main(INTERVAL)


def test_invalid_token():
    """ Invalid Sentry token """
    did.base.Config(BAD_TOKEN_CONFIG)
    with pytest.raises(did.base.ReportError):
        did.cli.main(INTERVAL)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Acceptance tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_sentry_assigned():
    """ Check expected assigned issues """
    did.base.Config(OK_CONFIG)
    stats = did.cli.main("""
        --sentry-assigned {0}""".format(INTERVAL))[0][0].stats[0].stats[0].stats
    _m = [
        'TESTPROJECT-4 - Test issue only assigned',
        'TESTPROJECT-1 - Test issue'
    ]
    assert len(stats) == 2
    assert stats[0] == _m[0]


def test_sentry_resolved():
    """ Check expected resolved issues """
    did.base.Config(OK_CONFIG)
    stats = did.cli.main("""
        --sentry-resolved {0}""".format(INTERVAL))[0][0].stats[0].stats[1].stats
    _m = [
        'TESTPROJECT-3 - Test issue only resolved',
        'TESTPROJECT-1 - Test issue'
    ]
    assert len(stats) == 2
    assert stats[0] == _m[0]


def test_sentry_commented():
    """ Check expected commented issues """
    did.base.Config(OK_CONFIG)
    stats = did.cli.main("""
        --sentry-commented {0}""".format(INTERVAL))[0][0].stats[0].stats[2].stats
    _m = [
        'TESTPROJECT-2 - Test issue only commented',
        'TESTPROJECT-1 - Test issue'
    ]
    assert len(stats) == 2
    assert stats[0] == _m[0]


def test_sentry_no_issues():
    """ Check for no issues """
    did.base.Config(OK_CONFIG)
    stats = did.cli.main(INTERVAL_EMPTY)[0][0].stats[0].stats[0].stats
    assert not stats