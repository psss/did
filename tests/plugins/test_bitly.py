# coding: utf-8
""" Tests for the Bitly plugin """

from __future__ import unicode_literals, absolute_import

import pytest

from did.base import ConfigError

BASIC_CONFIG = """
[general]
email = "Chris Ward" <cward@redhat.com>

[bitly]
type = bitly
"""

BAD_TOKEN_CONFIG = BASIC_CONFIG + "\ntoken = bad-token"

INTERVAL = "--since 2015-10-01 --until 2015-10-03"


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

    I haven't found a way to test the user-history API call without a token.
    Can't test that, but we can test that it always fails if token is not
    defined.
    """
    import did
    did.base.Config(BASIC_CONFIG)
    # FIXME: is SystemExit really a reasonable exception?
    # why not let the exception that occured just happen?
    # why the use of sys.exit?
    # Testing required that we check for SystemExit exception
    # even though that's not the actual error that is triggered
    with pytest.raises((SystemExit, ConfigError)):
        did.cli.main(INTERVAL)


def test_invalid_token():
    """ Invalid bitly token """
    import did
    did.base.Config(BAD_TOKEN_CONFIG)
    with pytest.raises((SystemExit, ConfigError)):
        did.cli.main(INTERVAL)
