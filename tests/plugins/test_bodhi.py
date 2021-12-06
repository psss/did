# coding: utf-8
"""
Tests for the Bodhi plugin

"""

import pytest

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

[bodhi]
type = bodhi
url = https://bodhi.fedoraproject.org/
login = mikelo2
"""

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def test_pagure_issues_created():
    """ Created issues """
    did.base.Config(CONFIG)
    option = "--bodhi-updates-created "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[0].stats
    assert any(["FEDORA-2021-7b8832fad4 - doctl" in str(stat)
               for stat in stats])
    stats = did.cli.main(option + BEFORE)[0][0].stats[0].stats[0].stats
    assert not stats
    stats = did.cli.main(option + AFTER)[0][0].stats[0].stats[0].stats
    assert not stats


def test_pagure_missing_url():
    """ Missing url """
    did.base.Config("[bodhi]\ntype = bodhi")
    with pytest.raises(did.base.ReportError):
        did.cli.main(INTERVAL)
