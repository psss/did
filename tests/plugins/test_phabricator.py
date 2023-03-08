# coding: utf-8
""" Tests for the Phabricator plugin """

import os
import re
from typing import List

import pytest

import did.base
import did.cli

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

INTERVAL = "--since 2023-01-23 --until 2023-01-29"

SEC = "ph"

CONFIG_BASE = f"""
[general]
email = "Jane Doe" <jane@doe.com>
width = 120

[{SEC}]
type = phabricator
"""

URL = "url = https://reviews.llvm.org/api/"
LOGINS = "login = nikic"
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


def get_named_stat(options: str):
    """
    Retrieve the statistics by option name.
    """
    for stat in did.cli.main(f"{options} {INTERVAL}")[0][0].stats[0].stats:
        if stat.option in options:
            assert stat.stats is not None
            return stat.stats
    pytest.fail(reason=f"No stat found with options {options}")


def expect(key: str) -> List[str]:
    """
    Returns the list of sorted Differential IDs for each query key.
    """
    expectations = {
        "created": ["D142438", "D142441", "D142473"],
        "closed": ["D142441", "D142473"],
        "commented": ["D136524", "D137361", "D139441", "D139934", "D140849", "D140850",
                      "D141386", "D141712", "D141823", "D141994", "D142234", "D142255",
                      "D142270", "D142271", "D142292", "D142293", "D142330", "D142345",
                      "D142360", "D142370", "D142373", "D142385", "D142387", "D142390",
                      "D142427", "D142429", "D142441", "D142444", "D142450", "D142451",
                      "D142473", "D142519", "D142542", "D142546", "D142551", "D142580",
                      "D142618", "D142633", "D142680", "D142687", "D142708", "D142721",
                      "D142725", "D142783", "D142787", "D142801", "D142827", "D142828",
                      "D142830", "D142832"],
        "changes-requested": ["D142234", "D142255", "D142293", "D142360", "D142385",
                              "D142429", "D142830"],
        "accepted": ["D136524", "D137361", "D139441", "D139934", "D140849", "D140850",
                     "D141994", "D142270", "D142271", "D142330", "D142370", "D142385",
                     "D142387", "D142390", "D142429", "D142444", "D142450", "D142451",
                     "D142519", "D142633", "D142721", "D142801", "D142827", "D142828"],
        }
    return expectations[key]


@pytest.mark.parametrize(
    "options,expectations",
    [
        ("--ph-differentials-created", expect("created")),
        ("--ph-differentials-closed", expect("closed")),
        ("--ph-differentials-commented", expect("commented")),
        ("--ph-differentials-changes-requested", expect("changes-requested")),
        ("--ph-differentials-created --verbose", expect("created")),
        ("--ph-differentials-closed --verbose", expect("closed")),
        ("--ph-differentials-commented --verbose", expect("commented")),
        ("--ph-differentials-changes-requested --verbose", expect("changes-requested")),
        ],
    )
@pytest.mark.skipif("PHABRICATOR_TOKEN" not in os.environ,
                    reason="No PHABRICATOR_TOKEN environment variable found")
def test_differentials(options, expectations):
    did.base.Config(CONFIG_OK)
    stats = get_named_stat(options)
    assert len(expectations) == len(stats)
    for i, id in enumerate(expectations):
        pattern = f"{id} \\S+"
        if "--verbose" in options:
            pattern = f"https://reviews\\.llvm\\.org/{id} \\S+"
        regex = re.compile(pattern)
        assert regex
        assert regex.match(str(stats[i]))
