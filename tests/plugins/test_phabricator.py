# coding: utf-8
""" Tests for the Phabricator plugin """

import os

import pytest

import did.base
import did.cli

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

INTERVAL = "--since 2022-05-01 --until 2022-09-01"

CONFIG_BASE = """
[general]
email = "Jane Doe" <jane@doe.com>
width = 120

[ph]
type = phabricator
"""

URL = "url = https://reviews.llvm.org/api/"
LOGINS = "login = kwk, kkleine"
TOKEN = "token = " + os.getenv(key="PHABRICATOR_TOKEN", default="NoTokenSpecified")

CONFIG_OK = f"""
{CONFIG_BASE}
{URL}
{LOGINS}
{TOKEN}
"""

CONFIG_BAD_MISSING_URL = f"""
{CONFIG_BASE}
{LOGINS}
{TOKEN}
"""

CONFIG_BAD_MISSING_LOGINS = f"""
{CONFIG_BASE}
{URL}
{TOKEN}
"""

CONFIG_BAD_MISSING_TOKEN = f"""
{CONFIG_BASE}
{URL}
{LOGINS}
"""

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Smoke tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def test_missing_url():
    """ Missing phabricator URL results in Exception """
    did.base.Config(CONFIG_BAD_MISSING_URL)
    with pytest.raises(did.base.ConfigError):
        did.cli.main(INTERVAL)


def test_missing_logins():
    """ Missing phabricator logins results in Exception """
    did.base.Config(CONFIG_BAD_MISSING_LOGINS)
    with pytest.raises(did.base.ConfigError):
        did.cli.main(INTERVAL)


def test_missing_token():
    """ Missing phabricator token results in Exception """
    did.base.Config(CONFIG_BAD_MISSING_TOKEN)
    with pytest.raises(did.base.ConfigError):
        did.cli.main(INTERVAL)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Acceptance tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@pytest.mark.skipif("PHABRICATOR_TOKEN" not in os.environ,
                    reason="No PHABRICATOR_TOKEN environment variable found")
def test_differentials_created():
    """ Differentials created """
    did.base.Config(CONFIG_OK)
    # Non verbose search
    option = "--ph-differentials-created "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[0].stats
    needle = "D129553 [standalone-build-x86_64]: build lld"
    assert any([needle in str(stat) for stat in stats])
    # Verbose search (URL is prefixed instead of differential number)
    option = "--ph-differentials-created --verbose "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[0].stats
    needle = "https://reviews.llvm.org/D129553 [standalone-build-x86_64]: build lld"
    assert any([needle in str(stat) for stat in stats])


@pytest.mark.skipif("PHABRICATOR_TOKEN" not in os.environ,
                    reason="No PHABRICATOR_TOKEN environment variable found")
def test_differentials_reviewed():
    """ Differentials reviewed """
    did.base.Config(CONFIG_OK)
    # Non verbose search
    option = "--ph-differentials-reviewed "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[1].stats
    needle = "D99780 workflows: Add GitHub action for automating some release tasks"
    assert any([needle in str(stat) for stat in stats])
    # Verbose search (URL is prefixed instead of differential number)
    option = "--ph-differentials-reviewed --verbose "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[1].stats
    needle = "https://reviews.llvm.org/D99780 workflows: Add GitHub action "\
             "for automating some release tasks"
    assert any([needle in str(stat) for stat in stats])
