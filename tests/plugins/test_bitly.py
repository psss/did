# coding: utf-8
""" Tests for the Bitly plugin """

from __future__ import unicode_literals, absolute_import

import pytest

from bitly_api import BitlyError

import did.base
import did.cli
import did.plugins

BASIC_CONFIG = """
[general]
email = "Chris Ward" <cward@redhat.com>

[bitly]
type = bitly
"""

BAD_TOKEN_CONFIG = BASIC_CONFIG + "\ntoken = bad-token"
# test token created by "Chris Ward" <kejbaly2+did@gmail.com>
OK_CONFIG = BASIC_CONFIG + "\ntoken = 77912602cc1d712731b2d8a2810cf8500d2d0f89"

# one link should be present
INTERVAL = "--since 2015-10-06 --until 2015-10-07 --bitly"
# No links should be present
INTERVAL1 = "--since 2015-10-07 --until 2015-10-08 --bitly"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Smoke tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_import():
    """  Test basic module import """
    from did.plugins.bitly import BitlyStats
    assert BitlyStats


def test_missing_token():
    """
    Missing bitly token results in Exception
    """
    with pytest.raises(did.base.ConfigFileError):
        did.cli.main(INTERVAL, BASIC_CONFIG)


def test_invalid_token():
    """ Invalid bitly token """
    with pytest.raises(BitlyError):
        did.cli.main(INTERVAL, BAD_TOKEN_CONFIG)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Acceptance tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_bitly_saved():
    """ Check expected saved links are returned """
    result = did.cli.main(INTERVAL, OK_CONFIG)
    stats = result[0][0].stats[0].stats[0].stats
    _m = (
        "http://bit.ly/kejbaly2_roreilly_innerwars_reddit - "
        "Quest to decode and play my brother's INNER WARS album : bucketlist"
    )
    assert len(stats) == 1
    assert stats[0] == _m
