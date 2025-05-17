# coding: utf-8
"""
Tests for the Koji plugin
"""

import logging

from _pytest.logging import LogCaptureFixture

import did.base
import did.cli

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

INTERVAL = "--since 2021-10-01 --until 2021-10-12"
BEFORE = "--since 2018-09-01 --until 2018-09-02"
AFTER = "--since 2018-11-27 --until 2018-11-30"

CONFIG = """
[general]
email = "Mikel Olasagasti Uranga" <mikel@olasagasti.info>

[koji]
type = koji
url = https://koji.fedoraproject.org/kojihub
weburl = https://koji.fedoraproject.org/koji
login = mikelo2
"""

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def test_koji_build():
    """ Created issues """
    did.base.Config(CONFIG)
    option = "--koji-builds "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[0].stats
    assert any("doctl-1.65.0-1.fc34" in str(stat) for stat in stats)
    stats = did.cli.main(
        option + INTERVAL + " --format=markdown"
        )[0][0].stats[0].stats[0].stats
    assert any(
        "[doctl-1.65.0-1.fc34](https://koji.fedoraproject.org/"
        in str(stat) for stat in stats)
    stats = did.cli.main(option + BEFORE)[0][0].stats[0].stats[0].stats
    assert not stats
    stats = did.cli.main(option + AFTER)[0][0].stats[0].stats[0].stats
    assert not stats


def test_koji_missing_url(caplog: LogCaptureFixture):
    """ Missing url """
    did.base.Config("""
                    [general]
                    email = "Mikel Olasagasti Uranga" <mikel@olasagasti.info>
                    [koji]
                    type = koji
                    """)
    with caplog.at_level(logging.ERROR):
        did.cli.main(INTERVAL)
        assert "Skipping section koji due to error: No koji url set" in caplog.text
