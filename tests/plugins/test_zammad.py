# coding: utf-8
""" Tests for the Zammad plugin """

import logging

from _pytest.logging import LogCaptureFixture

import did.base
import did.cli

BASIC_CONFIG = """
[general]
email = "Did Tester" <the.did.tester@gmail.com>

[zammad]
type = zammad
"""

INTERVAL = "--since 2023-01-23 --until 2023-01-29"

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Smoke tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def test_missing_url(caplog: LogCaptureFixture):
    """ Missing Zammad url results in Error logged """
    # using a generic url just to avoid failing on missing url
    did.base.Config(BASIC_CONFIG)
    with caplog.at_level(logging.ERROR):
        did.cli.main(INTERVAL)
        assert "Skipping section zammad due to error: No zammad url set" in caplog.text


def test_wrong_url(caplog: LogCaptureFixture):
    """ Giving a non-Zammad url results in Exception """
    did.base.Config(BASIC_CONFIG + "url=https://www.google.com")
    with caplog.at_level(logging.ERROR):
        did.cli.main(INTERVAL)
        assert "Zammad search on https://www.google.com failed." in caplog.text


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Acceptance tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
