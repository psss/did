# coding: utf-8
""" Tests for the Zammad plugin """

import pytest

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


def test_missing_url():
    """ Missing Zammad url results in ReportError """
    # using a generic url just to avoid failing on missing url
    did.base.Config(BASIC_CONFIG)
    with pytest.raises(did.base.ReportError, match="No zammad url set in.*"):
        did.cli.main()


def test_wrong_url():
    """ Giving a non-Zammad url results in Exception """
    did.base.Config(BASIC_CONFIG + "url=https://www.google.com")
    with pytest.raises(did.base.ReportError,
                       match="Zammad search on https://www.google.com failed."):
        did.cli.main(INTERVAL)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Acceptance tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
